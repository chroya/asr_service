import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.models.models import User
from app.core.config import settings
from app.services.redis_service import get_user_request_count, get_user_duration

logger = logging.getLogger(__name__)

# 密码处理上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """对密码进行哈希处理"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建访问令牌
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def get_user(db: Session, user_id: int) -> Optional[User]:
    """根据ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    return db.query(User).filter(User.username == username).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """根据邮箱获取用户"""
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_data: Dict[str, Any]) -> User:
    """
    创建新用户
    """
    hashed_password = get_password_hash(user_data["password"])
    db_user = User(
        username=user_data["username"],
        email=user_data["email"],
        hashed_password=hashed_password,
        limit_count=user_data.get("limit_count", settings.DEFAULT_USER_LIMIT_COUNT),
        limit_duration=user_data.get("limit_duration", settings.DEFAULT_USER_LIMIT_DURATION),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"创建新用户: {db_user.username}")
    return db_user

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    验证用户
    """
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def check_user_limits(user: User) -> Optional[str]:
    """
    检查用户是否超出使用限制
    
    Returns:
        Optional[str]: 如果超出限制，返回错误消息；否则，返回None
    """
    # 检查调用次数限制
    current_count = get_user_request_count(user.id)
    if current_count >= user.limit_count:
        return f"超出调用次数限制 ({current_count}/{user.limit_count})"
    
    # 检查处理时长限制
    current_duration = get_user_duration(user.id)
    if current_duration >= user.limit_duration:
        return f"超出处理时长限制 ({current_duration:.2f}/{user.limit_duration}秒)"
    
    return None 