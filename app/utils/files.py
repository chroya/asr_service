import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import settings

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

async def get_file_size_mb(file: UploadFile) -> float:
    """
    获取上传文件的大小（MB）
    
    Args:
        file: 上传的文件对象
        
    Returns:
        float: 文件大小（MB）
    """
    # 保存当前文件位置
    current_position = file.file.tell()
    
    # 移动到文件末尾以获取大小
    file.file.seek(0, 2)  # 2表示从文件末尾开始
    file_size = file.file.tell()
    
    # 恢复原始位置
    file.file.seek(current_position)
    
    # 转换为MB
    return file_size / (1024 * 1024)

async def save_upload_file(file: UploadFile, task_id: str) -> str:
    """
    保存上传的文件
    
    Args:
        file: 上传的文件对象
        task_id: 任务ID，用于命名文件
        
    Returns:
        str: 保存的文件路径
    """
    # 确保上传目录存在
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # 确定文件扩展名
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    # 创建文件路径
    file_path = os.path.join(settings.UPLOAD_DIR, f"{task_id}{file_ext}")
    
    # 将文件保存到指定路径
    with open(file_path, "wb") as buffer:
        # 重置文件指针
        file.file.seek(0)
        
        # 复制文件内容
        shutil.copyfileobj(file.file, buffer)
    
    return file_path

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