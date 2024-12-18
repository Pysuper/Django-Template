from typing import Any, Dict

from django.conf import settings
from django.core.cache import cache


class SystemSettings:
    """系统配置管理器"""

    CACHE_KEY = "system_settings"
    CACHE_TIMEOUT = 3600  # 1小时

    @classmethod
    def get_all_settings(cls) -> Dict[str, Any]:
        """获取所有系统配置"""
        # 先从缓存获取
        settings_dict = cache.get(cls.CACHE_KEY)
        if settings_dict is not None:
            return settings_dict

        # 从数据库获取
        from apps.system.models import SystemConfig

        settings_dict = {item.key: item.value for item in SystemConfig.objects.filter(is_active=True)}

        # 添加默认配置
        settings_dict.update(cls.get_default_settings())

        # 缓存配置
        cache.set(cls.CACHE_KEY, settings_dict, cls.CACHE_TIMEOUT)
        return settings_dict

    @staticmethod
    def get_default_settings() -> Dict[str, Any]:
        """获取默认配置"""
        return {
            # 站点配置
            "SITE_NAME": getattr(settings, "SITE_NAME", "后台管理系统"),
            "SITE_DESCRIPTION": getattr(settings, "SITE_DESCRIPTION", "基于Django的后台管理系统"),
            "SITE_KEYWORDS": getattr(settings, "SITE_KEYWORDS", "Django,后台管理"),
            "SITE_AUTHOR": getattr(settings, "SITE_AUTHOR", "Admin"),
            "SITE_URL": getattr(settings, "SITE_URL", "http://localhost:8000"),
            # 用户配置
            "ACCOUNT_ALLOW_REGISTRATION": getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True),
            "ACCOUNT_EMAIL_VERIFICATION": getattr(settings, "ACCOUNT_EMAIL_VERIFICATION", "optional"),
            "ACCOUNT_LOGIN_ATTEMPTS_LIMIT": getattr(settings, "ACCOUNT_LOGIN_ATTEMPTS_LIMIT", 5),
            "ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT": getattr(settings, "ACCOUNT_LOGIN_ATTEMPTS_TIMEOUT", 300),
            "ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE": getattr(settings, "ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE", False),
            # 安全配置
            "SECURITY_PASSWORD_MIN_LENGTH": getattr(settings, "SECURITY_PASSWORD_MIN_LENGTH", 8),
            "SECURITY_PASSWORD_COMPLEXITY": getattr(settings, "SECURITY_PASSWORD_COMPLEXITY", True),
            "SECURITY_SESSION_TIMEOUT": getattr(settings, "SECURITY_SESSION_TIMEOUT", 1800),
            "SECURITY_LOGIN_CAPTCHA": getattr(settings, "SECURITY_LOGIN_CAPTCHA", True),
            "SECURITY_API_RATE_LIMIT": getattr(settings, "SECURITY_API_RATE_LIMIT", 100),
            # 文件上传配置
            "UPLOAD_FILE_TYPES": getattr(settings, "UPLOAD_FILE_TYPES", "jpg,jpeg,png,gif,doc,docx,xls,xlsx,pdf"),
            "UPLOAD_FILE_SIZE_LIMIT": getattr(settings, "UPLOAD_FILE_SIZE_LIMIT", 10485760),  # 10MB
            "UPLOAD_IMAGE_SIZE_LIMIT": getattr(settings, "UPLOAD_IMAGE_SIZE_LIMIT", 5242880),  # 5MB
            "UPLOAD_STORAGE_BACKEND": getattr(settings, "UPLOAD_STORAGE_BACKEND", "local"),
            # 缓存配置
            "CACHE_MIDDLEWARE_SECONDS": getattr(settings, "CACHE_MIDDLEWARE_SECONDS", 300),
            "CACHE_MIDDLEWARE_KEY_PREFIX": getattr(settings, "CACHE_MIDDLEWARE_KEY_PREFIX", "django_cache"),
            "CACHE_MIDDLEWARE_ANONYMOUS_ONLY": getattr(settings, "CACHE_MIDDLEWARE_ANONYMOUS_ONLY", False),
            # API配置
            "API_VERSION": getattr(settings, "API_VERSION", "v1"),
            "API_TITLE": getattr(settings, "API_TITLE", "后台管理系统API"),
            "API_DESCRIPTION": getattr(settings, "API_DESCRIPTION", "基于Django的后台管理系统API"),
            "API_TERMS_OF_SERVICE": getattr(settings, "API_TERMS_OF_SERVICE", None),
            "API_CONTACT_EMAIL": getattr(settings, "API_CONTACT_EMAIL", None),
            # 其他配置
            "ENABLE_DEMO_MODE": getattr(settings, "ENABLE_DEMO_MODE", False),
            "ENABLE_API_DOCUMENTATION": getattr(settings, "ENABLE_API_DOCUMENTATION", True),
            "ENABLE_ADMIN_DOCUMENTATION": getattr(settings, "ENABLE_ADMIN_DOCUMENTATION", True),
            "ENABLE_SITE_STATISTICS": getattr(settings, "ENABLE_SITE_STATISTICS", True),
        }

    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        """获取指定配置"""
        settings_dict = cls.get_all_settings()
        return settings_dict.get(key, default)

    @classmethod
    def set_setting(cls, key: str, value: Any) -> None:
        """设置指定配置"""
        from apps.system.models import SystemConfig

        # 更新数据库
        SystemConfig.objects.update_or_create(key=key, defaults={"value": value, "is_active": True})

        # 清除缓存
        cache.delete(cls.CACHE_KEY)

    @classmethod
    def refresh_cache(cls) -> None:
        """刷新配置缓存"""
        cache.delete(cls.CACHE_KEY)
        cls.get_all_settings()


def system_settings(request) -> Dict[str, Any]:
    """系统配置上下文处理器"""
    return {
        "SYSTEM_SETTINGS": SystemSettings.get_all_settings(),
        "SITE_NAME": SystemSettings.get_setting("SITE_NAME"),
        "SITE_DESCRIPTION": SystemSettings.get_setting("SITE_DESCRIPTION"),
        "API_VERSION": SystemSettings.get_setting("API_VERSION"),
        "ENABLE_DEMO_MODE": SystemSettings.get_setting("ENABLE_DEMO_MODE"),
    }


def user_settings(request) -> Dict[str, Any]:
    """用户配置上下文处理器"""
    user_settings = {}

    if request.user.is_authenticated:
        from apps.users.models import UserSettings

        settings_obj = UserSettings.objects.filter(user=request.user).first()
        if settings_obj:
            user_settings = {
                "theme": settings_obj.theme,
                "language": settings_obj.language,
                "timezone": settings_obj.timezone,
            }

    return {"USER_SETTINGS": user_settings}
