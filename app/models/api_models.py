from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# 用户模型
class UserCreate(BaseModel):
    """用户创建模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str

class UserInfo(BaseModel):
    """用户信息模型"""
    id: int
    username: str
    email: str
    is_active: bool
    limit_count: int
    limit_duration: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# 令牌模型
class Token(BaseModel):
    """令牌模型"""
    access_token: str
    token_type: str = "bearer"

# 转写模型
class TranscriptionCreate(BaseModel):
    """转写创建请求模型"""
    language: Optional[str] = None
    
    @validator('language')
    def validate_language(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError('语言代码必须是2字符的ISO代码（如"zh", "en"）')
        return v

class TranscriptionResponse(BaseModel):
    """转写响应模型"""
    task_id: str
    status: str
    
    class Config:
        from_attributes = True

class TranscriptionStatus(BaseModel):
    """转写状态模型"""
    task_id: str
    status: str
    user_id: int
    original_filename: str
    file_size: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    audio_duration: Optional[float] = None
    transcription_path: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class TranscriptionResult(BaseModel):
    """转写结果模型"""
    task_id: str
    language: Optional[str] = None
    segments: List[Dict[str, Any]] = []
    text: str = ""
    
    class Config:
        from_attributes = True

# 用户限制模型
class UserLimitInfo(BaseModel):
    """用户限制信息模型"""
    user_id: int
    username: str
    limit_count: int
    current_count: int
    limit_duration: float
    current_duration: float
    remaining_count: int
    remaining_duration: float

# 系统模型
class HealthCheck(BaseModel):
    """系统健康检查模型"""
    status: str = "ok"
    version: str
    timestamp: datetime 