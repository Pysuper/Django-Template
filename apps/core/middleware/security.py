"""
Security Middleware / 安全中间件

提供安全相关的HTTP头和安全检查功能
"""

import functools
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Type, cast

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.html import escape

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])


class SecurityMiddleware:
    """
    安全中间件 / Security Middleware

    添加安全相关的HTTP响应头
    Adds security-related HTTP headers to responses

    Features:
        - X-Content-Type-Options: nosniff
        - X-Frame-Options: DENY
        - X-XSS-Protection: 1; mode=block
        - Referrer-Policy: strict-origin-when-cross-origin
        - Content-Security-Policy
        - Strict-Transport-Security (HTTPS only)

    Example:
        # 在settings.py中配置
        MIDDLEWARE = [
            ...
            'apps.core.middleware.security.SecurityMiddleware',
            ...
        ]

        SECURITY_HEADERS = {
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
        }
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """
        初始化中间件

        Args:
            get_response: 下一个中间件或视图的调用函数
        """
        self.get_response = get_response
        self.security_headers = self._get_security_headers()

    def _get_security_headers(self) -> Dict[str, str]:
        """
        获取安全头配置

        Returns:
            安全头字典
        """
        return {
            'X-Frame-Options': 'DENY',
            'X-Content-Type-Options': 'nosniff',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'",
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        }

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求并添加安全头

        Args:
            request: HTTP请求对象

        Returns:
            带有安全头的HTTP响应对象
        """
        response = self.get_response(request)

        # 添加安全头
        for header, value in self.security_headers.items():
            response[header] = value

        # 如果是HTTPS请求，添加HSTS头
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response


class XSSProtectionMiddleware:
    """
    XSS防护中间件 / XSS Protection Middleware

    检测和过滤XSS攻击
    Detects and filters XSS attacks

    Features:
        - 检测常见的XSS攻击模式
        - 清理和过滤用户输入
        - 转义HTML特殊字符

    Example:
        # 在settings.py中配置
        MIDDLEWARE = [
            ...
            'apps.core.middleware.security.XSSProtectionMiddleware',
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
        self.xss_patterns = self._compile_xss_patterns()

    def _compile_xss_patterns(self) -> List[re.Pattern]:
        """
        编译XSS检测模式

        Returns:
            正则表达式模式列表
        """
        patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<link[^>]*>',
            r'<meta[^>]*>',
        ]
        return [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in patterns]

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求并检查XSS

        Args:
            request: HTTP请求对象

        Returns:
            HTTP响应对象，或错误响应（如果检测到XSS）
        """
        # 检查GET参数
        for key, value in request.GET.items():
            if self._detect_xss(value):
                logger.warning(f'XSS attempt detected in GET parameter: {key}')
                return JsonResponse(
                    {'error': 'Invalid input detected'},
                    status=400
                )

        # 检查POST参数
        if request.method in ('POST', 'PUT', 'PATCH'):
            for key, value in request.POST.items():
                if self._detect_xss(value):
                    logger.warning(f'XSS attempt detected in POST parameter: {key}')
                    return JsonResponse(
                        {'error': 'Invalid input detected'},
                        status=400
                    )

        return self.get_response(request)

    def _detect_xss(self, text: str) -> bool:
        """
        检测文本中是否包含XSS

        Args:
            text: 待检测的文本

        Returns:
            True如果检测到XSS，否则False
        """
        for pattern in self.xss_patterns:
            if pattern.search(text):
                return True
        return False


class SQLInjectionProtectionMiddleware:
    """
    SQL注入防护中间件 / SQL Injection Protection Middleware

    检测SQL注入攻击
    Detects SQL injection attacks

    Example:
        # 在settings.py中配置
        MIDDLEWARE = [
            ...
            'apps.core.middleware.security.SQLInjectionProtectionMiddleware',
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
        self.sql_injection_patterns = self._compile_sql_patterns()

    def _compile_sql_patterns(self) -> List[re.Pattern]:
        """
        编译SQL注入检测模式

        Returns:
            正则表达式模式列表
        """
        patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC)\b)",
            r"(--)",
            r"(;)",
            r"(')",
            r"(\/\*.*?\*\/)",
            r"(\b(OR|AND)\b\s+\d+\s*[=<>])",
            r"(\b(OR|AND)\b\s+\w+\s*[=<>])",
        ]
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求并检查SQL注入

        Args:
            request: HTTP请求对象

        Returns:
            HTTP响应对象，或错误响应（如果检测到SQL注入）
        """
        # 检查GET参数
        for key, value in request.GET.items():
            if self._detect_sql_injection(value):
                logger.warning(f'SQL injection attempt detected in GET parameter: {key}')
                return JsonResponse(
                    {'error': 'Invalid input detected'},
                    status=400
                )

        # 检查POST参数
        if request.method in ('POST', 'PUT', 'PATCH'):
            for key, value in request.POST.items():
                if self._detect_sql_injection(value):
                    logger.warning(f'SQL injection attempt detected in POST parameter: {key}')
                    return JsonResponse(
                        {'error': 'Invalid input detected'},
                        status=400
                    )

        return self.get_response(request)

    def _detect_sql_injection(self, text: str) -> bool:
        """
        检测文本中是否包含SQL注入

        Args:
            text: 待检测的文本

        Returns:
            True如果检测到SQL注入，否则False
        """
        for pattern in self.sql_injection_patterns:
            if pattern.search(text):
                return True
        return False


class CORSMiddleware:
    """
    CORS中间件 / CORS Middleware

    处理跨域资源共享
    Handles Cross-Origin Resource Sharing

    Example:
        # 在settings.py中配置
        MIDDLEWARE = [
            ...
            'apps.core.middleware.security.CORSMiddleware',
            ...
        ]

        CORS_ALLOWED_ORIGINS = [
            'https://example.com',
            'https://app.example.com',
        ]

        CORS_ALLOW_CREDENTIALS = True
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """
        初始化中间件

        Args:
            get_response: 下一个中间件或视图的调用函数
        """
        self.get_response = get_response
        self.allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        self.allow_credentials = getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)
        self.allowed_methods = getattr(settings, 'CORS_ALLOWED_METHODS', ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
        self.allowed_headers = getattr(settings, 'CORS_ALLOWED_HEADERS', ['Content-Type', 'Authorization'])

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求并添加CORS头

        Args:
            request: HTTP请求对象

        Returns:
            带有CORS头的HTTP响应对象
        """
        origin = request.META.get('HTTP_ORIGIN')

        # 检查是否是预检请求
        if request.method == 'OPTIONS':
            response = JsonResponse({'status': 'ok'})
        else:
            response = self.get_response(request)

        # 如果origin在允许列表中，添加CORS头
        if origin in self.allowed_origins or '*' in self.allowed_origins:
            response['Access-Control-Allow-Origin'] = origin if origin != '*' else '*'
            response['Access-Control-Allow-Credentials'] = 'true' if self.allow_credentials else 'false'
            response['Access-Control-Allow-Methods'] = ', '.join(self.allowed_methods)
            response['Access-Control-Allow-Headers'] = ', '.join(self.allowed_headers)
            response['Access-Control-Max-Age'] = '86400'  # 24小时

        return response

def xss_clean(func: T) -> T:
    """
    XSS清理装饰器 / XSS clean decorator

    清理函数参数中的XSS代码
    Cleans XSS code from function arguments

    Example:
        @xss_clean
        def my_view(request, text):
            # text已经被清理
            return JsonResponse({'result': text})
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        cleaned_args = []
        for arg in args:
            if isinstance(arg, str):
                cleaned_args.append(escape(arg))
            else:
                cleaned_args.append(arg)

        cleaned_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                cleaned_kwargs[key] = escape(value)
            else:
                cleaned_kwargs[key] = value

        return func(*cleaned_args, **cleaned_kwargs)

    return cast(T, wrapper)
