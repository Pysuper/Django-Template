from datetime import timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.authentication.models import LoginHistory, VerificationCode

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """用户工厂类"""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    phone = factory.Sequence(lambda n: f"1380013{n:04d}")
    password = factory.PostGenerationMethodCall("set_password", "password123")
    is_active = True
    is_staff = False
    is_superuser = False

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                self.groups.add(group)

    @factory.post_generation
    def user_permissions(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for permission in extracted:
                self.user_permissions.add(permission)


class SuperUserFactory(UserFactory):
    """超级用户工厂类"""
    is_staff = True
    is_superuser = True


class LoginHistoryFactory(DjangoModelFactory):
    """登录历史工厂类"""

    class Meta:
        model = LoginHistory

    user = factory.SubFactory(UserFactory)
    ip_address = factory.Sequence(lambda n: f"192.168.1.{n}")
    user_agent = factory.Faker("user_agent")
    location = factory.Faker("city")
    status = True


class VerificationCodeFactory(DjangoModelFactory):
    """验证码工厂类"""

    class Meta:
        model = VerificationCode

    user = factory.SubFactory(UserFactory)
    type = factory.Iterator(["email", "sms"])
    purpose = factory.Iterator(["register", "login", "reset_password", "bind"])
    target = factory.LazyAttribute(
        lambda obj: (
            obj.user.email if obj.type == "email" else obj.user.phone
        )
    )
    code = factory.Sequence(lambda n: f"{n:06d}")
    expired_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(minutes=5)
    )
    is_used = False


class ExpiredVerificationCodeFactory(VerificationCodeFactory):
    """过期验证码工厂类"""
    expired_at = factory.LazyFunction(
        lambda: timezone.now() - timedelta(minutes=1)
    ) 