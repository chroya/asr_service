import os
import time
from datetime import datetime, timedelta
from celery import shared_task
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def ensure_directories_exist():
    """
    确保必要的目录存在
    
    检查并创建上传目录和转写结果目录，如果它们不存在的话。
    这是一个防御性编程的做法，确保系统运行时目录结构完整。
    """
    directories = [
        settings.UPLOAD_DIR,      # 音频文件上传目录
        settings.TRANSCRIPTION_DIR  # 转写结果存储目录
    ]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"创建目录: {directory}")

def cleanup_directory(directory: str, cutoff_time: datetime) -> None:
    """
    清理指定目录中的过期文件
    
    Args:
        directory: 要清理的目录路径
        cutoff_time: 截止时间，早于这个时间的文件将被删除
    """
    if not os.path.exists(directory):
        logger.warning(f"目录不存在，跳过清理: {directory}")
        return
        
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            # 只处理文件，跳过目录
            if not os.path.isfile(file_path):
                continue
                
            # 获取文件最后修改时间
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            # 如果文件早于截止时间，则删除
            if file_time < cutoff_time:
                try:
                    os.remove(file_path)
                    logger.info(f"已删除过期文件: {file_path}")
                except OSError as e:
                    logger.error(f"删除文件失败 {file_path}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"处理文件时出错 {file_path}: {str(e)}")
            continue

@shared_task
def cleanup_old_files():
    """
    定期清理任务：删除超过12小时的文件
    
    清理范围包括：
    1. 上传目录中的音频文件
    2. 转写结果目录中的JSON文件
    
    清理策略：
    - 基于文件的最后修改时间
    - 超过12小时的文件将被删除
    - 出错的文件会被记录但不会影响其他文件的处理
    """
    try:
        # 确保目录结构完整
        ensure_directories_exist()
        
        # 计算12小时前的时间点作为清理阈值
        cutoff_time = datetime.now() - timedelta(hours=settings.CLEAN_FILE_TIMEOUT)
        
        # 清理上传目录
        logger.info("开始清理上传目录...")
        cleanup_directory(settings.UPLOAD_DIR, cutoff_time)
        
        # 清理转写结果目录
        logger.info("开始清理转写结果目录...")
        cleanup_directory(settings.TRANSCRIPTION_DIR, cutoff_time)
        
        logger.info("文件清理任务完成")
                            
    except Exception as e:
        logger.error(f"清理任务执行出错: {str(e)}") 