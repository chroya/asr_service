from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.models import User
from app.models.api_models import UserInfo, UserLimitInfo
from app.services.redis_service import get_user_request_count, get_user_duration

router = APIRouter()

@router.get("/me", response_model=UserInfo)
async def read_user_me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息
    """
    return current_user

@router.get("/me/limits", response_model=UserLimitInfo)
async def read_user_limits(current_user: User = Depends(get_current_user)):
    """
    获取当前用户的使用限制信息
    """
    # 获取当前使用计数
    current_count = get_user_request_count(current_user.id)
    current_duration = get_user_duration(current_user.id)
    
    # 计算剩余
    remaining_count = max(0, current_user.limit_count - current_count)
    remaining_duration = max(0.0, current_user.limit_duration - current_duration)
    
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "limit_count": current_user.limit_count,
        "current_count": current_count,
        "limit_duration": current_user.limit_duration,
        "current_duration": current_duration,
        "remaining_count": remaining_count,
        "remaining_duration": remaining_duration
    } 