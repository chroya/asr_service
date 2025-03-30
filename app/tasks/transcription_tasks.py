import os
import logging
import time
from typing import Dict, Any, Optional
from celery import shared_task

from app.core.celery import celery_app
from app.services.transcription_service import TranscriptionService
from app.services.cloud_stats import CloudStatsService

logger = logging.getLogger(__name__)

# 服务实例
transcription_service = TranscriptionService()
cloud_stats_service = CloudStatsService()

def create_task_result(
    status: str,
    task_id: str,
    error: Optional[str] = None,
    timings: Optional[Dict[str, float]] = None,
    **extra_data
) -> Dict[str, Any]:
    """
    创建统一的任务结果格式
    
    Args:
        status: 任务状态 ('completed', 'failed', 'processing')
        task_id: 任务ID
        error: 错误信息(如果有)
        timings: 各步骤耗时信息
        **extra_data: 额外的数据字段
    
    Returns:
        Dict[str, Any]: 格式化的任务结果
    """
    result = {
        "status": status,
        "task_id": task_id,
        "timestamp": time.time()
    }
    
    if error:
        result["error"] = error
        
    if timings:
        result["timings"] = timings
        
    # 添加额外数据
    result.update(extra_data)
    
    return result

# 使用celery_app.task装饰器替代shared_task，确保任务直接注册到应用
@celery_app.task(name="process_transcription", bind=True)
def process_transcription(self, task_id: str):
    """
    使用Celery处理转写任务
    
    Args:
        self: Celery任务实例
        task_id: 任务ID
    """
    # 记录任务开始时间
    start_time = time.time()
    logger.info(f"开始处理转写任务: {task_id}")
    
    # 获取任务信息
    task = transcription_service.get_task(task_id)
    if not task:
        logger.error(f"任务不存在: {task_id}")
        return create_task_result(
            status="failed",
            task_id=task_id,
            error="任务不存在",
            timings={"task_received": time.time() - start_time}
        )
    
    # 获取客户端ID
    client_id = task.client_id
    
    try:
        # 调用同步处理方法
        async_result = process_task_sync(task_id, start_time)
        
        # 如果任务成功完成，报告任务完成
        if async_result['status'] == 'completed':
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
            code=1,
            message=f"处理失败: {str(e)}"
        )
        return create_task_result(
            status="failed",
            task_id=task_id,
            error=str(e),
            timings={
                "task_received": time.time() - start_time,
                "total_time": time.time() - start_time
            }
        )

def process_task_sync(task_id: str, start_time: float):
    """
    同步处理转写任务
    
    Args:
        task_id: 任务ID
        start_time: 任务开始时间
    
    Returns:
        dict: 包含处理结果的字典
    """
    # 记录任务接收时间
    task_received_time = time.time() - start_time
    
    # 获取任务信息
    task = transcription_service.get_task(task_id)
    if not task:
        logger.error(f"任务不存在: {task_id}")
        return create_task_result(
            status="failed",
            task_id=task_id,
            error="任务不存在",
            timings={"task_received": task_received_time}
        )
    
    # 检查文件是否存在
    if not os.path.exists(task.file_path):
        transcription_service.update_task(
            task_id,
            status="failed",
            error_message="文件不存在",
            code=1,
            message="文件不存在"
        )
        logger.error(f"任务音频文件不存在: {task.file_path}")
        return create_task_result(
            status="failed",
            task_id=task_id,
            error="文件不存在",
            timings={
                "task_received": task_received_time,
                "file_check": time.time() - start_time - task_received_time
            }
        )
    
    try:
        # 执行原有的TranscriptionService.process_task的同步版本
        result = transcription_service.process_task_sync(task_id)
        
        if result['status'] == 'completed':
            # 添加详细的时间信息
            timings = {
                "task_received": task_received_time,
                "model_loading": result.get('model_loading_time', 0),
                "transcription": result.get('transcription_time', 0),
                "speaker_diarization": result.get('diarization_time', 0) if task.extra_params.speaker else 0,
                "post_processing": result.get('post_processing_time', 0),
                "total_time": time.time() - start_time
            }
            
            return create_task_result(
                status="completed",
                task_id=task_id,
                audio_duration=result.get('audio_duration', 0),
                result=result.get('result', {}),
                timings=timings
            )
        else:
            return create_task_result(
                status="failed",
                task_id=task_id,
                error=result.get('error', "未知错误"),
                timings={
                    "task_received": task_received_time,
                    "total_time": time.time() - start_time
                }
            )
            
    except Exception as e:
        logger.exception(f"处理任务失败: {task_id} - {str(e)}")
        return create_task_result(
            status="failed",
            task_id=task_id,
            error=str(e),
            timings={
                "task_received": task_received_time,
                "total_time": time.time() - start_time
            }
        ) 