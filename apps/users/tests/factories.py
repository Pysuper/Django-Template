"""
Factory Boy Factories for User Management / 用户管理工厂类

This module contains factory classes for creating test data.
此模块包含用于创建测试数据的工厂类。
"""

import factory
from django.contrib.auth import get_user_model

from apps.users.models import Role, UserSettings

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    """
    Factory for User model / 用户模型工厂

    Usage:
        user = UserFactory()
        admin_user = UserFactory(is_staff=True)
        custom_user = UserFactory(username="custom", email="custom@example.com")
    """

    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    phone = factory.Sequence(lambda n: f"138{n:08d}")
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Set password for user / 为用户设置密码"""
        if not create:
            return

        if extracted:
            password = extracted
        else:
            password = "testpass123"

        obj.set_password(password)
        obj.save()


class AdminUserFactory(UserFactory):
    """
    Factory for admin users / 管理员用户工厂

    Usage:
        admin = AdminUserFactory()
    """

    is_staff = True
    is_superuser = True


class RoleFactory(factory.django.DjangoModelFactory):
    """
    Factory for Role model / 角色模型工厂

    Usage:
        role = RoleFactory()
        admin_role = RoleFactory(code="admin", level=1)
    """

    class Meta:
        model = Role
        django_get_or_create = ("code",)

    name = factory.Sequence(lambda n: f"Role {n}")
    code = factory.Sequence(lambda n: f"role_{n}")
    level = 1
    is_default = False
    description = "Test role"


class DefaultRoleFactory(RoleFactory):
    """
    Factory for default role / 默认角色工厂

    Usage:
        default_role = DefaultRoleFactory()
    """

    is_default = True
    name = "Default Role"
    code = "default"


class UserSettingsFactory(factory.django.DjangoModelFactory):
    """
    Factory for UserSettings model / 用户设置模型工厂

    Usage:
        settings = UserSettingsFactory(user=my_user)
        settings_with_custom_theme = UserSettingsFactory(theme="dark")
    """

    class Meta:
        model = UserSettings
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    theme = "light"
    language = "zh-hans"
    timezone = "Asia/Shanghai"
