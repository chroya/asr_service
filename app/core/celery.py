import os
from celery import Celery
from app.core.config import settings

# 创建Celery实例
celery_app = Celery(
    "asr_service",
    broker=f"redis://{':' + settings.REDIS_PASSWORD + '@' if settings.REDIS_PASSWORD else ''}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB_CELERY}"
)

# 配置Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    task_acks_late=True,  # 任务完成后才确认任务已经完成
    task_reject_on_worker_lost=True,  # worker崩溃后，任务会被重新执行
    result_backend=f"redis://{':' + settings.REDIS_PASSWORD + '@' if settings.REDIS_PASSWORD else ''}{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB_CELERY}",
    imports=["app.tasks.transcription_tasks", "app.tasks.cleanup_tasks"],  # 添加cleanup_tasks到导入列表
    broker_connection_retry_on_startup=True,  # 解决启动时的连接重试警告
)

# 自动发现任务 - 保留但增加直接导入
celery_app.autodiscover_tasks(["app.tasks"])

# 定义Beat定时任务
celery_app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'app.tasks.cleanup_tasks.cleanup_old_files',
        'schedule': 3600.0,  # 每小时执行一次
    },
}
