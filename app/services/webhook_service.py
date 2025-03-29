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
        result: Dict[str, Any],
        duration: int,
        use_time: int
    ) -> bool:
        """
        发送转写完成的webhook通知
        
        Args:
            extra_params: 给uploadfile的参数，可以是字典或Pydantic模型
            result: 任务执行结果，JSON字符串格式
            duration: 音频时长，单位为秒
            use_time: 任务耗时，单位为秒
            
        Returns:
            bool: 发送是否成功
        """
        try:
            # 如果extra_params是Pydantic模型，转换为字典
            if isinstance(extra_params, BaseModel):
                extra_params = extra_params.model_dump_json()
            
            # 准备webhook数据并确保使用标准JSON格式（双引号）
            webhook_data = json.loads(json.dumps({
                "extra_params": extra_params,
                "result": result,
                "duration": duration,
                "use_time": use_time
            }))
            
            logger.info(f"发送webhook通知: {self.webhook_url}")
            logger.info(f"Webhook数据: {json.dumps(webhook_data)}")
            
            # 发送POST请求
            response = requests.post(
                self.webhook_url,
                json=webhook_data,  # requests会自动处理JSON序列化
                timeout=self.timeout
            )
            
            # 检查响应
            if response.status_code == 200:
                logger.info(f"Webhook发送成功: {response.status_code}")
                return True
            else:
                logger.warning(f"Webhook发送失败: 状态码 {response.status_code}
                # logger.warning(f"Webhook发送失败: 状态码 {response.status_code}, 响应: {response.text}")
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