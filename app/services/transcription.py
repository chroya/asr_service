import os
import json
import uuid
import logging
import time
import shutil
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.whisperx import WhisperXProcessor
from app.utils.storage import RedisStorage
from app.schemas.transcription import TranscriptionTask
from app.services.mqtt_service import mqtt_service

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
        language: Optional[str] = None
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
            
        Returns:
            TranscriptionTask: 创建的任务信息
        """
        # 创建任务数据
        task = TranscriptionTask(
            task_id=task_id,
            client_id=client_id,
            status="pending",
            filename=original_filename,
            file_path=file_path,
            result_path=result_path,
            language=language,
            created_at=datetime.now().isoformat()
        )
        
        # 存储任务数据
        self.storage.save(task_id, task.dict())
        
        # 添加到客户端任务列表
        self._add_to_client_tasks(client_id, task_id)
        
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
        
        # 从客户端任务列表移除
        self._remove_from_client_tasks(task.client_id, task_id)
        
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
        task_ids = self.storage.get(f"client:{client_id}:tasks") or []
        
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
            completed_at=None
        )
        
        return task
    
    async def process_task(self, task_id: str, on_complete: Optional[Callable[[float], None]] = None) -> None:
        """
        处理转写任务
        
        Args:
            task_id: 任务ID
            on_complete: 完成后的回调函数，接收音频时长参数
        """
        # 获取任务信息
        task = self.get_task(task_id)
        if not task:
            logger.error(f"任务不存在: {task_id}")
            return
        
        # 检查文件是否存在
        if not os.path.exists(task.file_path):
            self.update_task(
                task_id,
                status="failed",
                error_message="音频文件不存在"
            )
            logger.error(f"任务音频文件不存在: {task.file_path}")
            return
        
        try:
            # 更新任务状态为处理中
            self.update_task(
                task_id,
                status="processing",
                started_at=datetime.now().isoformat()
            )
            
            # 开始处理
            start_time = time.time()
            result, audio_duration = await self.processor.process_audio(
                task.file_path,
                task.result_path,
                task_id=task_id,
                language=task.language,
                callback=lambda p, m: self._update_progress(task_id, p, m)
            )
            end_time = time.time()
            
            # 处理完成，保存结果
            processing_time = end_time - start_time
            logger.info(f"任务完成 {task_id}: 音频长度={audio_duration}秒, 处理时间={processing_time:.2f}秒")
            
            # 更新任务状态和结果
            self.update_task(
                task_id,
                status="completed",
                completed_at=datetime.now().isoformat(),
                audio_duration=audio_duration,
                processing_time=processing_time,
                result=result
            )
            
            # 构建结果文件路径和文件名
            result_filename = f"{task_id}.json"
            
            # 发送MQTT消息通知
            mqtt_service.send_transcription_complete(task_id, result_filename)
            
            # 调用完成回调
            if on_complete:
                on_complete(audio_duration)
            
        except Exception as e:
            logger.exception(f"处理任务时出错 {task_id}: {str(e)}")
            self.update_task(
                task_id,
                status="failed",
                error_message=str(e)
            )
    
    def _update_progress(self, task_id: str, progress: int, message: str) -> None:
        """更新任务进度"""
        self.update_task(
            task_id,
            progress=progress,
            progress_message=message
        )
    
    def _add_to_client_tasks(self, client_id: str, task_id: str) -> None:
        """将任务添加到客户端任务列表"""
        task_list = self.storage.get(f"client:{client_id}:tasks") or []
        if task_id not in task_list:
            task_list.append(task_id)
            self.storage.save(f"client:{client_id}:tasks", task_list)
    
    def _remove_from_client_tasks(self, client_id: str, task_id: str) -> None:
        """从客户端任务列表中移除任务"""
        task_list = self.storage.get(f"client:{client_id}:tasks") or []
        if task_id in task_list:
            task_list.remove(task_id)
            self.storage.save(f"client:{client_id}:tasks", task_list) 