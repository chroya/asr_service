import logging
import os
import json
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Form, status, Request, Response, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from app.core.config import settings
from app.services.transcription_service import TranscriptionService
from app.services.cloud_stats import CloudStatsService
from app.utils.files import validate_audio_file, save_upload_file, get_file_size_bytes, get_file_size_mb
from app.utils.file_validation import validate_content_id
from app.utils.ecm_to_wav import ecm_to_wav  # 导入ecm转wav函数
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
        file: 要转写的音频文件（支持标准音频格式和ECM格式）
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
    # 初始化变量，防止异常处理中引用错误
    u_id = None
    task_id = None
    language = "auto"
    mode_id = None
    ai_mode = None
    speaker = False
    whisper_arch = None
    content_id = None
    server_id = None
    
    # 提取JWT token
    jwt_token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        jwt_token = auth_header.split(" ")[1]
    
    try:
        # 解析 extra_params JSON 字符串
        params = json.loads(extra_params)
        
        # 提取基本参数
        u_id = params.get("u_id")
        task_id = params.get("task_id")
        language = params.get("language", "auto")
        mode_id = params.get("mode_id")
        ai_mode = params.get("ai_mode")
        speaker = params.get("speaker", False)
        whisper_arch = params.get("whisper_arch")
        content_id = params.get("content_id")
        server_id = params.get("server_id")
        duration = params.get("duration")
        
        logger.info(f"收到 POST 请求，extra_params参数为：{params}")
        
        # 验证参数和文件
        validated_params, error_response = await validate_params_and_file(file, params, response)
        if error_response:
            return error_response
        
        # 提取验证后的参数，可能修改的是whisper_arch和file_size_bytes
        whisper_arch = validated_params.get("whisper_arch")
        file_size_bytes = validated_params.get("file_size_bytes")

        # 保存上传的文件（增加ECM格式检测和转换）
        filename = file.filename
        client_id = str(u_id)

        # 创建任务以获取uni_key
        task = transcription_service.create_task(
            task_id=task_id,
            file_path="",  # 先设置为空，稍后更新
            result_path="",  # 先设置为空，稍后更新
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
            duration=duration,
            file_size=file_size_bytes,
            jwt_token=jwt_token  # 保存JWT token到任务中
        )
        
        # 使用新的保存函数处理可能的ECM文件
        file_path = await save_upload_file_with_ecm_check(file, task.uni_key)
        
        # 创建结果文件路径，使用uni_key作为文件名
        result_path = os.path.join(settings.TRANSCRIPTION_DIR, f"{task.uni_key}.json")
        
        # 更新任务的文件路径和结果路径
        task = transcription_service.update_task(
            uni_key=task.uni_key,
            file_path=file_path,
            result_path=result_path
        )
        
        # 将任务添加到Celery队列
        process_transcription.delay(task.uni_key)
        
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

    except (json.JSONDecodeError, ValueError) as e:
        error_response = create_error_response(
            file_filename=file.filename,
            code=ERROR_PROCESSING_FAILED,
            message=f"解析参数失败: {str(e)}",
            u_id=u_id,
            task_id=task_id,
            mode_id=mode_id,
            language=language,
            ai_mode=ai_mode,
            speaker=speaker,
            whisper_arch=whisper_arch,
            content_id=content_id,
            server_id=server_id
        )
        response.status_code = status.HTTP_200_OK
        return error_response

@router.get("/download/{uni_key}", response_class=Response)
async def download_result_file(
    uni_key: str,
    request: Request,
    response: Response,
    _: bool = Depends(jwt_auth_middleware),  # 添加JWT鉴权
    transcription_service: TranscriptionService = Depends(get_transcription_service)
):
    """
    通过任务唯一标识符下载转写结果文件
    
    需要在请求头中提供有效的JWT令牌：
    Authorization: Bearer <your_jwt_token>
    """
    # 检查uni_key是否以.json结尾
    if uni_key.endswith('.json'):
        # 直接查找文件
        file_path = os.path.join(settings.TRANSCRIPTION_DIR, uni_key)
        if not os.path.exists(file_path):
            error_response = {
                "uni_key": uni_key,
                "status": "failed",
                "code": ERROR_RESULT_NOT_FOUND,
                "message": get_error_message(ERROR_RESULT_NOT_FOUND)
            }
            return Response(
                content=json.dumps(error_response, ensure_ascii=False),
                media_type="application/json",
                status_code=status.HTTP_200_OK
            )
    else:
        # 获取任务信息
        task = transcription_service.get_task(uni_key)
        
        # 如果任务不存在
        if not task:
            error_response = {
                "uni_key": uni_key,
                "status": "failed",
                "code": ERROR_TASK_NOT_FOUND,
                "message": get_error_message(ERROR_TASK_NOT_FOUND)
            }
            return Response(
                content=json.dumps(error_response, ensure_ascii=False),
                media_type="application/json",
                status_code=status.HTTP_200_OK
            )
            
        # 如果任务未完成
        if task.status != "completed":
            error_response = {
                "uni_key": uni_key,
                "task_id": task.task_id,
                "status": "failed",
                "code": ERROR_TASK_NOT_COMPLETED,
                "message": get_error_message(ERROR_TASK_NOT_COMPLETED)
            }
            return Response(
                content=json.dumps(error_response, ensure_ascii=False),
                media_type="application/json",
                status_code=status.HTTP_200_OK
            )
        
        file_path = task.result_path
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        error_response = {
            "uni_key": uni_key,
            "status": "failed",
            "code": ERROR_RESULT_NOT_FOUND,
            "message": get_error_message(ERROR_RESULT_NOT_FOUND)
        }
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            media_type="application/json",
            status_code=status.HTTP_200_OK
        )
    
    # 读取文件内容
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 获取文件名
    filename = os.path.basename(file_path)
    
    # 返回响应
    return Response(
        content=content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

# 新增接口：通过uni_key和content_id查询server_id
@router.get("/transcription/server_id")
async def get_server_id(uni_key: str, content_id: str, 
                        _: bool = Depends(jwt_auth_middleware), 
                        transcription_service: TranscriptionService = Depends(get_transcription_service)):
    """
    根据uni_key和content_id查询server_id
    
    Args:
        uni_key: 任务唯一标识符
        content_id: 内容ID
        
    Returns:
        Dict: 包含server_id的响应结果
    """
    # 获取任务信息
    task = transcription_service.get_task(uni_key)
    
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

# 添加辅助函数用于创建错误响应和参数对象
def create_extra_params(
    file_filename: str,
    u_id: Optional[int] = None,
    task_id: Optional[str] = None,
    mode_id: Optional[int] = None,
    language: Optional[str] = "auto",
    ai_mode: Optional[str] = None,
    speaker: bool = False,
    whisper_arch: Optional[str] = None,
    content_id: Optional[str] = None,
    server_id: Optional[str] = None
) -> TranscriptionExtraParams:
    """
    创建转写任务的额外参数对象
    
    Args:
        file_filename: 文件名
        u_id: 用户ID
        task_id: 任务ID
        mode_id: 模型ID
        language: 语言代码
        ai_mode: AI模式
        speaker: 是否启用说话人分离
        whisper_arch: whisper模型名
        content_id: 内容ID
        server_id: 服务器ID
    
    Returns:
        TranscriptionExtraParams: 创建的参数对象
    """
    return TranscriptionExtraParams(
        u_id=u_id if u_id is not None else 0,
        record_file_name=file_filename,
        task_id=task_id if task_id is not None else "unknown",
        mode_id=mode_id if mode_id is not None else 0,
        language=language if language is not None else "unknown",
        ai_mode=ai_mode if ai_mode is not None else "unknown",
        speaker=speaker,
        whisper_arch=whisper_arch if whisper_arch is not None else "unknown",
        content_id=content_id if content_id is not None else "unknown",
        server_id=server_id if server_id is not None else "unknown"
    )

def create_error_response(
    file_filename: str,
    code: int,
    message: str,
    u_id: Optional[int] = None,
    task_id: Optional[str] = None,
    file_path: str = "",
    file_size: Optional[int] = None,
    mode_id: Optional[int] = None,
    language: Optional[str] = "auto",
    ai_mode: Optional[str] = None,
    speaker: bool = False,
    whisper_arch: Optional[str] = None,
    content_id: Optional[str] = None,
    server_id: Optional[str] = None
) -> SimplifiedTranscriptionTask:
    """
    创建错误响应对象
    
    Args:
        file_filename: 文件名
        code: 错误代码
        message: 错误消息
        u_id: 用户ID
        task_id: 任务ID
        file_path: 文件路径
        file_size: 文件大小
        mode_id: 模型ID
        language: 语言代码
        ai_mode: AI模式
        speaker: 是否启用说话人分离
        whisper_arch: whisper模型名
        content_id: 内容ID
        server_id: 服务器ID
    
    Returns:
        SimplifiedTranscriptionTask: 创建的错误响应对象
    """
    extra_params = create_extra_params(
        file_filename=file_filename,
        u_id=u_id,
        task_id=task_id,
        mode_id=mode_id,
        language=language,
        ai_mode=ai_mode,
        speaker=speaker,
        whisper_arch=whisper_arch,
        content_id=content_id,
        server_id=server_id
    )
    
    return SimplifiedTranscriptionTask(
        task_id=task_id if task_id is not None else "unknown",
        client_id=str(u_id) if u_id is not None else "unknown",
        filename=file_filename,
        file_path=file_path,
        file_size=file_size,
        created_at=datetime.now().isoformat(),
        code=code,
        message=message,
        extra_params=extra_params
    )

async def save_upload_file_with_ecm_check(file: UploadFile, uni_key: str) -> str:
    """
    保存上传的文件，并检查是否为ECM格式，如果是则转换为WAV
    
    Args:
        file: 上传的文件对象
        uni_key: 任务唯一标识符
        
    Returns:
        str: 保存的文件路径（对于ECM格式会返回转换后的WAV路径）
    """
    # 获取原始文件名和后缀
    original_filename = file.filename
    filename_without_ext, file_ext = os.path.splitext(original_filename)
    
    # 保存原始文件以检查格式
    temp_path = os.path.join(settings.UPLOAD_DIR, f"{uni_key}_temp")
    with open(temp_path, "wb") as buffer:
        # 读取文件的前20个字节来检查是否为ECM格式
        header = await file.read(20)
        await file.seek(0)  # 重置文件指针
        
        # 写入临时文件
        shutil.copyfileobj(file.file, buffer)
    
    # 检查是否为ECM格式 (0x45, 0x43, 0x4D 对应 'E', 'C', 'M')
    is_ecm = (header[0] == 0x45 and header[1] == 0x43 and header[2] == 0x4D)
    
    if is_ecm:
        logger.info(f"检测到ECM格式文件: {file.filename}")
        # 为转换后的WAV文件创建路径，使用格式 taskid_filename.wav
        wav_path = os.path.join(settings.UPLOAD_DIR, f"{uni_key}_{filename_without_ext}.wav")
        # 调用转换函数
        try:
            ecm_to_wav(temp_path, wav_path)
            logger.info(f"ECM文件已成功转换为WAV: {wav_path}")
            # 删除临时的ECM文件
            os.remove(temp_path)
            return wav_path
        except Exception as e:
            logger.error(f"ECM转WAV失败: {str(e)}")
            # 转换失败时，仍然使用原始文件但保持指定的命名格式
            final_path = os.path.join(settings.UPLOAD_DIR, f"{uni_key}_{filename_without_ext}{file_ext}")
            os.rename(temp_path, final_path)
            return final_path
    else:
        # 如果不是ECM格式，使用标准命名格式
        final_path = os.path.join(settings.UPLOAD_DIR, f"{uni_key}_{filename_without_ext}{file_ext}")
        os.rename(temp_path, final_path)
        return final_path

async def validate_params_and_file(
    file: UploadFile,
    params_dict: Dict[str, Any],
    response: Response
) -> Tuple[Optional[Dict[str, Any]], Optional[SimplifiedTranscriptionTask]]:
    """
    验证参数和文件
    
    Args:
        file: 上传的文件对象
        params_dict: 参数字典
        response: FastAPI响应对象
    
    Returns:
        Tuple[Optional[Dict[str, Any]], Optional[SimplifiedTranscriptionTask]]:
        如果验证通过，返回(参数字典, None)
        如果验证失败，返回(None, 错误响应)
    """
    # 提取参数
    u_id = params_dict.get("u_id")
    task_id = params_dict.get("task_id")
    language = params_dict.get("language", "auto")
    mode_id = params_dict.get("mode_id")
    ai_mode = params_dict.get("ai_mode")
    speaker = params_dict.get("speaker", False)
    whisper_arch = params_dict.get("whisper_arch")
    content_id = params_dict.get("content_id")
    server_id = params_dict.get("server_id")
    
    # 验证whisper_arch
    if whisper_arch not in ARCH_LIST:
        whisper_arch = settings.WHISPER_MODEL_NAME
        params_dict["whisper_arch"] = whisper_arch
    
    # 验证必须的参数
    if not all([u_id, task_id, mode_id, ai_mode]):
        error_response = create_error_response(
            file_filename=file.filename,
            code=ERROR_PROCESSING_FAILED,
            message="缺少必要的参数",
            u_id=u_id,
            task_id=task_id,
            mode_id=mode_id,
            language=language,
            ai_mode=ai_mode,
            speaker=speaker,
            whisper_arch=whisper_arch,
            content_id=content_id,
            server_id=server_id
        )
        response.status_code = status.HTTP_200_OK
        return None, error_response
    
    # 验证内容ID
    if content_id and settings.CONTENT_ID_VERIFICATION_ENABLED:
        # 读取文件内容
        file_content = await file.read()
        is_valid = validate_content_id(file_content, u_id, content_id)
        # 重置文件指针
        await file.seek(0)
        
        if not is_valid:
            error_response = create_error_response(
                file_filename=file.filename,
                code=ERROR_PROCESSING_FAILED,
                message=f"内容验证失败: {content_id}",
                u_id=u_id,
                task_id=task_id,
                mode_id=mode_id,
                language=language,
                ai_mode=ai_mode,
                speaker=speaker,
                whisper_arch=whisper_arch,
                content_id=content_id,
                server_id=server_id
            )
            response.status_code = status.HTTP_200_OK
            return None, error_response
    
    # 检查文件前20个字节，判断是否为ECM格式
    header = await file.read(20)
    await file.seek(0)  # 重置文件指针
    
    is_ecm = (len(header) >= 3 and header[0] == 0x45 and header[1] == 0x43 and header[2] == 0x4D)
    
    # 如果是ECM格式，不需要继续验证音频格式
    if not is_ecm:
        # 验证文件格式
        if not await validate_audio_file(file):
            error_response = create_error_response(
                file_filename=file.filename,
                code=ERROR_INVALID_FILE_FORMAT,
                message=ERROR_MESSAGES[ERROR_INVALID_FILE_FORMAT],
                u_id=u_id,
                task_id=task_id,
                mode_id=mode_id,
                language=language,
                ai_mode=ai_mode,
                speaker=speaker,
                whisper_arch=whisper_arch,
                content_id=content_id,
                server_id=server_id
            )
            response.status_code = status.HTTP_200_OK
            return None, error_response
    
    # 检查文件大小
    file_size_bytes = await get_file_size_bytes(file)
    file_size_mb = file_size_bytes / (1024 * 1024)
    
    # 检查文件是否太小
    if file_size_bytes < settings.MIN_UPLOAD_SIZE_BYTES:
        error_response = create_error_response(
            file_filename=file.filename,
            code=ERROR_FILE_TOO_SMALL,
            message=f"{ERROR_MESSAGES[ERROR_FILE_TOO_SMALL]}。最小限制: {settings.MIN_UPLOAD_SIZE_BYTES}字节",
            u_id=u_id,
            task_id=task_id,
            file_size=file_size_bytes,
            mode_id=mode_id,
            language=language,
            ai_mode=ai_mode,
            speaker=speaker,
            whisper_arch=whisper_arch,
            content_id=content_id,
            server_id=server_id
        )
        response.status_code = status.HTTP_200_OK
        return None, error_response
    
    # 检查文件是否太大
    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        error_response = create_error_response(
            file_filename=file.filename,
            code=ERROR_FILE_TOO_LARGE,
            message=f"{ERROR_MESSAGES[ERROR_FILE_TOO_LARGE]}。最大允许: {settings.MAX_UPLOAD_SIZE_MB}MB",
            u_id=u_id,
            task_id=task_id,
            file_size=file_size_bytes,
            mode_id=mode_id,
            language=language,
            ai_mode=ai_mode,
            speaker=speaker,
            whisper_arch=whisper_arch,
            content_id=content_id,
            server_id=server_id
        )
        response.status_code = status.HTTP_200_OK
        return None, error_response
    
    # 返回验证通过的参数和文件大小
    params_dict["file_size_bytes"] = file_size_bytes
    return params_dict, None

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

@router.delete("/task/{uni_key}")
async def delete_task(
    uni_key: str,
    transcription_service: TranscriptionService = Depends(get_transcription_service)
):
    """
    删除转写任务及相关文件
    
    Args:
        uni_key: 任务唯一标识符
    """
    # 尝试删除任务
    success = transcription_service.delete_task(uni_key)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="任务不存在或删除失败"
        )
    
    return {"success": True, "message": "任务已成功删除"}

@router.post("/retry_task/{uni_key}")
async def retry_task(
    uni_key: str,
    transcription_service: TranscriptionService = Depends(get_transcription_service)
):
    """
    重试转写任务
    
    Args:
        uni_key: 任务唯一标识符
    """
    # 重置任务状态
    task = transcription_service.reset_task(uni_key)
    
    if not task:
        raise HTTPException(
            status_code=404,
            detail="任务不存在或重置失败"
        )
    
    # 将任务添加到Celery队列
    process_transcription.delay(uni_key)
    
    return {"success": True, "message": "任务已重新提交处理"}