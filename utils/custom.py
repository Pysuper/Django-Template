from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Model, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer

User = get_user_model()


class CustomModelSerializer(ModelSerializer):
    """自定义模型序列化器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = self.context.get("request")
        self.user = self.request.user if self.request else None

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """数据验证"""
        # 创建时自动添加创建者
        if not self.instance and self.user and hasattr(self.Meta.model, "create_by"):
            attrs["create_by"] = self.user

        # 更新时自动添加更新者
        if self.instance and self.user and hasattr(self.Meta.model, "update_by"):
            attrs["update_by"] = self.user
            attrs["update_time"] = datetime.now()

        return super().validate(attrs)


class CustomPagination(PageNumberPagination):
    """自定义分页器"""

    page_size = 10
    page_size_query_param = "size"
    max_page_size = 1000
    page_query_param = "page"

    def get_paginated_response(self, data: List[Dict[str, Any]]) -> Response:
        """自定义分页响应格式"""
        return Response(
            OrderedDict(
                [
                    ("code", status.HTTP_200_OK),
                    ("message", _("获取成功")),
                    (
                        "data",
                        OrderedDict(
                            [
                                ("list", data),
                                (
                                    "pagination",
                                    {
                                        "page": self.page.number,
                                        "size": self.page_size,
                                        "total": self.page.paginator.count,
                                        "pages": self.page.paginator.num_pages,
                                    },
                                ),
                            ]
                        ),
                    ),
                ]
            )
        )


class LargePagination(CustomPagination):
    """大数据分页器"""

    page_size = 50
    max_page_size = 5000

    def paginate_queryset(self, queryset: QuerySet, request: HttpRequest, view=None) -> Optional[List[Any]]:
        """分页查询优化"""
        if not self.get_page_size(request):
            return None

        paginator = self.django_paginator_class(queryset.only("id"), self.get_page_size(request))  # 只查询ID
        page_number = request.query_params.get(self.page_query_param, 1)

        try:
            self.page = paginator.page(page_number)
        except Exception as e:
            from utils.log.logger import logger

            logger.warning(f"分页错误: {str(e)}")
            self.page = paginator.page(1)

        # 获取完整数据
        ids = [obj.id for obj in self.page]
        self.page.object_list = queryset.filter(id__in=ids)

        return list(self.page)


class RolePermission(BasePermission):
    """角色权限控制"""

    def has_permission(self, request: HttpRequest, view: Any) -> bool:
        """检查权限"""
        # 超级管理员拥有所有权限
        if request.user.is_superuser:
            return True

        # 获取用户角色权限
        perms = self.get_role_permissions(request.user)
        if not perms:
            return False

        # 检查视图权限
        required_perms = self.get_view_permissions(view)
        if not required_perms:
            return True

        return any(perm in perms for perm in required_perms)

    def get_role_permissions(self, user: User) -> List[str]:
        """获取用户角色权限"""
        # 尝试从缓存获取
        cache_key = f"user_perms_{user.id}"
        perms = cache.get(cache_key)
        if perms is not None:
            return perms

        # 从数据库获取
        perms = list(user.roles.values_list("permissions__code", flat=True).distinct())

        # 缓存权限
        cache.set(cache_key, perms, timeout=300)  # 缓存5分钟

        return perms

    def get_view_permissions(self, view: Any) -> List[str]:
        """获取视图所需权限"""
        if not hasattr(view, "permission_required"):
            return []

        if isinstance(view.permission_required, str):
            return [view.permission_required]

        return list(view.permission_required)


class DataPermission(BasePermission):
    """数据权限控制"""

    def has_permission(self, request: HttpRequest, view: Any) -> bool:
        """检查数据权限"""
        if request.user.is_superuser:
            return True

        if not hasattr(view, "data_scope_required"):
            return True

        return self.check_data_scope(request.user, view.data_scope_required)

    def has_object_permission(self, request: HttpRequest, view: Any, obj: Model) -> bool:
        """检查对象权限"""
        if request.user.is_superuser:
            return True

        # 检查数据所有者
        if hasattr(obj, "create_by") and obj.create_by == request.user:
            return True

        # 检查数据范围
        if hasattr(view, "data_scope_required"):
            return self.check_object_scope(request.user, obj, view.data_scope_required)

        return True

    def check_data_scope(self, user: User, required_scope: str) -> bool:
        """检查数据范围"""
        from utils.error import DataScopeEnum

        # 获取用户数据范围
        user_scope = self.get_user_data_scope(user)
        if not user_scope:
            return False

        # 检查数据范围
        scope_levels = {
            DataScopeEnum.ALL.value: 0,
            DataScopeEnum.DEPT_AND_CHILD.value: 1,
            DataScopeEnum.DEPT.value: 2,
            DataScopeEnum.SELF.value: 3,
        }

        return scope_levels.get(user_scope, 999) <= scope_levels.get(required_scope, 999)

    def check_object_scope(self, user: User, obj: Model, required_scope: str) -> bool:
        """检查对象范围"""
        from utils.error import DataScopeEnum

        # 获取用户数据范围
        user_scope = self.get_user_data_scope(user)
        if not user_scope:
            return False

        # 检查数据范围
        if user_scope == DataScopeEnum.ALL.value:
            return True

        if user_scope == DataScopeEnum.DEPT_AND_CHILD.value:
            return self.check_dept_and_child_scope(user, obj)

        if user_scope == DataScopeEnum.DEPT.value:
            return self.check_dept_scope(user, obj)

        if user_scope == DataScopeEnum.SELF.value:
            return self.check_self_scope(user, obj)

        return False

    def get_user_data_scope(self, user: User) -> Optional[str]:
        """获取用户数据范围"""
        # 尝试从缓存获取
        cache_key = f"user_scope_{user.id}"
        scope = cache.get(cache_key)
        if scope is not None:
            return scope

        # 从数据库获取
        scope = user.roles.values_list("data_scope", flat=True).first()

        # 缓存数据范围
        cache.set(cache_key, scope, timeout=300)  # 缓存5分钟

        return scope

    def check_dept_and_child_scope(self, user: User, obj: Model) -> bool:
        """检查部门及子部门范围"""
        if not hasattr(obj, "dept"):
            return False

        return obj.dept.is_child_of(user.dept)

    def check_dept_scope(self, user: User, obj: Model) -> bool:
        """检查部门范围"""
        if not hasattr(obj, "dept"):
            return False

        return obj.dept == user.dept

    def check_self_scope(self, user: User, obj: Model) -> bool:
        """检查个人范围"""
        if hasattr(obj, "create_by"):
            return obj.create_by == user

        if hasattr(obj, "user"):
            return obj.user == user

        return False


class CustomPermission(RolePermission, DataPermission):
    """自定义权限"""

    def has_permission(self, request: HttpRequest, view: Any) -> bool:
        """检查权限"""
        return super(RolePermission, self).has_permission(request, view) and super(DataPermission, self).has_permission(
            request, view
        )

    def has_object_permission(self, request: HttpRequest, view: Any, obj: Model) -> bool:
        """检查对象权限"""
        return super(RolePermission, self).has_object_permission(request, view, obj) and super(
            DataPermission, self
        ).has_object_permission(request, view, obj)
