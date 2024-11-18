from .base import *  # noqa
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="fqmGV7RmY715h6IMpkdU2g1q0E5yP7yb8k12Rq0x8sqdREFK29OBisYO2ME1c4d4",
)

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://:redis_QjjNJH@119.45.4.159:16379/7"),
        "CONNECTION_POOL_KWARGS": {"max_connections": 100},
        "OPTIONS": {
            "PASSWORD": env("REDIS_PASSWORD", default="redis_QjjNJH"),
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
        },
    }
}

# EMAIL
# ------------------------------------------------------------------------------
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

# django-debug-toolbar
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["debug_toolbar"]

MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": ["debug_toolbar.panels.redirects.RedirectsPanel"],
    "SHOW_TEMPLATE_CONTEXT": True,
}

INTERNAL_IPS = [
    "127.0.0.1",
    "10.0.2.2",
    "119.45.4.159",
]
if env("USE_DOCKER", default="yes") == "yes":
    import socket

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]

# django-extensions
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["django_extensions"]

# Celery
# ------------------------------------------------------------------------------
CELERY_TASK_EAGER_PROPAGATES = True

# PySuper
# ------------------------------------------------------------------------------
CSRF_COOKIE_SECURE = False  # 在开发环境下可以设为 False
CSRF_COOKIE_HTTPONLY = True
USER_TYPE = [
    ("principal", "校长"),
    ("dean", "院长"),
    ("head", "系主任"),
    ("counselor", "辅导员"),
    ("homeroom", "班主任"),
    ("teacher", "老师"),
    ("leader", "班长"),
    ("student", "学生"),
]