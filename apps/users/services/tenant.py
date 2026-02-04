"""
多租户服务 / Multi-Tenancy Services

提供多租户系统的核心功能
"""

import logging
from typing import Optional, TYPE_CHECKING

from django.conf import settings
from django.core.cache import cache
from django.db.models import QuerySet

if TYPE_CHECKING:
    from apps.users.models import Tenant, User

logger = logging.getLogger(__name__)


class TenantService:
    """
    租户服务类 / Tenant Service Class

    提供租户管理的核心功能
    Provides core tenant management functionality

    Example:
        >>> service = TenantService()
        >>> tenant = service.get_tenant_by_code('acme')
        >>> service.create_tenant('Acme Corp', 'acme')
    """

    def __init__(self):
        """初始化租户服务"""
        self.cache_prefix = "tenant"
        self.cache_timeout = 3600  # 1小时
        self.multi_tenant_enabled = getattr(settings, 'MULTI_TENANT_ENABLED', True)

    def _get_cache_key(self, key_type: str, identifier: str) -> str:
        """生成缓存键"""
        return f"{self.cache_prefix}:{key_type}:{identifier}"

    def get_tenant_by_id(self, tenant_id: int) -> Optional['Tenant']:
        """
        根据ID获取租户 / Get tenant by ID

        Args:
            tenant_id: 租户ID / Tenant ID

        Returns:
            Optional[Tenant]: 租户实例或None / Tenant instance or None
        """
        if not self.multi_tenant_enabled:
            return None

        # 检查缓存
        cache_key = self._get_cache_key("id", str(tenant_id))
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 查询数据库
        from apps.users.models import Tenant

        try:
            tenant = Tenant.objects.get(id=tenant_id, del_flag=False)
            cache.set(cache_key, tenant, self.cache_timeout)
            return tenant
        except Tenant.DoesNotExist:
            return None

    def get_tenant_by_code(self, code: str) -> Optional['Tenant']:
        """
        根据代码获取租户 / Get tenant by code

        Args:
            code: 租户代码 / Tenant code

        Returns:
            Optional[Tenant]: 租户实例或None / Tenant instance or None

        Example:
            >>> service = TenantService()
            >>> tenant = service.get_tenant_by_code('acme')
            >>> if tenant:
            ...     print(tenant.name)
        """
        if not self.multi_tenant_enabled:
            return None

        # 检查缓存
        cache_key = self._get_cache_key("code", code)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 查询数据库
        from apps.users.models import Tenant

        try:
            tenant = Tenant.objects.get(code=code, del_flag=False)
            cache.set(cache_key, tenant, self.cache_timeout)
            return tenant
        except Tenant.DoesNotExist:
            return None

    def get_tenant_by_domain(self, domain: str) -> Optional['Tenant']:
        """
        根据域名获取租户 / Get tenant by domain

        Args:
            domain: 租户域名 / Tenant domain

        Returns:
            Optional[Tenant]: 租户实例或None / Tenant instance or None

        Example:
            >>> service = TenantService()
            >>> tenant = service.get_tenant_by_domain('acme.example.com')
            >>> if tenant:
            ...     return tenant
        """
        if not self.multi_tenant_enabled:
            return None

        # 检查缓存
        cache_key = self._get_cache_key("domain", domain)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 查询数据库
        from apps.users.models import Tenant

        try:
            tenant = Tenant.objects.get(domain=domain, del_flag=False)
            cache.set(cache_key, tenant, self.cache_timeout)
            return tenant
        except Tenant.DoesNotExist:
            return None

    def create_tenant(
        self,
        name: str,
        code: str,
        domain: Optional[str] = None,
        max_users: int = 100,
        **kwargs
    ) -> 'Tenant':
        """
        创建租户 / Create tenant

        Args:
            name: 租户名称 / Tenant name
            code: 租户代码 / Tenant code
            domain: 租户域名 / Tenant domain
            max_users: 最大用户数 / Maximum users
            **kwargs: 其他参数 / Other parameters

        Returns:
            Tenant: 创建的租户实例 / Created tenant instance

        Raises:
            ValueError: 如果多租户未启用 / If multi-tenancy is disabled
            ValidationError: 如果验证失败 / If validation fails

        Example:
            >>> service = TenantService()
            >>> tenant = service.create_tenant(
            ...     name='Acme Corp',
            ...     code='acme',
            ...     domain='acme.example.com',
            ...     max_users=200
            ... )
        """
        if not self.multi_tenant_enabled:
            raise ValueError("Multi-tenancy is not enabled")

        from apps.users.models import Tenant

        # 检查代码是否已存在
        if Tenant.objects.filter(code=code).exists():
            raise ValueError(f"Tenant with code '{code}' already exists")

        # 检查域名是否已存在
        if domain and Tenant.objects.filter(domain=domain).exists():
            raise ValueError(f"Tenant with domain '{domain}' already exists")

        # 创建租户
        tenant = Tenant.objects.create(
            name=name,
            code=code,
            domain=domain,
            max_users=max_users,
            **kwargs
        )

        logger.info(f"Created tenant: {name} ({code})")

        return tenant

    def update_tenant(
        self,
        tenant: 'Tenant',
        **kwargs
    ) -> 'Tenant':
        """
        更新租户信息 / Update tenant information

        Args:
            tenant: 租户实例 / Tenant instance
            **kwargs: 要更新的字段 / Fields to update

        Returns:
            Tenant: 更新后的租户实例 / Updated tenant instance

        Example:
            >>> service = TenantService()
            >>> tenant = service.get_tenant_by_code('acme')
            >>> service.update_tenant(tenant, name='New Name', max_users=200)
        """
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)

        tenant.save()

        # 清除缓存
        self._clear_tenant_cache(tenant.id, tenant.code, tenant.domain)

        logger.info(f"Updated tenant: {tenant.code}")

        return tenant

    def deactivate_tenant(self, tenant: 'Tenant') -> None:
        """
        停用租户 / Deactivate tenant

        Args:
            tenant: 租户实例 / Tenant instance

        Example:
            >>> service = TenantService()
            >>> tenant = service.get_tenant_by_code('acme')
            >>> service.deactivate_tenant(tenant)
        """
        tenant.is_active = False
        tenant.save()

        # 清除缓存
        self._clear_tenant_cache(tenant.id, tenant.code, tenant.domain)

        logger.warning(f"Deactivated tenant: {tenant.code}")

    def activate_tenant(self, tenant: 'Tenant') -> None:
        """
        激活租户 / Activate tenant

        Args:
            tenant: 租户实例 / Tenant instance

        Example:
            >>> service = TenantService()
            >>> tenant = service.get_tenant_by_code('acme')
            >>> service.activate_tenant(tenant)
        """
        tenant.is_active = True
        tenant.save()

        # 清除缓存
        self._clear_tenant_cache(tenant.id, tenant.code, tenant.domain)

        logger.info(f"Activated tenant: {tenant.code}")

    def is_tenant_active(self, tenant: 'Tenant') -> bool:
        """
        检查租户是否激活 / Check if tenant is active

        Args:
            tenant: 租户实例 / Tenant instance

        Returns:
            bool: 是否激活 / Whether tenant is active

        Example:
            >>> service = TenantService()
            >>> tenant = service.get_tenant_by_code('acme')
            >>> if service.is_tenant_active(tenant):
            ...     print("Tenant is active")
        """
        if not tenant:
            return False

        return tenant.is_active and not tenant.is_expired()

    def can_add_user(self, tenant: 'Tenant') -> bool:
        """
        检查租户是否可以添加用户 / Check if tenant can add user

        Args:
            tenant: 租户实例 / Tenant instance

        Returns:
            bool: 是否可以添加用户 / Whether can add user

        Example:
            >>> service = TenantService()
            >>> tenant = service.get_tenant_by_code('acme')
            >>> if service.can_add_user(tenant):
            ...     # 可以添加新用户
        """
        if not tenant:
            return False

        return tenant.is_active and tenant.is_within_user_limit() and not tenant.is_expired()

    def get_tenant_user_count(self, tenant: 'Tenant') -> int:
        """
        获取租户的用户数量 / Get tenant's user count

        Args:
            tenant: 租户实例 / Tenant instance

        Returns:
            int: 用户数量 / User count

        Example:
            >>> service = TenantService()
            >>> tenant = service.get_tenant_by_code('acme')
            >>> count = service.get_tenant_user_count(tenant)
            >>> print(f"User count: {count}")
        """
        if not tenant:
            return 0

        return tenant.get_user_count()

    def filter_queryset_by_tenant(
        self,
        user: 'User',
        queryset: QuerySet
    ) -> QuerySet:
        """
        根据用户租户过滤查询集 / Filter queryset by user's tenant

        Args:
            user: 用户实例 / User instance
            queryset: 查询集 / QuerySet

        Returns:
            QuerySet: 过滤后的查询集 / Filtered queryset

        Example:
            >>> service = TenantService()
            >>> queryset = Document.objects.all()
            >>> filtered = service.filter_queryset_by_tenant(user, queryset)
        """
        if not self.multi_tenant_enabled:
            return queryset

        if not user or not user.is_authenticated:
            return queryset.none()

        # 超级管理员可以看到所有租户的数据
        if user.is_superuser:
            return queryset

        # 过滤用户的租户数据
        if hasattr(user, 'tenant'):
            return queryset.filter(tenant=user.tenant)

        return queryset.none()

    def _clear_tenant_cache(
        self,
        tenant_id: int,
        code: str,
        domain: Optional[str] = None
    ) -> None:
        """清除租户缓存"""
        keys = [
            self._get_cache_key("id", str(tenant_id)),
            self._get_cache_key("code", code),
        ]
        if domain:
            keys.append(self._get_cache_key("domain", domain))

        cache.delete_many(keys)

    def get_all_tenants(self) -> QuerySet:
        """
        获取所有租户 / Get all tenants

        Returns:
            QuerySet: 租户查询集 / Tenant queryset

        Example:
            >>> service = TenantService()
            >>> tenants = service.get_all_tenants()
            >>> for tenant in tenants:
            ...     print(tenant.name)
        """
        from apps.users.models import Tenant

        return Tenant.objects.filter(del_flag=False)


# 创建全局租户服务实例
tenant_service = TenantService()
