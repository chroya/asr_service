from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


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
