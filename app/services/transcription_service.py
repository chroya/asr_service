import os
import logging
import time
import uuid
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.whisperx import WhisperXProcessor
from app.services.redis_service import RedisService
from app.utils.error_codes import (
     SUCCESS, ERROR_PROCESSING_FAILED, get_error_message
)
from app.schemas.transcription import TranscriptionTask, TranscriptionExtraParams
from app.utils.gpu_monitor import get_gpu_memory_info, get_celery_concurrency

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
        redis_service = RedisService()
        self.storage = redis_service.get_client(prefix="transcription:")
        
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
        mode_id: Optional[int] = None,
        ai_mode: Optional[str] = None,
        speaker: bool = False,
        whisper_arch: str = settings.WHISPER_MODEL_NAME,
        content_id: Optional[str] = None,
        server_id: Optional[str] = None,
        duration: Optional[float] = None,
        file_size: Optional[int] = None,
        jwt_token: Optional[str] = None
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
            mode_id: 模板ID
            ai_mode: AI模式
            speaker: 是否启用说话人分离
            whisper_arch: Whisper架构
            content_id: 内容ID
            server_id: 服务器ID
            file_size: 文件大小（字节）
            jwt_token: JWT令牌（可选）
            
        Returns:
            TranscriptionTask: 创建的任务信息
        """
        # 生成唯一标识符
        uni_key = f"uni_{uuid.uuid4()}"
        
        # 基于uni_key更新结果文件路径
        result_path = os.path.join(settings.TRANSCRIPTION_DIR, f"{uni_key}.json")
        
        # 创建额外参数
        extra_params = TranscriptionExtraParams(
            u_id=u_id,
            record_file_name=original_filename,
            task_id=task_id,
            mode_id=mode_id,
            language=language or "auto",
            ai_mode=ai_mode,
            speaker=speaker,
            whisper_arch=whisper_arch,
            content_id=content_id,
            server_id=server_id,
            duration=duration
        )
        
        # 创建任务数据
        task = TranscriptionTask(
            task_id=task_id,
            uni_key=uni_key,
            client_id=client_id,
            status="pending",
            filename=original_filename,
            file_path=file_path,
            file_size=file_size,
            result_path=result_path,
            language=language,
            created_at=datetime.now().isoformat(),
            extra_params=extra_params.dict() if extra_params else None,
            code=SUCCESS,  # 创建任务时设置为成功状态
            message=get_error_message(SUCCESS),  # 没有错误信息
            jwt_token=jwt_token  # 存储JWT令牌
        )
        
        # 存储任务数据
        self.storage.save(uni_key, task.model_dump())
        
        return task
    
    def get_task(self, uni_key: str) -> Optional[TranscriptionTask]:
        """
        获取任务信息
        
        Args:
            uni_key: 任务唯一标识符
            
        Returns:
            TranscriptionTask: 任务信息，如果不存在则返回None
        """
        task_data = self.storage.get(uni_key)
        if not task_data:
            return None
        
        return TranscriptionTask(**task_data)
    
    def update_task(self, uni_key: str, **updates) -> Optional[TranscriptionTask]:
        """
        更新任务信息
        
        Args:
            uni_key: 任务唯一标识符
            **updates: 要更新的字段
            
        Returns:
            TranscriptionTask: 更新后的任务信息，如果不存在则返回None
        """
        task_data = self.storage.get(uni_key)
        if not task_data:
            return None
        
        # 更新字段
        for key, value in updates.items():
            task_data[key] = value
        
        # 保存更新后的数据
        self.storage.save(uni_key, task_data)
        
        return TranscriptionTask(**task_data)
    
    def delete_task(self, uni_key: str) -> bool:
        """
        删除任务
        
        Args:
            uni_key: 任务唯一标识符
            
        Returns:
            bool: 是否成功删除
        """
        task = self.get_task(uni_key)
        if not task:
            return False
        
        # 删除文件
        if task.file_path and os.path.exists(task.file_path):
            try:
                os.remove(task.file_path)
            except Exception as e:
                logger.error(f"删除任务文件失败 {uni_key}: {str(e)}")
        
        # 删除结果文件，使用uni_key作为文件名
        if task.result_path and os.path.exists(task.result_path):
            try:
                os.remove(task.result_path)
            except Exception as e:
                logger.error(f"删除结果文件失败 {uni_key}: {str(e)}")
        
        # 删除任务数据
        self.storage.delete(uni_key)
        
        return True
    
    def reset_task(self, uni_key: str) -> Optional[TranscriptionTask]:
        """
        重置任务状态，准备重新处理
        
        Args:
            uni_key: 任务唯一标识符
            
        Returns:
            TranscriptionTask: 重置后的任务信息
        """
        task = self.get_task(uni_key)
        if not task:
            return None
        
        # 更新任务状态
        task = self.update_task(
            uni_key,
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
    
    def _update_progress(self, uni_key: str, progress: int, message: str) -> None:
        """更新任务进度"""
        self.update_task(
            uni_key,
            progress=progress,
            progress_message=message
        )
    
    '''
    同步方法，在celery中使用
    '''
    def process_task_sync(self, uni_key: str) -> Dict[str, Any]:
        """
        同步处理转写任务
        
        Args:
            uni_key: 任务唯一标识符
            
        Returns:
            Dict[str, Any]: 处理结果的字典表示
        """
        # 获取任务信息 - 仅用于获取任务参数，不做存在性检查
        task = self.get_task(uni_key)
        
        try:
            # 更新任务状态为处理中
            self.update_task(
                uni_key,
                status="processing",
                started_at=datetime.now().isoformat()
            )
            
            # 获取额外参数
            language = task.language
            speaker_diarization = task.extra_params.speaker if task.extra_params else False
            whisper_arch = task.extra_params.whisper_arch if task.extra_params else settings.WHISPER_MODEL_NAME
            
            if task.extra_params and 'language' in task.extra_params:
                language = task.extra_params.get('language')
                
            if task.extra_params and 'speaker' in task.extra_params:
                speaker_diarization = task.extra_params.get('speaker', False)
            
            # 开始处理
            start_time = time.time()
            
            # 各阶段时间测量
            model_loading_start = time.time()
            
            # 获取处理器，记录模型加载时间
            model_load_result = self.processor.prepare_model(whisper_arch)
            model_loading_time = time.time() - model_loading_start
            
            logger.info(f"模型加载耗时: {model_loading_time:.2f}秒")
            
            # 开始转写处理
            transcription_start = time.time()
            
            # 调用处理器处理音频，使用uni_key作为文件标识符
            result_data = self.processor.process_audio(
                task.file_path,
                task.result_path,
                uni_key,  # 使用uni_key替代task_id
                language=language if language != "auto" else None,
                speaker_diarization=speaker_diarization,
                callback=lambda progress, message: self._update_progress(uni_key, progress, message),
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
            
            # 获取GPU信息和Celery并发数
            total_gpu_memory, free_gpu_memory = get_gpu_memory_info()
            celery_concurrency = get_celery_concurrency()
            
            # 准备额外参数，包含GPU信息和Celery并发数
            extra_params_dict = task.extra_params
            if isinstance(extra_params_dict, dict):
                extra_params_dict.update({
                    "total_gpu_memory": total_gpu_memory,
                    "free_gpu_memory": free_gpu_memory,
                    "oncurrency": celery_concurrency
                })
            
            # 更新任务状态和结果
            self.update_task(
                uni_key,
                status="completed",
                result=result,
                completed_at=datetime.now().isoformat(),
                audio_duration=audio_duration,
                processing_time=processing_time,
                progress=100,
                progress_message="处理完成",
                code=SUCCESS,  # 成功状态码
                message=get_error_message(SUCCESS),  # 成功状态消息为空
                extra_params=extra_params_dict  # 更新额外参数
            )

            # 处理完成的log，包括音频时长、处理耗时和GPU信息
            logger.info(f"Task {uni_key} completed. Audio duration: {audio_duration} seconds, Processing time: {processing_time} seconds")
            logger.info(f"Task {uni_key} timings: model_loading={model_loading_time:.2f}s, transcription={transcription_time:.2f}s, diarization={diarization_time:.2f}s, post_processing={post_processing_time:.2f}s")
            logger.info(f"Task {uni_key} GPU info: total={total_gpu_memory}MB, free={free_gpu_memory}MB, concurrency={celery_concurrency}")
            
            return {
                "status": "completed",
                "code": SUCCESS,
                "audio_duration": audio_duration,
                "result": result,
                "model_loading_time": model_loading_time,
                "transcription_time": transcription_time,
                "diarization_time": diarization_time,
                "post_processing_time": post_processing_time,
                "total_processing_time": processing_time,
                "total_gpu_memory": total_gpu_memory,
                "free_gpu_memory": free_gpu_memory,
                "concurrency": celery_concurrency
            }
                
        except Exception as e:
            # 更新任务状态为失败
            error_message = str(e)
            self.update_task(
                uni_key,
                status="failed",
                error_message=error_message,
                completed_at=datetime.now().isoformat(),
                code=ERROR_PROCESSING_FAILED,
                message=get_error_message(ERROR_PROCESSING_FAILED, f"处理失败: {error_message}")
            )
            logger.exception(f"处理任务失败: {uni_key} - {error_message}")
            return {
                "status": "failed", 
                "error": error_message,
                "code": ERROR_PROCESSING_FAILED
            } 