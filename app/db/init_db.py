import logging
from sqlalchemy.orm import Session
from app.db.database import Base, engine
from app.models.models import User, Transcription
from app.services.user_service import create_user
from app.core.config import settings

logger = logging.getLogger(__name__)

def init_db(db: Session) -> None:
    """
    初始化数据库
    """
    # 创建表
    Base.metadata.create_all(bind=engine)
    
    # 检查是否需要添加初始用户
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        logger.info("创建管理员用户")
        user_in = {
            "username": "admin",
            "email": "admin@example.com",
            "password": "admin123",
            "limit_count": 100,
            "limit_duration": 3600
        }
        create_user(db, user_in)

def reset_db() -> None:
    """
    重置数据库（仅开发环境使用）
    """
    if settings.DEBUG:
        logger.warning("重置数据库...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        logger.info("数据库已重置") 