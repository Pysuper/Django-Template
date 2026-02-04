"""
RBAC服务 / RBAC Services

提供基于角色的访问控制服务
"""

from typing import List, Optional, TYPE_CHECKING

from django.core.cache import cache
from django.db.models import QuerySet
from django.utils import timezone

if TYPE_CHECKING:
    from apps.users.models import User, Role, Permission, Menu, Button, Tenant


class RBACService:
    """
    RBAC服务类 / RBAC Service Class

    提供完整的RBAC功能服务
    Provides complete RBAC functionality services

    Example:
        >>> service = RBACService()
        >>> # 检查权限
        >>> has_perm = service.has_permission(user, 'user:view')
        >>> # 获取用户菜单
        >>> menus = service.get_user_menus(user)
    """

    def __init__(self):
        """初始化RBAC服务"""
        self.cache_prefix = "rbac"
        self.cache_timeout = 3600  # 1小时

    def _get_cache_key(self, user_id: int, key_type: str) -> str:
        """生成缓存键"""
        return f"{self.cache_prefix}:user:{user_id}:{key_type}"

    def _clear_user_cache(self, user_id: int) -> None:
        """清除用户缓存"""
        keys = [
            self._get_cache_key(user_id, "permissions"),
            self._get_cache_key(user_id, "menus"),
            self._get_cache_key(user_id, "roles"),
            self._get_cache_key(user_id, "data_scope"),
        ]
        cache.delete_many(keys)

    def has_permission(self, user: 'User', permission_code: str) -> bool:
        """
        检查用户是否有指定权限 / Check if user has permission

        Args:
            user: 用户实例 / User instance
            permission_code: 权限代码 / Permission code

        Returns:
            bool: 是否有权限 / Whether user has permission

        Example:
            >>> service = RBACService()
            >>> if service.has_permission(user, 'user:create'):
            ...     # 用户有创建用户的权限
        """
        if not user or not user.is_authenticated:
            return False

        # 超级管理员拥有所有权限
        if user.is_superuser:
            return True

        # 租户管理员拥有所有权限
        if hasattr(user, 'is_tenant_admin') and user.is_tenant_admin:
            return True

        # 检查权限
        return user.has_permission(permission_code)

    def has_role(self, user: 'User', role_code: str) -> bool:
        """
        检查用户是否有指定角色 / Check if user has role

        Args:
            user: 用户实例 / User instance
            role_code: 角色代码 / Role code

        Returns:
            bool: 是否有角色 / Whether user has role

        Example:
            >>> service = RBACService()
            >>> if service.has_role(user, 'admin'):
            ...     # 用户是管理员
        """
        if not user or not user.is_authenticated:
            return False

        return user.has_role(role_code)

    def has_any_role(self, user: 'User', role_codes: List[str]) -> bool:
        """
        检查用户是否有任一角色 / Check if user has any of the roles

        Args:
            user: 用户实例 / User instance
            role_codes: 角色代码列表 / List of role codes

        Returns:
            bool: 是否有任一角色 / Whether user has any role

        Example:
            >>> service = RBACService()
            >>> if service.has_any_role(user, ['admin', 'manager']):
            ...     # 用户是管理员或经理
        """
        if not user or not user.is_authenticated:
            return False

        from apps.users.models import Role

        return user.roles.filter(
            code__in=role_codes,
            is_active=True,
            del_flag=False
        ).exists()

    def has_all_roles(self, user: 'User', role_codes: List[str]) -> bool:
        """
        检查用户是否有所有角色 / Check if user has all roles

        Args:
            user: 用户实例 / User instance
            role_codes: 角色代码列表 / List of role codes

        Returns:
            bool: 是否有所有角色 / Whether user has all roles

        Example:
            >>> service = RBACService()
            >>> if service.has_all_roles(user, ['admin', 'auditor']):
            ...     # 用户既是管理员又是审计员
        """
        if not user or not user.is_authenticated:
            return False

        from apps.users.models import Role

        user_roles = set(
            user.roles.filter(
                is_active=True,
                del_flag=False
            ).values_list('code', flat=True)
        )

        return set(role_codes).issubset(user_roles)

    def get_user_permissions(self, user: 'User') -> List[str]:
        """
        获取用户所有权限代码 / Get user's all permissions

        Args:
            user: 用户实例 / User instance

        Returns:
            List[str]: 权限代码列表 / List of permission codes

        Example:
            >>> service = RBACService()
            >>> permissions = service.get_user_permissions(user)
            >>> print(permissions)
            ['user:view', 'user:create', 'user:update']
        """
        if not user or not user.is_authenticated:
            return []

        # 检查缓存
        cache_key = self._get_cache_key(user.id, "permissions")
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 获取权限
        permissions = user.get_permissions()

        # 缓存结果
        cache.set(cache_key, permissions, self.cache_timeout)

        return permissions

    def get_user_menus(self, user: 'User') -> List['Menu']:
        """
        获取用户可访问的菜单 / Get user's accessible menus

        Args:
            user: 用户实例 / User instance

        Returns:
            List[Menu]: 菜单列表 / List of menus

        Example:
            >>> service = RBACService()
            >>> menus = service.get_user_menus(user)
            >>> for menu in menus:
            ...     print(menu.title)
        """
        if not user or not user.is_authenticated:
            return []

        # 检查缓存
        cache_key = self._get_cache_key(user.id, "menus")
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 获取菜单
        menus = user.get_menus()

        # 缓存结果
        cache.set(cache_key, menus, self.cache_timeout)

        return menus

    def get_user_roles(self, user: 'User') -> List['Role']:
        """
        获取用户所有角色 / Get user's all roles

        Args:
            user: 用户实例 / User instance

        Returns:
            List[Role]: 角色列表 / List of roles

        Example:
            >>> service = RBACService()
            >>> roles = service.get_user_roles(user)
            >>> for role in roles:
            ...     print(role.name)
        """
        if not user or not user.is_authenticated:
            return []

        # 检查缓存
        cache_key = self._get_cache_key(user.id, "roles")
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 获取角色
        from apps.users.models import Role

        roles = list(
            user.roles.filter(
                is_active=True,
                del_flag=False
            ).select_related('tenant')
        )

        # 缓存结果
        cache.set(cache_key, roles, self.cache_timeout)

        return roles

    def assign_role(self, user: 'User', role: 'Role') -> None:
        """
        为用户分配角色 / Assign role to user

        Args:
            user: 用户实例 / User instance
            role: 角色实例 / Role instance

        Example:
            >>> service = RBACService()
            >>> service.assign_role(user, admin_role)
        """
        user.roles.add(role)
        self._clear_user_cache(user.id)

    def remove_role(self, user: 'User', role: 'Role') -> None:
        """
        移除用户角色 / Remove role from user

        Args:
            user: 用户实例 / User instance
            role: 角色实例 / Role instance

        Example:
            >>> service = RBACService()
            >>> service.remove_role(user, admin_role)
        """
        user.roles.remove(role)
        self._clear_user_cache(user.id)

    def assign_permission(self, role: 'Role', permission: 'Permission') -> None:
        """
        为角色分配权限 / Assign permission to role

        Args:
            role: 角色实例 / Role instance
            permission: 权限实例 / Permission instance

        Example:
            >>> service = RBACService()
            >>> service.assign_permission(role, perm)
        """
        role.permissions.add(permission)

    def remove_permission(self, role: 'Role', permission: 'Permission') -> None:
        """
        移除角色权限 / Remove permission from role

        Args:
            role: 角色实例 / Role instance
            permission: 权限实例 / Permission instance

        Example:
            >>> service = RBACService()
            >>> service.remove_permission(role, perm)
        """
        role.permissions.remove(permission)

    def get_user_data_scope(self, user: 'User') -> str:
        """
        获取用户的数据访问范围 / Get user's data access scope

        Args:
            user: 用户实例 / User instance

        Returns:
            str: 数据范围 / Data scope
                 - 'all': 全部数据 / All data
                 - 'dept_and_sub': 本部门及子部门数据 / Department and sub-department data
                 - 'dept': 本部门数据 / Department data
                 - 'self': 仅本人数据 / Self data only

        Example:
            >>> service = RBACService()
            >>> scope = service.get_user_data_scope(user)
            >>> if scope == 'all':
            ...     # 用户可以访问所有数据
        """
        if not user or not user.is_authenticated:
            return 'self'

        # 超级管理员
        if user.is_superuser:
            return 'all'

        # 租户管理员
        if hasattr(user, 'is_tenant_admin') and user.is_tenant_admin:
            return 'all'

        # 检查缓存
        cache_key = self._get_cache_key(user.id, "data_scope")
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 获取数据范围
        data_scope = user.get_data_scope()

        # 缓存结果
        cache.set(cache_key, data_scope, self.cache_timeout)

        return data_scope

    def filter_data_by_scope(
        self,
        user: 'User',
        queryset: QuerySet
    ) -> QuerySet:
        """
        根据用户数据范围过滤查询集 / Filter queryset by user's data scope

        Args:
            user: 用户实例 / User instance
            queryset: 查询集 / QuerySet

        Returns:
            QuerySet: 过滤后的查询集 / Filtered queryset

        Example:
            >>> service = RBACService()
            >>> queryset = Document.objects.all()
            >>> filtered = service.filter_data_by_scope(user, queryset)
        """
        if not user or not user.is_authenticated:
            return queryset.none()

        scope = self.get_user_data_scope(user)

        # 超级管理员和租户管理员可以访问所有数据
        if scope == 'all':
            return queryset

        # 获取用户的部门
        if hasattr(user, 'department') and user.department:
            dept = user.department

            # 本部门及子部门数据
            if scope == 'dept_and_sub':
                dept_ids = [dept.id] + [
                    d.id for d in dept.get_descendants()
                ]
                return queryset.filter(department__id__in=dept_ids)

            # 本部门数据
            elif scope == 'dept':
                return queryset.filter(department=dept)

        # 仅本人数据
        return queryset.filter(id=user.id)


# 创建全局RBAC服务实例
rbac_service = RBACService()
