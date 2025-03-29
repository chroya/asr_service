import os
import logging
from logging.handlers import TimedRotatingFileHandler
import time
from pathlib import Path

from app.core.config import settings

def setup_logging(
    log_level=None, 
    log_format=None,
    console_output=None
):
    """
    配置日志系统
    
    Args:
        log_level: 日志级别，默认使用配置文件中的值
        log_format: 日志格式，默认使用配置文件中的值
        console_output: 是否输出到控制台，默认使用配置文件中的值
    """
    # 从配置中获取默认值
    if log_level is None:
        log_level = getattr(logging, settings.LOG_LEVEL)
    if log_format is None:
        log_format = settings.LOG_FORMAT
    if console_output is None:
        console_output = settings.LOG_CONSOLE_OUTPUT
    
    # 确保logs目录存在
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建格式化器
    formatter = logging.Formatter(log_format)
    
    # 添加文件处理器（按小时滚动）
    # 检查是否是通过supervisord运行的
    is_supervisord = 'SUPERVISOR_ENABLED' in os.environ or os.environ.get('SUPERVISOR_PROCESS_NAME') is not None
    
    # 在非supervisord环境或明确要求时添加文件处理器
    if not is_supervisord or settings.LOG_ALWAYS_TO_FILE:
        log_file = log_dir / settings.LOG_FILE
        file_handler = TimedRotatingFileHandler(
            filename=log_file,
            when="H",
            interval=1,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        # 设置后缀格式为yyyy-MM-dd_HH
        file_handler.suffix = "%Y-%m-%d_%H"
        root_logger.addHandler(file_handler)
        logging.info("日志系统已初始化，日志文件将按小时存储在 %s 目录", log_dir.absolute())
    
    # 如果需要控制台输出，添加控制台处理器
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        root_logger.addHandler(console_handler)

def test_logging():
    """测试日志记录功能"""
    loggers = [
        logging.getLogger("app"),
        logging.getLogger("app.api"),
        logging.getLogger("app.services"),
        logging.getLogger("app.core")
    ]
    
    for logger in loggers:
        logger.debug("这是一条调试日志")
        logger.info("这是一条信息日志")
        logger.warning("这是一条警告日志")
        logger.error("这是一条错误日志")
    
    logging.info("日志测试完成")

if __name__ == "__main__":
    setup_logging(log_level=logging.DEBUG)
    test_logging() 