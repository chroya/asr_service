from fastapi import APIRouter
from app.routes.api import router as api_router
from app.routes.web import router as web_router

# 创建主路由器
api_app_router = APIRouter()
web_app_router = APIRouter()

# 包含子路由
api_app_router.include_router(api_router)
web_app_router.include_router(web_router)

# 健康检查路由
@api_app_router.get("/health", tags=["系统"])
async def health_check():
    """系统健康检查"""
    import psutil
    # 读取系统cpu、内存状态
    cpu_percent = psutil.cpu_percent()
    mem_percent = psutil.virtual_memory().percent

    return {'status': 'ok', 'cpu_percent': cpu_percent, 'mem_percent': mem_percent, 'message': '系统正常'} 