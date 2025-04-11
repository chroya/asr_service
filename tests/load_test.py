#!/usr/bin/env python
"""
ASR服务转写接口压力测试脚本

这个脚本使用asyncio和aiohttp来模拟大量并发用户请求ASR服务的转写API，
用于测试服务的性能和稳定性。

使用方法:
    python load_test.py --url http://localhost:8000/api/uploadfile --users 10 --duration 60

作者：Cursor
"""

import hashlib
import os
import sys
import time
import aiohttp
import asyncio
import argparse
from pathlib import Path
import logging
import random
import uuid
from datetime import datetime
import json
from typing import List, Dict, Any, Optional, Tuple

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('tests/load_test.log')
    ]
)
logger = logging.getLogger("load_test")

# 测试统计数据
class TestStats:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.response_times = []
        self.start_time = None
        self.end_time = None
        
    def add_result(self, success: bool, response_time: float):
        """添加测试结果"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.response_times.append(response_time)
    
    def print_summary(self):
        """打印测试结果摘要"""
        if not self.response_times:
            logger.error("没有测试数据")
            return
        
        duration = (self.end_time - self.start_time).total_seconds()
        avg_response_time = sum(self.response_times) / len(self.response_times)
        max_response_time = max(self.response_times)
        min_response_time = min(self.response_times)
        success_rate = (self.successful_requests / self.total_requests) * 100 if self.total_requests > 0 else 0
        
        # 计算不同百分位的响应时间
        sorted_times = sorted(self.response_times)
        p50 = sorted_times[int(len(sorted_times) * 0.5)]
        p90 = sorted_times[int(len(sorted_times) * 0.9)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        # 计算每秒请求数
        rps = self.total_requests / duration if duration > 0 else 0
        
        logger.info("=" * 60)
        logger.info("测试结果摘要")
        logger.info("=" * 60)
        logger.info(f"总请求数: {self.total_requests}")
        logger.info(f"成功请求数: {self.successful_requests}")
        logger.info(f"失败请求数: {self.failed_requests}")
        logger.info(f"成功率: {success_rate:.2f}%")
        logger.info(f"总测试时间: {duration:.2f}秒")
        logger.info(f"每秒请求数(RPS): {rps:.2f}")
        logger.info("-" * 60)
        logger.info(f"最小响应时间: {min_response_time:.2f}秒")
        logger.info(f"最大响应时间: {max_response_time:.2f}秒")
        logger.info(f"平均响应时间: {avg_response_time:.2f}秒")
        logger.info(f"50%请求响应时间: {p50:.2f}秒")
        logger.info(f"90%请求响应时间: {p90:.2f}秒") 
        logger.info(f"95%请求响应时间: {p95:.2f}秒")
        logger.info(f"99%请求响应时间: {p99:.2f}秒")
        logger.info("=" * 60)

async def send_upload_request(
    session: aiohttp.ClientSession, 
    url: str, 
    audio_file_path: str,
    test_stats: TestStats,
    user_id: int
) -> Tuple[bool, Dict[str, Any]]:
    """
    发送文件上传请求
    
    Args:
        session: HTTP会话
        url: 上传URL
        audio_file: 音频文件路径
        test_stats: 测试统计对象
        user_id: 模拟用户ID
        
    Returns:
        (是否成功, 响应数据)
    """
    try:
        # 生成唯一ID
        u_id = 123  # 用户ID，根据实际情况修改
        uuid_str = str(uuid.uuid4()).replace("-", "")
        
        # 计算文件的md5作为task_id
        with open(audio_file_path, 'rb') as f:
            file_hash = hashlib.md5(f.read(2*1024*1024)).hexdigest()  # 读取前2MB计算md5
        
        task_id = f"{file_hash}"
        
        # 准备文件和参数
        filename = os.path.basename(audio_file_path)
        
        # 构建extra_params
        extra_params = {
            "u_id": u_id,
            "record_file_name": filename,
            "uuid": uuid_str,
            "task_id": task_id,
            "mode_id": 10001,  # 默认模板ID，根据需要修改
            "language": "auto",  # 自动检测语言
            "ai_mode": "GPT-4o",  # 使用的AI模式
            "speaker": False  # 是否启用说话人分离
        }
        
        # 发送请求
        data = aiohttp.FormData()
        data.add_field('file',
                      open(audio_file_path, 'rb'),
                      filename=filename,
                      content_type='audio/mpeg')
        data.add_field('extra_params',
                      json.dumps(extra_params),
                      content_type='application/json')

        logger.info(f"用户{user_id} - 上传文件: {filename}")
        logger.debug(f"用户{user_id} - 参数: {json.dumps(extra_params, indent=2, ensure_ascii=False)}")

        # 记录请求开始时间
        start_time = time.time()
        
        # 发送请求
        async with session.post(url, data=data, timeout=300) as response:
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 解析响应
            response_data = await response.json()
            success = response.status == 200  
            
            # 记录结果
            test_stats.add_result(success, response_time)
            
            if success:
                logger.info(f"用户{user_id} - 请求成功: task_id={response_data.get('task_id', 'unknown')}, 响应时间={response_time:.2f}秒")
                logger.info(f"用户{user_id} - 状态: {response_data.get('status', 'unknown')}")
            else:
                logger.error(f"用户{user_id} - 请求失败: status={response.status}, response={response_data}, 响应时间={response_time:.2f}秒")
            
            return success, response_data
    
    except Exception as e:
        response_time = time.time() - start_time
        test_stats.add_result(False, response_time)
        logger.error(f"用户{user_id} - 请求异常: {str(e)}, 响应时间={response_time:.2f}秒")
        return False, {"error": str(e)}

async def user_task(
    user_id: int, 
    url: str, 
    audio_files: List[str], 
    test_stats: TestStats,
    duration: int
):
    """
    模拟单个用户的任务
    
    Args:
        user_id: 用户ID
        url: API URL
        audio_files: 音频文件列表
        test_stats: 测试统计对象
        duration: 测试持续时间(秒)
    """
    logger.info(f"用户{user_id}开始测试")
    
    # 创建会话
    async with aiohttp.ClientSession() as session:
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # 随机选择一个音频文件
            audio_file = random.choice(audio_files)
            
            # 发送请求
            await send_upload_request(session, url, audio_file, test_stats, user_id)
            
            # 随机等待一段时间再发送下一个请求(0.5-3秒)
            wait_time = random.uniform(0.5, 3)
            await asyncio.sleep(wait_time)
    
    logger.info(f"用户{user_id}完成测试")

async def run_load_test(
    url: str, 
    concurrent_users: int, 
    duration: int,
    audio_files: List[str]
):
    """
    运行负载测试
    
    Args:
        url: API URL
        concurrent_users: 并发用户数
        duration: 测试持续时间(秒)
        audio_files: 音频文件列表
    """
    logger.info(f"开始负载测试 - URL: {url}, 并发用户: {concurrent_users}, 持续时间: {duration}秒")
    
    # 初始化测试统计数据
    test_stats = TestStats()
    test_stats.start_time = datetime.now()
    
    # 创建用户任务
    tasks = []
    for i in range(concurrent_users):
        task = asyncio.create_task(user_task(i+1, url, audio_files, test_stats, duration))
        tasks.append(task)
    
    # 等待所有任务完成
    await asyncio.gather(*tasks)
    
    # 记录结束时间
    test_stats.end_time = datetime.now()
    
    # 打印测试结果
    test_stats.print_summary()

def find_audio_files(directory: str) -> List[str]:
    """查找目录中的音频文件"""
    audio_extensions = ['.mp3', '.wav', '.m4a', '.ogg', '.flac']
    audio_files = []
    
    for ext in audio_extensions:
        audio_files.extend(list(Path(directory).glob(f"**/*{ext}")))
    
    return [str(f) for f in audio_files]

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='ASR服务转写接口压力测试')
    
    parser.add_argument('--url', type=str, default='http://localhost:8000/api/uploadfile',
                        help='ASR服务转写API的URL')
    
    parser.add_argument('--users', type=int, default=10,
                        help='并发用户数')
    
    parser.add_argument('--duration', type=int, default=10,
                        help='测试持续时间(秒)')
    
    parser.add_argument('--audio-dir', type=str, default='./uploads',
                        help='音频样本存放目录')
    
    return parser.parse_args()

def main():
    # 解析参数
    args = parse_arguments()
    
    # 查找音频文件
    audio_files = find_audio_files(args.audio_dir)
    
    if not audio_files:
        logger.error(f"在目录 {args.audio_dir} 中未找到音频文件")
        sys.exit(1)
    
    logger.info(f"找到 {len(audio_files)} 个音频文件用于测试")
    
    # 运行测试
    asyncio.run(run_load_test(
        url=args.url,
        concurrent_users=args.users,
        duration=args.duration,
        audio_files=audio_files
    ))

if __name__ == "__main__":
    main() 