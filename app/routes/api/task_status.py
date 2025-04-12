from fastapi import APIRouter, Query, Depends
from app.services.task_status_service import TaskStatusService
from typing import Dict, Any

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