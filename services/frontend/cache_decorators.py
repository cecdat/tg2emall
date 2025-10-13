"""
缓存装饰器模块
提供函数缓存装饰器
"""

import functools
import logging
from typing import Any, Callable, Optional, Union
from cache_manager import get_cache_manager, CacheKeys, CacheTTL

logger = logging.getLogger(__name__)

def cached(key_template: str, ttl: Union[int, None] = None, key_func: Optional[Callable] = None):
    """
    缓存装饰器
    
    Args:
        key_template: 缓存键模板，支持{arg_name}占位符
        ttl: 过期时间（秒），None表示使用默认值
        key_func: 自定义键生成函数，接收函数参数，返回缓存键
    
    Example:
        @cached("user:{user_id}", ttl=300)
        def get_user(user_id):
            return db.get_user(user_id)
        
        @cached("articles:list", ttl=600, key_func=lambda limit, offset: f"articles:list:{limit}:{offset}")
        def get_articles(limit, offset):
            return db.get_articles(limit, offset)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()
            
            # 如果Redis不可用，直接执行原函数
            if not cache.is_available():
                return func(*args, **kwargs)
            
            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # 使用模板生成键
                cache_key = key_template
                # 获取函数参数名
                import inspect
                sig = inspect.signature(func)
                bound_args = sig.bind(*args, **kwargs)
                bound_args.apply_defaults()
                
                # 替换模板中的占位符
                for param_name, param_value in bound_args.arguments.items():
                    cache_key = cache_key.replace(f"{{{param_name}}}", str(param_value))
            
            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                # 缓存命中（减少调试日志）
                return cached_result
            
            # 缓存未命中，执行原函数
            # 缓存未命中（减少调试日志）
            result = func(*args, **kwargs)
            
            # 将结果存入缓存
            if result is not None:
                cache.set(cache_key, result, ttl)
                # 结果已缓存（减少调试日志）
            
            return result
        
        return wrapper
    return decorator

def cache_invalidate(pattern: str):
    """
    缓存失效装饰器
    在函数执行后删除匹配的缓存
    
    Args:
        pattern: 要删除的缓存键模式
    
    Example:
        @cache_invalidate("articles:*")
        def update_article(article_id):
            # 更新文章后，删除所有文章相关缓存
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 执行函数后删除缓存
            cache = get_cache_manager()
            if cache.is_available():
                deleted_count = cache.delete_pattern(pattern)
                # 缓存失效（减少日志输出）
            
            return result
        
        return wrapper
    return decorator

def cache_conditional(condition_func: Callable[[Any], bool]):
    """
    条件缓存装饰器
    根据条件决定是否缓存结果
    
    Args:
        condition_func: 条件函数，接收函数结果，返回是否应该缓存
    
    Example:
        @cached("user:{user_id}", ttl=300)
        @cache_conditional(lambda result: result is not None)
        def get_user(user_id):
            return db.get_user(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 如果条件满足，缓存结果
            if condition_func(result):
                cache = get_cache_manager()
                if cache.is_available():
                    # 这里需要重新生成缓存键，简化处理
                    cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
                    cache.set(cache_key, result)
            
            return result
        
        return wrapper
    return decorator

# 预定义的缓存装饰器
def cache_articles(ttl: int = CacheTTL.MEDIUM):
    """文章列表缓存装饰器"""
    return cached("articles:list:{limit}:{offset}", ttl=ttl)

def cache_article_detail(ttl: int = CacheTTL.LONG):
    """文章详情缓存装饰器"""
    return cached("article:{article_id}", ttl=ttl)

def cache_popular_articles(ttl: int = CacheTTL.SHORT):
    """热门文章缓存装饰器"""
    return cached("articles:popular:{limit}", ttl=ttl)

def cache_recent_articles(ttl: int = CacheTTL.SHORT):
    """最新文章缓存装饰器"""
    return cached("articles:recent:{limit}", ttl=ttl)

def cache_search_results(ttl: int = CacheTTL.MEDIUM):
    """搜索结果缓存装饰器"""
    return cached("search:{query}:{page}:{per_page}", ttl=ttl)

def cache_categories(ttl: int = CacheTTL.LONG):
    """分类列表缓存装饰器"""
    return cached("categories:list", ttl=ttl)

def cache_advertisements(ttl: int = CacheTTL.LONG):
    """广告位缓存装饰器"""
    return cached("ads:{position}", ttl=ttl)

def invalidate_article_cache():
    """文章相关缓存失效装饰器"""
    return cache_invalidate("article:*")

def invalidate_articles_list_cache():
    """文章列表缓存失效装饰器"""
    return cache_invalidate("articles:*")

def invalidate_search_cache():
    """搜索缓存失效装饰器"""
    return cache_invalidate("search:*")
