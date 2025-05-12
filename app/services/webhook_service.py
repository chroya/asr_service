import json
import logging
import requests
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)

class WebhookService:
    """
    Webhook服务：负责向外部系统发送webhook通知
    """
    
    def __init__(self):
        """初始化webhook服务"""
        # 从配置中读取Webhook接口地址
        self.webhook_url = settings.WEBHOOK_TRANSCRIPTION_URL
        self.timeout = settings.WEBHOOK_TIMEOUT
        # 重试相关参数
        self.max_retries = 2  # 最大重试次数
        self.retry_delay = 3  # 重试间隔（秒）
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    def send_transcription_complete(
        self,
        extra_params: Union[Dict[str, Any], BaseModel],
        result: str,
        code: int,
        use_time: int,
        jwt_token: Optional[str] = None
    ) -> bool:
        """
        发送转写完成的webhook通知（非阻塞）
        
        Args:
            extra_params: 给uploadfile的参数，可以是字典或Pydantic模型
            result: JSON文件下载地址
            code: 错误码，0表示成功
            use_time: 任务耗时，单位为秒
            jwt_token: JWT令牌，用于认证
            
        Returns:
            bool: 请求是否已提交（不代表发送成功）
        """
        try:
            # 如果extra_params是Pydantic模型，转换为字典
            if isinstance(extra_params, BaseModel):
                extra_params = extra_params.model_dump_json()
            # 如果extra_params是字典，转换为JSON字符串
            if isinstance(extra_params, dict):
                extra_params = json.dumps(extra_params)
            
            # 准备webhook数据
            webhook_data = {
                "extra_params": extra_params,
                "result": result,
                "code": code,
                "use_time": use_time
            }
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # 如果有JWT令牌，添加到请求头
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"
            
            # 提交异步任务到线程池
            self.executor.submit(
                self._send_webhook_with_retries,
                webhook_data,
                headers
            )
            
            return True
                
        except Exception as e:
            logger.exception(f"准备webhook数据失败: {str(e)}")
            return False
    
    def _send_webhook_with_retries(self, webhook_data: Dict[str, Any], headers: Dict[str, str]) -> None:
        """
        带重试的webhook发送实现（在线程池中执行）
        
        Args:
            webhook_data: webhook数据
            headers: HTTP请求头
        """
        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                if retry_count > 0:
                    logger.info(f"尝试第{retry_count}次重新发送webhook...")
                
                logger.info(f"发送Webhook通知: {json.dumps(webhook_data)}")
                
                response = requests.post(
                    self.webhook_url,
                    json=webhook_data,
                    timeout=self.timeout,
                    headers=headers
                )
                
                # 检查响应
                if response.status_code == 200:
                    logger.info(f"Webhook发送成功: {response.status_code}")
                    return
                else:
                    logger.warning(f"Webhook发送失败: 状态码 {response.status_code}, 响应: {response.text}")
                    # 如果已达最大重试次数，放弃重试
                    if retry_count >= self.max_retries:
                        logger.error(f"Webhook发送失败，已达最大重试次数({self.max_retries})，放弃重试")
                        return
                    
                    # 否则增加重试次数并等待
                    retry_count += 1
                    time.sleep(self.retry_delay)
            
            except Exception as e:
                logger.warning(f"发送webhook异常: {str(e)}")
                # 如果已达最大重试次数，放弃重试
                if retry_count >= self.max_retries:
                    logger.exception(f"Webhook发送异常，已达最大重试次数({self.max_retries})，放弃重试")
                    return
                
                # 否则增加重试次数并等待
                retry_count += 1
                time.sleep(self.retry_delay)


# 单例模式
_webhook_service = None

def get_webhook_service() -> WebhookService:
    """
    获取WebhookService实例（单例模式）
    
    Returns:
        WebhookService: Webhook服务实例
    """
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService()
    return _webhook_service 