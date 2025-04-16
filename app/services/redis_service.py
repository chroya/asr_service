import json
import logging
import redis
from redis import ConnectionPool
from typing import Dict, List, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisService:
    """
    Redis服务单例类，管理Redis连接池
    """
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisService, cls).__new__(cls)
            try:
                # 创建连接池
                cls._pool = ConnectionPool(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    decode_responses=False  # 我们会自己处理JSON编解码
                )
                logger.info(f"Redis连接池已初始化: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except Exception as e:
                logger.error(f"Redis连接池初始化失败: {str(e)}")
                raise
        return cls._instance
    
    def get_client(self, prefix: str = "") -> "RedisClient":
        """
        获取Redis客户端
        
        Args:
            prefix: 键前缀，用于区分不同类型的数据
            
        Returns:
            RedisClient: Redis客户端实例
        """
        return RedisClient(self._pool, prefix)


class RedisClient:
    """
    Redis客户端类，用于存储和检索数据
    """
    
    def __init__(self, pool: ConnectionPool, prefix: str = ""):
        """
        初始化Redis客户端
        
        Args:
            pool: Redis连接池
            prefix: 键前缀，用于区分不同类型的数据
        """
        self.prefix = prefix
        self.redis = redis.Redis(connection_pool=pool)
    
    def _get_key(self, key: str) -> str:
        """
        获取带前缀的键名
        
        Args:
            key: 原始键名
            
        Returns:
            str: 带前缀的键名
        """
        return f"{self.prefix}{key}"
    
    def save(self, key: str, data: Any) -> bool:
        """
        保存数据到Redis
        
        Args:
            key: 键名
            data: 要存储的数据，将会被JSON序列化
            
        Returns:
            bool: 是否成功保存
        """
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            redis_key = self._get_key(key)
            self.redis.set(redis_key, json_data)
            return True
        except Exception as e:
            logger.error(f"保存数据到Redis失败 {key}: {str(e)}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        从Redis获取数据
        
        Args:
            key: 键名
            
        Returns:
            Any: 获取的数据，如果不存在或出错则返回None
        """
        try:
            redis_key = self._get_key(key)
            data = self.redis.get(redis_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"从Redis获取数据失败 {key}: {str(e)}")
            return None
    
    def delete(self, key: str) -> bool:
        """
        从Redis删除数据
        
        Args:
            key: 键名
            
        Returns:
            bool: 是否成功删除
        """
        try:
            redis_key = self._get_key(key)
            self.redis.delete(redis_key)
            return True
        except Exception as e:
            logger.error(f"从Redis删除数据失败 {key}: {str(e)}")
            return False
    
    def get_keys(self, pattern: str) -> List[str]:
        """
        获取符合模式的所有键
        
        Args:
            pattern: 键模式，例如"task:*"
            
        Returns:
            List[str]: 符合模式的键列表
        """
        try:
            redis_pattern = self._get_key(pattern)
            keys = self.redis.keys(redis_pattern)
            # 移除前缀
            if self.prefix:
                return [k.decode('utf-8').replace(self.prefix, '', 1) for k in keys]
            return [k.decode('utf-8') for k in keys]
        except Exception as e:
            logger.error(f"从Redis获取键列表失败 {pattern}: {str(e)}")
            return [] 