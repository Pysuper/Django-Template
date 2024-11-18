from django.conf import settings


def allauth_settings(request):
    """
    用于模板中获取全局配置
    返回是否允许注册的配置项
    """
    return {
        # 是否允许用户注册的配置
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
    }
