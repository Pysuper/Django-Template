"""
权限装饰器 / Permission Decorators

提供权限检查的装饰器
"""

import functools
from typing import Callable, List, Optional

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.users.services.rbac import rbac_service


def require_permission(permission_code: str):
    """
    权限要求装饰器 / Require permission decorator

    检查用户是否具有指定权限
    Checks if user has the specified permission

    Args:
        permission_code: 权限代码 / Permission code

    Example:
        @require_permission('user:create')
        def create_user(request):
            # 只有有 user:create 权限的用户才能访问
            pass
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            if not rbac_service.has_permission(request.user, permission_code):
                raise PermissionDenied(f"Permission required: {permission_code}")

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def require_role(role_code: str):
    """
    角色要求装饰器 / Require role decorator

    检查用户是否具有指定角色
    Checks if user has the specified role

    Args:
        role_code: 角色代码 / Role code

    Example:
        @require_role('admin')
        def admin_view(request):
            # 只有管理员角色的用户才能访问
            pass
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            if not rbac_service.has_role(request.user, role_code):
                raise PermissionDenied(f"Role required: {role_code}")

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def require_any_role(role_codes: List[str]):
    """
    任一角色要求装饰器 / Require any role decorator

    检查用户是否具有任一指定角色
    Checks if user has any of the specified roles

    Args:
        role_codes: 角色代码列表 / List of role codes

    Example:
        @require_any_role(['admin', 'manager'])
        def management_view(request):
            # 管理员或经理角色的用户都能访问
            pass
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            if not rbac_service.has_any_role(request.user, role_codes):
                raise PermissionDenied(f"One of these roles required: {', '.join(role_codes)}")

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def require_all_roles(role_codes: List[str]):
    """
    所有角色要求装饰器 / Require all roles decorator

    检查用户是否具有所有指定角色
    Checks if user has all of the specified roles

    Args:
        role_codes: 角色代码列表 / List of role codes

    Example:
        @require_all_roles(['admin', 'auditor'])
        def audit_view(request):
            # 必须同时是管理员和审计员才能访问
            pass
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            if not rbac_service.has_all_roles(request.user, role_codes):
                raise PermissionDenied(f"All these roles required: {', '.join(role_codes)}")

            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


def require_tenant_admin(view_func: Callable) -> Callable:
    """
    租户管理员装饰器 / Require tenant admin decorator

    检查用户是否是租户管理员
    Checks if user is a tenant administrator

    Example:
        @require_tenant_admin
        def tenant_settings_view(request):
            # 只有租户管理员才能访问
            pass
    """
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)

        if not request.user.is_superuser:
            if not hasattr(request.user, 'is_tenant_admin') or not request.user.is_tenant_admin:
                raise PermissionDenied("Tenant admin required")

        return view_func(request, *args, **kwargs)
    return wrapped_view


def data_scope_required(view_func: Callable) -> Callable:
    """
    数据范围装饰器 / Data scope decorator

    根据用户的数据访问范围过滤数据
    Filter data based on user's data access scope

    Example:
        @data_scope_required
        def user_list_view(request):
            # 视函数自动根据用户的数据范围过滤
            queryset = User.objects.all()
            # 已经自动过滤
            pass
    """
    @functools.wraps(view_func)
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(settings.LOGIN_URL)

        # 将数据范围信息添加到请求中
        from apps.users.services.rbac import rbac_service
        request.data_scope = rbac_service.get_user_data_scope(request.user)

        return view_func(request, *args, **kwargs)
    return wrapped_view


# DRF权限类
from rest_framework import permissions


class HasPermission(permissions.BasePermission):
    """
    权限检查类 / Permission check class

    用于DRF视图的权限检查
    Permission check for DRF views

    Example:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [HasPermission]
            required_permission = 'user:view'
    """
    required_permission = None

    def has_permission(self, request, view):
        """检查是否有权限"""
        if not request.user or not request.user.is_authenticated:
            return False

        # 超级管理员拥有所有权限
        if request.user.is_superuser:
            return True

        # 获取需要的权限
        permission_code = getattr(view, 'required_permission', None)
        if not permission_code:
            return True

        return rbac_service.has_permission(request.user, permission_code)


class HasRole(permissions.BasePermission):
    """
    角色检查类 / Role check class

    用于DRF视图的角色检查
    Role check for DRF views

    Example:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [HasRole]
            required_role = 'admin'
    """
    required_role = None

    def has_permission(self, request, view):
        """检查是否有角色"""
        if not request.user or not request.user.is_authenticated:
            return False

        # 超级管理员拥有所有角色
        if request.user.is_superuser:
            return True

        # 获取需要的角色
        role_code = getattr(view, 'required_role', None)
        if not role_code:
            return True

        return rbac_service.has_role(request.user, role_code)


class IsTenantAdmin(permissions.BasePermission):
    """
    租户管理员检查类 / Tenant admin check class

    检查用户是否是租户管理员
    Checks if user is a tenant administrator

    Example:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [IsTenantAdmin]
    """

    def has_permission(self, request, view):
        """检查是否是租户管理员"""
        if not request.user or not request.user.is_authenticated:
            return False

        # 超级管理员
        if request.user.is_superuser:
            return True

        # 租户管理员
        return hasattr(request.user, 'is_tenant_admin') and request.user.is_tenant_admin


class DataScopePermission(permissions.BasePermission):
    """
    数据范围权限类 / Data scope permission class

    根据用户的数据访问范围过滤数据
    Filter data based on user's data access scope

    Example:
        class MyViewSet(viewsets.ModelViewSet):
            permission_classes = [DataScopePermission]
    """

    def has_permission(self, request, view):
        """检查是否有权限"""
        if not request.user or not request.user.is_authenticated:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        """检查对象权限"""
        # 超级管理员可以访问所有对象
        if request.user.is_superuser:
            return True

        # 租户管理员可以访问租户内的所有对象
        if hasattr(request.user, 'is_tenant_admin') and request.user.is_tenant_admin:
            return True

        # 检查数据范围
        from apps.users.services.rbac import rbac_service
        data_scope = rbac_service.get_user_data_scope(request.user)

        # 全部数据
        if data_scope == 'all':
            return True

        # 仅本人数据
        if data_scope == 'self':
            return obj.id == request.user.id

        # 部门数据
        if hasattr(request.user, 'department'):
            if data_scope == 'dept':
                return hasattr(obj, 'department') and obj.department == request.user.department
            elif data_scope == 'dept_and_sub':
                if hasattr(obj, 'department'):
                    dept_ids = [request.user.department.id] + [
                        d.id for d in request.user.department.get_descendants()
                    ]
                    return obj.department.id in dept_ids

        return False
