import os
from celery import Celery
from app.core.config import settings

# 创建Celery实例
celery_app = Celery(
    "asr_service",
    broker=f"redis://{':' + settings.REDIS_PASSWORD + '@' if settings.REDIS_PASSWORD else ''}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
)

# 配置Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    task_time_limit=3600,  # 任务最多执行1小时
    worker_max_tasks_per_child=10,  # 每个worker最多处理10个任务，然后重启
    task_acks_late=True,  # 任务完成后才确认任务已经完成
    task_reject_on_worker_lost=True,  # worker崩溃后，任务会被重新执行
    result_backend=f"redis://{':' + settings.REDIS_PASSWORD + '@' if settings.REDIS_PASSWORD else ''}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
    imports=["app.tasks.transcription_tasks"],  # 直接导入任务模块
    broker_connection_retry_on_startup=True,  # 解决启动时的连接重试警告
)

# 自动发现任务 - 保留但增加直接导入
celery_app.autodiscover_tasks(["app.tasks"])

# 定义Beat定时任务
celery_app.conf.beat_schedule = {
    # 可以在这里添加定期任务
}

# 启动Celery时的命令行参数
celery_app.conf.worker_concurrency = os.cpu_count() or 2  # 根据CPU核心数设置并发数 