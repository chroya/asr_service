from fastapi import APIRouter, Query, Depends
from typing import Dict, Any, List, Optional

from app.dependencies.services import get_task_status_service
from app.services.task_status_service import TaskStatusService
from app.schemas.transcription import TranscriptionTask

router = APIRouter()

@router.get("/get_task_status", response_model=Dict[str, Any])
async def get_task_status(
    uni_key: str = Query(..., description="任务唯一标识符"),
    task_status_service: TaskStatusService = Depends(get_task_status_service)
) -> Dict[str, Any]:
    """
    获取任务状态
    :param uni_key: 任务唯一标识符
    :param task_status_service: 任务状态服务
    :return: 任务状态信息
    """
    return await task_status_service.get_task_status(uni_key)

@router.get("/tasks", response_model=List[TranscriptionTask])
async def list_tasks(
    uni_keys: Optional[List[str]] = Query(None, description="任务唯一标识符列表，不提供则返回所有任务"),
    limit: int = Query(10, description="每页返回的任务数量"),
    offset: int = Query(0, description="分页偏移量"),
    task_status_service: TaskStatusService = Depends(get_task_status_service)
) -> List[TranscriptionTask]:
    """
    获取任务列表
    
    Args:
        uni_keys: 任务唯一标识符列表，不提供则返回所有任务
        limit: 每页返回的任务数量，默认10
        offset: 分页偏移量，默认0
        task_status_service: 任务状态服务
        
    Returns:
        List[TranscriptionTask]: 任务列表
    """
    return await task_status_service.get_tasks(uni_keys, limit, offset)

@router.get("/task/{uni_key}", response_model=TranscriptionTask)
async def get_task_detail(
    uni_key: str,
    task_status_service: TaskStatusService = Depends(get_task_status_service)
) -> TranscriptionTask:
    """
    获取单个任务的详细信息
    
    Args:
        uni_key: 任务唯一标识符
        task_status_service: 任务状态服务
        
    Returns:
        TranscriptionTask: 任务详细信息
    """
    return await task_status_service.get_task_detail(uni_key) 