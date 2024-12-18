import hashlib
import re
from datetime import datetime
from typing import Any, Dict, Optional

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.http import HttpRequest
from django.utils.translation import gettext as _

from utils.error import BusinessError, ErrorCode

User = get_user_model()


class BaseAdapter:
    """基础适配器"""

    def __init__(self):
        self.cache_timeout = 300  # 缓存5分钟

    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """获取缓存键"""
        return f"{prefix}:{identifier}"

    def _cache_get(self, key: str) -> Any:
        """获取缓存"""
        return cache.get(key)

    def _cache_set(self, key: str, value: Any, timeout: Optional[int] = None) -> None:
        """设置缓存"""
        cache.set(key, value, timeout or self.cache_timeout)

    def _cache_delete(self, key: str) -> None:
        """删除缓存"""
        cache.delete(key)

    def _validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    def _validate_username(self, username: str) -> bool:
        """验证用户名格式"""
        pattern = r"^[a-zA-Z0-9_-]{4,16}$"
        return bool(re.match(pattern, username))

    def _generate_avatar(self, email: str) -> str:
        """生成默认头像"""
        email_hash = hashlib.md5(email.lower().encode()).hexdigest()
        avatar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=identicon&s=200"
        return avatar_url


class AccountAdapter(DefaultAccountAdapter, BaseAdapter):
    """账号适配器"""

    def __init__(self):
        super().__init__()
        self.username_regex = re.compile(r"^[a-zA-Z0-9_-]{4,16}$")
        self.email_regex = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

    def is_open_for_signup(self, request: HttpRequest) -> bool:
        """是否开放注册"""
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)

    def get_login_redirect_url(self, request: HttpRequest) -> str:
        """登录重定向URL"""
        next_url = request.GET.get("next")
        if next_url and self._is_safe_url(next_url):
            return next_url
        return getattr(settings, "LOGIN_REDIRECT_URL", "/")

    def get_logout_redirect_url(self, request: HttpRequest) -> str:
        """登出重定向URL"""
        next_url = request.GET.get("next")
        if next_url and self._is_safe_url(next_url):
            return next_url
        return getattr(settings, "LOGOUT_REDIRECT_URL", "/")

    def get_email_confirmation_redirect_url(self, request: HttpRequest) -> str:
        """邮箱确认重定向URL"""
        next_url = request.GET.get("next")
        if next_url and self._is_safe_url(next_url):
            return next_url
        return getattr(settings, "EMAIL_CONFIRMATION_REDIRECT_URL", "/")

    def clean_username(self, username: str) -> str:
        """清理用户名"""
        username = super().clean_username(username)
        if not self.username_regex.match(username):
            raise BusinessError(
                error_code=ErrorCode.PARAM_ERROR,
                message=_("用户名只能包含字母、数字、下划线和连字符，长度4-16位"),
            )
        return username

    def clean_email(self, email: str) -> str:
        """清理邮箱"""
        email = super().clean_email(email)
        if not self.email_regex.match(email):
            raise BusinessError(error_code=ErrorCode.PARAM_ERROR, message=_("邮箱格式不正确"))
        return email

    def clean_password(self, password: str, user: Optional[User] = None) -> str:
        """清理密码"""
        min_length = getattr(settings, "ACCOUNT_PASSWORD_MIN_LENGTH", 8)
        if len(password) < min_length:
            raise BusinessError(
                error_code=ErrorCode.PARAM_ERROR,
                message=_("密码长度不能小于%(min_length)d位") % {"min_length": min_length},
            )

        if not any(c.isupper() for c in password):
            raise BusinessError(error_code=ErrorCode.PARAM_ERROR, message=_("密码必须包含大写字母"))

        if not any(c.islower() for c in password):
            raise BusinessError(error_code=ErrorCode.PARAM_ERROR, message=_("密码必须包含小写字母"))

        if not any(c.isdigit() for c in password):
            raise BusinessError(error_code=ErrorCode.PARAM_ERROR, message=_("密码必须包含数字"))

        return password

    def save_user(self, request: HttpRequest, user: User, form: Any, commit: bool = True) -> User:
        """保存用户"""
        user = super().save_user(request, user, form, commit=False)

        # 设置默认头像
        if not user.avatar:
            user.avatar = self._generate_avatar(user.email)

        # 设置默认昵称
        if not user.nickname:
            user.nickname = user.username

        # 设置注册IP
        if not user.register_ip:
            user.register_ip = self._get_client_ip(request)

        if commit:
            user.save()

        return user

    def populate_username(self, request: HttpRequest, user: User) -> str:
        """生成用户名"""
        # 尝试使用邮箱前缀作为用户名
        username = user.email.split("@")[0]

        # 如果用户名已存在，添加随机数字后缀
        if User.objects.filter(username=username).exists():
            base_username = username
            for i in range(1, 1000):
                username = f"{base_username}{i}"
                if not User.objects.filter(username=username).exists():
                    break

        return username

    def _is_safe_url(self, url: str) -> bool:
        """检查URL是否安全"""
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
        from django.utils.http import url_has_allowed_host_and_scheme

        return url_has_allowed_host_and_scheme(url, allowed_hosts)

    def _get_client_ip(self, request: HttpRequest) -> str:
        """获取客户端IP"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0]
        return request.META.get("REMOTE_ADDR", "")


class SocialAccountAdapter(DefaultSocialAccountAdapter, BaseAdapter):
    """社交账号适配器"""

    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any) -> bool:
        """是否开放社交账号注册"""
        return getattr(settings, "SOCIALACCOUNT_ALLOW_REGISTRATION", True)

    def get_connect_redirect_url(self, request: HttpRequest, socialaccount: Any) -> str:
        """社交账号关联重定向URL"""
        next_url = request.GET.get("next")
        if next_url and self._is_safe_url(next_url):
            return next_url
        return getattr(settings, "SOCIAL_CONNECT_REDIRECT_URL", "/")

    def authentication_error(
        self,
        request: HttpRequest,
        provider_id: str,
        error: Optional[Exception] = None,
        exception: Optional[Exception] = None,
        extra_context: Optional[Dict] = None,
    ) -> None:
        """社交账号认证错误处理"""
        # 记录错误日志
        if error or exception:
            from utils.log.logger import logger

            logger.error(
                f"社交账号认证错误 - Provider: {provider_id}, "
                f"Error: {error}, Exception: {exception}, "
                f"Context: {extra_context}"
            )
        super().authentication_error(request, provider_id, error, exception, extra_context)

    def pre_social_login(self, request: HttpRequest, sociallogin: Any) -> None:
        """社交账号登录前处理"""
        if sociallogin.is_existing:
            return

        # 检查邮箱是否已存在
        email = sociallogin.account.extra_data.get("email")
        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass

    def populate_user(self, request: HttpRequest, sociallogin: Any, data: Dict[str, Any]) -> User:
        """填充用户信息"""
        user = super().populate_user(request, sociallogin, data)

        # 设置用户名
        if not user.username:
            user.username = self.generate_unique_username(data)

        # 设置昵称
        if not user.nickname:
            user.nickname = data.get("name") or user.username

        # 设置头像
        if not user.avatar and "picture" in sociallogin.account.extra_data:
            avatar_url = sociallogin.account.extra_data["picture"]
            self._save_social_avatar(user, avatar_url)

        return user

    def generate_unique_username(self, data: Dict[str, Any]) -> str:
        """生成唯一用户名"""
        # 尝试使用社交账号的用户名
        username = data.get("username", "")

        # 如果没有用户名，使用邮箱前缀
        if not username:
            username = data.get("email", "").split("@")[0]

        # 如果用户名已存在，添加随机数字后缀
        if User.objects.filter(username=username).exists():
            base_username = username
            for i in range(1, 1000):
                username = f"{base_username}{i}"
                if not User.objects.filter(username=username).exists():
                    break

        return username

    def _save_social_avatar(self, user: User, avatar_url: str) -> None:
        """保存社交账号头像"""
        import requests

        try:
            response = requests.get(avatar_url)
            if response.status_code == 200:
                filename = f"avatars/{user.username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
                content = ContentFile(response.content)
                user.avatar.save(filename, content, save=True)
        except Exception as e:
            from utils.log.logger import logger

            logger.error(f"保存社交账号头像失败: {str(e)}")

    def _is_safe_url(self, url: str) -> bool:
        """检查URL是否安全"""
        allowed_hosts = getattr(settings, "ALLOWED_HOSTS", [])
        from django.utils.http import url_has_allowed_host_and_scheme

        return url_has_allowed_host_and_scheme(url, allowed_hosts)
