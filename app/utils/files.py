import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Union, Callable
import asyncio
import aiofiles
from fastapi import UploadFile
import logging

from app.core.config import settings

# 定义常量
CHUNK_SIZE = 1024 * 1024  # 1MB 的块大小
logger = logging.getLogger(__name__)

async def validate_audio_file(file: UploadFile) -> bool:
    """
    验证上传文件是否为有效的音频文件
    
    Args:
        file: 上传的文件对象
        
    Returns:
        bool: 是否为有效的音频文件
    """
    # 检查文件类型
    valid_extensions = [".mp3", ".wav", ".m4a", ".ogg", ".flac"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    # 检查MIME类型（如果可用）
    content_type = file.content_type
    valid_mime_types = [
        "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", 
        "audio/m4a", "audio/ogg", "audio/flac", "audio/x-flac"
    ]
    
    # 至少需要满足一个条件：扩展名有效或MIME类型有效
    return (file_ext in valid_extensions) or (content_type in valid_mime_types)

async def get_file_size_bytes(file: UploadFile) -> int:
    """
    获取上传文件的大小（字节）- 优化的异步实现
    
    Args:
        file: 上传的文件对象
        
    Returns:
        int: 文件大小（字节）
    """
    try:
        # 尝试直接从文件对象获取大小
        if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
            current_position = file.file.tell()
            file.file.seek(0, 2)  # 移动到文件末尾
            file_size = file.file.tell()
            file.file.seek(current_position)  # 恢复位置
            return file_size
    except Exception:
        pass
    
    # 如果无法直接获取，使用content-length头
    if 'content-length' in file.headers:
        return int(file.headers['content-length'])
    
    # 最后的备选方案：读取整个文件（不推荐）
    content = await file.read()
    await file.seek(0)  # 重置文件指针
    return len(content)

async def get_file_size_mb(file: UploadFile) -> float:
    """
    获取上传文件的大小（MB）
    
    Args:
        file: 上传的文件对象
        
    Returns:
        float: 文件大小（MB）
    """
    bytes_size = await get_file_size_bytes(file)
    return bytes_size / (1024 * 1024)

async def save_upload_file(
    file: UploadFile,
    uni_key: str,
    progress_callback: Optional[Callable[[float], None]] = None,
    return_size: bool = False
) -> str:
    """
    异步保存上传的文件，支持分块处理和进度回调
    
    Args:
        file: 上传的文件对象
        uni_key: 任务唯一标识符，用于命名文件
        progress_callback: 进度回调函数，参数为上传进度(0-100)
        return_size: 是否返回文件大小
        
    Returns:
        Union[str, tuple[str, float]]: 如果return_size为True，返回(文件路径, 文件大小MB)的元组，
                                      否则只返回文件路径
    """
    # 确保上传目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # 确定文件扩展名和保存路径
    file_path = os.path.join(settings.UPLOAD_DIR, f"{uni_key}_{file.filename}")
    
    total_size = 0
    file_size_mb = await get_file_size_mb(file)
    
    try:
        async with aiofiles.open(file_path, "wb") as buffer:
            while True:
                # 分块读取文件内容
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                
                # 异步写入文件块
                await buffer.write(chunk)
                
                # 更新进度
                total_size += len(chunk)
                if progress_callback:
                    progress = (total_size / (file_size_mb * 1024 * 1024)) * 100
                    progress_callback(min(progress, 100))
                
                # 让出控制权给其他协程
                await asyncio.sleep(0)
        
        logger.info(f"文件保存成功: {file_path}, 大小: {file_size_mb:.2f}MB")
        if return_size:
            return (file_path, file_size_mb)
        return file_path
        
    except Exception as e:
        # 如果保存失败，清理临时文件
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"文件保存失败: {str(e)}")
        raise e

def delete_file(file_path: str) -> bool:
    """
    删除文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否成功删除
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False 