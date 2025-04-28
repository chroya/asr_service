import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from typing import Optional

# 加载环境变量
load_dotenv()

class Settings():
    """应用设置"""
    # 基础设置
    APP_NAME: str = os.getenv("APP_NAME", "ASR Service")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    
    # JWT验证服务设置
    JWT_VERIFY_URL: str = os.getenv("JWT_VERIFY_URL", "http://123.57.134.165/api/v1/file/verify")
    JWT_VERIFY_TIMEOUT: int = int(os.getenv("JWT_VERIFY_TIMEOUT", "5"))  # 验证请求超时时间，单位：秒
    JWT_AUTH_ENABLED: bool = os.getenv("JWT_AUTH_ENABLED", "True").lower() in ("true", "1", "t")
    
    # 移除用户认证相关密钥
    # SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret_key_change_in_production")
    # ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    HF_TOKEN: str = os.getenv("HF_TOKEN", "")
    
    # 日志设置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
    LOG_DIR: str = os.getenv("LOG_DIR", "logs")
    LOG_FILE: str = os.getenv("LOG_FILE", "asr_service.log")
    LOG_BACKUP_COUNT: int = int(os.getenv("LOG_BACKUP_COUNT", "72"))  # 3天
    LOG_CONSOLE_OUTPUT: bool = os.getenv("LOG_CONSOLE_OUTPUT", "True").lower() in ("true", "1", "t")
    LOG_ALWAYS_TO_FILE: bool = os.getenv("LOG_ALWAYS_TO_FILE", "True").lower() in ("true", "1", "t")  # 在supervisor环境中是否仍输出到文件
    
    # Redis设置
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_DB_CELERY: int = int(os.getenv("REDIS_DB_CELERY", "1")) # celery使用
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    
    # MQTT设置
    MQTT_CLIENT_ID: str = os.getenv("MQTT_CLIENT_ID", "asr_service_111")
    MQTT_BROKER: str = "s55f779f.ala.cn-hangzhou.emqxsl.cn"
    MQTT_PORT: int = 8883
    MQTT_USERNAME: str = "test2"
    MQTT_PASSWORD: str = "test2"
    MQTT_CERT_PATH: str = os.getenv("MQTT_CERT_PATH", "./cert/emqxsl-ca.crt")
    
    # 文件上传设置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    TRANSCRIPTION_DIR: str = os.getenv("TRANSCRIPTION_DIR", "./transcriptions")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "250"))  # 默认250MB
    MIN_UPLOAD_SIZE_BYTES: int = int(os.getenv("MIN_UPLOAD_SIZE_BYTES", "1024"))  # 默认最小1KB
    
    # 用户限制设置 - 仅保留用于控制u_id限额的设置
    DEFAULT_USER_LIMIT_COUNT: int = int(os.getenv("DEFAULT_USER_LIMIT_COUNT", "10"))
    DEFAULT_USER_LIMIT_DURATION: int = int(os.getenv("DEFAULT_USER_LIMIT_DURATION", "600"))  # 单位：秒

    # 内容ID验证设置
    CONTENT_ID_VERIFICATION_ENABLED: bool = os.getenv("CONTENT_ID_VERIFICATION_ENABLED", "False").lower() in ("true", "1", "t")
    CONTENT_ID_MAX_SAMPLE_SIZE: int = int(os.getenv("CONTENT_ID_MAX_SAMPLE_SIZE", "2097152"))  # 默认2MB

    # 云端API设置
    CLOUD_STATS_API_URL: Optional[str] = os.getenv("CLOUD_STATS_API_URL")
    CLOUD_API_KEY: Optional[str] = os.getenv("CLOUD_API_KEY")

    # 文件下载设置
    BASE_URL: str = os.getenv("BASE_URL", "http://150.109.15.121:8000")
    DOWNLOAD_URL_PREFIX: str = os.getenv("DOWNLOAD_URL_PREFIX", "/api/download")
    UPLOAD_URL:str = os.getenv("UPLOAD_URL", BASE_URL+"/api/uploadfile")
    
    # Webhook设置
    WEBHOOK_TRANSCRIPTION_URL: str = os.getenv("WEBHOOK_TRANSCRIPTION_URL", "http://123.57.134.165/api/v1/webhook/transcription")
    WEBHOOK_TIMEOUT: int = int(os.getenv("WEBHOOK_TIMEOUT", "10"))  # 默认10秒超时

    # Celery设置
    CELERY_WORKER_CONCURRENCY: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", "2"))
    CELERY_TASK_TIME_LIMIT: int = int(os.getenv("CELERY_TASK_TIME_LIMIT", "3600"))
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", "50"))

    WHISPER_MODEL_NAME= "base" if DEBUG else os.getenv("WHISPER_MODEL_NAME", "large-v3-turbo")

    CLEAN_FILE_TIMEOUT= int(os.getenv("CLEAN_FILE_TIMEOUT", "12"))


    # 转写任务配置
    MAX_TRANSCRIPTION_RETRY: int = int(os.getenv("MAX_TRANSCRIPTION_RETRY", "3"))  # 转写任务最大重试次数

    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局设置实例
settings = Settings() 