from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv
from fastapi.responses import RedirectResponse

from app.routes import api_app_router, web_app_router
from app.core.config import settings
from app.utils.logging_config import setup_logging

# 配置日志
setup_logging(log_level=logging.INFO)

logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 创建目录
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.TRANSCRIPTION_DIR, exist_ok=True)

def create_app() -> FastAPI:
    """
    创建FastAPI应用
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="语音转写服务API",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    
    # 设置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 挂载静态文件
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # 挂载API路由
    app.include_router(api_app_router, prefix="/api", tags=["API"])
    app.include_router(web_app_router, prefix="/web", tags=["网页"])
    
    @app.get("/")
    async def root():
        return {"message": "欢迎使用语音转写服务，请访问 /api/docs 查看API文档，或 /demo 使用演示页面"}
    
    @app.get("/demo", response_class=RedirectResponse)
    async def demo():
        return "/static/upload_demo.html"
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False) 