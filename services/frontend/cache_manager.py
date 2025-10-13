"""
Redis缓存管理模块
提供统一的缓存接口和策略
"""

import json
import logging
import redis
from typing import Any, Optional, Union
from datetime import timedelta

logger = logging.getLogger(__name__)

class CacheManager:
    """Redis缓存管理器"""
    
    def __init__(self, host='localhost', port=6379, db=0, password=None, decode_responses=True):
        """
        初始化Redis连接
        
        Args:
            host: Redis服务器地址
            port: Redis端口
            db: 数据库编号
            password: 密码
            decode_responses: 是否自动解码响应
        """
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=decode_responses,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # 测试连接
            self.redis_client.ping()
            # Redis连接成功（减少日志输出）
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.redis_client = None
    
    def is_available(self) -> bool:
        """检查Redis是否可用"""
        if not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存数据，如果不存在或解析失败返回None
        """
        if not self.is_available():
            return None
            
        try:
            value = self.redis_client.get(key)
            if value is None:
                return None
            
            # 尝试解析JSON
            try:
                parsed_value = json.loads(value)
                # 恢复datetime对象
                return self._restore_datetime_objects(parsed_value)
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON，直接返回字符串
                return value
        except Exception as e:
            logger.error(f"获取缓存失败 {key}: {e}")
            return None
    
    def _restore_datetime_objects(self, obj: Any) -> Any:
        """递归恢复对象中的datetime对象"""
        if isinstance(obj, dict):
            return {k: self._restore_datetime_objects(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._restore_datetime_objects(item) for item in obj]
        elif isinstance(obj, str):
            # 尝试解析ISO格式的datetime字符串
            try:
                from datetime import datetime
                return datetime.fromisoformat(obj)
            except (ValueError, TypeError):
                return obj
        else:
            return obj
    
    def set(self, key: str, value: Any, ttl: Optional[Union[int, timedelta]] = None) -> bool:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒或timedelta对象）
            
        Returns:
            是否设置成功
        """
        if not self.is_available():
            return False
            
        try:
            # 序列化数据，处理datetime对象
            serialized_value = self._serialize_value(value)
            
            # 设置TTL
            if ttl is None:
                self.redis_client.set(key, serialized_value)
            else:
                if isinstance(ttl, timedelta):
                    ttl = int(ttl.total_seconds())
                self.redis_client.setex(key, ttl, serialized_value)
            
            return True
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {e}")
            return False
    
    def _serialize_value(self, value: Any) -> str:
        """序列化值，处理datetime等特殊类型"""
        if isinstance(value, (dict, list)):
            # 递归处理字典和列表中的datetime对象
            processed_value = self._process_datetime_objects(value)
            return json.dumps(processed_value, ensure_ascii=False)
        elif hasattr(value, 'isoformat'):  # datetime对象
            return value.isoformat()
        else:
            return str(value)
    
    def _process_datetime_objects(self, obj: Any) -> Any:
        """递归处理对象中的datetime对象"""
        if isinstance(obj, dict):
            return {k: self._process_datetime_objects(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._process_datetime_objects(item) for item in obj]
        elif hasattr(obj, 'isoformat'):  # datetime对象
            return obj.isoformat()
        else:
            return obj
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否删除成功
        """
        if not self.is_available():
            return False
            
        try:
            result = self.redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        批量删除匹配模式的缓存
        
        Args:
            pattern: 匹配模式（支持*通配符）
            
        Returns:
            删除的键数量
        """
        if not self.is_available():
            return 0
            
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"批量删除缓存失败 {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        if not self.is_available():
            return False
            
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"检查缓存存在性失败 {key}: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间
        
        Args:
            key: 缓存键
            
        Returns:
            剩余秒数，-1表示永不过期，-2表示键不存在
        """
        if not self.is_available():
            return -2
            
        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"获取TTL失败 {key}: {e}")
            return -2
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        递增计数器
        
        Args:
            key: 缓存键
            amount: 递增数量
            
        Returns:
            递增后的值，失败返回None
        """
        if not self.is_available():
            return None
            
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"递增计数器失败 {key}: {e}")
            return None
    
    def expire(self, key: str, ttl: Union[int, timedelta]) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 缓存键
            ttl: 过期时间
            
        Returns:
            是否设置成功
        """
        if not self.is_available():
            return False
            
        try:
            if isinstance(ttl, timedelta):
                ttl = int(ttl.total_seconds())
            return bool(self.redis_client.expire(key, ttl))
        except Exception as e:
            logger.error(f"设置过期时间失败 {key}: {e}")
            return False

# 缓存键常量
class CacheKeys:
    """缓存键常量"""
    
    # 文章相关
    ARTICLE = "article:{id}"  # 单篇文章
    ARTICLES_LIST = "articles:list:{limit}:{offset}"  # 文章列表
    ARTICLES_CATEGORY = "articles:category:{category}:{limit}:{offset}"  # 分类文章
    RECENT_ARTICLES = "articles:recent:{limit}"  # 最新文章
    POPULAR_ARTICLES = "articles:popular:{limit}"  # 热门文章
    
    # 搜索相关
    SEARCH_RESULTS = "search:{query}:{page}:{per_page}"  # 搜索结果
    POPULAR_SEARCHES = "search:popular"  # 热门搜索
    
    # 分类相关
    CATEGORIES = "categories:list"  # 分类列表
    
    # 广告相关
    ADVERTISEMENTS = "ads:{position}"  # 广告位
    
    # 统计相关
    STATS = "stats:general"  # 统计信息
    
    # 首页相关
    HOMEPAGE_DATA = "homepage:data"  # 首页完整数据

# 缓存TTL常量（秒）
class CacheTTL:
    """缓存过期时间常量"""
    
    # 短期缓存（1-5分钟）
    SHORT = 300  # 5分钟
    
    # 中期缓存（10-30分钟）
    MEDIUM = 1800  # 30分钟
    
    # 长期缓存（1-6小时）
    LONG = 21600  # 6小时
    
    # 超长期缓存（1天）
    VERY_LONG = 86400  # 1天

# 全局缓存管理器实例
def get_cache_manager() -> CacheManager:
    """获取缓存管理器实例"""
    import os
    
    # 从环境变量读取Redis配置
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', '6379'))
    redis_db = int(os.getenv('REDIS_DB', '0'))
    redis_password = os.getenv('REDIS_PASSWORD', None)
    
    return CacheManager(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password
    )

# 创建全局实例
cache_manager = get_cache_manager()
