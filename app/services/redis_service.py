import json
import logging
from redis import Redis
from typing import Any, Dict, Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis连接实例
redis_client = None

def get_redis_client() -> Redis:
    """
    获取Redis客户端实例
    """
    global redis_client
    if redis_client is None:
        logger.info(f"连接Redis服务器: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    return redis_client

def save_task(task_id: str, task_data: Dict[str, Any]) -> bool:
    """
    保存任务数据到Redis
    """
    try:
        client = get_redis_client()
        task_key = f"task:{task_id}"
        client.hset(task_key, mapping=task_data)
        client.expire(task_key, 86400)  # 设置24小时过期
        return True
    except Exception as e:
        logger.error(f"保存任务到Redis失败: {str(e)}")
        return False

def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """
    从Redis获取任务数据
    """
    try:
        client = get_redis_client()
        task_key = f"task:{task_id}"
        task_data = client.hgetall(task_key)
        return task_data if task_data else None
    except Exception as e:
        logger.error(f"从Redis获取任务失败: {str(e)}")
        return None

def update_task_status(task_id: str, status: str, **kwargs) -> bool:
    """
    更新任务状态
    """
    try:
        client = get_redis_client()
        task_key = f"task:{task_id}"
        update_data = {"status": status, **kwargs}
        client.hset(task_key, mapping=update_data)
        return True
    except Exception as e:
        logger.error(f"更新任务状态失败: {str(e)}")
        return False

def delete_task(task_id: str) -> bool:
    """
    删除任务
    """
    try:
        client = get_redis_client()
        task_key = f"task:{task_id}"
        client.delete(task_key)
        return True
    except Exception as e:
        logger.error(f"删除任务失败: {str(e)}")
        return False

def get_pending_tasks() -> List[Dict[str, Any]]:
    """
    获取所有等待处理的任务
    """
    try:
        client = get_redis_client()
        tasks = []
        for key in client.keys("task:*"):
            task_data = client.hgetall(key)
            if task_data.get("status") == "pending":
                task_data["task_id"] = key.split(":")[1]
                tasks.append(task_data)
        return tasks
    except Exception as e:
        logger.error(f"获取等待处理任务失败: {str(e)}")
        return []

def increment_user_request_count(user_id: int) -> int:
    """
    增加用户请求计数
    """
    try:
        client = get_redis_client()
        count_key = f"user:{user_id}:request_count"
        count = client.incr(count_key)
        # 设置24小时过期
        client.expire(count_key, 86400)
        return count
    except Exception as e:
        logger.error(f"增加用户请求计数失败: {str(e)}")
        return 0

def get_user_request_count(user_id: int) -> int:
    """
    获取用户请求计数
    """
    try:
        client = get_redis_client()
        count_key = f"user:{user_id}:request_count"
        count = client.get(count_key)
        return int(count) if count else 0
    except Exception as e:
        logger.error(f"获取用户请求计数失败: {str(e)}")
        return 0

def add_user_duration(user_id: int, duration: float) -> float:
    """
    增加用户音频处理时长
    """
    try:
        client = get_redis_client()
        duration_key = f"user:{user_id}:duration"
        
        # 获取当前值
        current = client.get(duration_key)
        current_duration = float(current) if current else 0
        
        # 增加新的时长
        new_duration = current_duration + duration
        client.set(duration_key, new_duration)
        
        # 设置24小时过期
        client.expire(duration_key, 86400)
        
        return new_duration
    except Exception as e:
        logger.error(f"增加用户音频处理时长失败: {str(e)}")
        return 0

def get_user_duration(user_id: int) -> float:
    """
    获取用户音频处理时长
    """
    try:
        client = get_redis_client()
        duration_key = f"user:{user_id}:duration"
        duration = client.get(duration_key)
        return float(duration) if duration else 0
    except Exception as e:
        logger.error(f"获取用户音频处理时长失败: {str(e)}")
        return 0 