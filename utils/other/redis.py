import hashlib
import json
import logging
from typing import Any, Optional

from django.core.cache import caches

logger = logging.getLogger(__name__)


class FastJsonRedisSerializer:
    """自定义 Redis 序列化器，使用 JSON 序列化和反序列化对象"""

    def serialize(self, obj: Any) -> Optional[bytes]:
        """
        序列化对象为 JSON 字符串
        :param obj: 要序列化的对象
        :return: 序列化后的字节串
        """
        if obj is None:
            return None
        return json.dumps(obj, default=str).encode("utf-8")

    def deserialize(self, data: Optional[bytes]) -> Any:
        """
        反序列化 JSON 字符串为对象
        :param data: 要反序列化的字节串
        :return: 反序列化后的对象
        """
        if not data:
            return None
        return json.loads(data.decode("utf-8"))


class StringRedisSerializer:
    """字符串类型 Redis 键的序列化器"""

    def serialize(self, obj: str) -> bytes:
        """序列化字符串为字节数组"""
        return json.dumps(obj).encode("utf-8")

    def deserialize(self, data: Optional[bytes]) -> Optional[str]:
        """反序列化字节数组为字符串"""
        return data.decode("utf-8") if data else None


def generate_cache_key(target: Any, method: Any, *params: Any) -> str:
    """
    生成缓存键，使用 SHA-256 哈希
    :param target: 目标对象
    :param method: 方法对象
    :param params: 参数列表
    :return: 哈希后的缓存键
    """
    container = {
        "class": str(target.__class__.__name__),
        "methodName": method.__name__,
        "package": target.__module__,
        "params": params,
    }
    json_string = json.dumps(container, default=str)
    return hashlib.sha256(json_string.encode("utf-8")).hexdigest()


class CustomCache:
    """自定义缓存类，使用 Django 的缓存系统，封装常用的缓存操作"""

    def __init__(self, cache_name: str = "default"):
        """
        初始化缓存对象
        :param cache_name: 缓存配置名称
        """
        self.cache = caches[cache_name]

    def get(self, key: str) -> Any:
        """
        获取缓存值
        :param key: 缓存键
        :return: 缓存的值
        """
        try:
            return self.cache.get(key)
        except Exception as e:
            logger.error(f"缓存获取错误，键[{key}]: {e}")
            return None

    def set(self, key: str, value: Any, timeout: int = 7200) -> bool:
        """
        设置缓存值
        :param key: 缓存键
        :param value: 缓存值
        :param timeout: 过期时间(秒)
        :return: 是否设置成功
        """
        try:
            self.cache.set(key, value, timeout)
            return True
        except Exception as e:
            logger.error(f"缓存设置错误，键[{key}]: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存
        :param key: 缓存键
        :return: 是否删除成功
        """
        try:
            self.cache.delete(key)
            return True
        except Exception as e:
            logger.error(f"缓存删除错误，键[{key}]: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查键是否存在
        :param key: 缓存键
        :return: 是否存在
        """
        return self.cache.get(key) is not None

    def incr(self, key: str, delta: int = 1) -> Optional[int]:
        """
        递增计数器
        :param key: 缓存键
        :param delta: 增量值
        :return: 增加后的值
        """
        try:
            return self.cache.incr(key, delta)
        except Exception as e:
            logger.error(f"计数器递增错误，键[{key}]: {e}")
            return None

    def clear(self) -> bool:
        """
        清空所有缓存
        :return: 是否清空成功
        """
        try:
            self.cache.clear()
            return True
        except Exception as e:
            logger.error(f"缓存清空错误: {e}")
            return False


# 在 Django 项目中使用
# def my_view(request):
#     cache = CustomCache()
#     key = generate_cache_key(MyClass, my_method, arg1, arg2)
#     result = cache.get(key)
#     if result is None:
#         result = expensive_operation()
#         cache.set(key, result)
#     return JsonResponse(result)


# 注意：在 Django 2.2 及以上版本中，可以直接使用 Django's caching framework'
# import json
# import hashlib
# import logging
# from django.conf import settings
# from django.core.cache import caches
# from django.core.cache.backends.redis import RedisCache

# from django.views.decorators.cache import cache_page
#
# logger = logging.getLogger(__name__)
#
#
# class FastJsonRedisSerializer:
#     """自定义 Redis 序列化器，使用 JSON 序列化和反序列化对象"""
#
#     def serialize(self, obj):
#         """序列化对象为 JSON 字符串"""
#         if obj is None:
#             return None
#         return json.dumps(obj).encode('utf-8')
#
#     def deserialize(self, data):
#         """反序列化 JSON 字符串为对象"""
#         if not data:
#             return None
#         return json.loads(data.decode('utf-8'))
#
#
# def generate_cache_key(target, method, *params):
#     """生成缓存键，使用 SHA-256 哈希"""
#     container = {
#         "class": str(target.__class__.__name__),
#         "methodName": method.__name__,
#         "params": params
#         }
#     json_string = json.dumps(container, default=str)
#     return hashlib.sha256(json_string.encode('utf-8')).hexdigest()
#
#
# def my_view(request):
#     """示例视图，使用缓存"""
#     cache = caches['default']  # 获取默认缓存
#     key = generate_cache_key(MyClass, my_method, arg1, arg2)  # 生成缓存键
#     result = cache.get(key)  # 尝试从缓存中获取结果
#
#     if result is None:  # 如果缓存未命中
#         result = expensive_operation()  # 执行计算
#         cache.set(key, result, timeout=7200)  # 将结果存入缓存，设置过期时间为 2 小时
#
#     return JsonResponse(result)
