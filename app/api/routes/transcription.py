import os
import json
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.models.api_models import TranscriptionCreate, TranscriptionResponse, TranscriptionStatus, TranscriptionResult
from app.models.models import Transcription
from app.services.transcription_service import create_transcription_task, transcribe_audio, update_transcription_result
from app.core.config import settings
from app.services.transcription import TranscriptionService
from app.services.cloud_stats import CloudStatsService
from app.utils.files import validate_audio_file, save_upload_file, get_file_size_mb
from app.utils.error_codes import (
    SUCCESS, ERROR_FILE_NOT_FOUND, ERROR_PROCESSING_FAILED, 
    ERROR_INVALID_FILE_FORMAT, ERROR_FILE_TOO_LARGE,
    ERROR_TASK_NOT_FOUND, ERROR_TASK_NOT_COMPLETED, ERROR_RESULT_NOT_FOUND,
    ERROR_MESSAGES, get_error_message
)
from app.schemas.transcription import TranscriptionTask, RateLimitInfo

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

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TranscriptionTask)
async def create_transcription_task(
    background_tasks: BackgroundTasks,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    u_id: int = Form(...),
    uuid: str = Form(...),
    task_id: str = Form(...),
    mode_id: int = Form(...),
    ai_mode: str = Form(...),
    speaker: bool = Form(False)
):
    """
    创建一个新的转写任务
    """
    
    # 验证文件
    if not validate_audio_file(file):
        error_response = TranscriptionTask(
            task_id=task_id,
            client_id=str(u_id),
            status="failed",
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
        error_response = TranscriptionTask(
            task_id=task_id,
            client_id=str(u_id),
            status="failed",
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
        uuid=uuid,
        mode_id=mode_id,
        ai_mode=ai_mode,
        speaker=speaker
    )
    
    # 将任务添加到后台处理队列
    background_tasks.add_task(
        transcription_service.process_task,
        task_id,
        on_complete=lambda duration: cloud_stats_service.report_task_completion(client_id, duration)
    )
    
    # 添加速率限制信息到响应头
    add_rate_limit_headers(response, client_id)
    
    return task

@router.get("/{task_id}", response_model=TranscriptionTask)
async def get_task(task_id: str, request: Request, response: Response):
    """
    获取转写任务的状态和信息
    """
    task = transcription_service.get_task(task_id)
    if not task:
        error_response = TranscriptionTask(
            task_id=task_id,
            client_id="unknown",
            status="failed",
            filename="",
            file_path="",
            created_at=datetime.now().isoformat(),
            code=ERROR_TASK_NOT_FOUND,
            message=ERROR_MESSAGES[ERROR_TASK_NOT_FOUND]
        )
        response.status_code = status.HTTP_404_NOT_FOUND
        return error_response
    
    # 获取客户端ID
    client_id = request.headers.get("X-Client-ID", task.client_id)
    
    # 添加速率限制信息到响应头
    add_rate_limit_headers(response, client_id)
    
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, request: Request, response: Response):
    """
    删除转写任务
    """
    task = transcription_service.get_task(task_id)
    if not task:
        error_response = {
            "task_id": task_id,
            "status": "failed",
            "code": ERROR_TASK_NOT_FOUND,
            "message": ERROR_MESSAGES[ERROR_TASK_NOT_FOUND]
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            media_type="application/json",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # 获取客户端ID
    client_id = request.headers.get("X-Client-ID", task.client_id)
    
    # 添加速率限制信息到响应头
    add_rate_limit_headers(response, client_id)
    
    transcription_service.delete_task(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{task_id}/retry", response_model=TranscriptionTask)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    response: Response
):
    """
    重试失败的转写任务
    """
    task = transcription_service.get_task(task_id)
    if not task:
        error_response = TranscriptionTask(
            task_id=task_id,
            client_id="unknown",
            status="failed",
            filename="",
            file_path="",
            created_at=datetime.now().isoformat(),
            code=ERROR_TASK_NOT_FOUND,
            message=ERROR_MESSAGES[ERROR_TASK_NOT_FOUND]
        )
        response.status_code = status.HTTP_404_NOT_FOUND
        return error_response
    
    # 获取客户端ID（从请求头）
    client_id = request.headers.get("X-Client-ID", task.client_id)
    
    # 添加速率限制信息到响应头
    add_rate_limit_headers(response, client_id)
    
    # 重置任务状态
    task = transcription_service.reset_task(task_id)
    
    # 将任务添加到后台处理队列
    background_tasks.add_task(
        transcription_service.process_task,
        task_id,
        on_complete=lambda duration: cloud_stats_service.report_task_completion(client_id, duration)
    )
    
    return task

@router.get("/{task_id}/download", response_class=Response)
async def download_task_result(task_id: str, request: Request, response: Response):
    """
    下载转写任务的结果
    """
    task = transcription_service.get_task(task_id)
    if not task:
        error_response = {
            "task_id": task_id,
            "status": "failed",
            "code": ERROR_TASK_NOT_FOUND,
            "message": ERROR_MESSAGES[ERROR_TASK_NOT_FOUND]
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            media_type="application/json",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # 获取客户端ID
    client_id = request.headers.get("X-Client-ID", task.client_id)
    
    # 添加速率限制信息到响应头
    add_rate_limit_headers(response, client_id)
    
    if task.status != "completed":
        error_response = {
            "task_id": task_id,
            "status": task.status,
            "code": ERROR_TASK_NOT_COMPLETED,
            "message": ERROR_MESSAGES[ERROR_TASK_NOT_COMPLETED]
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            media_type="application/json",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    result = task.result
    if not result:
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
    
    # 创建结果JSON文件
    result_json = json.dumps(result, ensure_ascii=False, indent=2)
    
    # 返回响应
    return Response(
        content=result_json,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{task_id}.json"',
            **response.headers
        }
    )

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

@router.get("/client/{client_id}/tasks", response_model=List[TranscriptionTask])
async def get_client_tasks(client_id: str, request: Request, response: Response, limit: int = 10, offset: int = 0):
    """
    获取指定客户端的所有转写任务
    """
    # 添加速率限制信息到响应头
    add_rate_limit_headers(response, client_id)
    
    tasks = transcription_service.get_client_tasks(client_id, limit, offset)
    return tasks

@router.get("/", response_model=List[TranscriptionStatus])
async def list_transcriptions(
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0,
    client_id: Optional[str] = None
):
    """
    列出转写任务，可选按客户端ID过滤
    """
    query = db.query(Transcription)
    
    if client_id:
        query = query.filter(Transcription.client_id == client_id)
    
    transcriptions = query.order_by(Transcription.created_at.desc()).offset(offset).limit(limit).all()
    
    return transcriptions

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    删除转写任务
    """
    transcription = db.query(Transcription).filter(
        Transcription.task_id == task_id
    ).first()
    
    if not transcription:
        error_response = {
            "task_id": task_id,
            "status": "failed",
            "code": ERROR_TASK_NOT_FOUND,
            "message": ERROR_MESSAGES[ERROR_TASK_NOT_FOUND]
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            media_type="application/json",
            status_code=status.HTTP_404_NOT_FOUND
        )
    
    # 删除相关文件
    if transcription.file_path and os.path.exists(transcription.file_path):
        os.remove(transcription.file_path)
    
    if transcription.transcription_path and os.path.exists(transcription.transcription_path):
        os.remove(transcription.transcription_path)
    
    # 从数据库中删除
    db.delete(transcription)
    db.commit()
    
    return None

# 后台任务处理函数
async def process_transcription(db: Session, task_id: str, file_path: str, language: Optional[str] = None):
    """
    处理转写任务（后台任务）
    """
    result = transcribe_audio(task_id, file_path, language)
    
    if result["success"]:
        update_transcription_result(
            db,
            task_id,
            "completed",
            transcription_path=result["transcription_path"],
            audio_duration=result["audio_duration"]
        )
    else:
        update_transcription_result(
            db,
            task_id,
            "failed",
            error_message=result["error"]
        ) 