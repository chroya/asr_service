import logging
import os
import json
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Form, status, Request, Response, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.services.transcription_service import TranscriptionService
from app.services.cloud_stats import CloudStatsService
from app.utils.files import validate_audio_file, save_upload_file, get_file_size_bytes, get_file_size_mb
from app.utils.error_codes import (
    SUCCESS, ERROR_FILE_NOT_FOUND, ERROR_PROCESSING_FAILED, 
    ERROR_INVALID_FILE_FORMAT, ERROR_FILE_TOO_LARGE, ERROR_FILE_TOO_SMALL,
    ERROR_TASK_NOT_FOUND, ERROR_TASK_NOT_COMPLETED, ERROR_RESULT_NOT_FOUND,
    ERROR_MESSAGES, get_error_message
)
from app.schemas.transcription import TranscriptionTask, RateLimitInfo, TranscriptionExtraParams, SimplifiedTranscriptionTask
from app.tasks.transcription_tasks import process_transcription
from app.utils.whisper_arch import ARCH_LIST
from app.core.auth import jwt_auth_middleware
from app.dependencies.services import get_transcription_service

router = APIRouter()

# 服务实例
# transcription_service = TranscriptionService()
# cloud_stats_service = CloudStatsService()


# 新增接口：通过task_id和content_id查询server_id
@router.get("/transcription/server_id")
async def get_server_id(task_id: str, content_id: str, 
                        _: bool = Depends(jwt_auth_middleware), 
                        transcription_service: TranscriptionService = Depends(get_transcription_service)):
    """
    根据task_id和content_id查询server_id
    
    Args:
        server_id: 请求路径中的server_id参数(仅作为路径标识，不实际使用)
        task_id: 任务ID
        content_id: 内容ID
        
    Returns:
        Dict: 包含server_id的响应结果
    """
    # 获取任务信息
    task = transcription_service.get_task(task_id)
    
    # 任务不存在
    if not task:
        return {
            "code": -1,
            "message": "failed",
            "data": ""
        }
    
    # 获取extra_params
    extra_params = task.extra_params
    
    # 验证content_id是否匹配
    task_content_id = ""
    if extra_params:
        # extra_params可能是字典或对象，需要适配两种获取方式
        if isinstance(extra_params, dict):
            task_content_id = extra_params.get("content_id", "")
        else:
            task_content_id = getattr(extra_params, "content_id", "")
    
    if not task_content_id or task_content_id != content_id:
        return {
            "code": -1, 
            "message": "failed",
            "data": ""
        }
    
    # 获取server_id
    found_server_id = ""
    if extra_params:
        if isinstance(extra_params, dict):
            found_server_id = extra_params.get("server_id", "")
        else:
            found_server_id = getattr(extra_params, "server_id", "")
    
    # 返回结果
    return {
        "code": 0,
        "message": "ok",
        "data": found_server_id
    }

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

logger = logging.getLogger(__name__)

@router.post("/uploadfile", status_code=status.HTTP_200_OK, response_model=SimplifiedTranscriptionTask)
async def create_transcription_task(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    extra_params: str = Form(...),
    _: bool = Depends(jwt_auth_middleware),  # 添加JWT鉴权
    transcription_service: TranscriptionService = Depends(get_transcription_service)
):
    """
    创建一个新的转写任务
    
    需要在请求头中提供有效的JWT令牌：
    Authorization: Bearer <your_jwt_token>
    
    参数:
        file: 要转写的音频文件
        extra_params: JSON字符串，包含额外参数:
            {
                "u_id": 用户ID (必须),
                "record_file_name": 文件名,
                "task_id": 任务ID(必须),
                "mode_id": 模型ID(必须),
                "language": 语言代码,
                "ai_mode": AI模式(必须),
                "speaker": 是否启用说话人分离(布尔值),
                "whisper_arch": whisper模型名,具体见 whisper_arch.py,
                "content_id": 内容ID,
                "server_id": 服务器ID
            }
    """
    try:
        # 解析 extra_params JSON 字符串
        params = json.loads(extra_params)
        
        # 提取参数
        u_id = params.get("u_id")
        task_id = params.get("task_id")
        language = params.get("language", "auto")
        mode_id = params.get("mode_id")
        ai_mode = params.get("ai_mode")
        speaker = params.get("speaker", False)
        whisper_arch = params.get("whisper_arch")
        content_id = params.get("content_id")
        server_id = params.get("server_id")

        logger.info(f"收到 POST 请求，extra_params参数为：{params}")
        
        if whisper_arch not in ARCH_LIST:
            whisper_arch = settings.WHISPER_MODEL_NAME
        
        # 验证必须的参数
        if not all([u_id, task_id, mode_id, ai_mode]):
            raise ValueError("缺少必要的参数")
        
    except (json.JSONDecodeError, ValueError) as e:
        error_response = SimplifiedTranscriptionTask(
            task_id=task_id if 'task_id' in locals() else "unknown",
            client_id=str(u_id) if 'u_id' in locals() else "unknown",
            filename=file.filename,
            file_path="",
            file_size=None,
            created_at=datetime.now().isoformat(),
            code=ERROR_PROCESSING_FAILED,
            message=f"解析参数失败: {str(e)}",
            extra_params=TranscriptionExtraParams(
                u_id=u_id if 'u_id' in locals() else 0,
                record_file_name=file.filename,
                task_id=task_id if 'task_id' in locals() else "unknown",
                mode_id=mode_id if 'mode_id' in locals() else 0,
                language=language if 'language' in locals() else "unknown",
                ai_mode=ai_mode if 'ai_mode' in locals() else "unknown",
                speaker=speaker if 'speaker' in locals() else False,
                whisper_arch=whisper_arch if 'whisper_arch' in locals() else "unknown",
                content_id=content_id if 'content_id' in locals() else "unknown",
                server_id=server_id if 'server_id' in locals() else "unknown"
            )
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
            file_size=None,
            created_at=datetime.now().isoformat(),
            code=ERROR_INVALID_FILE_FORMAT,
            message=ERROR_MESSAGES[ERROR_INVALID_FILE_FORMAT],
            extra_params=TranscriptionExtraParams(
                u_id=u_id,
                record_file_name=file.filename,
                task_id=task_id,
                mode_id=mode_id,
                language=language,
                ai_mode=ai_mode,
                speaker=speaker,
                whisper_arch=whisper_arch,
                content_id=content_id,
                server_id=server_id
            )
        )
        response.status_code = status.HTTP_400_BAD_REQUEST
        return error_response
    
    # 检查文件大小
    file_size_bytes = await get_file_size_bytes(file)
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    # 检查文件是否太小
    if file_size_bytes < settings.MIN_UPLOAD_SIZE_BYTES:
        error_response = SimplifiedTranscriptionTask(
            task_id=task_id,
            client_id=str(u_id),
            filename=file.filename,
            file_path="",
            file_size=file_size_bytes,
            created_at=datetime.now().isoformat(),
            code=ERROR_FILE_TOO_SMALL,
            message=f"{ERROR_MESSAGES[ERROR_FILE_TOO_SMALL]}。最小限制: {settings.MIN_UPLOAD_SIZE_BYTES}字节",
            extra_params=TranscriptionExtraParams(
                u_id=u_id,
                record_file_name=file.filename,
                task_id=task_id,
                mode_id=mode_id,
                language=language,
                ai_mode=ai_mode,
                speaker=speaker,
                whisper_arch=whisper_arch,
                content_id=content_id,
                server_id=server_id
            )
        )
        response.status_code = status.HTTP_400_BAD_REQUEST
        return error_response
    
    # 检查文件是否太大
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        error_response = SimplifiedTranscriptionTask(
            task_id=task_id,
            client_id=str(u_id),
            filename=file.filename,
            file_path="",
            file_size=file_size_bytes,
            created_at=datetime.now().isoformat(),
            code=ERROR_FILE_TOO_LARGE,
            message=f"{ERROR_MESSAGES[ERROR_FILE_TOO_LARGE]}。最大允许: {settings.MAX_UPLOAD_SIZE_MB}MB",
            extra_params=TranscriptionExtraParams(
                u_id=u_id,
                record_file_name=file.filename,
                task_id=task_id,
                mode_id=mode_id,
                language=language,
                ai_mode=ai_mode,
                speaker=speaker,
                whisper_arch=whisper_arch,
                content_id=content_id,
                server_id=server_id
            )
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
        mode_id=mode_id,
        ai_mode=ai_mode,
        speaker=speaker,
        whisper_arch=whisper_arch,
        content_id=content_id,
        server_id=server_id,
        file_size=file_size_bytes
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
        file_size=task.file_size,
        result_path=task.result_path,
        created_at=task.created_at,
        extra_params=task.extra_params,
        code=task.code,
        message=task.message
    )
    
    return simplified_task

@router.get("/download/{task_id}", response_class=Response)
async def download_result_file(
    task_id: str,
    request: Request,
    response: Response,
    _: bool = Depends(jwt_auth_middleware)  # 添加JWT鉴权
):
    """
    通过任务ID和文件名下载转写结果文件
    
    需要在请求头中提供有效的JWT令牌：
    Authorization: Bearer <your_jwt_token>
    """
    if '.' in task_id:
        filename = task_id
    else:
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