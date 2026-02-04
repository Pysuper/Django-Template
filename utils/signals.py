"""
Utility Signals Module / 工具信号模块

This module contains base signal processor classes and system-level signal handlers.
此模块包含基础信号处理器类和系统级信号处理器。

User-specific signals have been moved to apps/users/signals.py to avoid circular dependencies.
用户特定的信号已移至 apps/users/signals.py 以避免循环依赖。
"""

import logging
from typing import Any, Dict, Optional

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import models, transaction
from django.db.models.signals import post_migrate
from django.dispatch import receiver

logger = logging.getLogger(__name__)

User = get_user_model()


class SignalProcessor:
    """
    Signal processor base class / 信号处理器基类

    Provides common methods for signal handlers.
    为信号处理器提供通用方法。
    """

    @classmethod
    def log_changes(cls, instance: models.Model, old_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log data changes / 记录数据变更

        Args:
            instance: Model instance
            old_data: Dictionary of old field values
        """
        if old_data:
            changes = {}
            for field, old_value in old_data.items():
                new_value = getattr(instance, field, None)
                if old_value != new_value:
                    changes[field] = {"old": old_value, "new": new_value}

            if changes:
                logger.info(
                    f"Data changed - Model: {instance.__class__.__name__}, "
                    f"ID: {instance.pk}, Changes: {changes}"
                )

    @classmethod
    def clear_cache(cls, instance: models.Model) -> None:
        """
        Clear cache for the model instance / 清理模型实例的缓存

        Args:
            instance: Model instance
        """
        from django.core.cache import cache

        model_name = instance.__class__.__name__.lower()
        cache_keys = [
            f"{model_name}_{instance.pk}",
            f"{model_name}_list",
            f"{model_name}_all"
        ]
        cache.delete_many(cache_keys)


class SystemSignals(SignalProcessor):
    """
    System-related signal handlers / 系统相关信号处理器

    Handles post-migration operations like creating default data.
    处理迁移后操作，如创建默认数据。
    """

    @classmethod
    @receiver(post_migrate)
    def handle_post_migrate(cls, sender: Any, **kwargs) -> None:
        """
        Handle post-migration operations / 处理迁移后操作

        Args:
            sender: The sender of the signal
            **kwargs: Additional keyword arguments
        """
        try:
            with transaction.atomic():
                # Create superuser / 创建超级管理员
                cls.create_superuser()

                # Create default roles / 创建默认角色
                cls.create_default_roles()

                # Create default permission groups / 创建默认权限组
                cls.create_default_groups()

                # Initialize system settings / 初始化系统设置
                cls.init_system_settings()

        except Exception as e:
            logger.error(f"System initialization failed: {str(e)}")

    @staticmethod
    def create_superuser() -> None:
        """
        Create superuser if not exists / 如果不存在则创建超级管理员

        Note: Update the default password in production!
        注意：在生产环境中更新默认密码！
        """
        from django.conf import settings

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                password=getattr(settings, 'START_PASSWORD', 'admin123'),
                email="admin@example.com",
                phone="13800000000"
            )
            logger.info("Superuser account created successfully")

    @staticmethod
    def create_default_roles() -> None:
        """
        Create default roles / 创建默认角色

        Creates standard roles for the application if they don't exist.
        如果默认角色不存在则创建它们。
        """
        from apps.users.models import Role

        default_roles = [
            {
                "name": "Super Administrator",
                "code": "admin",
                "level": 1,
                "is_default": False,
                "description": "System super administrator / 系统超级管理员"
            },
            {
                "name": "Regular User",
                "code": "user",
                "level": 2,
                "is_default": True,
                "description": "Regular user / 普通用户"
            },
        ]

        for role_data in default_roles:
            Role.objects.get_or_create(
                code=role_data["code"],
                defaults=role_data
            )
        logger.info("Default roles created successfully")

    @staticmethod
    def create_default_groups() -> None:
        """
        Create default permission groups / 创建默认权限组

        Creates standard permission groups with appropriate permissions.
        创建具有适当权限的标准权限组。
        """
        default_groups = [
            {
                "name": "Administrators",
                "permissions": [
                    "add_user", "change_user", "delete_user", "view_user"
                ]
            },
            {
                "name": "Regular Users",
                "permissions": ["view_user"]
            },
        ]

        for group_data in default_groups:
            group, created = Group.objects.get_or_create(name=group_data["name"])
            if created:
                permissions = Permission.objects.filter(
                    codename__in=group_data["permissions"]
                )
                group.permissions.set(permissions)
        logger.info("Default permission groups created successfully")

    @staticmethod
    def init_system_settings() -> None:
        """
        Initialize system settings / 初始化系统设置

        Creates default system configuration settings.
        创建默认系统配置设置。
        """
        from apps.system.models import SystemConfig

        default_settings = [
            {
                "key": "site_name",
                "value": "Django Admin System",
                "type": "string",
                "description": "Site name / 站点名称"
            },
            {
                "key": "site_description",
                "value": "Django-based admin system",
                "type": "string",
                "description": "Site description / 站点描述"
            },
        ]

        for setting in default_settings:
            SystemConfig.objects.get_or_create(
                key=setting["key"],
                defaults=setting
            )
        logger.info("System settings initialized successfully")


# Legacy signal handlers (for backward compatibility)
# These are kept for backward compatibility but should not be used in new code
# 遗留信号处理器（用于向后兼容），不应在新代码中使用

def create_default_login_properties(sender, **kwargs):
    """
    Legacy: Create default login properties

    DEPRECATED: This function is deprecated. Use apps.users.signals instead.
    已弃用：此函数已弃用。请改用 apps.users.signals。
    """
    logger.warning(
        "create_default_login_properties is deprecated. "
        "Use apps.users.signals instead."
    )


def create_user(sender, instance, created, **kwargs):
    """
    Legacy: Create user handler

    DEPRECATED: This function is deprecated. Use apps.users.signals instead.
    已弃用：此函数已弃用。请改用 apps.users.signals。
    """
    logger.warning(
        "create_user signal handler is deprecated. "
        "Use apps.users.signals instead."
    )
