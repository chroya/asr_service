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
from app.schemas.transcription import TranscriptionTask

router = APIRouter()

# 服务实例
transcription_service = TranscriptionService()
cloud_stats_service = CloudStatsService()

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=TranscriptionTask)
async def create_transcription_task(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    language: Optional[str] = Form(None)
):
    """
    创建一个新的转写任务
    """
    # 获取客户端ID（从请求头）
    client_id = request.headers.get("X-Client-ID", str(uuid.uuid4()))
    
    # 验证文件
    if not validate_audio_file(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的音频文件。支持的格式：MP3, WAV, FLAC, M4A, OGG"
        )
    
    # 检查文件大小
    file_size_mb = await get_file_size_mb(file)
    if file_size_mb > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制。最大允许: {settings.MAX_UPLOAD_SIZE}MB"
        )
    
    # 保存上传的文件
    filename = file.filename
    task_id = str(uuid.uuid4())
    file_path = await save_upload_file(file, task_id)
    
    # 创建任务
    task = transcription_service.create_task(
        task_id=task_id,
        file_path=file_path,
        original_filename=filename,
        client_id=client_id,
        language=language
    )
    
    # 将任务添加到后台处理队列
    background_tasks.add_task(
        transcription_service.process_task,
        task_id,
        on_complete=lambda duration: cloud_stats_service.report_task_completion(client_id, duration)
    )
    
    return task

@router.get("/{task_id}", response_model=TranscriptionTask)
async def get_task(task_id: str):
    """
    获取转写任务的状态和信息
    """
    task = transcription_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    return task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    """
    删除转写任务
    """
    task = transcription_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    transcription_service.delete_task(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post("/{task_id}/retry", response_model=TranscriptionTask)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    重试失败的转写任务
    """
    task = transcription_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 获取客户端ID（从请求头）
    client_id = request.headers.get("X-Client-ID", task.client_id)
    
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
async def download_task_result(task_id: str):
    """
    下载转写任务的结果
    """
    task = transcription_service.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="任务尚未完成"
        )
    
    result = task.result
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务结果不存在"
        )
    
    # 创建结果JSON文件
    result_json = json.dumps(result, ensure_ascii=False, indent=2)
    
    # 返回响应
    return Response(
        content=result_json,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="transcription_{task_id}.json"'
        }
    )

@router.get("/client/{client_id}/tasks", response_model=List[TranscriptionTask])
async def get_client_tasks(client_id: str, limit: int = 10, offset: int = 0):
    """
    获取指定客户端的所有转写任务
    """
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到转写任务"
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