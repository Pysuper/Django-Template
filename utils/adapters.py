from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpRequest


class AccountAdapter(DefaultAccountAdapter):
    """普通账号注册适配器"""

    def is_open_for_signup(self, request: HttpRequest):
        # 检查是否允许注册新账号
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_login_redirect_url(self, request):
        """登录后重定向URL"""
        return getattr(settings, "LOGIN_REDIRECT_URL", "/")

    def get_logout_redirect_url(self, request):
        """登出后重定向URL"""
        return getattr(settings, "LOGOUT_REDIRECT_URL", "/")

    def get_email_confirmation_redirect_url(self, request):
        """邮箱确认后重定向URL"""
        return getattr(settings, "EMAIL_CONFIRMATION_REDIRECT_URL", "/")

    def save_user(self, request, user, form, commit=True):
        """保存用户信息"""
        user = super().save_user(request, user, form, commit=False)
        user.save()
        return user

    def populate_username(self, request, user):
        """生成用户名"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        username = user.email.split("@")[0]
        if User.objects.filter(username=username).exists():
            i = 1
            while User.objects.filter(username=f"{username}{i}").exists():
                i += 1
            username = f"{username}{i}"
        return username


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """社交账号注册适配器"""

    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        # 检查是否允许社交账号注册
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_connect_redirect_url(self, request, socialaccount):
        """社交账号关联后重定向URL"""
        return getattr(settings, "SOCIAL_CONNECT_REDIRECT_URL", "/")

    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """社交账号认证错误处理"""
        return super().authentication_error(request, provider_id, error, exception, extra_context)

    def pre_social_login(self, request, sociallogin):
        """社交账号登录前处理"""
        if sociallogin.is_existing:
            return

        # 检查邮箱是否已存在
        if "email" in sociallogin.account.extra_data:
            try:
                user = get_user_model().objects.get(email=sociallogin.account.extra_data["email"])
                sociallogin.connect(request, user)
            except get_user_model().DoesNotExist:
                pass

    def populate_user(self, request, sociallogin, data):
        """填充用户信息"""
        user = super().populate_user(request, sociallogin, data)
        if not user.username:
            user.username = self.generate_unique_username(data)
        return user

    def generate_unique_username(self, data):
        """生成唯一用户名"""
        username = data.get("username", "")
        if not username:
            username = data.get("email", "").split("@")[0]

        from django.contrib.auth import get_user_model

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            i = 1
            while User.objects.filter(username=f"{username}{i}").exists():
                i += 1
            username = f"{username}{i}"
        return username
