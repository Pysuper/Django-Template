"""
多租户中间件 / Multi-Tenancy Middleware

处理多租户系统的请求上下文
"""

import logging
from typing import Callable, Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

from apps.users.services.tenant import tenant_service

logger = logging.getLogger(__name__)


class TenantMiddleware(MiddlewareMixin):
    """
    租户中间件 / Tenant Middleware

    从请求中识别租户，并将其添加到请求上下文中
    Identifies tenant from request and adds it to request context

    租户识别方式：
    1. 子域名: tenant.example.com
    2. HTTP头: X-Tenant-Code
    3. 查询参数: ?tenant=code

    Example:
        # settings.py
        MIDDLEWARE = [
            ...
            'apps.users.middleware.TenantMiddleware',
            ...
        ]
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """
        初始化中间件

        Args:
            get_response: 下一个中间件或视图
        """
        self.get_response = get_response
        self.multi_tenant_enabled = getattr(settings, 'MULTI_TENANT_ENABLED', True)

    def process_request(self, request: HttpRequest) -> None:
        """
        处理请求，识别租户

        Args:
            request: HTTP请求对象
        """
        # 如果多租户未启用，跳过
        if not self.multi_tenant_enabled:
            return

        # 尝试识别租户
        tenant = self._identify_tenant(request)

        if tenant:
            # 检查租户状态
            if not tenant_service.is_tenant_active(tenant):
                logger.warning(f"Inactive tenant accessed: {tenant.code}")
                # 可以选择返回403或继续处理

            # 将租户添加到请求对象
            request.tenant = tenant

            # 如果用户已认证，检查用户是否属于该租户
            if request.user.is_authenticated:
                if hasattr(request.user, 'tenant'):
                    if request.user.tenant != tenant:
                        logger.warning(
                            f"User {request.user.username} accessing "
                            f"different tenant {tenant.code}"
                        )
                else:
                    logger.warning(
                        f"User {request.user.username} has no tenant"
                    )
        else:
            # 如果没有识别到租户，且是必需的，返回401
            tenant_required = getattr(settings, 'MULTI_TENANT_REQUIRED', False)
            if tenant_required and not request.user.is_superuser:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Tenant identification required")

    def _identify_tenant(self, request: HttpRequest) -> Optional:
        """
        识别请求中的租户

        Args:
            request: HTTP请求对象

        Returns:
            租户实例或None
        """
        tenant = None

        # 1. 从HTTP头获取租户
        tenant_code = request.META.get('HTTP_X_TENANT_CODE')
        if tenant_code:
            tenant = tenant_service.get_tenant_by_code(tenant_code)
            if tenant:
                logger.debug(f"Tenant identified from header: {tenant_code}")
                return tenant

        # 2. 从子域名获取租户
        host = request.get_host()
        if host:
            # 提取子域名
            parts = host.split('.')
            if len(parts) > 2:  # 有子域名
                subdomain = parts[0]
                # 尝试通过域名查找租户
                tenant = tenant_service.get_tenant_by_domain(host)
                if tenant:
                    logger.debug(f"Tenant identified from domain: {host}")
                    return tenant

                # 尝试通过子域名（代码）查找租户
                tenant = tenant_service.get_tenant_by_code(subdomain)
                if tenant:
                    logger.debug(f"Tenant identified from subdomain: {subdomain}")
                    return tenant

        # 3. 从查询参数获取租户（仅用于API）
        if hasattr(request, 'GET'):
            tenant_code = request.GET.get('tenant')
            if tenant_code:
                tenant = tenant_service.get_tenant_by_code(tenant_code)
                if tenant:
                    logger.debug(f"Tenant identified from query param: {tenant_code}")
                    return tenant

        logger.debug(f"No tenant identified for request: {request.path}")
        return None


class TenantContextMiddleware:
    """
    租户上下文中间件 / Tenant Context Middleware

    为模板和视图提供租户上下文
    Provides tenant context for templates and views

    Example:
        # settings.py
        MIDDLEWARE = [
            ...
            'apps.users.middleware.TenantContextMiddleware',
            ...
        ]
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """
        初始化中间件

        Args:
            get_response: 下一个中间件或视图
        """
        self.get_response = get_response
        self.multi_tenant_enabled = getattr(settings, 'MULTI_TENANT_ENABLED', True)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求

        Args:
            request: HTTP请求对象

        Returns:
            HTTP响应对象
        """
        # 处理请求
        response = self.get_response(request)

        # 添加租户信息到响应头（如果存在）
        if self.multi_tenant_enabled and hasattr(request, 'tenant'):
            response['X-Tenant-Code'] = request.tenant.code
            response['X-Tenant-Name'] = request.tenant.name

        return response


class TenantIsolationMiddleware:
    """
    租户隔离中间件 / Tenant Isolation Middleware

    确保用户只能访问自己租户的数据
    Ensures users can only access their own tenant's data

    Example:
        # settings.py
        MIDDLEWARE = [
            ...
            'apps.users.middleware.TenantIsolationMiddleware',
            ...
        ]
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        """
        初始化中间件

        Args:
            get_response: 下一个中间件或视图
        """
        self.get_response = get_response
        self.multi_tenant_enabled = getattr(settings, 'MULTI_TENANT_ENABLED', True)
        # 排除的路径
        self.excluded_paths = getattr(settings, 'TENANT_ISOLATION_EXCLUDE_PATHS', [
            '/admin/',
            '/health/',
            '/metrics/',
        ])

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        处理请求，执行租户隔离检查

        Args:
            request: HTTP请求对象

        Returns:
            HTTP响应对象
        """
        if not self.multi_tenant_enabled:
            return self.get_response(request)

        # 检查是否需要排除
        for path in self.excluded_paths:
            if request.path.startswith(path):
                return self.get_response(request)

        # 检查用户认证
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 超级管理员跳过检查
        if request.user.is_superuser:
            return self.get_response(request)

        # 检查用户是否有租户
        if not hasattr(request.user, 'tenant') or not request.user.tenant:
            logger.error(f"User {request.user.username} has no tenant")
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("User has no tenant assigned")

        # 检查用户租户是否与请求租户匹配
        if hasattr(request, 'tenant') and request.tenant:
            if request.user.tenant != request.tenant:
                logger.error(
                    f"User {request.user.username} trying to access "
                    f"different tenant {request.tenant.code}"
                )
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied("Tenant mismatch")

        return self.get_response(request)
