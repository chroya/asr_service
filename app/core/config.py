import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Optional

# 加载环境变量
# load_dotenv()

class Settings():
    """应用设置"""
    # 基础设置
    APP_NAME: str = os.getenv("APP_NAME", "ASR Service")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key_change_in_production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    WHISPER_MODEL_NAME: str = os.getenv("WHISPER_MODEL_NAME", "")
    
    # 数据库设置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./asr_service.db")
    
    # Redis设置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    
    # MQTT设置
    # MQTT_BROKER: str = "broker.emqx.io"
    # MQTT_PORT: int = 1883
    # MQTT_USERNAME: str = ""
    # MQTT_PASSWORD: str = ""

    MQTT_CLIENT_ID: str = os.getenv("MQTT_CLIENT_ID", "asr_service_111")
    MQTT_BROKER: str = "s55f779f.ala.cn-hangzhou.emqxsl.cn"
    MQTT_PORT: int = 8883
    MQTT_USERNAME: str = "test2"
    MQTT_PASSWORD: str = "test2"
    MQTT_CERT_PATH: str = os.getenv("MQTT_CERT_PATH", "./cert/emqxsl-ca.crt")
    
    # 文件上传设置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    TRANSCRIPTION_DIR: str = os.getenv("TRANSCRIPTION_DIR", "./transcriptions")
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "250000000"))  # 默认250MB
    
    # 用户限制设置
    DEFAULT_USER_LIMIT_COUNT: int = int(os.getenv("DEFAULT_USER_LIMIT_COUNT", "10"))
    DEFAULT_USER_LIMIT_DURATION: int = int(os.getenv("DEFAULT_USER_LIMIT_DURATION", "600"))  # 单位：秒

    # 云端API设置
    CLOUD_STATS_API_URL: Optional[str] = os.getenv("CLOUD_STATS_API_URL")
    CLOUD_API_KEY: Optional[str] = os.getenv("CLOUD_API_KEY")

    # 文件下载设置
    BASE_URL: str = os.getenv("BASE_URL", "http://150.109.15.121:8000")
    DOWNLOAD_URL_PREFIX: str = os.getenv("DOWNLOAD_URL_PREFIX", "/api/uploadfile/download")

    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局设置实例
settings = Settings() 