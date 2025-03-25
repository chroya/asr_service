import json
import logging
import os
import paho.mqtt.client as mqtt
from typing import Dict, Any, Optional, Callable
from app.core.config import settings

logger = logging.getLogger(__name__)

# MQTT客户端实例
mqtt_client = None

class MQTTService:
    """MQTT服务，用于发送消息通知"""
    
    def __init__(self):
        """初始化MQTT客户端"""
        self.client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)
        
        # 设置认证信息（如果有）
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        
        # 设置回调
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        # 连接MQTT broker
        try:
            self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"MQTT连接失败: {str(e)}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            logger.info("MQTT连接成功")
        else:
            logger.error(f"MQTT连接失败，返回码: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        if rc != 0:
            logger.warning("MQTT意外断开连接")
            # 尝试重新连接
            try:
                self.client.reconnect()
            except Exception as e:
                logger.error(f"MQTT重连失败: {str(e)}")
    
    def send_transcription_complete(self, task_id: str,) -> bool:
        """
        发送转写完成通知
        
        Args:
            task_id: 任务ID
            result_filename: 转写结果文件名
            
        Returns:
            bool: 是否发送成功
        """
        try:
            # 构建下载URL
            download_url = f"{settings.BASE_URL}{settings.DOWNLOAD_URL_PREFIX}/{task_id}"
            
            # 构建消息内容
            message = {
                "code": 0,
                "type": 1,
                "task_id": task_id,
                "results": download_url
            }
            
            # 发送消息，使用task_id作为topic
            result = self.client.publish(get_topic(task_id), json.dumps(message))
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"MQTT消息发送成功: {task_id}, 下载链接: {download_url}")
                return True
            else:
                logger.error(f"MQTT消息发送失败: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"发送MQTT消息时出错: {str(e)}")
            return False
    
    def __del__(self):
        """清理资源"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
        except:
            pass

# 创建全局MQTT服务实例
mqtt_service = MQTTService()

def get_topic(task_id: str) -> str:
    """
    获取MQTT主题
    """
    return f"Topic_{task_id}"
