from fastapi import APIRouter
from app.api.routes import transcription, web

# 创建主路由器
router = APIRouter()

# 包含其他路由
router.include_router(transcription.router)
# 注释掉web路由，web界面通常依赖用户系统
# router.include_router(web.router, prefix="/web", tags=["网页"])

# 健康检查路由
@router.get("/health", tags=["系统"])
async def health_check():
    """系统健康检查"""
    return {"status": "ok"} 