import functools
import logging
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

from celery import Task, shared_task
from celery.result import AsyncResult
from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from .logging import log_timing

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

class BaseTask(Task):
    """基础任务类"""
    
    # 默认重试次数
    max_retries = 3
    
    # 默认重试延迟（秒）
    default_retry_delay = 60
    
    # 是否忽略结果
    ignore_result = False
    
    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
        """任务失败回调"""
        logger.error(
            f"Task {self.name} failed",
            extra={
                "data": {
                    "task_id": task_id,
                    "args": args,
                    "kwargs": kwargs,
                    "exception": str(exc),
                }
            },
            exc_info=True,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)
        
    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo: Any) -> None:
        """任务重试回调"""
        logger.warning(
            f"Task {self.name} retrying",
            extra={
                "data": {
                    "task_id": task_id,
                    "args": args,
                    "kwargs": kwargs,
                    "exception": str(exc),
                    "retry_count": self.request.retries,
                }
            },
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)
        
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """任务成功回调"""
        logger.info(
            f"Task {self.name} succeeded",
            extra={
                "data": {
                    "task_id": task_id,
                    "args": args,
                    "kwargs": kwargs,
                    "result": retval,
                }
            },
        )
        super().on_success(retval, task_id, args, kwargs)

class TransactionAwareTask(BaseTask):
    """事务感知任务类"""
    
    def apply_async(self, *args: Any, **kwargs: Any) -> AsyncResult:
        """异步执行任务"""
        # 如果在事务中，等待事务提交后再执行任务
        if transaction.get_connection().in_atomic_block:
            transaction.on_commit(lambda: super().apply_async(*args, **kwargs))
            return AsyncResult(None)
        return super().apply_async(*args, **kwargs)

def task(*args: Any, **kwargs: Any) -> Callable[[T], T]:
    """任务装饰器"""
    def decorator(func: T) -> T:
        # 设置默认参数
        kwargs.setdefault("bind", True)
        kwargs.setdefault("base", TransactionAwareTask)
        
        # 使用Celery的shared_task装饰器
        task_func = shared_task(*args, **kwargs)(func)
        return cast(T, task_func)
    return decorator

def periodic_task(*args: Any, **kwargs: Any) -> Callable[[T], T]:
    """周期任务装饰器"""
    def decorator(func: T) -> T:
        # 设置默认参数
        kwargs.setdefault("bind", True)
        kwargs.setdefault("base", TransactionAwareTask)
        
        # 使用Celery的shared_task装饰器
        task_func = shared_task(*args, **kwargs)(func)
        return cast(T, task_func)
    return decorator

def retry_task(
    max_retries: int = 3,
    countdown: int = 60,
    exponential_backoff: bool = True,
    jitter: bool = True,
) -> Callable[[T], T]:
    """重试任务装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(self: Task, *args: Any, **kwargs: Any) -> Any:
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                # 计算重试延迟
                retry_count = self.request.retries
                if exponential_backoff:
                    delay = countdown * (2 ** retry_count)
                else:
                    delay = countdown
                    
                # 添加随机抖动
                if jitter:
                    import random
                    delay = random.uniform(delay * 0.5, delay * 1.5)
                    
                # 重试任务
                raise self.retry(
                    exc=exc,
                    countdown=delay,
                    max_retries=max_retries
                )
        return cast(T, wrapper)
    return decorator

def rate_limit(
    key: str,
    limit: int,
    period: int,
    wait: bool = False,
    raise_on_limit: bool = True,
) -> Callable[[T], T]:
    """速率限制装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = f"rate_limit:{key}"
            
            # 获取当前计数
            count = cache.get(cache_key, 0)
            
            if count >= limit:
                if wait:
                    # 等待直到下一个周期
                    import time
                    time.sleep(period)
                    count = 0
                elif raise_on_limit:
                    raise Exception(f"Rate limit exceeded: {limit} requests per {period} seconds")
                else:
                    return None
                    
            # 增加计数
            cache.set(cache_key, count + 1, timeout=period)
            
            return func(*args, **kwargs)
        return cast(T, wrapper)
    return decorator

def task_lock(
    key: str,
    timeout: int = 3600,
    blocking: bool = True,
    raise_on_locked: bool = True,
) -> Callable[[T], T]:
    """任务锁装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            lock_key = f"task_lock:{key}"
            
            # 尝试获取锁
            acquired = cache.add(lock_key, True, timeout=timeout)
            
            if not acquired:
                if blocking:
                    # 等待直到获取锁
                    import time
                    while not cache.add(lock_key, True, timeout=timeout):
                        time.sleep(1)
                elif raise_on_locked:
                    raise Exception(f"Task {key} is already running")
                else:
                    return None
                    
            try:
                return func(*args, **kwargs)
            finally:
                # 释放锁
                cache.delete(lock_key)
        return cast(T, wrapper)
    return decorator

def task_chain(*tasks: Task) -> Task:
    """任务链"""
    from celery import chain
    return chain(*tasks)

def task_group(*tasks: Task) -> Task:
    """任务组"""
    from celery import group
    return group(*tasks)

def task_chord(header: Task, body: Task) -> Task:
    """任务和弦"""
    from celery import chord
    return chord(header)(body)

# 使用示例
"""
# 1. 基本任务
@task()
def my_task(self, arg1, arg2):
    # 任务逻辑
    return result

# 2. 周期任务
@periodic_task(run_every=timedelta(hours=1))
def hourly_task(self):
    # 任务逻辑
    pass

# 3. 重试任务
@task()
@retry_task(max_retries=3, countdown=60)
def retry_task(self, arg):
    # 可能失败的任务逻辑
    pass

# 4. 速率限制任务
@task()
@rate_limit(key="my_task", limit=100, period=60)
def rate_limited_task(self):
    # 任务逻辑
    pass

# 5. 带锁的任务
@task()
@task_lock(key="unique_task")
def locked_task(self):
    # 需要互斥的任务逻辑
    pass

# 6. 任务链
task_chain = task_chain(task1.s(), task2.s(), task3.s())
task_chain.apply_async()

# 7. 任务组
task_group = task_group(task1.s(), task2.s(), task3.s())
task_group.apply_async()

# 8. 任务和弦
task_chord = task_chord(task_group, callback_task.s())
task_chord.apply_async()
""" 