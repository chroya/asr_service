import os
import json
import uuid
import logging
import time
import shutil
import asyncio
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.whisperx import WhisperXProcessor
from app.utils.storage import RedisStorage
from app.utils.error_codes import (
    SUCCESS, ERROR_FILE_NOT_FOUND, ERROR_PROCESSING_FAILED, 
    ERROR_MESSAGES, get_error_message
)
from app.schemas.transcription import TranscriptionTask, TranscriptionExtraParams
from app.services.mqtt_service import get_mqtt_service
from app.services.webhook_service import get_webhook_service

logger = logging.getLogger(__name__)

class TranscriptionService:
    """
    转写服务：管理音频转写任务，包括任务创建、获取、删除等操作
    """
    
    def __init__(self):
        """初始化转写服务"""
        # 创建存储目录
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.TRANSCRIPTION_DIR, exist_ok=True)
        
        # 初始化数据存储
        self.storage = RedisStorage(prefix="transcription:")
        
        # 初始化转写处理器
        self.processor = WhisperXProcessor()
    
    def create_task(
        self, 
        task_id: str, 
        file_path: str, 
        result_path: str,
        original_filename: str,
        client_id: str,
        language: Optional[str] = None,
        u_id: Optional[int] = None,
        uuid: Optional[str] = None,
        mode_id: Optional[int] = None,
        ai_mode: Optional[str] = None,
        speaker: bool = False,
        whisper_arch: str = settings.WHISPER_MODEL_NAME
    ) -> TranscriptionTask:
        """
        创建新的转写任务
        
        Args:
            task_id: 任务ID
            file_path: 音频文件路径
            result_path: 结果文件路径
            original_filename: 原始文件名
            client_id: 客户端ID
            language: 音频语言代码（可选）
            u_id: 用户ID
            uuid: 唯一标识符
            mode_id: 模板ID
            ai_mode: AI模式
            speaker: 是否启用说话人分离
            whisper_arch: Whisper架构
            
        Returns:
            TranscriptionTask: 创建的任务信息
        """
        # 创建额外参数
        extra_params = TranscriptionExtraParams(
            u_id=u_id,
            record_file_name=original_filename,
            uuid=uuid,
            task_id=task_id,
            mode_id=mode_id,
            language=language or "auto",
            ai_mode=ai_mode,
            speaker=speaker,
            whisper_arch=whisper_arch
        )
        
        # 创建任务数据
        task = TranscriptionTask(
            task_id=task_id,
            client_id=client_id,
            status="pending",
            filename=original_filename,
            file_path=file_path,
            result_path=result_path,
            language=language,
            created_at=datetime.now().isoformat(),
            extra_params=extra_params.dict() if extra_params else None,
            code=SUCCESS,  # 创建任务时设置为成功状态
            message=get_error_message(SUCCESS),  # 没有错误信息
        )
        
        # 存储任务数据
        self.storage.save(task_id, task.model_dump())
        
        return task
    
    def get_task(self, task_id: str) -> Optional[TranscriptionTask]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            TranscriptionTask: 任务信息，如果不存在则返回None
        """
        task_data = self.storage.get(task_id)
        if not task_data:
            return None
        
        return TranscriptionTask(**task_data)
    
    def update_task(self, task_id: str, **updates) -> Optional[TranscriptionTask]:
        """
        更新任务信息
        
        Args:
            task_id: 任务ID
            **updates: 要更新的字段
            
        Returns:
            TranscriptionTask: 更新后的任务信息，如果不存在则返回None
        """
        task_data = self.storage.get(task_id)
        if not task_data:
            return None
        
        # 更新字段
        for key, value in updates.items():
            task_data[key] = value
        
        # 保存更新后的数据
        self.storage.save(task_id, task_data)
        
        return TranscriptionTask(**task_data)
    
    def delete_task(self, task_id: str) -> bool:
        """
        删除任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功删除
        """
        task = self.get_task(task_id)
        if not task:
            return False
        
        # 删除文件
        if task.file_path and os.path.exists(task.file_path):
            try:
                os.remove(task.file_path)
            except Exception as e:
                logger.error(f"删除任务文件失败 {task_id}: {str(e)}")
        
        # 删除结果文件
        result_path = os.path.join(settings.TRANSCRIPTION_DIR, f"{task_id}.json")
        if os.path.exists(result_path):
            try:
                os.remove(result_path)
            except Exception as e:
                logger.error(f"删除结果文件失败 {task_id}: {str(e)}")
        
        # 删除任务数据
        self.storage.delete(task_id)
        
        return True
    
    def get_client_tasks(self, client_id: str, limit: int = 10, offset: int = 0) -> List[TranscriptionTask]:
        """
        获取客户端的任务列表
        
        Args:
            client_id: 客户端ID
            limit: 返回的最大任务数量
            offset: 偏移量
            
        Returns:
            List[TranscriptionTask]: 任务列表
        """
        # 获取客户端的任务ID列表
        task_ids = self.storage.get_keys("") or []
        
        # 分页
        task_ids = task_ids[offset:offset + limit]
        
        # 获取每个任务的详细信息
        tasks = []
        for task_id in task_ids:
            task = self.get_task(task_id)
            if task:
                tasks.append(task)
        
        # 按创建时间倒序排序
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        
        return tasks
    
    def reset_task(self, task_id: str) -> Optional[TranscriptionTask]:
        """
        重置任务状态，准备重新处理
        
        Args:
            task_id: 任务ID
            
        Returns:
            TranscriptionTask: 重置后的任务信息
        """
        task = self.get_task(task_id)
        if not task:
            return None
        
        # 更新任务状态
        task = self.update_task(
            task_id,
            status="pending",
            progress=0,
            error_message=None,
            result=None,
            started_at=None,
            completed_at=None,
            code=SUCCESS,  # 重置为成功状态码
            message=get_error_message(SUCCESS)  # 清空错误消息
        )
        
        return task
    
    def _update_progress(self, task_id: str, progress: int, message: str) -> None:
        """更新任务进度"""
        self.update_task(
            task_id,
            progress=progress,
            progress_message=message
        )
    
    '''
    同步方法，在celery中使用
    '''
    def process_task_sync(self, task_id: str) -> Dict[str, Any]:
        """
        同步处理转写任务（Celery任务使用）
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict[str, Any]: 处理结果的字典表示
        """
        # 获取任务信息
        task = self.get_task(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return {"status": "failed", "error": "任务不存在"}
        
        # 检查文件是否存在
        if not os.path.exists(task.file_path):
            self.update_task(
                task_id,
                status="failed",
                error_message=ERROR_MESSAGES[ERROR_FILE_NOT_FOUND],
                code=ERROR_FILE_NOT_FOUND,
                message=ERROR_MESSAGES[ERROR_FILE_NOT_FOUND]
            )
            logger.error(f"任务音频文件不存在: {task.file_path}")
            return {"status": "failed", "error": "文件不存在"}
        
        try:
            # 更新任务状态为处理中
            self.update_task(
                task_id,
                status="processing",
                started_at=datetime.now().isoformat()
            )
            
            # 获取额外参数
            language = task.language
            speaker_diarization = task.extra_params.speaker if task.extra_params else False
            whisper_arch = task.extra_params.whisper_arch if task.extra_params else whisper_arch
            
            if task.extra_params and 'language' in task.extra_params:
                language = task.extra_params.get('language')
                
            if task.extra_params and 'speaker' in task.extra_params:
                speaker_diarization = task.extra_params.get('speaker', False)
            
            # 开始处理
            start_time = time.time()
            init_time = time.time() - start_time
            
            # 各阶段时间测量
            model_loading_start = time.time()
            
            # 获取处理器，记录模型加载时间
            model_load_result = self.processor.prepare_model(whisper_arch)
            model_loading_time = time.time() - model_loading_start
            
            logger.info(f"模型加载耗时: {model_loading_time:.2f}秒")
            
            # 开始转写处理
            transcription_start = time.time()
            
            # 调用处理器处理音频
            result_data = self.processor.process_audio(
                task.file_path,
                task.result_path,
                task_id,
                language=language if language != "auto" else None,
                speaker_diarization=speaker_diarization,
                callback=lambda progress, message: self._update_progress(task_id, progress, message),
                whisper_arch=whisper_arch
            )
            
            result, audio_duration, detailed_timings = result_data
            
            # 获取转写和说话人分离的时间（如果有）
            transcription_time = detailed_timings.get('transcription_time', time.time() - transcription_start)
            diarization_time = detailed_timings.get('diarization_time', 0)
            
            # 后处理时间
            post_processing_start = time.time()
            
            # 计算处理时间
            processing_time = time.time() - start_time
            post_processing_time = time.time() - post_processing_start
            
            # 更新任务状态和结果
            self.update_task(
                task_id,
                status="completed",
                result=result,
                completed_at=datetime.now().isoformat(),
                audio_duration=audio_duration,
                processing_time=processing_time,
                progress=100,
                progress_message="处理完成",
                code=SUCCESS,  # 成功状态码
                message=get_error_message(SUCCESS)  # 成功状态消息为空
            )

            # 处理完成的log，包括音频时长、处理耗时
            logger.info(f"Task {task_id} completed. Audio duration: {audio_duration} seconds, Processing time: {processing_time} seconds")
            logger.info(f"Task {task_id} timings: model_loading={model_loading_time:.2f}s, transcription={transcription_time:.2f}s, diarization={diarization_time:.2f}s, post_processing={post_processing_time:.2f}s")
            
            # 发送MQTT通知
            get_mqtt_service().send_transcription_complete(task_id)
            
            # 发送Webhook通知
            webhook_service = get_webhook_service()
            webhook_service.send_transcription_complete(
                extra_params=task.extra_params or {},
                result=result,
                duration=int(audio_duration),
                use_time=int(processing_time)
            )
            
            return {
                "status": "completed",
                "audio_duration": audio_duration,
                "result": result,
                "model_loading_time": model_loading_time,
                "transcription_time": transcription_time,
                "diarization_time": diarization_time,
                "post_processing_time": post_processing_time,
                "total_processing_time": processing_time
            }
                
        except Exception as e:
            # 更新任务状态为失败
            error_message = str(e)
            self.update_task(
                task_id,
                status="failed",
                error_message=error_message,
                completed_at=datetime.now().isoformat(),
                code=ERROR_PROCESSING_FAILED,
                message=get_error_message(ERROR_PROCESSING_FAILED, f"处理失败: {error_message}")
            )
            logger.exception(f"处理任务失败: {task_id} - {error_message}")
            return {"status": "failed", "error": error_message} 