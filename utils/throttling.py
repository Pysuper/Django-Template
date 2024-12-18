import hashlib
import logging
import time
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from rest_framework.exceptions import Throttled
from rest_framework.throttling import BaseThrottle

from .cache import CacheManager

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

@dataclass
class ThrottleState:
    """节流状态数据类"""
    rate: str
    num_requests: int
    duration: int
    key: str
    history: List[float]
    remaining: int
    available_in: float

class BaseRateThrottle(BaseThrottle):
    """基础速率限制类"""
    
    cache_format = "throttle:%(scope)s:%(ident)s"
    timer = time.time
    cache_manager = CacheManager(prefix="throttle")
    
    def __init__(self):
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        
    def get_cache_key(self, request: HttpRequest, view: Optional[Any] = None) -> str:
        """获取缓存键"""
        ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident
        }
        
    def get_rate(self) -> str:
        """获取速率限制"""
        if not getattr(self, "rate", None):
            return getattr(settings, f"{self.scope.upper()}_THROTTLE_RATE", None)
        return self.rate
        
    def parse_rate(self, rate: str) -> Tuple[int, int]:
        """解析速率限制"""
        if rate is None:
            return None, None
            
        num, period = rate.split("/")
        num_requests = int(num)
        
        # 解析时间周期
        if period[-1] == "s":
            duration = int(period[:-1])
        elif period[-1] == "m":
            duration = int(period[:-1]) * 60
        elif period[-1] == "h":
            duration = int(period[:-1]) * 3600
        elif period[-1] == "d":
            duration = int(period[:-1]) * 86400
        else:
            duration = int(period)
            
        return num_requests, duration
        
    def allow_request(
        self,
        request: HttpRequest,
        view: Optional[Any] = None
    ) -> Union[bool, Tuple[bool, Dict[str, Any]]]:
        """检查请求是否允许"""
        if self.rate is None:
            return True
            
        self.key = self.get_cache_key(request, view)
        self.history = self.cache_manager.get(self.key, [])
        self.now = self.timer()
        
        # 删除过期的历史记录
        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
            
        # 检查是否超过限制
        if len(self.history) >= self.num_requests:
            return self.throttle_failure()
            
        return self.throttle_success()
        
    def throttle_success(self) -> Union[bool, Tuple[bool, Dict[str, Any]]]:
        """请求通过"""
        self.history.insert(0, self.now)
        self.cache_manager.set(self.key, self.history, timeout=self.duration)
        
        remaining = self.num_requests - len(self.history)
        available_in = 0 if remaining else self.duration - (self.now - self.history[-1])
        
        return True, {
            "requests_remaining": remaining,
            "available_in": available_in,
        }
        
    def throttle_failure(self) -> Union[bool, Tuple[bool, Dict[str, Any]]]:
        """请求被限制"""
        available_in = self.duration - (self.now - self.history[-1])
        
        return False, {
            "requests_remaining": 0,
            "available_in": available_in,
        }
        
    def wait(self) -> Optional[float]:
        """获取等待时间"""
        if self.history:
            remaining_duration = self.duration - (self.now - self.history[-1])
            if remaining_duration > 0:
                available_in = remaining_duration
                return available_in
        return None

class UserRateThrottle(BaseRateThrottle):
    """用户速率限制"""
    
    scope = "user"
    
    def get_cache_key(self, request: HttpRequest, view: Optional[Any] = None) -> str:
        """获取缓存键"""
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
            
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident
        }

class AnonRateThrottle(BaseRateThrottle):
    """匿名用户速率限制"""
    
    scope = "anon"
    
    def get_cache_key(self, request: HttpRequest, view: Optional[Any] = None) -> str:
        """获取缓存键"""
        if request.user.is_authenticated:
            return None  # 已认证用户不受限制
            
        return super().get_cache_key(request, view)

class ScopedRateThrottle(BaseRateThrottle):
    """作用域速率限制"""
    
    scope_attr = "throttle_scope"
    
    def __init__(self):
        super().__init__()
        self.scope = None
        
    def allow_request(
        self,
        request: HttpRequest,
        view: Optional[Any] = None
    ) -> Union[bool, Tuple[bool, Dict[str, Any]]]:
        """检查请求是否允许"""
        # 获取视图的作用域
        self.scope = getattr(view, self.scope_attr, None)
        
        if not self.scope:
            return True
            
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        
        return super().allow_request(request, view)

def throttle(
    rate: str,
    scope: Optional[str] = None,
    key_func: Optional[Callable[[HttpRequest], str]] = None,
) -> Callable[[T], T]:
    """节流装饰器"""
    def decorator(func: T) -> T:
        @wraps(func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            if key_func:
                key = key_func(request)
            else:
                if scope:
                    key = f"throttle:{scope}:{request.META.get('REMOTE_ADDR', '')}"
                else:
                    key = f"throttle:{func.__name__}:{request.META.get('REMOTE_ADDR', '')}"
                    
            # 解析速率限制
            num, period = rate.split("/")
            num_requests = int(num)
            
            # 解析时间周期
            if period[-1] == "s":
                duration = int(period[:-1])
            elif period[-1] == "m":
                duration = int(period[:-1]) * 60
            elif period[-1] == "h":
                duration = int(period[:-1]) * 3600
            elif period[-1] == "d":
                duration = int(period[:-1]) * 86400
            else:
                duration = int(period)
                
            # 获取历史记录
            cache_manager = CacheManager()
            history = cache_manager.get(key, [])
            now = time.time()
            
            # 删除过期的历史记录
            while history and history[-1] <= now - duration:
                history.pop()
                
            # 检查是否超过限制
            if len(history) >= num_requests:
                available_in = duration - (now - history[-1])
                
                logger.warning(
                    "Request throttled",
                    extra={
                        "data": {
                            "key": key,
                            "rate": rate,
                            "available_in": available_in,
                        }
                    }
                )
                
                return JsonResponse(
                    {
                        "detail": f"Request was throttled. Expected available in {int(available_in)} seconds.",
                        "available_in": int(available_in),
                    },
                    status=429
                )
                
            # 更新历史记录
            history.insert(0, now)
            cache_manager.set(key, history, timeout=duration)
            
            return func(request, *args, **kwargs)
        return cast(T, wrapper)
    return decorator

class BurstRateThrottle(BaseRateThrottle):
    """突发速率限制"""
    
    scope = "burst"
    
    def __init__(self):
        super().__init__()
        self.burst_rate = self.get_burst_rate()
        self.burst_num_requests, self.burst_duration = self.parse_rate(self.burst_rate)
        
    def get_burst_rate(self) -> str:
        """获取突发速率限制"""
        if not getattr(self, "burst_rate", None):
            return getattr(settings, f"{self.scope.upper()}_BURST_RATE", None)
        return self.burst_rate
        
    def allow_request(
        self,
        request: HttpRequest,
        view: Optional[Any] = None
    ) -> Union[bool, Tuple[bool, Dict[str, Any]]]:
        """检查请求是否允许"""
        if self.rate is None and self.burst_rate is None:
            return True
            
        self.key = self.get_cache_key(request, view)
        self.history = self.cache_manager.get(self.key, [])
        self.now = self.timer()
        
        # 检查突发限制
        if self.burst_rate:
            burst_history = [
                ts for ts in self.history
                if ts > self.now - self.burst_duration
            ]
            if len(burst_history) >= self.burst_num_requests:
                return self.throttle_failure()
                
        # 检查常规限制
        if self.rate:
            normal_history = [
                ts for ts in self.history
                if ts > self.now - self.duration
            ]
            if len(normal_history) >= self.num_requests:
                return self.throttle_failure()
                
        return self.throttle_success()

class WindowRateThrottle(BaseRateThrottle):
    """滑动窗口速率限制"""
    
    scope = "window"
    window_size = 10  # 窗口大小（秒）
    
    def allow_request(
        self,
        request: HttpRequest,
        view: Optional[Any] = None
    ) -> Union[bool, Tuple[bool, Dict[str, Any]]]:
        """检查请求是否允许"""
        if self.rate is None:
            return True
            
        self.key = self.get_cache_key(request, view)
        self.history = self.cache_manager.get(self.key, [])
        self.now = self.timer()
        
        # 计算当前窗口的请求数
        window_start = self.now - self.window_size
        window_requests = len([
            ts for ts in self.history
            if ts > window_start
        ])
        
        # 计算允许的请求数
        allowed_requests = int(
            self.num_requests * (self.window_size / self.duration)
        )
        
        if window_requests >= allowed_requests:
            return self.throttle_failure()
            
        return self.throttle_success()

# 使用示例
"""
# 1. 在视图中使用速率限制
from rest_framework.views import APIView

class ExampleView(APIView):
    throttle_classes = [UserRateThrottle]
    
    def get(self, request):
        return Response({"message": "Hello, World!"})

# 2. 使用装饰器
@throttle(rate="100/h")
def my_view(request):
    return JsonResponse({"message": "Hello, World!"})

# 3. 使用突发速率限制
class BurstView(APIView):
    throttle_classes = [BurstRateThrottle]
    
    def get(self, request):
        return Response({"message": "Hello, World!"})

# 4. 使用滑动窗口速率限制
class WindowView(APIView):
    throttle_classes = [WindowRateThrottle]
    
    def get(self, request):
        return Response({"message": "Hello, World!"})

# 5. 在settings.py中配置速率限制
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "apps.core.throttling.UserRateThrottle",
        "apps.core.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/hour",
        "anon": "100/hour",
        "burst": "60/minute",
        "window": "1000/hour",
    }
}
""" 