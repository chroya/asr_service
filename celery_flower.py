"""
Celery Flower监控启动脚本

使用方式:
    python celery_flower.py
"""
import os
import sys
import logging
from app.core.celery import celery_app
from app.utils.logging_config import setup_logging

if __name__ == "__main__":
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("启动Celery Flower监控...")
    
    # 启动Flower
    sys.argv = ["celery", "-A", "app.core.celery.celery_app", "flower", "--port=5555"]
    os.system("celery -A app.core.celery.celery_app flower --port=5555") 