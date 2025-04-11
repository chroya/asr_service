import os
import json
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Form, status, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.api_models import TranscriptionStatus
from app.core.config import settings
from app.services.transcription_service import TranscriptionService
from app.services.cloud_stats import CloudStatsService
from app.utils.files import validate_audio_file, save_upload_file, get_file_size_mb
from app.utils.error_codes import (
    SUCCESS, ERROR_FILE_NOT_FOUND, ERROR_PROCESSING_FAILED, 
    ERROR_INVALID_FILE_FORMAT, ERROR_FILE_TOO_LARGE,
    ERROR_TASK_NOT_FOUND, ERROR_TASK_NOT_COMPLETED, ERROR_RESULT_NOT_FOUND,
    ERROR_MESSAGES, get_error_message
)
from app.schemas.transcription import TranscriptionTask, RateLimitInfo, TranscriptionExtraParams, SimplifiedTranscriptionTask
from app.tasks.transcription_tasks import process_transcription
from app.utils.whisper_arch import ARCH_LIST

router = APIRouter()

# 服务实例
transcription_service = TranscriptionService()
cloud_stats_service = CloudStatsService()

def add_rate_limit_headers(response: Response, client_id: str) -> None:
    """
    向响应头添加速率限制信息
    
    Args:
        response: FastAPI响应对象
        client_id: 客户端ID
    """
    # rate_limit_info = cloud_stats_service.get_rate_limit_info(client_id)
    # if rate_limit_info:
    #     response.headers["X-Rate-Limit-Audio-Seconds"] = str(rate_limit_info.limit_audio_seconds)
    #     response.headers["X-Rate-Limit-Requests"] = str(rate_limit_info.limit_requests)
    #     response.headers["X-Rate-Remaining-Audio-Seconds"] = str(rate_limit_info.remaining_audio_seconds)
    #     response.headers["X-Rate-Remaining-Requests"] = str(rate_limit_info.remaining_requests)
    #     response.headers["X-Rate-Reset-Audio-Seconds"] = str(rate_limit_info.reset_audio_seconds)
    #     response.headers["X-Rate-Reset-Requests"] = str(rate_limit_info.reset_requests)
    #     if rate_limit_info.retry_after:
    #         response.headers["Retry-After"] = str(rate_limit_info.retry_after)

@router.post("/uploadfile", status_code=status.HTTP_200_OK, response_model=SimplifiedTranscriptionTask)
async def create_transcription_task(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    extra_params: str = Form(...)  # 接收JSON字符串
):
    """
    创建一个新的转写任务
    
    参数:
        file: 要转写的音频文件
        extra_params: JSON字符串，包含额外参数:
            {
                "u_id": 用户ID (必须),
                "record_file_name": 文件名,
                "uuid": 唯一标识符(必须),
                "task_id": 任务ID(必须),
                "mode_id": 模型ID(必须),
                "language": 语言代码,
                "ai_mode": AI模式(必须),
                "speaker": 是否启用说话人分离(布尔值),
                "whisper_arch": whisper模型名,具体见 whisper_arch.py
            }
    """
    try:
        # 解析 extra_params JSON 字符串
        params = json.loads(extra_params)
        
        # 提取参数
        u_id = params.get("u_id")
        task_id = params.get("task_id")
        language = params.get("language", "auto")
        # language = "auto"  # 先忽略传上来的参数，默认自动检测语言
        uuid_str = params.get("uuid")
        mode_id = params.get("mode_id")
        ai_mode = params.get("ai_mode")
        speaker = params.get("speaker", False)
        whisper_arch = params.get("whisper_arch")
        if whisper_arch not in ARCH_LIST:
            whisper_arch = settings.WHISPER_MODEL_NAME
        
        # 验证必须的参数
        if not all([u_id, task_id, uuid_str, mode_id, ai_mode]):
            raise ValueError("缺少必要的参数")
    except (json.JSONDecodeError, ValueError) as e:
        error_response = SimplifiedTranscriptionTask(
            task_id=task_id if 'task_id' in locals() else "unknown",
            client_id=str(u_id) if 'u_id' in locals() else "unknown",
            filename=file.filename,
            file_path="",
            created_at=datetime.now().isoformat(),
            code=ERROR_PROCESSING_FAILED,
            message=f"解析参数失败: {str(e)}"
        )
        response.status_code = status.HTTP_400_BAD_REQUEST
        return error_response
    
    # 验证文件
    if not await validate_audio_file(file):
        error_response = SimplifiedTranscriptionTask(
            task_id=task_id,
            client_id=str(u_id),
            filename=file.filename,
            file_path="",
            created_at=datetime.now().isoformat(),
            code=ERROR_INVALID_FILE_FORMAT,
            message=ERROR_MESSAGES[ERROR_INVALID_FILE_FORMAT]
        )
        response.status_code = status.HTTP_400_BAD_REQUEST
        return error_response
    
    # 检查文件大小
    file_size_mb = await get_file_size_mb(file)
    if file_size_mb > settings.MAX_UPLOAD_SIZE:
        error_response = SimplifiedTranscriptionTask(
            task_id=task_id,
            client_id=str(u_id),
            filename=file.filename,
            file_path="",
            created_at=datetime.now().isoformat(),
            code=ERROR_FILE_TOO_LARGE,
            message=f"{ERROR_MESSAGES[ERROR_FILE_TOO_LARGE]}。最大允许: {settings.MAX_UPLOAD_SIZE}MB"
        )
        response.status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
        return error_response
    
    # 保存上传的文件
    filename = file.filename
    client_id = str(u_id)

    file_path = await save_upload_file(file, task_id)
    # 创建结果文件路径
    result_path = os.path.join(settings.TRANSCRIPTION_DIR, f"{task_id}.json")
    
    # 创建任务
    task = transcription_service.create_task(
        task_id=task_id,
        file_path=file_path,
        result_path=result_path,
        original_filename=filename,
        client_id=client_id,
        language=language,
        u_id=u_id,
        uuid=uuid_str,
        mode_id=mode_id,
        ai_mode=ai_mode,
        speaker=speaker,
        whisper_arch=whisper_arch
    )
    
    # 将任务添加到Celery队列
    process_transcription.delay(task_id)
    
    # 添加速率限制信息到响应头
    add_rate_limit_headers(response, client_id)
    
    # 转换为简化版返回对象
    simplified_task = SimplifiedTranscriptionTask(
        task_id=task.task_id,
        client_id=task.client_id,
        filename=task.filename,
        file_path=task.file_path,
        result_path=task.result_path,
        created_at=task.created_at,
        extra_params=task.extra_params,
        code=task.code,
        message=task.message
    )
    
    return simplified_task

@router.get("/task/{task_id}", response_model=SimplifiedTranscriptionTask)
async def get_task(task_id: str, request: Request, response: Response):
    """
    获取转写任务的状态和信息
    """
    task = transcription_service.get_task(task_id)
    if not task:
        error_response = SimplifiedTranscriptionTask(
            task_id=task_id,
            client_id="unknown",
            filename="",
            file_path="",
            created_at=datetime.now().isoformat(),
            code=ERROR_TASK_NOT_FOUND,
            message=ERROR_MESSAGES[ERROR_TASK_NOT_FOUND]
        )
        response.status_code = status.HTTP_404_NOT_FOUND
        return error_response
    
    # 转换为简化版返回对象
    simplified_task = SimplifiedTranscriptionTask(
        task_id=task.task_id,
        client_id=task.client_id,
        filename=task.filename,
        file_path=task.file_path,
        result_path=task.result_path,
        created_at=task.created_at,
        extra_params=task.extra_params,
        code=task.code,
        message=task.message
    )
    
    return simplified_task

@router.get("/download/{task_id}", response_class=Response)
async def download_result_file(task_id: str, request: Request, response: Response):
    """
    通过任务ID和文件名下载转写结果文件
    """
    filename = f"{task_id}.json"
    # 构建文件路径
    file_path = os.path.join(settings.TRANSCRIPTION_DIR, filename)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        error_response = {
            "task_id": task_id,
            "status": "failed",
            "code": ERROR_RESULT_NOT_FOUND,
            "message": ERROR_MESSAGES[ERROR_RESULT_NOT_FOUND]
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            media_type="application/json",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # 读取文件内容
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 返回响应
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

@router.get("/tasks", response_model=List[TranscriptionStatus])
async def list_transcriptions(
    limit: int = 10,
    offset: int = 0,
    client_id: Optional[str] = ''
):
    """
    列出转写任务，可选按客户端ID过滤
    """
    tasks = transcription_service.get_client_tasks(client_id, limit, offset)

    return [
        TranscriptionStatus(**task.dict())
        for task in tasks
    ]