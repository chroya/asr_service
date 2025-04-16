#!/usr/bin/env python3
import logging
import sys
from datetime import datetime
from typing import Dict, Any

from app.services.redis_service import RedisService
from app.schemas.transcription import TranscriptionTask
from app.core.config import settings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_timestamp(value: Any) -> str:
    """将时间戳转换为ISO格式字符串"""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).isoformat()
    return value

def fix_extra_params(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """修复extra_params字段"""
    if 'extra_params' in task_data and task_data['extra_params']:
        extra_params = task_data['extra_params']
        # 确保whisper_arch字段存在
        if 'whisper_arch' not in extra_params:
            extra_params['whisper_arch'] = settings.WHISPER_MODEL_NAME
        task_data['extra_params'] = extra_params
    return task_data

def migrate_timestamps():
    """迁移Redis中的时间戳格式"""
    try:
        # 更新Redis连接初始化
        redis_service = RedisService()
        redis = redis_service.get_client(prefix="transcription:")
        
        # 获取所有任务ID
        task_ids = redis.get_keys("*")
        if not task_ids:
            logger.info("没有找到需要迁移的任务")
            return
        
        logger.info(f"找到 {len(task_ids)} 个任务需要迁移")
        
        # 迁移每个任务
        success_count = 0
        error_count = 0
        
        for task_id in task_ids:
            try:
                # 获取任务数据
                task_data = redis.get(task_id)
                if not task_data:
                    continue
                
                # 跳过非字典类型的数据
                if not isinstance(task_data, dict):
                    logger.warning(f"任务 {task_id} 的数据不是字典类型，跳过")
                    continue
                
                # 转换时间戳字段
                timestamp_fields = ['started_at', 'completed_at', 'created_at']
                for field in timestamp_fields:
                    if field in task_data and task_data[field]:
                        task_data[field] = convert_timestamp(task_data[field])
                
                # 修复extra_params字段
                task_data = fix_extra_params(task_data)
                
                # 验证数据格式
                try:
                    # 尝试转换为TranscriptionTask对象以验证数据格式
                    TranscriptionTask(**task_data)
                    
                    # 保存更新后的数据
                    redis.save(task_id, task_data)
                    success_count += 1
                    
                    if success_count % 100 == 0:
                        logger.info(f"已迁移 {success_count} 个任务")
                        
                except Exception as e:
                    logger.error(f"任务 {task_id} 数据格式验证失败: {str(e)}")
                    error_count += 1
                    
            except Exception as e:
                logger.error(f"处理任务 {task_id} 时出错: {str(e)}")
                error_count += 1
        
        logger.info(f"迁移完成！成功: {success_count}, 失败: {error_count}")
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_timestamps() 