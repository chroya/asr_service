from functools import lru_cache
from typing import Generator

from app.services.task_status_service import TaskStatusService
from app.services.transcription_service import TranscriptionService

@lru_cache()
def get_task_status_service() -> TaskStatusService:
    """
    获取TaskStatusService的单例实例
    """
    return TaskStatusService()

@lru_cache()
def get_transcription_service() -> TranscriptionService:
    """
    获取TranscriptionService的单例实例，启用模型预加载
    """
    return TranscriptionService(preload_model=True) 