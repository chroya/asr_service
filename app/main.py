from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from dotenv import load_dotenv

from app.api.routes import router as api_router
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

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
    app.include_router(api_router, prefix="/api")
    
    @app.get("/")
    async def root():
        return {"message": "欢迎使用语音转写服务，请访问 /web 使用Web界面或 /api/docs 查看API文档"}
    
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False) 