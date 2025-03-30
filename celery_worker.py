"""
Celery Worker启动脚本

使用方式:
    python celery_worker.py
"""
import logging
import sys
import os
import gc
import psutil
import signal
from app.core.celery import celery_app
from app.core.config import settings
from app.utils.logging_config import setup_logging


# 设置资源限制
def set_resource_limits():
    """设置资源限制，防止内存泄漏"""
    try:
        import resource
        # 设置软内存限制 (12GB)
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        resource.setrlimit(resource.RLIMIT_AS, (12 * 1024 * 1024 * 1024, hard))
        
        # 设置CPU时间限制 (1小时)
        soft, hard = resource.getrlimit(resource.RLIMIT_CPU)
        resource.setrlimit(resource.RLIMIT_CPU, (3600, hard))
    except Exception as e:
        print(f"设置资源限制失败: {str(e)}")

# 信号处理
def handle_exit_signal(signum, frame):
    """清理资源并退出"""
    logger.info(f"收到信号 {signum}，正在清理资源...")
    # 清理任何可能的子进程
    current_process = psutil.Process()
    children = current_process.children(recursive=True)
    for child in children:
        try:
            child.terminate()
        except:
            pass
    
    # 强制垃圾回收
    gc.collect()
    sys.exit(0)

if __name__ == "__main__":
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("启动Celery Worker...")
    
    # 注册信号处理
    signal.signal(signal.SIGTERM, handle_exit_signal)
    signal.signal(signal.SIGINT, handle_exit_signal)
    
    # 设置资源限制
    # set_resource_limits()
    
    # 打印注册的任务
    logger.info(f"注册的任务: {list(celery_app.tasks.keys())}")
    
    # 环境变量设置
    # os.environ['OMP_NUM_THREADS'] = '1'  # 限制OpenMP线程数
    # os.environ['MKL_NUM_THREADS'] = '1'  # 限制MKL线程数
    
    try:
        # 从配置中获取worker设置
        concurrency = settings.CELERY_WORKER_CONCURRENCY
        time_limit = settings.CELERY_TASK_TIME_LIMIT
        max_tasks_per_child = settings.CELERY_WORKER_MAX_TASKS_PER_CHILD
        
        logger.info(f"启动Celery Worker，并发数：{concurrency}，任务超时时间：{time_limit}秒，每个子进程最大任务数：{max_tasks_per_child}")

        # 启动Worker
        celery_app.worker_main([
            "worker",
            "--loglevel=info",
            "-P", "prefork",
            "--concurrency", str(concurrency),
            "--time-limit", str(time_limit),
            "--max-tasks-per-child", str(max_tasks_per_child),
            "--without-gossip",
            "--without-mingle"
        ])
    except Exception as e:
        logger.error(f"Celery Worker启动失败: {str(e)}")