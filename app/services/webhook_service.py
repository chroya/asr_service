import json
import logging
import requests
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
    
    def send_transcription_complete(
        self,
        extra_params: Union[Dict[str, Any], BaseModel],
        result: str,
        code: int,
        use_time: int,
        jwt_token: Optional[str] = None
    ) -> bool:
        """
        发送转写完成的webhook通知
        
        Args:
            extra_params: 给uploadfile的参数，可以是字典或Pydantic模型
            result: JSON文件下载地址
            code: 错误码，0表示成功
            use_time: 任务耗时，单位为秒
            jwt_token: JWT令牌，用于认证
            
        Returns:
            bool: 发送是否成功
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
            
            logger.info(f"发送Webhook通知: {json.dumps(webhook_data)}")
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # 如果有JWT令牌，添加到请求头
            if jwt_token:
                headers["Authorization"] = f"Bearer {jwt_token}"
            
            # 发送POST请求
            response = requests.post(
                self.webhook_url,
                json=webhook_data,
                timeout=self.timeout,
                headers=headers
            )
            
            # 检查响应
            if response.status_code == 200:
                logger.info(f"Webhook发送成功: {response.status_code}")
                return True
            else:
                logger.warning(f"Webhook发送失败: 状态码 {response.status_code}, 响应: {response.text}")
                return False
                
        except Exception as e:
            logger.exception(f"发送webhook失败: {str(e)}")
            return False


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