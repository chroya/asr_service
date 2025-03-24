import aiohttp
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

class CloudStatsService:
    """
    云端统计数据服务，用于向云API报告任务统计信息
    """
    
    def __init__(self):
        self.enabled = bool(settings.CLOUD_STATS_API_URL and settings.CLOUD_API_KEY)
        self.api_url = settings.CLOUD_STATS_API_URL
        self.api_key = settings.CLOUD_API_KEY
        self.max_retries = 3
        self.retry_delay = 2  # 秒
    
    async def _send_data(self, endpoint: str, data: Dict[str, Any]) -> bool:
        """
        向云API发送数据
        
        Args:
            endpoint: API端点路径
            data: 要发送的数据
            
        Returns:
            bool: 是否成功发送
        """
        if not self.enabled:
            logger.info("云统计服务未启用，跳过数据发送")
            return False
        
        url = f"{self.api_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        retries = 0
        while retries < self.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=data, headers=headers) as response:
                        if response.status == 200:
                            logger.info(f"成功向云API发送数据: {endpoint}")
                            return True
                        else:
                            response_text = await response.text()
                            logger.error(f"向云API发送数据失败: HTTP {response.status}, {response_text}")
            except Exception as e:
                logger.error(f"向云API发送数据时出错: {str(e)}")
            
            # 重试前等待
            retries += 1
            if retries < self.max_retries:
                await asyncio.sleep(self.retry_delay * retries)  # 逐渐增加等待时间
        
        logger.error(f"在{self.max_retries}次尝试后无法发送数据到云API")
        return False
    
    def report_task_completion(self, client_id: str, audio_duration: Optional[float] = None) -> None:
        """
        报告任务完成信息
        
        Args:
            client_id: 客户端ID
            audio_duration: 音频时长（秒）
        """
        if not self.enabled:
            return
        
        data = {
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "event_type": "task_completion",
            "data": {
                "audio_duration": audio_duration
            }
        }
        
        # 在后台运行，不阻塞主线程
        asyncio.create_task(self._send_data("stats/task", data))
    
    def report_client_statistics(self, client_id: str, task_count: int, total_duration: float) -> None:
        """
        报告客户端统计数据
        
        Args:
            client_id: 客户端ID
            task_count: 任务总数
            total_duration: 总处理时间（秒）
        """
        if not self.enabled:
            return
        
        data = {
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "event_type": "client_stats",
            "data": {
                "task_count": task_count,
                "total_duration": total_duration
            }
        }
        
        # 在后台运行，不阻塞主线程
        asyncio.create_task(self._send_data("stats/client", data)) 