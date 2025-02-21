import hashlib
import hashlib
import time
from functools import wraps
from typing import Any, Callable

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.translation import gettext as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from utils.error import BusinessError, ErrorCode
from utils.log.logger import logger
from utils.response import ApiResponse


def method_decorator(decorator: Callable) -> Callable:
    """方法装饰器，用于类方法的装饰"""

    def wrapper(view_func: Callable) -> Callable:
        view_func.decorator = decorator
        return view_func

    return wrapper


def cache_response(timeout: int = 300, key_prefix: str = "", cache_errors: bool = False) -> Callable:
    """
    缓存响应装饰器
    :param timeout: 缓存超时时间（秒）
    :param key_prefix: 缓存键前缀
    :param cache_errors: 是否缓存错误响应
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()}"

            # 尝试从缓存获取
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            # 执行函数
            response = func(*args, **kwargs)

            # 判断是否需要缓存
            if cache_errors or (isinstance(response, (Response, ApiResponse)) and response.status_code < 400):
                cache.set(cache_key, response, timeout)

            return response

        return wrapper

    return decorator


def rate_limit(key: str = "", rate: str = "60/m", block_time: int = 60) -> Callable:
    """
    请求频率限制装饰器
    :param key: 限制键（为空时使用IP）
    :param rate: 频率限制（次数/时间单位：s秒，m分钟，h小时，d天）
    :param block_time: 封禁时间（秒）
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
            # 解析频率限制
            count, period = rate.split("/")
            count = int(count)

            # 时间单位转换为秒
            time_units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
            period_seconds = time_units.get(period[-1], 60) * int(period[:-1] or 1)

            # 获取限制键
            if not key:
                client_ip = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR"))
                rate_key = f"rate_limit:{func.__name__}:{client_ip}"
            else:
                rate_key = f"rate_limit:{key}"

            # 获取当前请求次数
            current = cache.get(rate_key, 0)

            # 检查是否被封禁
            block_key = f"rate_limit_block:{rate_key}"
            if cache.get(block_key):
                raise BusinessError(error_code=ErrorCode.REQUEST_LIMIT, message=_("请求过于频繁，请稍后再试"))

            # 检查是否超过限制
            if current >= count:
                # 设置封禁
                cache.set(block_key, 1, block_time)
                raise BusinessError(error_code=ErrorCode.REQUEST_LIMIT, message=_("请求过于频繁，请稍后再试"))

            # 增加请求次数
            cache.set(rate_key, current + 1, period_seconds)

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def login_required(redirect_url: str = None) -> Callable:
    """
    登录验证装饰器
    :param redirect_url: 重定向URL
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
            if not request.user.is_authenticated:
                if redirect_url:
                    return HttpResponseRedirect(redirect_url)
                return HttpResponseRedirect(reverse(settings.LOGIN_URL))
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def permission_required(*permissions: str) -> Callable:
    """
    权限验证装饰器
    :param permissions: 权限列表
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
            if not request.user.is_authenticated:
                raise PermissionDenied(_("请先登录"))

            if not request.user.has_perms(permissions):
                raise PermissionDenied(_("没有操作权限"))

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def admin_required(func: Callable) -> Callable:
    """管理员验证装饰器"""

    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
        if not request.user.is_authenticated:
            raise PermissionDenied(_("请先登录"))

        if not request.user.is_staff:
            raise PermissionDenied(_("需要管理员权限"))

        return func(request, *args, **kwargs)

    return wrapper


def superuser_required(func: Callable) -> Callable:
    """超级管理员验证装饰器"""

    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
        if not request.user.is_authenticated:
            raise PermissionDenied(_("请先登录"))

        if not request.user.is_superuser:
            raise PermissionDenied(_("需要超级管理员权限"))

        return func(request, *args, **kwargs)

    return wrapper


def transaction_atomic(using: str = None, savepoint: bool = True) -> Callable:
    """
    事务装饰器
    :param using: 数据库别名
    :param savepoint: 是否使用保存点
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with transaction.atomic(using=using, savepoint=savepoint):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def log_action(action: str = "", level: str = "info") -> Callable:
    """
    操作日志装饰器
    :param action: 操作描述
    :param level: 日志级别
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
            # 记录操作开始
            start_time = time.time()

            try:
                response = func(request, *args, **kwargs)
                # 记录操作成功
                log_data = {
                    "user": request.user.username if request.user.is_authenticated else "anonymous",
                    "action": action or func.__name__,
                    "path": request.path,
                    "method": request.method,
                    "ip": request.META.get("REMOTE_ADDR"),
                    "duration": f"{(time.time() - start_time):.3f}s",
                    "status": "success",
                }
                getattr(logger, level)(f"操作日志: {log_data}")
                return response

            except Exception as e:
                # 记录操作失败
                log_data = {
                    "user": request.user.username if request.user.is_authenticated else "anonymous",
                    "action": action or func.__name__,
                    "path": request.path,
                    "method": request.method,
                    "ip": request.META.get("REMOTE_ADDR"),
                    "duration": f"{(time.time() - start_time):.3f}s",
                    "status": "error",
                    "error": str(e),
                }
                logger.error(f"操作日志: {log_data}")
                raise

        return wrapper

    return decorator


def metric_collection(name: str = "") -> Callable:
    """
    指标收集装饰器
    :param name: 指标名称
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            metric_name = name or func.__name__
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # 记录成功指标
                metric_key = f"metric:{metric_name}:success"
                cache.incr(metric_key)

                # 记录耗时
                duration_key = f"metric:{metric_name}:duration"
                durations = cache.get(duration_key) or []
                durations.append(duration)
                cache.set(duration_key, durations[-100:])  # 只保留最近100次

                return result

            except Exception as e:
                # 记录失败指标
                metric_key = f"metric:{metric_name}:error"
                cache.incr(metric_key)
                raise

        return wrapper

    return decorator


def sensitive_params(*params: str) -> Callable:
    """
    敏感参数处理装饰器
    :param params: 敏感参数名列表
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 处理kwargs中的敏感参数
            for param in params:
                if param in kwargs:
                    kwargs[param] = "******"

            # 处理args中的敏感参数（如果是字典）
            new_args = []
            for arg in args:
                if isinstance(arg, dict):
                    new_arg = arg.copy()
                    for param in params:
                        if param in new_arg:
                            new_arg[param] = "******"
                    new_args.append(new_arg)
                else:
                    new_args.append(arg)

            return func(*new_args, **kwargs)

        return wrapper

    return decorator


def deprecated(reason: str = "") -> Callable:
    """
    废弃警告装饰器
    :param reason: 废弃原因
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import warnings

            warnings.warn(f"{func.__name__} is deprecated. {reason}", DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    return decorator
