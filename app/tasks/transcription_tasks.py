import os
import logging
from celery import shared_task

from app.core.celery import celery_app
from app.services.transcription_service import TranscriptionService
from app.services.cloud_stats import CloudStatsService

logger = logging.getLogger(__name__)

# 服务实例
transcription_service = TranscriptionService()
cloud_stats_service = CloudStatsService()

# 使用celery_app.task装饰器替代shared_task，确保任务直接注册到应用
@celery_app.task(name="process_transcription", bind=True)
def process_transcription(self, task_id: str):
    """
    使用Celery处理转写任务
    
    Args:
        self: Celery任务实例
        task_id: 任务ID
    """
    logger.info(f"开始处理转写任务: {task_id}")
    
    # 获取任务信息
    task = transcription_service.get_task(task_id)
    if not task:
        logger.error(f"任务不存在: {task_id}")
        return {
            "status": "failed",
            "error": "任务不存在"
        }
    
    # 获取客户端ID
    client_id = task.client_id
    
    try:
        # 调用原有的process_task方法处理任务
        # 注意：Celery任务中不能使用异步函数，所以需要确保process_task是同步的
        # 我们不能使用原来的回调函数，而是直接在任务完成后调用统计服务
        async_result = process_task_sync(task_id)
        
        # 如果任务成功完成，报告任务完成
        if async_result.get('status') == 'completed':
            audio_duration = async_result.get('audio_duration', 0)
            cloud_stats_service.report_task_completion(client_id, audio_duration)
            
        return async_result
        
    except Exception as e:
        logger.exception(f"处理转写任务失败: {task_id} - {str(e)}")
        # 更新任务状态为失败
        transcription_service.update_task(
            task_id,
            status="failed",
            error_message=str(e),
            code=1,  # 处理失败错误码
            message=f"处理失败: {str(e)}"
        )
        return {
            "status": "failed",
            "error": str(e)
        }

def process_task_sync(task_id: str):
    """
    同步处理转写任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        dict: 包含处理结果的字典
    """
    # 获取任务信息
    task = transcription_service.get_task(task_id)
    if not task:
        logger.error(f"任务不存在: {task_id}")
        return {"status": "failed", "error": "任务不存在"}
    
    # 检查文件是否存在
    if not os.path.exists(task.file_path):
        transcription_service.update_task(
            task_id,
            status="failed",
            error_message="文件不存在",
            code=1,  # 文件不存在错误码
            message="文件不存在"
        )
        logger.error(f"任务音频文件不存在: {task.file_path}")
        return {"status": "failed", "error": "文件不存在"}
    
    try:
        # 执行原有的TranscriptionService.process_task的同步版本
        result = transcription_service.process_task_sync(task_id)
        return result
    except Exception as e:
        logger.exception(f"处理任务失败: {task_id} - {str(e)}")
        return {"status": "failed", "error": str(e)} 