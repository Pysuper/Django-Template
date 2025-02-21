from .base import *  # noqa

# 测试设置
DEBUG = False
TEMPLATE_DEBUG = False

# 使用内存数据库
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# 密码哈希设置
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# 邮件设置
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# 缓存设置
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# 媒体文件设置
MEDIA_ROOT = str(ROOT_DIR / "test_media")

# 静态文件设置
STATIC_ROOT = str(ROOT_DIR / "test_static")

# Celery设置
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# 安全设置
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# 日志设置
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# 测试运行器设置
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# 测试覆盖率设置
COVERAGE_REPORT_HTML_OUTPUT_DIR = str(ROOT_DIR / "htmlcov")
COVERAGE_MODULE_EXCLUDES = [
    "tests.*",
    "settings.*",
    "urls.*",
    "locale.*",
    "wsgi.*",
    "conftest.*",
    "migrations.*",
    "__init__.*",
]

# API设置
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# JWT设置
SIMPLE_JWT = {
    **SIMPLE_JWT,
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

# 验证码设置
VERIFICATION_CODE_EXPIRES = 300  # 5分钟
VERIFICATION_CODE_LENGTH = 6

# MFA设置
MFA_ISSUER_NAME = "TestApp"

# 文件上传设置
MAX_UPLOAD_SIZE = 5242880  # 5MB

# 调试工具栏
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: False,
}
