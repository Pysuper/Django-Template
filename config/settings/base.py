import datetime
import os
from datetime import timedelta
from pathlib import Path

import environ

# noinspection PyUnresolvedReferences
from utils.log.logger import *

# START
# ------------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=True)
if READ_DOT_ENV_FILE:
    env.read_env(str(ROOT_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=True)
TIME_ZONE = "Asia/Shanghai"
LANGUAGE_CODE = "en-us"
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = [str(ROOT_DIR / "locale")]

# SECURITY
# ------------------------------------------------------------------------------
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"] if DEBUG else ["*"])
CORS_ALLOW_ALL_ORIGINS = env.bool("DJANGO_CORS_ALLOW_ALL_ORIGINS", default=DEBUG)
CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])

DJANGO_ALLOWED_HOSTS = ["*"]

# DATABASES
# ------------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env.str("MYSQL_DATABASE", default="django_db"),
        "USER": env.str("MYSQL_USER", default="root"),
        "PASSWORD": env.str("MYSQL_PASSWORD", default="root"),
        "HOST": env.str("MYSQL_HOST", default="localhost"),
        "PORT": env.str("MYSQL_PORT", default="3306"),
        "CONN_MAX_AGE": env.int("MYSQL_CONN_MAX_AGE", default=60 * 60 * 6),
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {
            "init_command": 'SET sql_mode="STRICT_TRANS_TABLES"',
            "charset": "utf8mb4",
            "use_unicode": True,
            "sql_mode": "traditional",
        },
        "POOL": {
            "name": "default",
            "max_size": env.int("MYSQL_POOL_MAX_SIZE", default=20),
            "min_size": env.int("MYSQL_POOL_MIN_SIZE", default=5),
            "max_overflow": env.int("MYSQL_POOL_MAX_OVERFLOW", default=10),
            "timeout": env.int("MYSQL_POOL_TIMEOUT", default=30),
            "recycle": env.int("MYSQL_POOL_RECYCLE", default=3600),
            "echo": DEBUG,
            "pre_ping": True,
        },
    }
}
# 自定义数据库路由器
DATABASE_ROUTERS = ["utils.router.db.DatabaseAppsRouter"]
# 自定义应用与数据库映射
DATABASE_APPS_MAPPING = {
    # example:
    # 'app_name':'database_name',
    "indicator": "postkeeper",
}
# 默认自动字段设置为 BigAutoField
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django自带的应用
    # TODO：这里的 apps 按需添加，不用的可以删除，缩减Django的体积
    "django.contrib.auth",  # 用户认证系统
    "django.contrib.contenttypes",  # 内容类型框架
    # "django.contrib.sessions",  # 会话框架
    # "django.contrib.sites",  # 网站框架
    "django.contrib.messages",  # 消息框架
    # "django.contrib.staticfiles",  # 静态文件管理
    # "django.contrib.humanize",  # 方便的模板标签
    "django.contrib.admin",  # 管理后台
    # "django.forms",  # 表单处理
    # "django.contrib.humanize",  # 提供人性化的格式化工具
    # "django.contrib.sitemaps",  # 网站地图框架
    # "django.contrib.flatpages",  # 静态页面管理
    # 第三方应用
    # "simpleui",  # 简单的用户界面
    "allauth",  # 用于用户认证和注册的库
    "allauth.account",  # 处理用户账户的功能
    "allauth.socialaccount",  # 支持社交账户登录
    # "django_celery_beat",  # 用于定时任务调度
    "rest_framework",  # Django REST框架
    "rest_framework.authtoken",  # 提供基于Token的认证
    "rest_framework_simplejwt.token_blacklist",  # JWT黑名单支持
    "corsheaders",  # 处理跨域请求的库
    "drf_spectacular",  # 用于生成API文档
    "django_filters",  # 用于 Django 的过滤器
    # "django_rest_passwordreset",  # 用于重置密码的 REST API
    # "django_celery_results",  # 用于存储 Celery 任务结果
    # "django_extensions",  # 提供额外的管理命令和工具
    # "debug_toolbar",  # 用于调试的工具栏
    # "dauthz.apps.DauthzConfig",  # 权限管理应用
    # 本地应用
    "users",
]

# MIGRATIONS
# ------------------------------------------------------------------------------
MIGRATION_MODULES = {"sites": "django.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
AUTH_USER_MODEL = "users.User"
LOGIN_REDIRECT_URL = "users:redirect"
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    "apps.core.logging.RequestIdMiddleware",  # 添加请求ID中间件
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.logging.setup_request_logging",  # 请求日志中间件
]

# DAUTHZ
# DAUTHZ = {
#     "DEFAULT": {
#         "MODEL": {
#             "CONFIG_TYPE": "file",
#             "CONFIG_FILE_PATH": Path(__file__).parent.joinpath("dauthz-model.conf"),
#             "CONFIG_TEXT": "",
#         },
#         "ADAPTER": {"NAME": "casbin_adapter.adapter.Adapter"},
#         "LOG": {"ENABLED": False},
#     },
# }

# STATIC
# ------------------------------------------------------------------------------
STATIC_ROOT = str(ROOT_DIR / "staticfiles")
STATIC_URL = "/static/"
STATICFILES_DIRS = [str(ROOT_DIR / "static")]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
MEDIA_ROOT = str(ROOT_DIR / "media")
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(ROOT_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "utils.settings.allauth_settings",
            ],
        },
    }
]

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
FIXTURE_DIRS = (str(ROOT_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# EMAIL
# ------------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
ADMIN_URL = "admin/"
ADMINS = [("""PySuper""", "small.spider.p@gmail.com")]
MANAGERS = ADMINS

# LOGGING
# ------------------------------------------------------------------------------
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
if not os.path.isdir(LOGS_DIR):
    os.mkdir(LOGS_DIR)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    # 日志格式配置
    "formatters": {
        # 详细格式,包含线程、任务ID等信息
        "verbose": {
            "format": "[%(asctime)s][%(threadName)s:%(thread)d][task_id:%(name)s][%(filename)s:%(lineno)d][%(levelname)s][%(message)s]"
        },
        # 标准格式,包含基本的时间、文件等信息
        "standard": {
            "format": "[%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d] %(message)s",
        },
        # 简单格式,只含日志级别和消息
        "simple": {
            "format": "[%(levelname)s] %(message)s",
        },
        # 采集格式,只包含消息内容
        "collect": {
            "format": "%(message)s",
        },
        # 全日志格式
        "security": {
            "format": "[%(asctime)s][%(levelname)s][%(ip)s][%(user)s][%(message)s]",
        },
        # 性能日志格式
        "performance": {
            "format": "[%(asctime)s][%(levelname)s][%(duration).2fms][%(message)s]",
        },
        # 新增业务日志格式
        "business": {"format": "[%(asctime)s][%(levelname)s][%(business_type)s][%(user)s][%(message)s]"},
        # 新增审计日志格式
        "audit": {"format": "[%(asctime)s][%(levelname)s][%(user)s][%(action)s][%(resource)s][%(result)s]"},
        # 新增接口调用日志格式
        "api_call": {
            "format": "[%(asctime)s][%(levelname)s][%(method)s][%(url)s][%(status_code)s][%(response_time).2fms]"
        },
    },
    # 日志处理器配置
    "handlers": {
        # 原有处理器保持不变...
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file_handler": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",  # 修改为标准TimedRotatingFileHandler
            "filename": os.path.join(LOGS_DIR, "info.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 20,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "sql_handler": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "sql.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 20,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "error_handler": {
            "level": "ERROR",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "err.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 20,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "collect_handler": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "collect.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 20,
            "formatter": "collect",
            "encoding": "utf-8",
        },
        "api_handler": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "api.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 20,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "security_handler": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "security.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "security",
            "encoding": "utf-8",
        },
        "performance_handler": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "performance.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "performance",
            "encoding": "utf-8",
        },
        # 新业务日志处理器
        "business_handler": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "business.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "business",
            "encoding": "utf-8",
        },
        # 新增审计日志处理器
        "audit_handler": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "audit.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 90,
            "formatter": "audit",
            "encoding": "utf-8",
        },
        # 新增接口调用日志处理器
        "api_call_handler": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "api_call.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "api_call",
            "encoding": "utf-8",
        },
    },
    # 日志记录器配置
    "loggers": {
        # 保持原有记录器配置...
        "": {
            "handlers": ["console", "file_handler", "error_handler"],  # 添加console处理器
            "level": "DEBUG",
            "propagate": True,
        },
        "django.db.backends": {
            "handlers": ["console", "sql_handler"],
            "propagate": False,
            "level": "DEBUG",
        },
        "collect": {
            "handlers": ["console", "collect_handler"],
            "level": "INFO",
            "propagate": False,  # 设置为False避免重复记录
        },
        "api": {
            "handlers": ["console", "api_handler"],  # 添加console处理器
            "level": "INFO",
            "propagate": False,
        },
        "security": {
            "handlers": ["console", "security_handler"],
            "level": "INFO",
            "propagate": False,
        },
        "performance": {
            "handlers": ["console", "performance_handler"],
            "level": "INFO",
            "propagate": False,
        },
        "user_operation": {
            "handlers": ["console", "file_handler"],
            "level": "INFO",
            "propagate": False,
        },
        "system_monitor": {
            "handlers": ["console", "file_handler"],
            "level": "INFO",
            "propagate": False,
        },
        # 新业务日志记录器
        "business": {
            "handlers": ["console", "business_handler"],
            "level": "INFO",
            "propagate": False,
        },
        # 新增审计日志记录器
        "audit": {
            "handlers": ["console", "audit_handler"],
            "level": "INFO",
            "propagate": False,
        },
        # 新增接口调用日志记录器
        "api_call": {
            "handlers": ["console", "api_call_handler"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TIME_LIMIT = 5 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 60
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# CORS
# ------------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = env.bool("DJANGO_CORS_ALLOW_ALL_ORIGINS", default=DEBUG)

# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_ADAPTER = "users.adapters.AccountAdapter"
ACCOUNT_FORMS = {"signup": "users.forms.UserSignupForm"}
SOCIALACCOUNT_ADAPTER = "users.adapters.SocialAccountAdapter"
SOCIALACCOUNT_FORMS = {"signup": "users.forms.UserSocialSignupForm"}

# DRF
# -------------------------------------------------------------------------------
REST_FRAMEWORK = {
    # 自定义默认分页类
    "DEFAULT_PAGINATION_CLASS": "utils.custom.LargePagination",
    # 默认的每页显示的条数
    "PAGE_SIZE": 10,
    # # 自定义的异常处理器
    "EXCEPTION_HANDLER": "utils.handler.custom_exception_handler",
    # 自定义的权限类
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # JWT身份验证
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        # 基于会话身份验证
        "rest_framework.authentication.TokenAuthentication",
        # 基本身份验证，上线可取消
        "rest_framework.authentication.BasicAuthentication",
        # 会话身份验证，上线可取消
        "rest_framework.authentication.SessionAuthentication",
    ),
    # 默认的渲染器类。渲染器负责将API响应转换为客户端可以理解的格式
    "DEFAULT_RENDERER_CLASSES": (
        # JSON渲染器
        "rest_framework.renderers.JSONRenderer",
        # 浏览API渲染器
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    # 默认的解析器类，将客户端发送的请求数据解析为Python对象
    "DEFAULT_PARSER_CLASSES": (
        # JSON解析器
        "rest_framework.parsers.JSONParser",
        # 表单解析器
        "rest_framework.parsers.FormParser",
        # 多部分解析器
        "rest_framework.parsers.MultiPartParser",
    ),
    # 默认的权限类，只有经过身份验证的用户才能访问API端点
    "DEFAULT_PERMISSION_CLASSES": [
        # 自定义的RBAC权限类,用于实现基于角色的访问控制,可以在全局或视图级别使用
        "utils.custom.RbacPermission",
        # 允许所有用户访问,包括未认证用户,通常用于公开API
        "rest_framework.permissions.AllowAny",
        # 只允许已认证用户访问,要求用户必须登录,是最基本的认证要求
        # 全局默认需要登录认证,但是可以在具体的视图中通过permission_classes设置例外
        # 比如登录接口设置permission_classes = [AllowAny]
        # 于api/docs/这类接口, 我们可以在视图级别单独设置权限, 比如使用AllowAny或IsAdminUser
        # 在全局默认使用IsAuthenticated, 确保API安全性
        # "rest_framework.permissions.IsAuthenticated",
    ],
    # 设置默认的节流（限流）类和速率
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    # 匿名用户每天最多可以请求100次，而认证用户每天最多可以请求1000次。
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
    },
    # 默认的版本控制类，使用了命名空间版本控制，允许你通过URL路径来区分不��版本的API
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    # 默认的过滤器后端，它允许你在查询参数中使用过滤条件，这个可以在类里面设置
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    # 默认内容协商类。内容协商决定了客户端和服务器之间如何确定响应的格式
    "DEFAULT_CONTENT_NEGOTIATION_CLASS": "rest_framework.negotiation.DefaultContentNegotiation",
    # 默认的架构生成器类
    # DRF自带的自动架构生成器
    # 'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.AutoSchema',
    # 使用drf-spectacular库生成OpenAPI文档
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # 使用自定义的架构生成器
    # "DEFAULT_SCHEMA_CLASS": "config.extend_schema.CustomAutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Backend API",
    "DESCRIPTION": "Documentation of API endpoints of Backend",
    "VERSION": "1.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SERVE_INCLUDE_SCHEMA": False,
    "SERVERS": [
        {
            "url": "http://localhost:8000",
            "description": "Local Development server",
        },
        {
            "url": "https://dev.pysuper.com",
            "description": "Production server",
        },
    ],
}

# PySuper
# ------------------------------------------------------------------------------
# 不再自动重定向带斜的 URL 后缀，返回 404 状态码
APPEND_SLASH = False

# 学校CODE的位数
CODE_LENGTH = 6

# 阿里云短信
ALIYUN_SMS = {
    "ACCESS_KEY_ID": "your_access_key_id",
    "ACCESS_KEY_SECRET": "your_access_key_secret",
    "SIGN_NAME": "your_sms_sign_name",  # 短信签名
    "TEMPLATE_CODE": "your_template_code",  # 短信模板CODE
}

# 初始登录密码
START_PASSWORD = "123456"


# 读取密钥文件
def read_key(file_path):
    """读取密钥文件内容"""
    with open(file_path, "r") as file:
        return file.read()


# RSA 密钥配置，解密用户密码
RSA_PUBLIC_KEY = read_key(str(ROOT_DIR / "config/settings/pub.key"))
RSA_PRIVATE_KEY = read_key(str(ROOT_DIR / "config/settings/pri.key"))
RSA_PASSWORD = env.str("DJANGO_RSA_PASSWORD", default="change_me_in_production")

# 用户缓存默认闲置时间，单位：秒
USER_CACHE_IDLE_TIME = 3600

# LOGIN_CODE 相关
login_code_config = (
    ("ARITHMETIC", "算数"),
    ("CHINESE", "中文"),
    ("CHINESE_GIF", "中文闪图"),
    ("GIF", "闪图"),
    ("SPEC", "普通"),
)
SINGLE_LOGIN = True  # 单点登录
EXPIRATION_DELTA = timedelta(minutes=2)  # 验证码有效期（分钟）
LOGIN_CODE_TYPE = "ARITHMETIC"  # 验证码格式: ARITHMETIC、CHINESE、RANDOM
LOGIN_CODE_LENGTH = 4  # 验证码片长度
LOGIN_CODE_WIDTH = 120  # 验证码图片宽度
LOGIN_CODE_HEIGHT = 40  # 验证码图片高度
LOGIN_CODE_FONT_NAME = str(ROOT_DIR / "SimSun.ttf")  # 验证码字体路径
LOGIN_CODE_FONT_SIZE = 20  # 验证码字体大小
LOGIN_CODE_KEY = "captcha:"  # 验证码前缀

# JWT 相关
JWT_AUTH = {
    "JWT_EXPIRATION_DELTA": datetime.timedelta(days=100),
    "JWT_AUTH_HEADER_PREFIX": "Bearer ",
}
JWT_HEADER_NAME = "Authorization"  # 请求头头部名称
JWT_AUTH_HEADER_PREFIX = "Bearer "  # Token前缀
BASE64_SECRET_KEY = env.str("DJANGO_BASE64_SECRET_KEY", default="change_me_in_production")
TOKEN_LIFETIME = 3600  # JWT 有效期（秒）
ONLINE_KEY = "online-user:"  # 在线用户键前缀
TOKEN_DETECT = 1800  # Token 过期检测时间（秒）
TOKEN_RENEW_PERIOD = 3600  # Token 续期时间（秒）
SIMPLE_JWT = {
    # "BLACKLIST_AFTER_ROTATION": True,  # 刷新令牌时将旧令牌放黑名单
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(minutes=150),  # 访��令牌的有效期
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(days=1),  # 刷新令牌的有效期
}

# 设置文件上传下载读写权限
FILE_UPLOAD_PERMISSIONS = 0o666

# 短信验证码相关
ALI_SMS_ACCESS_KEY_ID = "your_access_key_id"  # 阿里云短信 Access Key ID
ALI_SMS_ACCESS_KEY_SECRET = "your_access_key_secret"  # 阿里云短信 Access Key Secret
ALI_SMS_REGION_ID = "cn-hangzhou"  # 阿里云短信 Region ID
ALI_SMS_ENDPOINT = "dysmsapi.aliyuncs.com"  # 阿里云短信 API 地址
ALI_SMS_SIGN_NAME = "your_sms_sign_name"  # 短信签名
ALI_SMS_CODE_TEMPLATE = "your_template_code"  # 短信模板CODE
SMS_CODE_KEY = "sms_code_"  # 短信验证码前缀
SMS_CODE_EXPIRE = 600  # 短信验证码过期时间（秒）
SMS_CODE_LENGTH = 6  # 短信验证码长度
