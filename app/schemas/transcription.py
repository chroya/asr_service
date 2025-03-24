from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TranscriptionSegment(BaseModel):
    """
    转写结果中的时间戳段
    """
    start: float = Field(..., description="开始时间（秒）")
    end: float = Field(..., description="结束时间（秒）")
    text: str = Field(..., description="文本内容")

class TranscriptionResult(BaseModel):
    """
    转写结果
    """
    text: str = Field(..., description="完整的转写文本")
    language: Optional[str] = Field(None, description="检测到的语言代码")
    segments: List[TranscriptionSegment] = Field(default_factory=list, description="带时间戳的文本片段")

class TranscriptionTask(BaseModel):
    """
    转写任务详情
    """
    task_id: str = Field(..., description="任务ID")
    client_id: str = Field(..., description="客户端ID")
    status: str = Field(..., description="任务状态：pending, processing, completed, failed")
    filename: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="文件存储路径")
    language: Optional[str] = Field(None, description="指定的语言（如未指定则为自动检测）")
    created_at: str = Field(..., description="创建时间")
    started_at: Optional[str] = Field(None, description="开始处理时间")
    completed_at: Optional[str] = Field(None, description="完成时间")
    progress: Optional[int] = Field(0, description="处理进度（0-100）")
    progress_message: Optional[str] = Field(None, description="进度信息")
    error_message: Optional[str] = Field(None, description="错误信息（如果失败）")
    result: Optional[Dict[str, Any]] = Field(None, description="转写结果")
    audio_duration: Optional[float] = Field(None, description="音频时长（秒）")
    processing_time: Optional[float] = Field(None, description="处理用时（秒）")
    
    class Config:
        schema_extra = {
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "client_id": "client-123",
                "status": "completed",
                "filename": "meeting.mp3",
                "file_path": "/uploads/123e4567-e89b-12d3-a456-426614174000.mp3",
                "language": "zh",
                "created_at": "2023-06-15T10:30:00",
                "started_at": "2023-06-15T10:30:05",
                "completed_at": "2023-06-15T10:31:15",
                "progress": 100,
                "audio_duration": 60.5,
                "processing_time": 70.2,
                "result": {
                    "text": "这是一段完整的转写文本。",
                    "language": "zh",
                    "segments": [
                        {"start": 0.0, "end": 2.5, "text": "这是"},
                        {"start": 2.5, "end": 5.0, "text": "一段完整的"},
                        {"start": 5.0, "end": 7.5, "text": "转写文本。"}
                    ]
                }
            }
        } 