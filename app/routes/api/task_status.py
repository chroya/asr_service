from fastapi import APIRouter, Query, Depends
from app.services.task_status_service import TaskStatusService
from typing import Dict, Any, List, Optional
from app.schemas.transcription import TranscriptionTask

router = APIRouter()

@router.get("/get_task_status", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str = Query(..., description="任务ID"),
    task_status_service: TaskStatusService = Depends()
) -> Dict[str, Any]:
    """
    获取任务状态
    :param task_id: 任务ID
    :param task_status_service: 任务状态服务
    :return: 任务状态信息
    """
    return await task_status_service.get_task_status(task_id)

@router.get("/tasks", response_model=List[TranscriptionTask])
async def list_tasks(
    task_ids: Optional[List[str]] = Query(None, description="任务ID列表，不提供则返回所有任务"),
    limit: int = Query(10, description="每页返回的任务数量"),
    offset: int = Query(0, description="分页偏移量"),
    task_status_service: TaskStatusService = Depends()
) -> List[TranscriptionTask]:
    """
    获取任务列表
    
    Args:
        task_ids: 任务ID列表，不提供则返回所有任务
        limit: 每页返回的任务数量，默认10
        offset: 分页偏移量，默认0
        task_status_service: 任务状态服务
        
    Returns:
        List[TranscriptionTask]: 任务列表
    """
    return await task_status_service.get_tasks(task_ids, limit, offset)

@router.get("/task/{task_id}", response_model=TranscriptionTask)
async def get_task_detail(
    task_id: str,
    task_status_service: TaskStatusService = Depends()
) -> TranscriptionTask:
    """
    获取单个任务的详细信息
    
    Args:
        task_id: 任务ID
        task_status_service: 任务状态服务
        
    Returns:
        TranscriptionTask: 任务详细信息
    """
    return await task_status_service.get_task_detail(task_id) 