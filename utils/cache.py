import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar, Union

from django.conf import settings
from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.http import HttpRequest
from django.utils.encoding import force_bytes

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

class CacheManager:
    """缓存管理器"""
    
    def __init__(self, prefix: str = "", timeout: Optional[int] = None):
        self.prefix = prefix
        self.timeout = timeout or getattr(settings, "CACHE_TIMEOUT", DEFAULT_TIMEOUT)
        
    def _make_key(self, key: str) -> str:
        """生成缓存键"""
        return f"{self.prefix}:{key}" if self.prefix else key
        
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存"""
        cache_key = self._make_key(key)
        value = cache.get(cache_key, default)
        logger.debug(f"Cache get: {cache_key}", extra={"data": {"value": value}})
        return value
        
    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None,
        version: Optional[int] = None
    ) -> bool:
        """设置缓存"""
        cache_key = self._make_key(key)
        timeout = timeout if timeout is not None else self.timeout
        result = cache.set(cache_key, value, timeout, version=version)
        logger.debug(
            f"Cache set: {cache_key}",
            extra={"data": {"value": value, "timeout": timeout, "result": result}}
        )
        return result
        
    def delete(self, key: str, version: Optional[int] = None) -> None:
        """删除缓存"""
        cache_key = self._make_key(key)
        cache.delete(cache_key, version=version)
        logger.debug(f"Cache delete: {cache_key}")
        
    def clear(self, pattern: Optional[str] = None) -> None:
        """清除缓存"""
        if pattern:
            pattern = self._make_key(pattern)
            keys = cache.keys(pattern)
            cache.delete_many(keys)
            logger.debug(f"Cache clear pattern: {pattern}", extra={"data": {"keys": keys}})
        else:
            cache.clear()
            logger.debug("Cache clear all")
            
    def get_or_set(
        self,
        key: str,
        default: Callable[[], Any],
        timeout: Optional[int] = None,
        version: Optional[int] = None
    ) -> Any:
        """获取缓存，如果不存在则设置"""
        cache_key = self._make_key(key)
        value = cache.get(cache_key)
        
        if value is None:
            value = default()
            timeout = timeout if timeout is not None else self.timeout
            cache.set(cache_key, value, timeout, version=version)
            logger.debug(
                f"Cache get_or_set (set): {cache_key}",
                extra={"data": {"value": value, "timeout": timeout}}
            )
        else:
            logger.debug(
                f"Cache get_or_set (get): {cache_key}",
                extra={"data": {"value": value}}
            )
            
        return value
        
    def incr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        """增加缓存值"""
        cache_key = self._make_key(key)
        value = cache.incr(cache_key, delta, version=version)
        logger.debug(
            f"Cache incr: {cache_key}",
            extra={"data": {"delta": delta, "value": value}}
        )
        return value
        
    def decr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        """减少缓存值"""
        cache_key = self._make_key(key)
        value = cache.decr(cache_key, delta, version=version)
        logger.debug(
            f"Cache decr: {cache_key}",
            extra={"data": {"delta": delta, "value": value}}
        )
        return value

def cache_key_generator(*args: Any, **kwargs: Any) -> str:
    """生成缓存键"""
    # 将参数转换为字符串
    key_parts = []
    
    # 处理位置参数
    for arg in args:
        if isinstance(arg, HttpRequest):
            # 对于请求对象，使用路径和查询参数
            key_parts.append(f"path={arg.path}")
            key_parts.append(f"query={arg.GET.urlencode()}")
        elif hasattr(arg, "pk"):
            # 对于模型实例，使用主键
            key_parts.append(f"pk={arg.pk}")
        else:
            # 其他类型直接转换为字符串
            key_parts.append(str(arg))
            
    # 处理关键字参数
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}={value}")
        
    # 生成键字符串
    key_string = ":".join(key_parts)
    
    # 使用MD5生成固定长度的键
    return hashlib.md5(force_bytes(key_string)).hexdigest()

def cached(
    timeout: Optional[int] = None,
    key_prefix: str = "",
    version: Optional[int] = None,
    key_generator: Optional[Callable[..., str]] = None
) -> Callable[[T], T]:
    """缓存装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            if key_generator:
                key = key_generator(*args, **kwargs)
            else:
                key = cache_key_generator(*args, **kwargs)
                
            if key_prefix:
                key = f"{key_prefix}:{key}"
                
            # 获取缓存
            cache_manager = CacheManager()
            result = cache_manager.get(key)
            
            if result is None:
                # 执行函数
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 设置缓存
                cache_manager.set(key, result, timeout=timeout, version=version)
                
                logger.debug(
                    f"Cache miss: {key}",
                    extra={
                        "data": {
                            "function": func.__name__,
                            "duration": duration,
                            "result": result
                        }
                    }
                )
            else:
                logger.debug(
                    f"Cache hit: {key}",
                    extra={
                        "data": {
                            "function": func.__name__,
                            "result": result
                        }
                    }
                )
                
            return result
        return cast(T, wrapper)
    return decorator

def cache_page(
    timeout: Optional[int] = None,
    key_prefix: Optional[str] = None,
    version: Optional[int] = None
) -> Callable[[T], T]:
    """页面缓存装饰器"""
    def decorator(view_func: T) -> T:
        @functools.wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            key_parts = [
                request.path,
                request.GET.urlencode(),
                request.META.get("HTTP_ACCEPT_LANGUAGE", ""),
                request.META.get("HTTP_USER_AGENT", "")
            ]
            
            if key_prefix:
                key_parts.insert(0, key_prefix)
                
            key = hashlib.md5(force_bytes(":".join(key_parts))).hexdigest()
            
            # 获取缓存
            cache_manager = CacheManager()
            response = cache_manager.get(key)
            
            if response is None:
                # 执行视图函数
                start_time = time.time()
                response = view_func(request, *args, **kwargs)
                duration = time.time() - start_time
                
                # 设置缓存
                if hasattr(response, "render") and callable(response.render):
                    response.add_post_render_callback(
                        lambda r: cache_manager.set(key, r, timeout=timeout, version=version)
                    )
                else:
                    cache_manager.set(key, response, timeout=timeout, version=version)
                    
                logger.debug(
                    f"Page cache miss: {key}",
                    extra={
                        "data": {
                            "path": request.path,
                            "duration": duration
                        }
                    }
                )
            else:
                logger.debug(
                    f"Page cache hit: {key}",
                    extra={
                        "data": {
                            "path": request.path
                        }
                    }
                )
                
            return response
        return cast(T, wrapper)
    return decorator

# 使用示例
"""
# 1. 使用缓存管理器
cache_manager = CacheManager(prefix="myapp", timeout=3600)
cache_manager.set("key", "value")
value = cache_manager.get("key")

# 2. 使用缓存装饰器
@cached(timeout=3600, key_prefix="myapp")
def expensive_function(arg1, arg2):
    # 耗时操作
    return result

# 3. 使用页面缓存装饰器
@cache_page(timeout=3600)
def my_view(request):
    # 视图逻辑
    return response
""" 