import logging
from datetime import datetime
from typing import Any, Dict, Optional, Type

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.db import models, transaction
from django.db.models.signals import post_migrate, post_save, pre_delete, pre_save
from django.dispatch import Signal, receiver

logger = logging.getLogger(__name__)

User = get_user_model()

# 自定义信号
user_logged_in = Signal()  # 用户登录信号
user_logged_out = Signal()  # 用户登出信号
user_login_failed = Signal()  # 用户登录失败信号
user_password_changed = Signal()  # 用户密码修改信号
user_password_reset = Signal()  # 用户密码重置信号


class SignalProcessor:
    """信号处理器基类"""

    @classmethod
    def log_changes(cls, instance: models.Model, old_data: Optional[Dict[str, Any]] = None) -> None:
        """记录数据变更"""
        if old_data:
            changes = {}
            for field, old_value in old_data.items():
                new_value = getattr(instance, field, None)
                if old_value != new_value:
                    changes[field] = {"old": old_value, "new": new_value}
            if changes:
                logger.info(f"数据变更 - 模型: {instance.__class__.__name__}, " f"ID: {instance.pk}, 变更: {changes}")

    @classmethod
    def clear_cache(cls, instance: models.Model) -> None:
        """清理缓存"""
        model_name = instance.__class__.__name__.lower()
        cache_keys = [f"{model_name}_{instance.pk}", f"{model_name}_list", f"{model_name}_all"]
        cache.delete_many(cache_keys)


class UserSignals(SignalProcessor):
    """用户相关信号处理"""

    @classmethod
    @receiver(post_save, sender=User)
    def handle_user_create(cls, sender: Type[User], instance: User, created: bool, **kwargs) -> None:
        """处理用户创建"""
        if created:
            # 加密密码
            if not instance.password.startswith("pbkdf2_sha256$"):
                instance.set_password(instance.password)
                instance.save()

            # 创建用户配置
            cls.create_user_settings(instance)

            # 分配默认角色
            cls.assign_default_role(instance)

            logger.info(f"新用户创建成功: {instance.username}")

    @classmethod
    @receiver(pre_save, sender=User)
    def handle_user_update(cls, sender: Type[User], instance: User, **kwargs) -> None:
        """处理用户更新"""
        if instance.pk:
            try:
                old_instance = sender.objects.get(pk=instance.pk)
                old_data = {
                    "username": old_instance.username,
                    "email": old_instance.email,
                    "is_active": old_instance.is_active,
                    "is_staff": old_instance.is_staff,
                }
                cls.log_changes(instance, old_data)
                cls.clear_cache(instance)
            except User.DoesNotExist:
                pass

    @classmethod
    @receiver(pre_delete, sender=User)
    def handle_user_delete(cls, sender: Type[User], instance: User, **kwargs) -> None:
        """处理用户删除"""
        # 清理用户数据
        cls.cleanup_user_data(instance)
        cls.clear_cache(instance)
        logger.info(f"用户删除: {instance.username}")

    @classmethod
    @receiver(user_logged_in)
    def handle_user_login(cls, sender: Type[User], user: User, request: Any, **kwargs) -> None:
        """处理用户登录"""
        # 更新登录信息
        user.last_login = datetime.now()
        user.login_count = getattr(user, "login_count", 0) + 1
        user.save(update_fields=["last_login", "login_count"])

        # 记录登录日志
        ip = request.META.get("REMOTE_ADDR")
        user_agent = request.META.get("HTTP_USER_AGENT")
        logger.info(f"用户登录 - 用户: {user.username}, IP: {ip}, 设备: {user_agent}")

    @staticmethod
    def create_user_settings(user: User) -> None:
        """创建用户配置"""
        from apps.users.models import UserSettings

        UserSettings.objects.create(user=user, theme="light", language="zh-hans", timezone="Asia/Shanghai")

    @staticmethod
    def assign_default_role(user: User) -> None:
        """分配默认角色"""
        from apps.users.models import Role

        default_role = Role.objects.filter(is_default=True).first()
        if default_role:
            user.roles.add(default_role)

    @staticmethod
    def cleanup_user_data(user: User) -> None:
        """清理用户数据"""
        # 这里可以添加清理用户相关数据的逻辑
        pass


class SystemSignals(SignalProcessor):
    """系统相关信号处理"""

    @classmethod
    @receiver(post_migrate)
    def handle_post_migrate(cls, sender: Any, **kwargs) -> None:
        """处理迁移后操作"""
        try:
            with transaction.atomic():
                # 创建超级管理员
                cls.create_superuser()

                # 创建默认角色
                cls.create_default_roles()

                # 创建默认权限组
                cls.create_default_groups()

                # 初始化系统配置
                cls.init_system_settings()

        except Exception as e:
            logger.error(f"系统初始化失败: {str(e)}")

    @staticmethod
    def create_superuser() -> None:
        """创建超级管理员"""
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin", password="admin123", email="admin@example.com", phone="13800000000"
            )
            logger.info("成功创建超级管理员账号")

    @staticmethod
    def create_default_roles() -> None:
        """创建默认角色"""
        from apps.users.models import Role

        default_roles = [
            {"name": "超级管理员", "code": "admin", "level": 1, "is_default": False, "description": "系统超级管理员"},
            {"name": "普通用户", "code": "user", "level": 2, "is_default": True, "description": "普通用户"},
        ]

        for role_data in default_roles:
            Role.objects.get_or_create(code=role_data["code"], defaults=role_data)
        logger.info("成功创建默认角色")

    @staticmethod
    def create_default_groups() -> None:
        """创建默认权限组"""
        default_groups = [
            {"name": "管理员组", "permissions": ["add_user", "change_user", "delete_user", "view_user"]},
            {"name": "普通用户组", "permissions": ["view_user"]},
        ]

        for group_data in default_groups:
            group, created = Group.objects.get_or_create(name=group_data["name"])
            if created:
                permissions = Permission.objects.filter(codename__in=group_data["permissions"])
                group.permissions.set(permissions)
        logger.info("成功创建默认权限组")

    @staticmethod
    def init_system_settings() -> None:
        """初始化系统配置"""
        from apps.system.models import SystemConfig

        default_settings = [
            {
                "key": "site_name",
                "value": "后台管理系统",
                "type": "string",
                "description": "站点名称",
            },
            {
                "key": "site_description",
                "value": "基于Django的后台管理系统",
                "type": "string",
                "description": "站点描述",
            },
        ]

        for setting in default_settings:
            SystemConfig.objects.get_or_create(key=setting["key"], defaults=setting)
        logger.info("成功初始化系统配置")
