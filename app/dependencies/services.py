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
    获取TranscriptionService的单例实例
    用于Web API服务，不会预加载模型
    """
    return TranscriptionService(preload_model=False, is_worker=False)

@lru_cache()
def get_worker_transcription_service() -> TranscriptionService:
    """
    获取TranscriptionService的单例实例，用于Celery worker进程
    将预加载large-v3-turbo模型
    """
    return TranscriptionService(preload_model=True, is_worker=True) 