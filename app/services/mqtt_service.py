import json
import logging
import paho.mqtt.client as mqtt
from typing import Dict, Any, Optional, Callable
from app.core.config import settings

logger = logging.getLogger(__name__)

# MQTT客户端实例
mqtt_client = None

def on_connect(client, userdata, flags, rc):
    """
    MQTT连接回调
    """
    if rc == 0:
        logger.info("已连接到MQTT代理")
    else:
        logger.error(f"MQTT连接失败，返回码: {rc}")

def on_disconnect(client, userdata, rc):
    """
    MQTT断开连接回调
    """
    if rc != 0:
        logger.warning(f"MQTT意外断开连接，返回码: {rc}")

def get_mqtt_client() -> mqtt.Client:
    """
    获取MQTT客户端实例
    """
    global mqtt_client
    if mqtt_client is None:
        logger.info(f"连接MQTT代理: {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
        client_id = settings.MQTT_CLIENT_ID
        mqtt_client = mqtt.Client(client_id=client_id)
        
        # 设置回调
        mqtt_client.on_connect = on_connect
        mqtt_client.on_disconnect = on_disconnect
        
        # 设置用户名密码（如果提供）
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            mqtt_client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        
        # 连接到代理
        try:
            mqtt_client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            mqtt_client.loop_start()  # 启动循环处理网络事件
        except Exception as e:
            logger.error(f"连接MQTT代理失败: {str(e)}")
    
    return mqtt_client

def publish_message(topic: str, payload: Dict[str, Any], qos: int = 0) -> bool:
    """
    发布消息到MQTT主题
    
    Args:
        topic: 主题
        payload: 消息内容（将转换为JSON）
        qos: 服务质量 (0, 1, 2)
    
    Returns:
        bool: 发布成功返回True，否则返回False
    """
    try:
        client = get_mqtt_client()
        message = json.dumps(payload)
        result = client.publish(topic, message, qos=qos)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"MQTT消息已发布到主题: {topic}")
            return True
        else:
            logger.error(f"MQTT消息发布失败，错误码: {result.rc}")
            return False
    except Exception as e:
        logger.error(f"MQTT消息发布出错: {str(e)}")
        return False

def subscribe_topic(topic: str, callback: Callable, qos: int = 0) -> bool:
    """
    订阅MQTT主题
    
    Args:
        topic: 主题
        callback: 回调函数，当收到消息时调用
        qos: 服务质量 (0, 1, 2)
    
    Returns:
        bool: 订阅成功返回True，否则返回False
    """
    try:
        client = get_mqtt_client()
        
        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload)
                callback(topic, payload)
            except json.JSONDecodeError:
                logger.warning(f"收到无效的JSON消息: {msg.payload}")
                callback(topic, msg.payload)
        
        client.on_message = on_message
        result = client.subscribe(topic, qos)
        
        if result[0] == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"已订阅MQTT主题: {topic}")
            return True
        else:
            logger.error(f"MQTT主题订阅失败，错误码: {result[0]}")
            return False
    except Exception as e:
        logger.error(f"MQTT主题订阅出错: {str(e)}")
        return False

def notify_transcription_complete(task_id: str, user_id: int, transcription_path: str, success: bool = True, error: Optional[str] = None) -> bool:
    """
    通知转写任务完成
    
    Args:
        task_id: 任务ID
        user_id: 用户ID
        transcription_path: 转写结果文件路径
        success: 是否成功完成
        error: 如果失败，错误信息
    
    Returns:
        bool: 发布成功返回True，否则返回False
    """
    topic = f"asr/transcription/{task_id}"
    
    payload = {
        "task_id": task_id,
        "user_id": user_id,
        "success": success,
        "transcription_path": transcription_path if success else None,
        "error": error
    }
    
    return publish_message(topic, payload, qos=1)

def close_mqtt_client():
    """
    关闭MQTT客户端连接
    """
    global mqtt_client
    if mqtt_client is not None:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        mqtt_client = None
        logger.info("MQTT客户端已关闭") 