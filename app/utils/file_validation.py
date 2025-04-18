import hashlib
import logging
import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)

def generate_content_id(file_content: bytes, user_id: int) -> str:
    """
    根据文件内容和用户ID生成内容ID
    
    Args:
        file_content: 文件字节内容
        user_id: 用户ID
    
    Returns:
        str: 生成的内容ID(MD5哈希值)
    """
    try:
        # 限制文件样本大小
        sample_size = min(len(file_content), settings.CONTENT_ID_MAX_SAMPLE_SIZE)
        sample = file_content[:sample_size]
        
        # 组合用户ID和文件样本
        user_id_bytes = f"{user_id}".encode('utf8')
        combined_data = user_id_bytes + sample
        
        # 计算MD5哈希
        content_id = hashlib.md5(combined_data).hexdigest()
        return content_id
    except Exception as e:
        logger.error(f"生成内容ID失败: {str(e)}")
        # 生成备用ID
        timestamp = int(datetime.datetime.now().timestamp() * 1000)
        random_num = hash(str(user_id) + str(timestamp)) % 10000
        fallback_id = hashlib.md5(f"{user_id}_{timestamp}_{random_num}".encode()).hexdigest()
        return fallback_id

def validate_content_id(file_content: bytes, user_id: int, provided_content_id: str) -> bool:
    """
    验证提供的content_id是否与文件内容和用户ID匹配
    
    Args:
        file_content: 文件字节内容
        user_id: 用户ID
        provided_content_id: 客户端提供的content_id
    
    Returns:
        bool: 验证是否通过
    """
    if not settings.CONTENT_ID_VERIFICATION_ENABLED:
        # 如果验证功能未启用，直接返回True
        return True
        
    # 生成内容ID
    calculated_content_id = generate_content_id(file_content, user_id)
    logger.info(f"收到的content_id:{provided_content_id} ，服务器计算的content_id: {calculated_content_id}")
    
    # 比较计算的哈希值与提供的content_id
    return calculated_content_id == provided_content_id 