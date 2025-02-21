import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Optional, Union

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils.functional import SimpleLazyObject
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

# 配置日志记录器
logger = logging.getLogger(__name__)


class BaseMiddleware:
    """中间件基类"""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        return None

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        return response

    def process_exception(self, request: HttpRequest, exception: Exception) -> Optional[HttpResponse]:
        return None


class SecurityMiddleware(BaseMiddleware):
    """安全中间件：包含多个安全相关的功能"""

    def __init__(self, get_response: Callable):
        super().__init__(get_response)
        self.allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
        self.allowed_ips = getattr(settings, "ALLOWED_IPS", ["127.0.0.1"])
        self.rate_limit = getattr(settings, "RATE_LIMIT", 100)  # 默认每分钟100次
        self.rate_limit_period = getattr(settings, "RATE_LIMIT_PERIOD", 60)  # 默认60秒

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 检查Host头
        if not self._validate_host(request):
            return HttpResponseForbidden("Invalid Host header")

        # 检查IP白名单
        if not self._validate_ip(request):
            return HttpResponseForbidden("IP not allowed")

        # 检查请求频率
        if not self._check_rate_limit(request):
            return HttpResponseForbidden("Too many requests")

        # 添加安全头
        response = self.get_response(request)
        return self._add_security_headers(response)

    def _validate_host(self, request: HttpRequest) -> bool:
        """验证Host头"""
        host = request.get_host()
        return host in self.allowed_hosts or not self.allowed_hosts

    def _validate_ip(self, request: HttpRequest) -> bool:
        """验证IP白名单"""
        ip = self._get_client_ip(request)
        return ip in self.allowed_ips or not self.allowed_ips

    def _check_rate_limit(self, request: HttpRequest) -> bool:
        """检查请求频率限制"""
        ip = self._get_client_ip(request)
        cache_key = f"rate_limit_{ip}"

        # 获取当前请求次数
        requests = cache.get(cache_key, 0)
        if requests >= self.rate_limit:
            return False

        # 更新请求次数
        cache.set(cache_key, requests + 1, self.rate_limit_period)
        return True

    def _add_security_headers(self, response: HttpResponse) -> HttpResponse:
        """添加安全响应头"""
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        for header, value in security_headers.items():
            response[header] = value
        return response

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """获取客户端真实IP"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR", "")


class RequestLoggingMiddleware(BaseMiddleware):
    """请求日志中间件：记录详细的请求和响应信息"""

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 记录请求开始时间
        request.start_time = time.time()

        # 记录请求信息
        self._log_request(request)

        try:
            response = self.get_response(request)
            self._log_response(request, response)
            return response
        except Exception as e:
            self._log_exception(request, e)
            raise

    def _log_request(self, request: HttpRequest) -> None:
        """记录请求信息"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "method": request.method,
            "path": request.path,
            "user": str(request.user),
            "ip": SecurityMiddleware._get_client_ip(request),
            "user_agent": request.META.get("HTTP_USER_AGENT", ""),
            "query_params": dict(request.GET),
            "request_id": request.META.get("HTTP_X_REQUEST_ID", ""),
        }

        # 记录POST数据（注意敏感信息处理）
        if request.method == "POST":
            try:
                log_data["body"] = self._sanitize_data(request.POST)
            except:
                log_data["body"] = "<无法解析的数据>"

        logger.info(f"Request: {json.dumps(log_data)}")

    def _log_response(self, request: HttpRequest, response: HttpResponse) -> None:
        """记录响应信息"""
        duration = time.time() - request.start_time

        log_data = {
            "status_code": response.status_code,
            "duration": f"{duration:.3f}s",
            "content_type": response.get("Content-Type", ""),
            "content_length": len(response.content) if hasattr(response, "content") else 0,
        }

        logger.info(f"Response: {json.dumps(log_data)}")

    def _log_exception(self, request: HttpRequest, exception: Exception) -> None:
        """记录异常信息"""
        duration = time.time() - request.start_time

        log_data = {
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "duration": f"{duration:.3f}s",
        }

        logger.error(f"Exception: {json.dumps(log_data)}", exc_info=True)

    @staticmethod
    def _sanitize_data(data: Any) -> Any:
        """清理敏感数据"""
        if isinstance(data, dict):
            return {k: "***" if k.lower() in ["password", "token", "secret"] else v for k, v in data.items()}
        return data


class JWTAuthMiddleware(BaseMiddleware):
    """JWT认证中间件：处理JWT认证并缓存用户信息"""

    def __init__(self, get_response: Callable):
        super().__init__(get_response)
        self.jwt_auth = JWTAuthentication()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.user = SimpleLazyObject(lambda: self._get_user(request))
        return self.get_response(request)

    def _get_user(self, request: HttpRequest) -> Union[AnonymousUser, Any]:
        """获取用户信息"""
        # 从请求头获取token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return AnonymousUser()

        token = auth_header.split(" ")[1]

        # 尝试从缓存获取用户
        cache_key = f"jwt_user_{token}"
        cached_user = cache.get(cache_key)
        if cached_user is not None:
            return cached_user

        try:
            # 验证token
            validated_token = self.jwt_auth.get_validated_token(token)
            user = self.jwt_auth.get_user(validated_token)

            # 缓存用户信息（设置过期时间略短于token过期时间）
            cache_timeout = getattr(settings, "JWT_USER_CACHE_TIMEOUT", 300)  # 默认5分钟
            cache.set(cache_key, user, cache_timeout)

            return user
        except (InvalidToken, TokenError) as e:
            logger.warning(f"Invalid token: {str(e)}")
            return AnonymousUser()


class APIThrottlingMiddleware(BaseMiddleware):
    """API限流中间件：基于用户或IP的API访问限制"""

    def __init__(self, get_response: Callable):
        super().__init__(get_response)
        self.rate_limits = {
            "anonymous": getattr(settings, "API_RATE_LIMIT_ANONYMOUS", 100),  # 每分钟访问次数
            "authenticated": getattr(settings, "API_RATE_LIMIT_AUTHENTICATED", 1000),
            "period": getattr(settings, "API_RATE_LIMIT_PERIOD", 60),  # 时间窗口（秒）
        }

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self._should_throttle(request):
            return self.get_response(request)

        return JsonResponse({"error": "Too many requests", "detail": "API rate limit exceeded"}, status=429)

    def _should_throttle(self, request: HttpRequest) -> bool:
        """检查是否应该限流"""
        # 获取限流key
        if request.user.is_authenticated:
            key = f"throttle_user_{request.user.id}"
            limit = self.rate_limits["authenticated"]
        else:
            key = f"throttle_ip_{SecurityMiddleware._get_client_ip(request)}"
            limit = self.rate_limits["anonymous"]

        # 获取当前时间窗口的请求次数
        current = cache.get(key, 0)

        # 超过限制
        if current >= limit:
            return True

        # 更新请求次数
        cache.set(key, current + 1, self.rate_limits["period"])
        return False
