from datetime import datetime
import os
import logging
import time
from typing import Dict, Any, Optional, Tuple

from app.core.celery import celery_app
from app.core.config import settings
from app.services.transcription_service import TranscriptionService
from app.services.cloud_stats import CloudStatsService
from app.services.mqtt_service import get_mqtt_service
from app.services.webhook_service import get_webhook_service
from app.utils.error_codes import (
    SUCCESS, ERROR_TASK_NOT_FOUND, ERROR_FILE_NOT_FOUND, 
    ERROR_PROCESSING_FAILED, ERROR_MAX_RETRY_EXCEEDED, get_error_message
)
from app.utils import get_download_url

logger = logging.getLogger(__name__)

# 服务实例
transcription_service = TranscriptionService()
cloud_stats_service = CloudStatsService()
webhook_service = get_webhook_service()

# 从配置中获取最大重试次数
MAX_RETRY_COUNT = settings.MAX_TRANSCRIPTION_RETRY

def create_task_result(
    status: str,
    task_id: str,
    uni_key: str,
    error: Optional[str] = None,
    timings: Optional[Dict[str, float]] = None,
    code: int = SUCCESS,
    **extra_data
) -> Dict[str, Any]:
    """
    创建统一的任务结果格式
    
    Args:
        status: 任务状态 ('completed', 'failed', 'processing')
        task_id: 任务ID
        uni_key: 任务唯一标识符
        error: 错误信息(如果有)
        timings: 各步骤耗时信息
        code: 错误码
        **extra_data: 额外的数据字段
    
    Returns:
        Dict[str, Any]: 格式化的任务结果
    """
    result = {
        "status": status,
        "task_id": task_id,
        "uni_key": uni_key,
        "timestamp": time.time(),
        "code": code
    }
    
    if error:
        result["error"] = error
        
    if timings:
        result["timings"] = timings
        
    # 添加额外数据
    result.update(extra_data)
    
    return result

def check_task_prerequisites(uni_key: str, start_time: float) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    检查任务的前置条件（任务是否存在，文件是否存在等）
    
    Args:
        uni_key: 任务唯一标识符
        start_time: 任务开始时间
        
    Returns:
        Tuple[Optional[Dict], Optional[Dict]]: (task, error_result)
        如果检查通过，返回 (task, None)
        如果检查失败，返回 (None, error_result)
    """
    # 获取任务信息
    task = transcription_service.get_task(uni_key)
    if not task:
        error_result = create_task_result(
            status="failed",
            task_id="unknown",  # 任务不存在时无法获取task_id
            uni_key=uni_key,
            error="任务不存在",
            code=ERROR_TASK_NOT_FOUND,
            timings={"task_received": time.time() - start_time}
        )
        return None, error_result
    
    # 检查文件是否存在
    if not os.path.exists(task.file_path):
        transcription_service.update_task(
            uni_key,
            status="failed",
            error_message=get_error_message(ERROR_FILE_NOT_FOUND),
            code=ERROR_FILE_NOT_FOUND,
            message=get_error_message(ERROR_FILE_NOT_FOUND)
        )
        error_result = create_task_result(
            status="failed",
            task_id=task.task_id,
            uni_key=uni_key,
            error=get_error_message(ERROR_FILE_NOT_FOUND),
            code=ERROR_FILE_NOT_FOUND,
            timings={
                "task_received": time.time() - start_time,
                "file_check": time.time() - start_time
            }
        )
        return None, error_result
    
    return task, None

@celery_app.task(name="process_transcription", bind=True)
def process_transcription(self, uni_key: str):
    """
    使用Celery处理转写任务
    
    Args:
        self: Celery任务实例
        uni_key: 任务唯一标识符
    """
    # 记录任务开始时间
    start_time = time.time()
    logger.info(f"开始处理转写任务: {uni_key}")
    
    # 检查任务前置条件
    task, error_result = check_task_prerequisites(uni_key, start_time)
    if error_result:
        # 发送失败通知
        get_mqtt_service().send_transcription_complete(
            task_id=error_result.get("task_id", "unknown"),
            code=error_result["code"],
            message=error_result["error"]
        )
        
        # 发送失败的Webhook通知 - 前置条件检查失败
        webhook_service.send_transcription_complete(
            extra_params={},  # 没有任务信息时使用空字典
            result="",  # 失败时没有 JSON 文件下载地址
            code=error_result["code"],
            use_time=int(time.time() - start_time),
            jwt_token=task.jwt_token if task else None
        )
        
        return error_result
    
    # 检查重试次数
    current_retry_count = task.retry_count
    logger.info(f"任务 {uni_key} 当前重试次数: {current_retry_count}")
    
    # 如果重试次数超过最大值，标记为失败并返回
    if current_retry_count >= MAX_RETRY_COUNT:
        error_msg = f"任务重试次数已达上限({MAX_RETRY_COUNT}次)"
        
        # 更新任务状态
        transcription_service.update_task(
            uni_key,
            status="failed",
            error_message=error_msg,
            code=ERROR_MAX_RETRY_EXCEEDED,
            message=get_error_message(ERROR_MAX_RETRY_EXCEEDED, error_msg)
        )
        
        # 发送失败通知
        get_mqtt_service().send_transcription_complete(
            task_id=task.task_id,
            code=ERROR_MAX_RETRY_EXCEEDED,
            message=error_msg
        )
        
        # 发送失败的Webhook通知
        webhook_service.send_transcription_complete(
            extra_params=task.extra_params or {},
            result="",  # 失败时没有 JSON 文件下载地址
            code=ERROR_MAX_RETRY_EXCEEDED,
            use_time=int(time.time() - start_time),
            jwt_token=task.jwt_token
        )
        
        error_result = create_task_result(
            status="failed",
            task_id=task.task_id,
            uni_key=uni_key,
            error=error_msg,
            code=ERROR_MAX_RETRY_EXCEEDED,
            timings={"task_received": time.time() - start_time}
        )
        
        return error_result
    
    try:
        # 更新任务状态为处理中
        transcription_service.update_task(
            uni_key,
            status="processing",
            started_at=datetime.now().isoformat()
        )
        
        # 执行转写处理
        result = transcription_service.process_task_sync(uni_key)
        
        if result['status'] == 'completed':
            audio_duration = result.get('audio_duration', 0)
            
            # 报告任务完成
            cloud_stats_service.report_task_completion(task.client_id, audio_duration)
            
            # 使用结果文件的文件名拼出下载URL
            download_url = get_download_url(task.result_path)
            # 发送Webhook通知
            webhook_service.send_transcription_complete(
                extra_params=task.extra_params or {},
                result= download_url,  # JSON 文件下载地址
                code=SUCCESS,
                use_time=int(time.time() - start_time),
                jwt_token=task.jwt_token if task else None
            )
            
            # 发送成功的MQTT通知
            get_mqtt_service().send_transcription_complete(task.task_id, code=SUCCESS)
            
            # 创建成功结果
            return create_task_result(
                status="completed",
                task_id=task.task_id,
                uni_key=uni_key,
                code=SUCCESS,
                audio_duration=audio_duration,
                result=result.get('result', {}),
                timings={
                    "total_time": time.time() - start_time,
                    "model_loading": result.get('model_loading_time', 0),
                    "transcription": result.get('transcription_time', 0),
                    "diarization": result.get('diarization_time', 0),
                    "post_processing": result.get('post_processing_time', 0)
                }
            )
        else:
            # 处理失败情况
            error_msg = result.get('error', "未知错误")
            # 获取服务返回的错误码，如果没有则使用 ERROR_PROCESSING_FAILED
            error_code = result.get('code', ERROR_PROCESSING_FAILED)
            error_result = create_task_result(
                status="failed",
                task_id=task.task_id,
                uni_key=uni_key,
                error=error_msg,
                code=error_code,
                timings={"total_time": time.time() - start_time}
            )
            
            # 发送失败的MQTT通知
            get_mqtt_service().send_transcription_complete(
                task.task_id, 
                code=error_code,
                message=error_msg
            )
            
            # 发送失败情况的Webhook通知
            webhook_service.send_transcription_complete(
                extra_params=task.extra_params or {},
                result="",  # 失败时没有 JSON 文件下载地址
                code=error_code,
                use_time=int(time.time() - start_time),
                jwt_token=task.jwt_token if task else None
            )
            
            return error_result
            
    except Exception as e:
        # 捕获任何未处理的异常
        error_msg = str(e)
        logger.exception(f"处理任务异常: {uni_key} - {error_msg}")
        
        # 更新任务状态
        transcription_service.update_task(
            uni_key,
            status="failed",
            error_message=error_msg,
            code=ERROR_PROCESSING_FAILED,
            message=get_error_message(ERROR_PROCESSING_FAILED, error_msg)
        )
        
        # 增加重试次数并将任务重新排队（如果未达到最大重试次数）
        new_retry_count = current_retry_count + 1
        if new_retry_count < MAX_RETRY_COUNT:
            # 更新重试计数
            transcription_service.update_task(uni_key, retry_count=new_retry_count)
            
            # 重新排队
            logger.info(f"重新排队任务 {uni_key}，重试次数: {new_retry_count}/{MAX_RETRY_COUNT}")
            self.retry(countdown=5, max_retries=MAX_RETRY_COUNT, exc=e)
        
        # 发送失败通知
        get_mqtt_service().send_transcription_complete(
            task.task_id,
            code=ERROR_PROCESSING_FAILED,
            message=error_msg
        )
        
        # 发送失败的Webhook通知
        webhook_service.send_transcription_complete(
            extra_params=task.extra_params or {},
            result="",  # 失败时没有 JSON 文件下载地址
            code=ERROR_PROCESSING_FAILED,
            use_time=int(time.time() - start_time),
            jwt_token=task.jwt_token
        )
        
        error_result = create_task_result(
            status="failed",
            task_id=task.task_id,
            uni_key=uni_key,
            error=error_msg,
            code=ERROR_PROCESSING_FAILED,
            timings={"total_time": time.time() - start_time}
        )
        
        return error_result 