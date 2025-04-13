from typing import Dict, List, Optional, Any, Union
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

class TranscriptionExtraParams(BaseModel):
    """
    转写任务的额外参数
    """
    u_id: int = Field(..., description="用户唯一标识ID")
    record_file_name: str = Field(..., description="录音文件名")
    task_id: str = Field(..., description="任务ID，格式为 UID:{用户ID}_文件前2MB内容的MD5")
    mode_id: int = Field(..., description="使用的模板ID（提示词模板）")
    language: str = Field(..., description="语言")
    ai_mode: str = Field(..., description="使用的AI模式（如 GPT-4o）")
    speaker: bool = Field(..., description="是否启用说话人分离")
    whisper_arch: str = Field(..., description="使用的Whisper模型名")
    content_id: str = Field(..., description="内容ID")
    server_id: str = Field(..., description="服务器ID")

class TranscriptionTask(BaseModel):
    """
    转写任务详情
    """
    task_id: str = Field(..., description="任务ID")
    client_id: Optional[str] = Field(None, description="客户端ID")
    status: str = Field(..., description="任务状态：pending, processing, completed, failed")
    filename: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="文件存储路径")
    result_path: Optional[str] = Field(None, description="结果文件存储路径")
    language: Optional[str] = Field(None, description="指定的语言（如未指定则为自动检测）")
    created_at: str = Field(..., description="创建时间")
    started_at: Optional[str] = Field(None, description="开始处理时间")
    completed_at: Optional[str] = Field(None, description="完成时间")
    progress: Optional[int] = Field(0, description="处理进度（0-100）")
    progress_message: Optional[str] = Field(None, description="进度信息")
    error_message: Optional[str] = Field(None, description="错误信息（如果失败）")
    audio_duration: Optional[float] = Field(None, description="音频时长（秒）")
    processing_time: Optional[float] = Field(None, description="处理用时（秒）")
    extra_params: Optional[TranscriptionExtraParams] = Field(None, description="额外参数")
    code: int = Field(0, description="状态码：0表示成功，其他值表示失败")
    message: str = Field("", description="状态消息，成功时为空，失败时为错误信息")

    class Config:
        json_schema_extra = {
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
                "code": 0,
                "message": "",
                "extra_params": {
                    "u_id": 12345,
                    "record_file_name": "会议记录.mp3",
                    "task_id": "UID:12345_a1b2c3d4e5f6",
                    "mode_id": 1,
                    "language": "zh",
                    "ai_mode": "GPT-4o",
                    "speaker": True,
                    "content_id": "abc123-def456-ghi789",
                    "server_id": "some-server-id"
                }
            }
        }

class SimplifiedTranscriptionTask(BaseModel):
    """
    简化版转写任务详情，去除了一些字段
    """
    task_id: str = Field(..., description="任务ID")
    client_id: str = Field(..., description="客户端ID")
    filename: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="文件存储路径")
    result_path: Optional[str] = Field(None, description="结果文件存储路径")
    created_at: str = Field(..., description="创建时间")
    extra_params: Optional[TranscriptionExtraParams] = Field(None, description="额外参数")
    code: int = Field(0, description="状态码：0表示成功，其他值表示失败")
    message: str = Field("", description="状态消息，成功时为空，失败时为错误信息")

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "123e4567-e89b-12d3-a456-426614174000",
                "client_id": "client-123",
                "filename": "meeting.mp3",
                "file_path": "/uploads/123e4567-e89b-12d3-a456-426614174000.mp3",
                "created_at": "2023-06-15T10:30:00",
                "code": 0,
                "message": "",
                "extra_params": {
                    "u_id": 12345,
                    "record_file_name": "会议记录.mp3",
                    "task_id": "UID:12345_a1b2c3d4e5f6",
                    "mode_id": 1,
                    "language": "zh",
                    "ai_mode": "GPT-4o",
                    "speaker": True,
                    "content_id": "abc123-def456-ghi789",
                    "server_id": "some-server-id"
                }
            }
        }

class RateLimitInfo(BaseModel):
    """
    速率限制信息
    """
    limit_audio_seconds: int  # 总音频时长限制（秒）
    limit_requests: int  # 总请求次数限制
    remaining_audio_seconds: int  # 剩余可用音频时长（秒）
    remaining_requests: int  # 剩余可用请求次数
    reset_audio_seconds: float  # 音频时长限制重置时间（小时）
    reset_requests: float  # 请求次数限制重置时间（小时）
    retry_after: Optional[float] = None  # 如果被限制，需要等待的时间（秒）

class TranscriptionResponse(BaseModel):
    """
    转写任务响应，包含任务信息和速率限制信息
    """
    task: TranscriptionTask
    rate_limit: RateLimitInfo

    class Config:
        json_schema_extra = {
            "example": {
                "task": {
                    "task_id": "123e4567-e89b-12d3-a456-426614174000",
                    # ... 其他 TranscriptionTask 示例保持不变 ...
                },
                "rate_limit": {
                    "limit_audio_seconds": 28800,
                    "limit_requests": 2000,
                    "remaining_audio_seconds": 7121,
                    "remaining_requests": 1985,
                    "reset_audio_seconds": 39.5,
                    "reset_requests": 43.2,
                    "retry_after": None
                }
            }
        }

class RateLimitConfig(BaseModel):
    """
    速率限制配置
    """
    monthly_minutes: int = Field(300, description="每月音频分钟数")
    rpm: int = Field(20, description="每分钟请求数")
    rpd: int = Field(2000, description="每日请求数")
    ash: int = Field(7200, description="每小时音频秒数")
    asd: int = Field(28800, description="每日音频秒数") 