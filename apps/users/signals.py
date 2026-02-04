"""
User Application Signals / 用户应用信号处理

This module contains all signal handlers related to user management.
此模块包含所有与用户管理相关的信号处理器。
"""

import logging
from datetime import datetime
from typing import Optional

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

User = get_user_model()


@receiver(post_save, sender=User)
def handle_user_create(sender, instance: User, created: bool, **kwargs) -> None:
    """
    Handle user creation signal / 处理用户创建信号

    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved
        created: Boolean; True if a new record was created
        **kwargs: Additional keyword arguments
    """
    if created:
        # Encrypt password if not already encrypted
        # 如果密码未加密，则加密密码
        if not instance.password.startswith("pbkdf2_sha256$"):
            instance.set_password(instance.password)
            instance.save()

        # Create user settings / 创建用户设置
        create_user_settings(instance)

        # Assign default role / 分配默认角色
        assign_default_role(instance)

        logger.info(f"New user created: {instance.username}")


@receiver(pre_save, sender=User)
def handle_user_update(sender, instance: User, **kwargs) -> None:
    """
    Handle user update signal / 处理用户更新信号

    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved
        **kwargs: Additional keyword arguments
    """
    if instance.pk:
        try:
            from django.core.cache import cache

            old_instance = sender.objects.get(pk=instance.pk)
            old_data = {
                "username": old_instance.username,
                "email": old_instance.email,
                "is_active": old_instance.is_active,
                "is_staff": old_instance.is_staff,
            }

            # Log changes / 记录变更
            changes = {}
            for field, old_value in old_data.items():
                new_value = getattr(instance, field, None)
                if old_value != new_value:
                    changes[field] = {"old": old_value, "new": new_value}

            if changes:
                logger.info(
                    f"User data changed - User: {instance.username}, "
                    f"ID: {instance.pk}, Changes: {changes}"
                )

            # Clear cache / 清理缓存
            model_name = instance.__class__.__name__.lower()
            cache_keys = [
                f"{model_name}_{instance.pk}",
                f"{model_name}_list",
                f"{model_name}_all"
            ]
            cache.delete_many(cache_keys)

        except User.DoesNotExist:
            pass


@receiver(pre_delete, sender=User)
def handle_user_delete(sender, instance: User, **kwargs) -> None:
    """
    Handle user deletion signal / 处理用户删除信号

    Args:
        sender: The model class that sent the signal
        instance: The actual instance being deleted
        **kwargs: Additional keyword arguments
    """
    from django.core.cache import cache

    # Cleanup user data / 清理用户数据
    cleanup_user_data(instance)

    # Clear cache / 清理缓存
    model_name = instance.__class__.__name__.lower()
    cache_keys = [
        f"{model_name}_{instance.pk}",
        f"{model_name}_list",
        f"{model_name}_all"
    ]
    cache.delete_many(cache_keys)

    logger.info(f"User deleted: {instance.username}")


def create_user_settings(user: User) -> None:
    """
    Create default user settings / 创建默认用户设置

    Args:
        user: User instance
    """
    from apps.users.models import UserSettings

    UserSettings.objects.get_or_create(
        user=user,
        defaults={
            "theme": "light",
            "language": "zh-hans",
            "timezone": "Asia/Shanghai"
        }
    )


def assign_default_role(user: User) -> None:
    """
    Assign default role to user / 为用户分配默认角色

    Args:
        user: User instance
    """
    from apps.users.models import Role

    default_role = Role.objects.filter(is_default=True).first()
    if default_role:
        user.roles.add(default_role)


def cleanup_user_data(user: User) -> None:
    """
    Cleanup user related data / 清理用户相关数据

    Args:
        user: User instance
    """
    # Add cleanup logic here / 在此添加清理逻辑
    # Example: Delete user sessions, logs, etc.
    pass


# Custom signals / 自定义信号
from django.dispatch import Signal

user_logged_in = Signal()  # User login signal / 用户登录信号
user_logged_out = Signal()  # User logout signal / 用户登出信号
user_login_failed = Signal()  # User login failed signal / 用户登录失败信号
user_password_changed = Signal()  # User password changed signal / 用户密码修改信号
user_password_reset = Signal()  # User password reset signal / 用户密码重置信号


@receiver(user_logged_in)
def handle_user_login(sender, user: User, request, **kwargs) -> None:
    """
    Handle user login signal / 处理用户登录信号

    Args:
        sender: The sender of the signal
        user: User instance
        request: HttpRequest object
        **kwargs: Additional keyword arguments
    """
    # Update login info / 更新登录信息
    user.last_login = datetime.now()
    user.login_count = getattr(user, "login_count", 0) + 1
    user.save(update_fields=["last_login", "login_count"])

    # Log login / 记录登录日志
    ip = request.META.get("REMOTE_ADDR")
    user_agent = request.META.get("HTTP_USER_AGENT")
    logger.info(
        f"User login - User: {user.username}, "
        f"IP: {ip}, Device: {user_agent}"
    )
