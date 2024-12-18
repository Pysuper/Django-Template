import hashlib
import pickle
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

from django.core.cache import caches
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.utils.encoding import force_bytes

from utils.log.logger import logger


class CacheKey:
    """缓存键管理器"""

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """
        生成缓存键
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 缓存键
        """
        # 将参数转换为字符串
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

        # 使用MD5生成唯一键
        key = hashlib.md5(force_bytes(":".join(key_parts))).hexdigest()
        return f"cache_key_{key}"

    @staticmethod
    def get_prefix(prefix: str) -> str:
        """
        获取带前缀的缓存键
        :param prefix: 前缀
        :return: 带前缀的缓���键
        """
        return f"{prefix}_{datetime.now().strftime('%Y%m%d')}"


class CacheManager:
    """缓存管理器"""

    def __init__(self, cache_alias: str = "default", timeout: int = DEFAULT_TIMEOUT):
        self.cache = caches[cache_alias]
        self.timeout = timeout
        self.key_generator = CacheKey()

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        :param key: 缓存键
        :param default: 默认值
        :return: 缓存值
        """
        try:
            value = self.cache.get(key, default)
            if value is None:
                logger.debug(f"Cache miss for key: {key}")
            return value
        except Exception as e:
            logger.error(f"获取缓存失败: {str(e)}")
            return default

    def set(
        self,
        key: str,
        value: Any,
        timeout: Optional[int] = None,
        version: Optional[int] = None,
    ) -> bool:
        """
        设置缓存值
        :param key: 缓存键
        :param value: 缓存值
        :param timeout: 过期时间
        :param version: 版本号
        :return: 是否成功
        """
        try:
            self.cache.set(key, value, timeout or self.timeout, version=version)
            return True
        except Exception as e:
            logger.error(f"设置缓存失败: {str(e)}")
            return False

    def delete(self, key: str, version: Optional[int] = None) -> bool:
        """
        删除缓存
        :param key: 缓存键
        :param version: 版本号
        :return: 是否成功
        """
        try:
            self.cache.delete(key, version=version)
            return True
        except Exception as e:
            logger.error(f"删除缓存失败: {str(e)}")
            return False

    def clear(self) -> bool:
        """
        清空缓存
        :return: 是否成功
        """
        try:
            self.cache.clear()
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {str(e)}")
            return False

    def get_many(self, keys: list) -> Dict[str, Any]:
        """
        批量获取缓存
        :param keys: 缓存键列表
        :return: 缓存值字典
        """
        try:
            return self.cache.get_many(keys)
        except Exception as e:
            logger.error(f"批量获取缓存失败: {str(e)}")
            return {}

    def set_many(
        self,
        data: Dict[str, Any],
        timeout: Optional[int] = None,
        version: Optional[int] = None,
    ) -> bool:
        """
        批量设置缓存
        :param data: 缓存数据字典
        :param timeout: 过期时间
        :param version: 版本号
        :return: 是否成功
        """
        try:
            self.cache.set_many(data, timeout or self.timeout, version=version)
            return True
        except Exception as e:
            logger.error(f"批量设置缓存失败: {str(e)}")
            return False

    def delete_many(self, keys: list, version: Optional[int] = None) -> bool:
        """
        批量删除缓存
        :param keys: 缓存键列表
        :param version: 版本号
        :return: 是否成功
        """
        try:
            self.cache.delete_many(keys, version=version)
            return True
        except Exception as e:
            logger.error(f"批量删除缓存失败: {str(e)}")
            return False

    def incr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        """
        递增缓存值
        :param key: 缓存键
        :param delta: 增量
        :param version: 版本号
        :return: 新值
        """
        try:
            return self.cache.incr(key, delta, version=version)
        except Exception as e:
            logger.error(f"递增缓存值失败: {str(e)}")
            return 0

    def decr(self, key: str, delta: int = 1, version: Optional[int] = None) -> int:
        """
        递减缓存值
        :param key: 缓存键
        :param delta: 减量
        :param version: 版本号
        :return: 新值
        """
        try:
            return self.cache.decr(key, delta, version=version)
        except Exception as e:
            logger.error(f"递减缓存值失败: {str(e)}")
            return 0


class CacheDecorator:
    """缓存装饰器"""

    def __init__(
        self,
        timeout: Optional[int] = None,
        key_prefix: str = "",
        cache_alias: str = "default",
        version: Optional[int] = None,
    ):
        self.timeout = timeout
        self.key_prefix = key_prefix
        self.cache_manager = CacheManager(cache_alias)
        self.version = version

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 生成缓存键
            cache_key = self._get_cache_key(func, *args, **kwargs)

            # 尝试从缓存获取
            cached_value = self.cache_manager.get(cache_key, version=self.version)
            if cached_value is not None:
                return pickle.loads(cached_value)

            # 执行函数
            result = func(*args, **kwargs)

            # 设置缓存
            self.cache_manager.set(
                cache_key,
                pickle.dumps(result),
                timeout=self.timeout,
                version=self.version,
            )

            return result

        return wrapper

    def _get_cache_key(self, func: Callable, *args, **kwargs) -> str:
        """
        生成缓存键
        :param func: 被装饰的函数
        :param args: 位置参数
        :param kwargs: 关键字参数
        :return: 缓存键
        """
        key_parts = [self.key_prefix, func.__module__, func.__name__]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return ":".join(key_parts)


class ModelCacheManager:
    """模型缓存管理器"""

    def __init__(self, model_class: Any, timeout: int = DEFAULT_TIMEOUT):
        self.model_class = model_class
        self.timeout = timeout
        self.cache_manager = CacheManager()

    def get_by_id(self, pk: Union[int, str]) -> Optional[Any]:
        """
        根据ID获取缓存的模型实例
        :param pk: 主键值
        :return: 模型实例
        """
        cache_key = f"{self.model_class.__name__}:id:{pk}"
        cached_data = self.cache_manager.get(cache_key)

        if cached_data is not None:
            return pickle.loads(cached_data)

        try:
            instance = self.model_class.objects.get(pk=pk)
            self.cache_manager.set(cache_key, pickle.dumps(instance), self.timeout)
            return instance
        except self.model_class.DoesNotExist:
            return None

    def invalidate_by_id(self, pk: Union[int, str]) -> None:
        """
        使指定ID的缓存失效
        :param pk: 主键值
        """
        cache_key = f"{self.model_class.__name__}:id:{pk}"
        self.cache_manager.delete(cache_key)

    def bulk_get_by_ids(self, pks: list) -> Dict[Union[int, str], Any]:
        """
        批量获取缓存的模型实例
        :param pks: 主键值列表
        :return: 模型实例字典
        """
        cache_keys = {pk: f"{self.model_class.__name__}:id:{pk}" for pk in pks}
        cached_data = self.cache_manager.get_many(list(cache_keys.values()))

        # 处理缓存命中的实例
        result = {}
        missing_pks = []
        for pk, cache_key in cache_keys.items():
            if cache_key in cached_data:
                result[pk] = pickle.loads(cached_data[cache_key])
            else:
                missing_pks.append(pk)

        # 获取缓存未命中��实例
        if missing_pks:
            instances = self.model_class.objects.filter(pk__in=missing_pks)
            to_cache = {}
            for instance in instances:
                pk = instance.pk
                result[pk] = instance
                to_cache[cache_keys[pk]] = pickle.dumps(instance)

            # 更新缓存
            if to_cache:
                self.cache_manager.set_many(to_cache, self.timeout)

        return result


# 创建默认缓存管理器实例
cache_manager = CacheManager()


def cache_method(
    timeout: Optional[int] = None,
    key_prefix: str = "",
    cache_alias: str = "default",
    version: Optional[int] = None,
) -> Callable:
    """
    方法缓存装饰器
    :param timeout: 过期时间
    :param key_prefix: 键前缀
    :param cache_alias: 缓存别名
    :param version: 版本号
    :return: 装饰器函数
    """
    return CacheDecorator(timeout, key_prefix, cache_alias, version)


def cache_page(
    timeout: Optional[int] = None,
    cache_alias: str = "default",
    key_prefix: str = "",
) -> Callable:
    """
    页面缓存装饰器
    :param timeout: 过期时间
    :param cache_alias: 缓存别名
    :param key_prefix: 键前缀
    :return: 装饰器函数
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:view:{request.path}:{request.method}"
            if request.GET:
                cache_key += f":{hashlib.md5(force_bytes(request.GET.urlencode())).hexdigest()}"

            # 获取缓存
            response = cache_manager.get(cache_key)
            if response is not None:
                return response

            # 执行视图函数
            response = view_func(request, *args, **kwargs)

            # 设置缓存
            if response.status_code == 200:
                cache_manager.set(cache_key, response, timeout)

            return response

        return wrapper

    return decorator


"""
使用示例：

# 基本用法
cache_manager = CacheManager()
cache_manager.set("my_key", "my_value", timeout=300)
value = cache_manager.get("my_key")

# 使用装饰器
@cache_method(timeout=300, key_prefix="user")
def get_user_info(user_id):
    # 一些耗时的操作
    return {"id": user_id, "name": "张三"}

# 使用模型缓存管理器
class UserCacheManager(ModelCacheManager):
    def __init__(self):
        super().__init__(User, timeout=3600)

user_cache = UserCacheManager()
user = user_cache.get_by_id(1)

# 使用页面缓存
@cache_page(timeout=300)
def my_view(request):
    # 一些耗时的操作
    return HttpResponse("Hello World")

# 配置示例
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PARSER_CLASS": "redis.connection.HiredisParser",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,
        }
    }
}
"""
