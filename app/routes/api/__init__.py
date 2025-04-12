from fastapi import APIRouter
from app.routes.api import transcription
from app.routes.api import task_status

# 创建API路由器
router = APIRouter()

# 包含其他路由
router.include_router(transcription.router, tags=["语音转写"])
router.include_router(task_status.router, tags=["任务状态"]) 