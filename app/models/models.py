from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 限制设置
    limit_count = Column(Integer, default=10)  # 默认限制10次
    limit_duration = Column(Integer, default=600)  # 默认限制600秒
    
    # 关联
    transcriptions = relationship("Transcription", back_populates="user")

class Transcription(Base):
    """转写任务模型"""
    __tablename__ = "transcriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(50), unique=True, index=True)
    client_id = Column(String(50), index=True)  # 客户端ID，用于替代用户ID
    
    # 文件信息
    original_filename = Column(String(255))
    file_path = Column(String(255))
    file_size = Column(Integer)  # 文件大小（字节）
    
    # 转写信息
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    transcription_path = Column(String(255), nullable=True)
    audio_duration = Column(Float, nullable=True)  # 音频时长（秒）
    
    # 时间信息
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 其他信息
    error_message = Column(Text, nullable=True)
    
    # 云端同步标志
    cloud_synced = Column(Boolean, default=False)  # 是否已同步到云端
    
    # 关联
    user = relationship("User", back_populates="transcriptions") 