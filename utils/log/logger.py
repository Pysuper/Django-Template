import json
import logging
import logging.config
import sys
from pathlib import Path
from typing import Dict, Optional

from django.conf import settings

# 日志级别映射
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# 默认日志配置
DEFAULT_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "%(levelname)s %(message)s",
        },
        "json": {
            "()": "utils.log.logger.JsonFormatter",
            "format": {
                "timestamp": "%(asctime)s",
                "level": "%(levelname)s",
                "name": "%(name)s",
                "line": "%(lineno)d",
                "message": "%(message)s",
            },
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "stream": sys.stdout,
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose",
            "filename": "logs/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "verbose",
            "filename": "logs/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "encoding": "utf-8",
            "level": "ERROR",
        },
        "json_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "json",
            "filename": "logs/json.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": True,
        },
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


class JsonFormatter(logging.Formatter):
    """JSON格式化器"""

    def __init__(self, format: Dict[str, str], **kwargs):
        super().__init__()
        self.format_dict = format
        self.kwargs = kwargs

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 创建基础数据
        data = {}
        for key, fmt in self.format_dict.items():
            data[key] = self._format_value(record, fmt)

        # 添加异常信息
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)

        # 添加额外数据
        if hasattr(record, "data"):
            data["data"] = record.data

        # 添加堆栈信息
        if hasattr(record, "stack_info") and record.stack_info:
            data["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(data, ensure_ascii=False)

    def _format_value(self, record: logging.LogRecord, fmt: str) -> str:
        """格式化单个值"""
        if hasattr(self, "_style"):
            # Python 3.2+ 使用 _style
            return self._style._format(fmt[2:-2], record)
        else:
            # 旧版本使用 % 操作符
            return fmt % record.__dict__


class ContextLogger:
    """上下文日志器，用于在日志中添加上下文信息"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.context = {}

    def add_context(self, **kwargs) -> None:
        """添加上下文信息"""
        self.context.update(kwargs)

    def remove_context(self, *keys) -> None:
        """移除上下文信息"""
        for key in keys:
            self.context.pop(key, None)

    def clear_context(self) -> None:
        """清除所有上下文信息"""
        self.context.clear()

    def _log(self, level: int, msg: str, *args, **kwargs) -> None:
        """记录日志"""
        if self.context:
            if "extra" not in kwargs:
                kwargs["extra"] = {}
            kwargs["extra"].update(self.context)
        self.logger.log(level, msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        """记录调试日志"""
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs) -> None:
        """记录信息日志"""
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """记录警告日志"""
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """记录错误日志"""
        self._log(logging.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs) -> None:
        """记录严重错误日志"""
        self._log(logging.CRITICAL, msg, *args, **kwargs)

    def exception(self, msg: str, *args, exc_info: bool = True, **kwargs) -> None:
        """记录异常日志"""
        self._log(logging.ERROR, msg, *args, exc_info=exc_info, **kwargs)


class LogManager:
    """日志管理器"""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            self.loggers = {}
            self._setup_logging()

    def _setup_logging(self) -> None:
        """设置日志配置"""
        # 获取日志配置
        log_config = getattr(settings, "LOGGING", DEFAULT_LOGGING)
        
        # 确保配置中包含版本号
        if "version" not in log_config:
            log_config["version"] = 1
            
        # 确保禁用现有日志记录器的标志存在
        if "disable_existing_loggers" not in log_config:
            log_config["disable_existing_loggers"] = False

        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        # 配置日志
        logging.config.dictConfig(log_config)

    def get_logger(self, name: Optional[str] = None) -> ContextLogger:
        """获取日志器"""
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = ContextLogger(logger)
        return self.loggers[name]


# 创建全局日志管理器实例
log_manager = LogManager()

# 创建默认日志器
logger = log_manager.get_logger(__name__)


def get_logger(name: Optional[str] = None) -> ContextLogger:
    """获取日志器的快捷方式"""
    return log_manager.get_logger(name)


class LoggerMixin:
    """日志混入类，为类添加日志功能"""

    @property
    def logger(self) -> ContextLogger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


"""
使用示例：

# 基本用法
logger.info("这是一条信息日志")
logger.error("这是一条错误日志", exc_info=True)

# 使用上下文日志器
logger = get_logger("my_app")
logger.add_context(user_id="123", ip="127.0.0.1")
logger.info("用户登录")
logger.remove_context("ip")
logger.info("执行操作")
logger.clear_context()

# 在类中使用日志混入
class MyClass(LoggerMixin):
    def my_method(self):
        self.logger.info("执行方法")
        try:
            # 一些操作
            pass
        except Exception as e:
            self.logger.exception("操作失败")

# 配置示例
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose"
        }
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": "INFO"
        }
    }
}
"""
