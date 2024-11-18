import logging
import time

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from rest_framework_simplejwt.authentication import JWTAuthentication

# 配置日志记录器
logger = logging.getLogger(__name__)


class AuthenticationMiddleware:
    """用户认证中间件：检查用户是否已登录"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 如果用户未登录且访问路径不是 /login/，则重定向到登录页
        if not request.user.is_authenticated and request.path != "/login/":
            return redirect("/login/")
        # 调用下一个中间件或视图
        response = self.get_response(request)
        return response


class IPWhitelistMiddleware:
    """IP 白名单中间件：限制访问仅允许特定 IP 地址"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_ips = ["127.0.0.1", "192.168.1.1"]  # 允许访问的示例 IP 地址

    def __call__(self, request):
        # 检查请求来源 IP 是否在白名单中
        if request.META["REMOTE_ADDR"] not in self.allowed_ips:
            return HttpResponseForbidden("Forbidden: Your IP is not allowed")
        response = self.get_response(request)
        return response


class RequestTimingMiddleware:
    """请求计时中间件：记录每个请求的处理时间"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 在请求到达视图前记录开始时间
        request.start_time = time.time()
        response = self.get_response(request)
        # 计算并输出请求耗时
        duration = time.time() - request.start_time
        print(f"Request took {duration} seconds.")
        return response


class CustomHeaderMiddleware:
    """自定义头部中间件：为每个响应添加自定义 HTTP 头"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # 添加自定义头部字段
        response["X-Custom-Header"] = "My Custom Value"
        return response


class BlockURLMiddleware:
    """URL 屏蔽中间件：阻止特定 URL 访问"""

    def __init__(self, get_response):
        self.get_response = get_response
        # 需要屏蔽的路径列表
        self.blocked_paths = ["/blocked-path/", "/maintenance/"]

    def __call__(self, request):
        # 如果请求路径在屏蔽列表中，返回 503 响应
        if request.path in self.blocked_paths:
            return HttpResponse("This page is currently unavailable", status=503)
        response = self.get_response(request)
        return response


class UserActivityLogMiddleware:
    """用户活动日志中间件：记录用户访问路径及 IP 信息"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # 记录用户信息及访问路径到日志
        user = request.user.username if request.user.is_authenticated else "Anonymous"
        logger.info(f"{user} accessed {request.path} from IP {request.META['REMOTE_ADDR']}")
        return response


class DisableCSRFMiddleware:
    """禁用 CSRF 检查中间件：用于特定路径或特殊情况的请求"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 设置属性以禁用 CSRF 检查
        setattr(request, "_dont_enforce_csrf_checks", True)
        response = self.get_response(request)
        return response


def get_user_jwt(request):
    """
    从请求头中获取并验证JWT token，返回对应的用户实例
    :param request: HTTP请求对象
    :return: 验证通过返回User实例，否则返回AnonymousUser
    """
    # 从请求头获取Authorization字段并分割
    token = request.headers.get("Authorization", "").split()

    # 验证token格式是否正确(Bearer token)
    if len(token) == 2 and token[0].lower() == "bearer":
        jwt_authenticator = JWTAuthentication()
        try:
            # 验证token的有效性
            validated_token = jwt_authenticator.get_validated_token(token[1])
            # 获取并返回对应的用户实例
            return jwt_authenticator.get_user(validated_token)
        except Exception as e:
            # 记录无效token的错误信息
            print(f"无效的Token: {e}")
            # TODO: 这里可以添加日志记录
    return AnonymousUser()


class JWTAuthenticationMiddleware(MiddlewareMixin):
    """
    JWT认证中间件
    用于处理请求中的JWT认证，将认证后的用户信息附加到request对象
    """

    def process_request(self, request):
        """
        处理每个请求，将认证用户信息添加到request对象
        使用SimpleLazyObject实现延迟加载，提高性能
        """
        request.user = SimpleLazyObject(lambda: get_user_jwt(request))


class DisableCSRFCheck(MiddlewareMixin):
    """
    CSRF验证禁用中间件
    用于特定场景下禁用Django的CSRF保护机制
    """

    def __init__(self, get_response):
        """
        初始化中间件
        :param get_response: 中间件链中的下一个中间件
        """
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request):
        """
        处理请求前禁用CSRF检查
        """
        setattr(request, "_dont_enforce_csrf_checks", True)

    def __call__(self, request):
        """
        中间件的调用方法，处理请求并返回响应
        :param request: HTTP请求对象
        :return: HTTP响应对象
        """
        response = self.get_response(request)
        return response
