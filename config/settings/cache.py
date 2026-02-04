"""
Cache Configuration Module

This module contains cache, session, and Celery configuration.
"""

from environs import Env

env = Env()


# Cache Configuration
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.str("CELERY_BROKER_URL", default="redis://localhost:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
        },
        "KEY_PREFIX": "django",
        "TIMEOUT": env.int("CACHE_TIMEOUT", default=300),
    }
}

# Cache Configuration
CACHE_TIMEOUT = env.int("CACHE_TIMEOUT", default=300)
CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = env.int("CACHE_MIDDLEWARE_SECONDS", default=600)
CACHE_MIDDLEWARE_KEY_PREFIX = "django_cache"

# Session Configuration
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = env.int("SESSION_COOKIE_AGE", default=1800)  # 30 minutes
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Celery Configuration
CELERY_BROKER_URL = env.str("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env.str("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# User Cache Settings
USER_CACHE_IDLE_TIME = env.int("USER_CACHE_IDLE_TIME", default=3600)
SINGLE_LOGIN = env.bool("SINGLE_LOGIN", default=True)

# Single Login Configuration
SINGLE_LOGIN_ENABLED = env.bool("SINGLE_LOGIN", default=True)
SESSION_SAVE_EVERY_REQUEST = True

# Initial Password
START_PASSWORD = env.str("START_PASSWORD", default="ChangeMe123!")
