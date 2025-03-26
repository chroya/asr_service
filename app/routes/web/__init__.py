from fastapi import APIRouter
from app.routes.web import web

# 创建Web路由器
router = APIRouter()

# 包含web路由
router.include_router(web.router) 