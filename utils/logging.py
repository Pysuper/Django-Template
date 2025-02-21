import copy
import json
import logging
import re
import threading
import time
import uuid
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional, Pattern, Type, TypeVar, cast

from django.conf import settings
from django.http import HttpRequest

# 类型变量
T = TypeVar("T", bound=Callable[..., Any])

class SensitiveDataFilter:
    """敏感数据过滤器"""
    
    # 敏感字段模式
    PATTERNS: List[Pattern] = [
        re.compile(r"password", re.I),
        re.compile(r"secret", re.I),
        re.compile(r"token", re.I),
        re.compile(r"key", re.I),
        re.compile(r"auth", re.I),
        re.compile(r"credit_card", re.I),
        re.compile(r"card_number", re.I),
    ]
    
    # 敏感数据掩码
    MASK = "******"
    
    @classmethod
    def filter_sensitive_data(cls, data: Any) -> Any:
        """过滤敏感数据"""
        if isinstance(data, dict):
            filtered_data = {}
            for key, value in data.items():
                # 检查键名是否包含敏感信息
                if any(pattern.search(key) for pattern in cls.PATTERNS):
                    filtered_data[key] = cls.MASK
                else:
                    filtered_data[key] = cls.filter_sensitive_data(value)
            return filtered_data
        elif isinstance(data, (list, tuple)):
            return [cls.filter_sensitive_data(item) for item in data]
        return data

class RequestFilter(logging.Filter):
    """请求日志过滤器"""
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.sensitive_filter = SensitiveDataFilter()
        
    def filter(self, record: logging.LogRecord) -> bool:
        """过滤并处理日志记录"""
        # 添加请求ID
        record.request_id = getattr(threading.current_thread(), "request_id", None)
        
        # 处理额外数据
        if hasattr(record, "data"):
            # 创建深拷贝以避免修改原始数据
            filtered_data = copy.deepcopy(record.data)
            # 过滤敏感信息
            record.data = self.sensitive_filter.filter_sensitive_data(filtered_data)
            
        return True

class CustomJsonFormatter(logging.Formatter):
    """自定义JSON格式化器"""
    
    def __init__(self, *args, **kwargs):
        self.default_fields = kwargs.pop("default_fields", {})
        super().__init__(*args, **kwargs)
        self.sensitive_filter = SensitiveDataFilter()
        
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        # 基础日志信息
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process": record.process,
            "thread": record.thread,
        }
        
        # 添加默认字段
        log_data.update(self.default_fields)
        
        # 添加异常信息
        if record.exc_info:
            log_data["exc_info"] = self.formatException(record.exc_info)
            
        # 添加堆栈信息
        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)
            
        # 添加额外字段
        if hasattr(record, "data"):
            # 过滤敏感信息
            filtered_data = self.sensitive_filter.filter_sensitive_data(record.data)
            log_data["data"] = filtered_data
            
        # 添加请求ID
        request_id = getattr(threading.current_thread(), "request_id", None)
        if request_id:
            log_data["request_id"] = request_id
            
        # 添加环境信息
        log_data["environment"] = getattr(settings, "ENVIRONMENT", "unknown")
            
        return json.dumps(log_data, ensure_ascii=False)

class AsyncRequestIdMiddleware:
    """异步请求ID中间件"""
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        
    async def __call__(self, request: HttpRequest) -> Any:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        threading.current_thread().request_id = request_id
        
        response = await self.get_response(request)
        response["X-Request-ID"] = request_id
        
        # 添加其他响应头
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["X-XSS-Protection"] = "1; mode=block"
        
        return response

@contextmanager
def log_context(**kwargs) -> Generator[None, None, None]:
    """日志上下文管理器"""
    thread = threading.current_thread()
    old_values = {}
    
    # 保存旧值并设置新值
    for key, value in kwargs.items():
        if hasattr(thread, key):
            old_values[key] = getattr(thread, key)
        setattr(thread, key, value)
        
    try:
        yield
    finally:
        # 恢复旧值
        for key in kwargs:
            if key in old_values:
                setattr(thread, key, old_values[key])
            else:
                delattr(thread, key)

class PerformanceLogger:
    """性能日志记录器"""
    
    def __init__(self, logger: Optional[logging.Logger] = None, context: Optional[dict] = None):
        self.logger = logger or logging.getLogger("performance")
        self.start_time = None
        self.checkpoints = {}
        self.context = context or {}
        
    def start(self, label: str = "start") -> None:
        """开始计时"""
        self.start_time = time.time()
        self.checkpoints[label] = self.start_time
        
        # 记录开始日志
        self.logger.debug(
            f"Performance monitoring started: {label}",
            extra={"data": {"context": self.context}}
        )
        
    def checkpoint(self, label: str, context: Optional[dict] = None) -> float:
        """记录检查点"""
        current_time = time.time()
        self.checkpoints[label] = current_time
        duration = current_time - self.start_time
        
        # 记录检查点日志
        checkpoint_data = {
            "label": label,
            "duration": duration,
            "context": {**self.context, **(context or {})}
        }
        self.logger.debug(
            f"Checkpoint reached: {label}",
            extra={"data": checkpoint_data}
        )
        
        return duration
        
    def end(self, label: str = "end", context: Optional[dict] = None) -> Dict[str, float]:
        """结束计时并记录日志"""
        if not self.start_time:
            raise RuntimeError("Performance logger not started")
            
        end_time = time.time()
        self.checkpoints[label] = end_time
        
        # 计算各阶段耗时
        durations = {}
        last_time = self.start_time
        for checkpoint, timestamp in self.checkpoints.items():
            duration = timestamp - last_time
            durations[checkpoint] = duration
            last_time = timestamp
            
        # 记录总耗时
        total_duration = end_time - self.start_time
        durations["total"] = total_duration
        
        # 记录日志
        performance_data = {
            "durations": durations,
            "checkpoints": self.checkpoints,
            "total_duration": total_duration,
            "context": {**self.context, **(context or {})}
        }
        
        self.logger.info(
            f"Performance monitoring completed: {label}",
            extra={"data": performance_data}
        )
        
        return durations

def get_logger(name: str) -> logging.Logger:
    """获取日志记录器"""
    return logging.getLogger(name)

def log_exception(
    exc: Exception,
    logger: Optional[logging.Logger] = None,
    request: Optional[HttpRequest] = None,
    context: Optional[dict] = None,
) -> None:
    """记录异常日志"""
    if logger is None:
        logger = logging.getLogger("apps")

    log_data = {
        "exc_type": type(exc).__name__,
        "exc_message": str(exc),
        "context": context or {},
    }

    if request:
        log_data.update({
            "method": request.method,
            "path": request.path,
            "user": str(getattr(request, "user", "AnonymousUser")),
            "ip": request.META.get("REMOTE_ADDR"),
            "request_id": getattr(threading.current_thread(), "request_id", None),
        })

    logger.error(
        f"Exception occurred: {type(exc).__name__}",
        extra={"data": log_data},
        exc_info=True,
    )

def log_timing(
    logger: Optional[logging.Logger] = None,
    level: int = logging.INFO,
    message: Optional[str] = None,
    threshold: Optional[float] = None,
) -> Callable[[T], T]:
    """函数执行时间日志装饰器"""
    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration = end_time - start_time
                
                # 只记录超过阈值的耗时
                if threshold is None or duration >= threshold:
                    log = logger or logging.getLogger(func.__module__)
                    log_message = message or f"{func.__name__} took {duration:.2f} seconds"
                    log.log(
                        level,
                        log_message,
                        extra={
                            "data": {
                                "function": func.__name__,
                                "duration": duration,
                                "threshold": threshold,
                            }
                        }
                    )
        return cast(T, wrapper)
    return decorator

def setup_request_logging(get_response: Callable) -> Callable:
    """请求日志中间件"""
    logger = logging.getLogger("django.request")

    def middleware(request: HttpRequest) -> Any:
        start_time = time.time()
        
        # 记录请求信息
        request_data = {
            "method": request.method,
            "path": request.path,
            "query_params": dict(request.GET),
            "headers": dict(request.headers),
            "user": str(getattr(request, "user", "AnonymousUser")),
            "ip": request.META.get("REMOTE_ADDR"),
            "request_id": getattr(threading.current_thread(), "request_id", None),
        }
        
        logger.info("Request started", extra={"data": request_data})
        
        try:
            response = get_response(request)
            duration = time.time() - start_time
            
            # 记录响应信息
            response_data = {
                **request_data,
                "status": response.status_code,
                "duration": f"{duration:.2f}s",
                "content_type": response.get("Content-Type", ""),
                "content_length": response.get("Content-Length", ""),
            }
            
            if response.status_code >= 400:
                logger.warning("Request failed", extra={"data": response_data})
            else:
                logger.info("Request completed", extra={"data": response_data})
                
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Request error",
                extra={
                    "data": {
                        **request_data,
                        "duration": f"{duration:.2f}s",
                        "error": str(e),
                    }
                },
                exc_info=True,
            )
            raise

    return middleware

class ModelLogger:
    """模型日志记录器"""
    def __init__(self, model_class: Type) -> None:
        self.logger = logging.getLogger(f"apps.{model_class.__module__}")
        self.model_name = model_class.__name__

    def log_create(self, instance: Any, user: Optional[str] = None) -> None:
        """记录创建操作"""
        self.logger.info(
            f"{self.model_name} created",
            extra={
                "data": {
                    "id": instance.pk,
                    "user": str(user or "system"),
                    "fields": {
                        field.name: getattr(instance, field.name)
                        for field in instance._meta.fields
                    },
                    "request_id": getattr(threading.current_thread(), "request_id", None),
                }
            },
        )

    def log_update(
        self,
        instance: Any,
        changed_fields: dict,
        user: Optional[str] = None
    ) -> None:
        """记录更新操作"""
        self.logger.info(
            f"{self.model_name} updated",
            extra={
                "data": {
                    "id": instance.pk,
                    "changed_fields": changed_fields,
                    "user": str(user or "system"),
                    "request_id": getattr(threading.current_thread(), "request_id", None),
                }
            },
        )

    def log_delete(self, instance: Any, user: Optional[str] = None) -> None:
        """记录删除操作"""
        self.logger.info(
            f"{self.model_name} deleted",
            extra={
                "data": {
                    "id": instance.pk,
                    "user": str(user or "system"),
                    "request_id": getattr(threading.current_thread(), "request_id", None),
                }
            },
        )

# 使用示例
"""
# 1. 使用JSON格式化器
handler = logging.StreamHandler()
formatter = CustomJsonFormatter(
    default_fields={"app_name": "my_app", "environment": "production"}
)
handler.setFormatter(formatter)
logger = logging.getLogger("my_logger")
logger.addHandler(handler)

# 2. 使用请求ID中间件
MIDDLEWARE = [
    'apps.core.logging.RequestIdMiddleware',
    ...
]

# 3. 使用日志上下文管理器
with log_context(user_id="123", transaction_id="abc"):
    logger.info("Processing transaction")

# 4. 使用性能日志记录器
perf_logger = PerformanceLogger()
perf_logger.start("开始处理")
# ... 处理逻辑 ...
perf_logger.checkpoint("步骤1完成")
# ... 更多处理 ...
perf_logger.checkpoint("步骤2完成")
durations = perf_logger.end("处理完成")

# 5. 在视图中使用装饰器
@log_timing(threshold=1.0)  # 只记录执行时间超过1秒的调用
def slow_view(request):
    # 视图逻辑...
    pass

# 6. 在模型中使用日志记录器
class MyModel(models.Model):
    name = models.CharField(max_length=100)
    logger = ModelLogger(model_class=__class__)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not is_new:
            old_instance = self.__class__.objects.get(pk=self.pk)
            changed_fields = {
                field.name: (getattr(old_instance, field.name), getattr(self, field.name))
                for field in self._meta.fields
                if getattr(old_instance, field.name) != getattr(self, field.name)
            }
            super().save(*args, **kwargs)
            if changed_fields:
                self.logger.log_update(self, changed_fields)
        else:
            super().save(*args, **kwargs)
            self.logger.log_create(self)

    def delete(self, *args, **kwargs):
        self.logger.log_delete(self)
        super().delete(*args, **kwargs)
""" 