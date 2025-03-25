#!/usr/bin/env python
"""
测试日志系统，验证按小时输出日志文件功能
"""
import logging
import time
from app.utils.logging_config import setup_logging, test_logging

if __name__ == "__main__":
    # 配置日志，使用DEBUG级别以显示所有日志
    setup_logging(log_level=logging.DEBUG)
    
    # 打印一些系统信息
    logging.info("开始测试日志系统...")
    logging.info("将在logs目录下创建按小时滚动的日志文件")
    
    # 执行测试
    test_logging()
    
    # 模拟应用程序运行并持续生成日志
    count = 0
    try:
        while count < 10:
            logging.info("测试日志消息 #%d", count)
            count += 1
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("测试被用户中断")
    
    logging.info("日志测试完成，请检查logs目录") 