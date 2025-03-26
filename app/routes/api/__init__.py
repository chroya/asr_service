from fastapi import APIRouter
from app.routes.api import transcription

# 创建API路由器
router = APIRouter()

# 包含其他路由
router.include_router(transcription.router, tags=["语音转写"]) 