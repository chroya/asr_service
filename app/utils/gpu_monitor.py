import subprocess
import logging
import os
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

def get_gpu_memory_info() -> Tuple[Optional[float], Optional[float]]:
    """
    获取GPU总显存和剩余显存信息
    
    Returns:
        Tuple[Optional[float], Optional[float]]: (总显存(MB), 剩余显存(MB))
        如果无法获取，则返回 (None, None)
    """
    try:
        # 执行nvidia-smi命令获取GPU信息
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.total,memory.free', '--format=csv,noheader,nounits'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        
        # 处理输出结果
        output = result.stdout.strip()
        if output:
            # 获取第一个GPU的信息（如果有多个GPU）
            gpu_info = output.split('\n')[0]
            total_memory, free_memory = map(float, gpu_info.split(','))
            
            logger.info(f"GPU总显存: {total_memory}MB, 剩余显存: {free_memory}MB")
            
            return total_memory, free_memory
    except Exception as e:
        logger.warning(f"获取GPU信息失败: {str(e)}")
    
    return None, None

def get_celery_concurrency() -> Optional[int]:
    """
    获取Celery当前并发进程数
    
    Returns:
        Optional[int]: Celery并发进程数，如果无法获取则返回None
    """
    try:
        # 从环境变量获取
        concurrency = os.environ.get('CELERY_WORKER_CONCURRENCY')
        if concurrency:
            return int(concurrency)
        
        # 如果环境变量没有设置，尝试获取活动的Celery进程数
        ps_result = subprocess.run(
            ['ps', 'aux', '|', 'grep', 'celery worker', '|', 'grep', '-v', 'grep', '|', 'wc', '-l'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        
        count = ps_result.stdout.strip()
        if count.isdigit():
            return int(count)
    except Exception as e:
        logger.warning(f"获取Celery并发进程数失败: {str(e)}")
    
    return None 