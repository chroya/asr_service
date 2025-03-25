from fastapi import APIRouter
import psutil
from app.api.routes import transcription, web

# 创建主路由器
router = APIRouter()

# 包含其他路由
router.include_router(transcription.router)
# web路由在外面独立悬挂，不寄居于api下
# router.include_router(web.router, prefix="/web", tags=["网页"])

# 健康检查路由
@router.get("/health", tags=["系统"])
async def health_check():
    """系统健康检查"""
    # 读取系统cpu、内存状态
    cpu_percent = psutil.cpu_percent()
    mem_percent = psutil.virtual_memory().percent

    return {'status': 'ok', 'cpu_percent': cpu_percent, 'mem_percent': mem_percent, 'message': '系统正常'}