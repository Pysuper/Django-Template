from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast
from pydantic import BaseModel, Field, validator
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import CsrfViewMiddleware
from django.utils.html import escape
import bleach
import functools
import logging
import re
from django.conf import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

class SecurityConfig(BaseModel):
    """安全配置模型"""
    xss_protection: bool = Field(default=True, description="是否启用XSS防护")
    csrf_protection: bool = Field(default=True, description="是否启用CSRF防护")
    csrf_trusted_origins: List[str] = Field(default_factory=list, description="CSRF可信源")
    sql_injection_protection: bool = Field(default=True, description="是否启用SQL注入防护")
    security_headers: Dict[str, str] = Field(
        default_factory=lambda: {
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }
    )

    @validator("csrf_trusted_origins")
    def validate_origins(cls, v: List[str]) -> List[str]:
        """验证可信源"""
        return [origin.lower() for origin in v]

@dataclass
class SecurityContext:
    """安全上下文"""
    request: HttpRequest
    config: SecurityConfig
    xss_filter: "XSSFilter"
    sql_filter: "SQLInjectionFilter"

class SecurityMiddleware:
    """安全中间件"""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.config = SecurityConfig(**(getattr(settings, "SECURITY_CONFIG", {})))
        self.xss_filter = XSSFilter()
        self.sql_filter = SQLInjectionFilter()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        context = SecurityContext(
            request=request,
            config=self.config,
            xss_filter=self.xss_filter,
            sql_filter=self.sql_filter
        )

        try:
            self._pre_process_request(context)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=403)

        response = self.get_response(request)
        return self._process_response(response)

    def _pre_process_request(self, context: SecurityContext) -> None:
        """请求预处理"""
        if context.config.csrf_protection:
            self._check_csrf(context)

        if context.config.xss_protection:
            self._check_xss(context)

        if context.config.sql_injection_protection:
            self._check_sql_injection(context)

    def _process_response(self, response: HttpResponse) -> HttpResponse:
        """响应处理"""
        for header, value in self.config.security_headers.items():
            response[header] = value
        return response

    def _check_csrf(self, context: SecurityContext) -> None:
        """CSRF检查"""
        if context.request.method not in ("GET", "HEAD", "OPTIONS", "TRACE"):
            csrf_middleware = CsrfViewMiddleware(self.get_response)
            origin = context.request.META.get("HTTP_ORIGIN", "")
            
            if origin and not any(
                origin.endswith(trusted) for trusted in context.config.csrf_trusted_origins
            ):
                raise PermissionError("CSRF check failed")

            reason = csrf_middleware.process_view(context.request, None, (), {})
            if reason:
                raise PermissionError(str(reason))

    def _check_xss(self, context: SecurityContext) -> None:
        """XSS检查"""
        if context.request.method in ("POST", "PUT", "PATCH"):
            if hasattr(context.request, "body"):
                cleaned_body = self.xss_filter.clean(
                    context.request.body.decode("utf-8")
                )
                if cleaned_body != context.request.body.decode("utf-8"):
                    raise ValueError("Potential XSS attack detected")

            if context.request.POST:
                for key, value in context.request.POST.items():
                    cleaned_value = self.xss_filter.clean(value)
                    if cleaned_value != value:
                        raise ValueError(
                            f"Potential XSS attack detected in field: {key}"
                        )

    def _check_sql_injection(self, context: SecurityContext) -> None:
        """SQL注入检查"""
        for key, value in context.request.GET.items():
            if self.sql_filter.is_suspicious(value):
                raise ValueError(
                    f"Potential SQL injection detected in parameter: {key}"
                )

        if context.request.method in ("POST", "PUT", "PATCH"):
            for key, value in context.request.POST.items():
                if self.sql_filter.is_suspicious(value):
                    raise ValueError(
                        f"Potential SQL injection detected in field: {key}"
                    )

class XSSFilter:
    """XSS过滤器"""

    def __init__(self) -> None:
        self.allowed_tags: Set[str] = {
            "a", "abbr", "acronym", "b", "blockquote", "code",
            "em", "i", "li", "ol", "strong", "ul", "p", "br",
            "div", "span", "h1", "h2", "h3", "h4", "h5", "h6",
        }

        self.allowed_attributes: Dict[str, List[str]] = {
            "a": ["href", "title"],
            "abbr": ["title"],
            "acronym": ["title"],
        }

        self.patterns = {
            "script": re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL),
            "event": re.compile(r"\bon\w+\s*=", re.IGNORECASE),
            "javascript": re.compile(r"javascript:", re.IGNORECASE),
            "data": re.compile(r"data:", re.IGNORECASE),
        }

    def clean(self, text: str) -> str:
        """清理文本"""
        if not text:
            return text

        cleaned_text = bleach.clean(
            text,
            tags=self.allowed_tags,
            attributes=self.allowed_attributes,
            strip=True
        )

        for pattern in self.patterns.values():
            cleaned_text = pattern.sub("", cleaned_text)

        return cleaned_text

    def escape(self, text: str) -> str:
        """转义文本"""
        return escape(text)

class SQLInjectionFilter:
    """SQL注入过滤器"""

    def __init__(self) -> None:
        self.patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in [
                r"(\b(select|insert|update|delete|drop|union|exec)\b)",
                r"(--)",
                r"(;)",
                r"(')",
                r"(\/\*.*?\*\/)",
                r"(\b(or|and)\b\s+\d+\s*[=<>])",
                r"(\b(or|and)\b\s+\w+\s*[=<>])",
            ]
        ]

    def is_suspicious(self, text: str) -> bool:
        """检查是否包含可疑内容"""
        if not text:
            return False
        return any(pattern.search(text) for pattern in self.patterns)

    def clean(self, text: str) -> str:
        """清理文本"""
        if not text:
            return text
        return functools.reduce(
            lambda t, p: p.sub("", t),
            self.patterns,
            text
        )

def xss_clean(func: T) -> T:
    """XSS清理装饰器"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        xss_filter = XSSFilter()
        cleaned_args = [
            xss_filter.clean(arg) if isinstance(arg, str) else arg
            for arg in args
        ]
        cleaned_kwargs = {
            key: xss_filter.clean(value) if isinstance(value, str) else value
            for key, value in kwargs.items()
        }
        return func(*cleaned_args, **cleaned_kwargs)
    return cast(T, wrapper)

def sql_injection_check(func: T) -> T:
    """SQL注入检查装饰器"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        sql_filter = SQLInjectionFilter()
        for arg in args:
            if isinstance(arg, str) and sql_filter.is_suspicious(arg):
                raise ValueError("Potential SQL injection detected")
        for value in kwargs.values():
            if isinstance(value, str) and sql_filter.is_suspicious(value):
                raise ValueError("Potential SQL injection detected")
        return func(*args, **kwargs)
    return cast(T, wrapper)
