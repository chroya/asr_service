import json
import logging
import os
import paho.mqtt.client as mqtt
from typing import Dict, Any, Optional, Callable
from app.core.config import settings

logger = logging.getLogger(__name__)

class MQTTService:
    """MQTT服务，用于发送消息通知"""
    _instance = None
    _is_initialized = False
    
    def __init__(self):
        """初始化MQTT客户端"""
        if not MQTTService._is_initialized:
            self.client = None
            MQTTService._is_initialized = True
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = MQTTService()
        return cls._instance
    
    def _ensure_connected(self):
        """确保MQTT客户端已连接"""
        if self.client is None:
            self.client = mqtt.Client()
            
            # 设置认证信息（如果有）
            if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
                self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
                self.client.tls_set(ca_certs=settings.MQTT_CERT_PATH)
            
            # 设置回调
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            
            # 连接MQTT broker
            logger.info(f"Connecting to MQTT broker {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
            try:
                self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT)
                self.client.loop_start()
            except Exception as e:
                logger.error(f"MQTT连接失败: {str(e)}")
                raise e
    
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            logger.info("MQTT连接成功")
        else:
            logger.error(f"MQTT连接失败，返回码: {rc}")
    
    def _on_disconnect(self, client, userdata, flags, rc):
        """断开连接回调"""
        if rc != 0:
            logger.warning(f"MQTT意外断开连接, rc: {rc}")
            # 尝试重新连接
            try:
                self.client.reconnect()
            except Exception as e:
                logger.error(f"MQTT重连失败: {str(e)}")
    
    def send_transcription_complete(self, task_id: str, code: int, message: Optional[str] = None) -> bool:
        """
        发送转写完成通知
        
        Args:
            task_id: 任务ID
            code: 状态码（0表示成功，其他值表示失败）
            message: 错误消息（失败时使用）
            
        Returns:
            bool: 是否发送成功
        """
        # 不发mqtt了
        # try:
        #     # 确保MQTT客户端已连接
        #     self._ensure_connected()
            
        #     # 构建消息内容
        #     mqtt_message = {
        #         "code": code,
        #         "type": 1,  # 1表示转录
        #         "task_id": task_id,
        #     }
            
        #     # 构建下载URL
        #     download_url = f"{settings.BASE_URL}{settings.DOWNLOAD_URL_PREFIX}/{task_id}.json"
            
        #     # 根据状态码设置data字段
        #     if code == 0:  # 成功状态
        #         mqtt_message["data"] = {"trans_results": download_url}
        #     else:  # 失败状态
        #         mqtt_message["data"] = message or "转写错误"
            
        #     # 发送消息，使用task_id作为topic
        #     topic = get_topic(task_id)
        #     result = self.client.publish(topic, json.dumps(mqtt_message))
        #     if result.rc == mqtt.MQTT_ERR_SUCCESS:
        #         logger.info(f"MQTT消息发送成功: {topic} , 下载链接: {download_url}, msg: {mqtt_message}")
        #         return True
        #     else:
        #         logger.error(f"MQTT消息发送失败: {result.rc}")
        #         # 尝试重新连接并发送消息
        #         try:
        #             self.client.reconnect()
        #             result = self.client.publish(topic, json.dumps(mqtt_message))
        #             if result.rc == mqtt.MQTT_ERR_SUCCESS:
        #                 logger.info(f"MQTT消息重新发送成功: {topic}")
        #                 return True
        #             else:
        #                 logger.error(f"MQTT消息重新发送失败: {result.rc}")
        #         except Exception as e:
        #             logger.error(f"重新连接MQTT客户端时出错: {str(e)}")
        #         return False
                
        # except Exception as e:
        #     logger.error(f"发送MQTT消息时出错: {str(e)}")
        #     return False
    
    def __del__(self):
        """清理资源"""
        if self.client:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass

# 全局MQTT服务实例
mqtt_service = None

def get_mqtt_service() -> MQTTService:
    """
    获取MQTT服务实例
    """
    global mqtt_service
    if mqtt_service is None:
        mqtt_service = MQTTService.get_instance()
    return mqtt_service

def get_topic(task_id: str) -> str:
    """
    获取MQTT主题
    """
    return f"Topic_{task_id}"
