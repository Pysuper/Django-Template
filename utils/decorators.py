import hashlib
from functools import wraps

from django.core.cache import cache
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.http import JsonResponse
from django.urls import reverse
from rest_framework import status

from error import ErrorCode, ParamError
from utils.handler import custom_exception_handler
from utils.log.logger import logger
from utils.response import XopsResponse

"""
@login_required
@admin_only
@cache_page(60 * 15)  # 缓存 15 分钟
@user_has_permission('app.view_model')
def my_view(request):
    # 视图逻辑
    pass
"""


# 结果写入缓存=> 装饰器：decorators
def cache_to_redis(timeout=60 * 15):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成一个唯一的缓存键
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            print(f"---i cache key->>{cache_key}")

            # 尝试从缓存获取结果
            if cache.get(cache_key) is not None:
                print(f"---i from cache key->>{cache_key}")
                return cache.get(cache_key)

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)

            return result

        return wrapper

    return decorator


# 请求频率限制=> 装饰器：decorators
def request_frequency_limit(func):
    """
    请求频率限制
    :param func:
    :return:
    """

    def wrapper(request, *args, **kwargs):

        body = str(request.body.decode("utf-8"))
        key = f"zfx_{hashlib.md5(body.encode('utf8')).hexdigest()}"
        val = cache.get(key)
        if val:
            logger.info(f"已存在key={key}")
            raise ParamError("请求太频繁，请稍后再请求", ErrorCode.PARAM_ERROR)
        else:
            # 给redis中加入了键为key，值为value缓存，过期时间60秒
            cache.set(key, "1", 60)

        try:
            func_result = func(request, *args, **kwargs)
            return func_result
        finally:
            # 删除redis中key的值
            cache.delete(key)

    return wrapper


# 用户认证、权限检查装饰器
def login_required(view_func):
    """
    检查用户是否登录，未登录则重定向到登录页面。
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 如果用户未登录，重定向到登录页
        if not request.user.is_authenticated:
            login_url = reverse("login")
            return HttpResponseRedirect(login_url)
        # 已登录则继续处理视图函数
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# 用户权限检查装饰器
def user_has_permission(permission):
    """
    检查用户是否具有指定的权限，无权限则返回403响应。
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 如果用户没有指定权限，返回403禁止访问
            if not request.user.has_perm(permission):
                return HttpResponseForbidden("Forbidden: You don't have permission to access this page.")
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


# 记录用户访问装饰器
def log_user_activity(view_func):
    """
    日志记录装饰器：记录用户的访问路径和用户名。
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 记录用户访问信息
        user = request.user.username if request.user.is_authenticated else "Anonymous"
        print(f"User {user} accessed {request.path}")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# 页面缓存装饰器
def cache_page(timeout):
    """
    页面缓存装饰器：缓存视图返回的页面指定时间。
    :param timeout: 缓存时间（秒）
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 缓存的键为视图路径
            cache_key = f"cache:{request.get_full_path()}"
            response = cache.get(cache_key)
            # 如果缓存存在，直接返回缓存内容
            if response:
                return response
            # 缓存不存在，则调用视图函数，并设置缓存
            response = view_func(request, *args, **kwargs)
            cache.set(cache_key, response, timeout)
            return response

        return _wrapped_view

    return decorator


# 允许仅管理员访问的装饰器
def admin_only(view_func):
    """
    限制仅管理员用户可访问视图，普通用户访问时返回403。
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 检查用户是否为管理员
        if not request.user.is_staff:
            return HttpResponseForbidden("Forbidden: Admins only.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# AJAX请求检查装饰器
def ajax_required(view_func):
    """
    AJAX 请求检查装饰器：仅允许 AJAX 请求访问视图。
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 检查请求是否为 AJAX 请求
        if not request.is_ajax():
            return HttpResponseForbidden("Forbidden: This view only accepts AJAX requests.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


# 日志记录装饰器
def log_request(func):
    """
    记录请求信息的装饰器。
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Request to {func.__name__} with args: {args} and kwargs: {kwargs}")
        return func(*args, **kwargs)

    return wrapper


# 性能监测装饰器
def performance_monitor(func):
    """
    监测函数执行时间的装饰器。
    返回JSON格式的响应，包含执行时间信息。
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        import time

        start_time = time.time()
        response = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"{func.__name__} executed in {execution_time:.4f} seconds")
        return JsonResponse({"status": "success", "execution_time": execution_time})

    return wrapper


# 全局响应拦截器装饰器
def global_response_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 获取原始响应
            response = func(*args, **kwargs)

            # 如果已经是XopsResponse类型,直接返回
            if isinstance(response, XopsResponse):
                return response

            # 统一响应格式
            return XopsResponse(data=response, message="success", code=status.HTTP_200_OK)

        except Exception as e:
            # 异常交给异常处理器处理
            return custom_exception_handler(e, context={"view": func})

    return wrapper
