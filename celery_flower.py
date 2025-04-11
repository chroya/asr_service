"""
Celery Flower监控启动脚本

使用方式:
    python celery_flower.py
"""
import os
import subprocess
import sys
import logging
from app.core.celery import celery_app
from app.utils.logging_config import setup_logging

if __name__ == "__main__":
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("启动Celery Flower监控...")
    
    # 设置 sys.argv
    sys.argv = ["celery", "-A", "app.core.celery.celery_app", "flower", "--port=5555"]

    # 使用 subprocess.run 启动 Flower
    subprocess.run(sys.argv)