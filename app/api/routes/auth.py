from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.models.api_models import Token, UserCreate, UserInfo
from app.db.database import get_db
from app.services.user_service import (
    authenticate_user, create_access_token, 
    get_user_by_username, create_user
)
from app.core.auth import get_current_user
from app.models.models import User
from app.core.config import settings

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    获取访问令牌
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=UserInfo)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    注册新用户
    """
    # 检查用户名是否已存在
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被使用"
        )
    
    # 创建新用户
    new_user = create_user(db, user_data.dict())
    return new_user

@router.get("/me", response_model=UserInfo)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息
    """
    return current_user 