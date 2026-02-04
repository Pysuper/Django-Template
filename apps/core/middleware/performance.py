"""
Performance Middleware / 性能监控中间件

提供请求响应时间和日志记录功能
"""

import json
import logging
import time
from typing import Any, Callable, Dict

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.utils import get_client_ip

logger = logging.getLogger(__name__)


class ResponseTimeMiddleware:
    """
    响应时间中间件 / Response Time Middleware

    添加X-Response-Time头，记录请求处理时间
    Adds X-Response-Time header to track request processing time

    Example:
        # 在settings.py中添加
        MIDDLEWARE = [
            ...
            'apps.core.middleware.ResponseTimeMiddleware',
            ...
        ]
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """
        初始化中间件

        Args:
            get_response: 下一个中间件或视图的调用函数
        """
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求

        Args:
            request: HTTP请求对象

        Returns:
            HTTP响应对象，包含X-Response-Time头
        """
        start_time = time.time()
        response = self.get_response(request)
        response_time = time.time() - start_time

        # 添加响应时间头（毫秒）
        response['X-Response-Time'] = f'{int(response_time * 1000)}'

        # 记录慢查询
        slow_request_threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD', 1.0)  # 1秒
        if response_time > slow_request_threshold:
            logger.warning(
                f'Slow request detected: {request.path} took {response_time:.2f}s',
                extra={
                    'path': request.path,
                    'method': request.method,
                    'response_time': response_time,
                }
            )

        return response


class RequestLogMiddleware:
    """
    请求日志中间件 / Request Logging Middleware

    记录请求的详细信息
    Logs detailed information about requests

    Features:
        - 记录请求路径、方法、IP地址
        - 记录请求参数和Body
        - 记录响应状态码和处理时间
        - 支持敏感数据过滤

    Example:
        # 在settings.py中配置
        MIDDLEWARE = [
            ...
            'apps.core.middleware.RequestLogMiddleware',
            ...
        ]

        REQUEST_LOGGING = True  # 启用请求日志
        REQUEST_LOGGING_SENSITIVE_FIELDS = ['password', 'token']  # 敏感字段
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """
        初始化中间件

        Args:
            get_response: 下一个中间件或视图的调用函数
        """
        self.get_response = get_response
        self.sensitive_fields = getattr(
            settings,
            'REQUEST_LOGGING_SENSITIVE_FIELDS',
            ['password', 'token', 'api_key', 'secret']
        )

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求并记录日志

        Args:
            request: HTTP请求对象

        Returns:
            HTTP响应对象
        """
        # 记录请求开始时间
        request.start_time = time.time()

        # 获取请求信息
        request_data = {
            'path': request.path,
            'method': request.method,
            'ip': get_client_ip(request),
            'user': str(request.user) if request.user.is_authenticated else 'Anonymous',
            'data': self._get_request_data(request),
        }

        response = self.get_response(request)

        # 记录响应信息
        response_data = {
            'status': response.status_code,
            'time': time.time() - request.start_time,
        }

        # 在这里可以添加日志记录逻辑
        if getattr(settings, 'REQUEST_LOGGING', False):
            logger.info(
                f'Request: {request.method} {request.path}',
                extra={
                    'request': request_data,
                    'response': response_data,
                }
            )

        return response

    def _get_request_data(self, request: HttpRequest) -> Dict[str, Any]:
        """
        获取请求数据

        Args:
            request: HTTP请求对象

        Returns:
            包含请求数据的字典
        """
        data = {}

        # GET参数
        if request.GET:
            data['GET'] = self._filter_sensitive_data(dict(request.GET))

        # POST参数
        if request.POST:
            data['POST'] = self._filter_sensitive_data(dict(request.POST))

        # Body数据
        if request.body:
            try:
                body_data = json.loads(request.body)
                data['body'] = self._filter_sensitive_data(body_data)
            except (json.JSONDecodeError, UnicodeDecodeError):
                # 如果不是JSON，不记录body
                pass

        return data

    def _filter_sensitive_data(self, data: Any) -> Any:
        """
        过滤敏感数据

        Args:
            data: 原始数据

        Returns:
            过滤后的数据
        """
        if isinstance(data, dict):
            return {
                k: '***FILTERED***' if k.lower() in self.sensitive_fields else self._filter_sensitive_data(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._filter_sensitive_data(item) for item in data]
        return data


class RequestSizeMiddleware:
    """
    请求大小限制中间件 / Request Size Limit Middleware

    限制请求大小，防止大文件攻击
    Limits request size to prevent large file attacks

    Example:
        # 在settings.py中配置
        MIDDLEWARE = [
            ...
            'apps.core.middleware.RequestSizeMiddleware',
            ...
        ]

        MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """
        初始化中间件

        Args:
            get_response: 下一个中间件或视图的调用函数
        """
        self.get_response = get_response
        self.max_size = getattr(settings, 'MAX_REQUEST_SIZE', 10 * 1024 * 1024)  # 10MB

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求，检查请求大小

        Args:
            request: HTTP请求对象

        Returns:
            HTTP响应对象，或错误响应（如果请求过大）
        """
        # 检查Content-Length
        content_length = request.META.get('CONTENT_LENGTH')
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    return JsonResponse(
                        {
                            'error': f'Request too large. Maximum size is {self.max_size} bytes'
                        },
                        status=413
                    )
            except ValueError:
                pass

        # 检查实际body大小
        if hasattr(request, 'body') and len(request.body) > self.max_size:
            return JsonResponse(
                {
                    'error': f'Request too large. Maximum size is {self.max_size} bytes'
                },
                status=413
            )

        return self.get_response(request)
