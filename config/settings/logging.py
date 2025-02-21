import os
from pathlib import Path

from .base import ROOT_DIR

# 日志文件路径
LOG_DIR = ROOT_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 日志配置
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "apps.core.logging.CustomJsonFormatter",
            "default_fields": {
                "service": "django-template",
                "environment": "development",
            },
        },
        "verbose": {
            "format": "[%(asctime)s][%(levelname)s][%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[%(levelname)s] %(message)s",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["require_debug_true"],
        },
        "file_error": {
            "level": "ERROR",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "error.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "json",
            "encoding": "utf-8",
        },
        "file_info": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "info.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "json",
            "encoding": "utf-8",
        },
        "file_debug": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "debug.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
            "formatter": "json",
            "filters": ["require_debug_true"],
            "encoding": "utf-8",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
            "include_html": True,
            "formatter": "verbose",
        },
        "security": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "security.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "json",
            "encoding": "utf-8",
        },
        "performance": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "performance.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "json",
            "encoding": "utf-8",
        },
        "request": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "request.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "json",
            "encoding": "utf-8",
        },
        "db": {
            "level": "DEBUG",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "db.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 7,
            "formatter": "json",
            "encoding": "utf-8",
        },
        "celery": {
            "level": "INFO",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": str(LOG_DIR / "celery.log"),
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "formatter": "json",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file_info", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console", "request"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["mail_admins", "file_error", "request"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["db"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["security", "mail_admins"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console", "file_info", "file_error", "file_debug"],
            "level": "DEBUG",
            "propagate": False,
        },
        "celery": {
            "handlers": ["celery", "console", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
        "celery.task": {
            "handlers": ["celery", "console", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
        "celery.beat": {
            "handlers": ["celery", "console", "file_error"],
            "level": "INFO",
            "propagate": False,
        },
        "performance": {
            "handlers": ["performance", "console"],
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console", "file_error"],
        "level": "INFO",
    },
}
