from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast
from pydantic import BaseModel, Field, validator
import gzip
import hashlib
import logging
import os
import re
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.middleware.gzip import GZipMiddleware
from django.utils.cache import (
    add_never_cache_headers,
    get_cache_key,
    get_max_age,
    learn_cache_key,
    patch_cache_control,
    patch_response_headers,
    patch_vary_headers,
)
from django.utils.encoding import force_bytes
from django.utils.http import http_date
from django.views.decorators.cache import cache_control, cache_page
from django.views.decorators.http import condition

from .cache import CacheManager

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

class StaticConfig(BaseModel):
    """静态文件配置"""
    cache_control: str = Field(
        default="public, max-age=31536000",
        description="缓存控制头"
    )
    gzip_types: Set[str] = Field(
        default={
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "text/html",
            "text/xml",
            "application/xml",
        },
        description="需要压缩的文件类型"
    )
    versioning: bool = Field(default=True, description="是否启用版本控制")
    manifest: bool = Field(default=True, description="是否启用清单文件")

class CacheConfig(BaseModel):
    """缓存配置"""
    default_timeout: int = Field(default=300, ge=0, description="默认超时时间")
    cache_control: str = Field(
        default="public, max-age=300",
        description="缓存控制头"
    )
    vary_headers: List[str] = Field(
        default=["Accept", "Accept-Encoding", "Accept-Language"],
        description="Vary头字段"
    )

class CompressionConfig(BaseModel):
    """压缩配置"""
    min_length: int = Field(default=200, ge=0, description="最小压缩长度")
    compress_level: int = Field(default=6, ge=1, le=9, description="压缩级别")
    content_types: Set[str] = Field(
        default={
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "text/xml",
            "application/xml",
        },
        description="需要压缩的内容类型"
    )

class PerformanceConfig(BaseModel):
    """性能配置"""
    static: StaticConfig = Field(default_factory=StaticConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    compression: CompressionConfig = Field(default_factory=CompressionConfig)

@dataclass
class CacheContext:
    """缓存上下文"""
    request: HttpRequest
    response: Optional[HttpResponse]
    config: CacheConfig
    cache_manager: CacheManager

@dataclass
class CompressionContext:
    """压缩上下文"""
    request: HttpRequest
    response: HttpResponse
    config: CompressionConfig

class OptimizedStaticStorage(ManifestStaticFilesStorage):
    """优化的静态文件存储"""
    
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.config = PerformanceConfig().static
        
    def post_process(
        self,
        paths: Dict[str, tuple],
        dry_run: bool = False,
        **options: Any
    ) -> List[tuple]:
        """后处理静态文件"""
        processed_files = super().post_process(paths, dry_run, **options)
        
        if not dry_run:
            for name, processed in processed_files:
                if processed:
                    path = self.path(name)
                    content_type = self._get_content_type(name)
                    if content_type in self.config.gzip_types:
                        self._gzip_file(path)
                        
        return processed_files
        
    def _get_content_type(self, name: str) -> str:
        """获取文件内容类型"""
        ext = os.path.splitext(name)[1].lower()
        return {
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".html": "text/html",
            ".xml": "application/xml",
        }.get(ext, "application/octet-stream")
        
    def _gzip_file(self, path: str) -> None:
        """压缩文件"""
        with open(path, "rb") as f_in:
            content = f_in.read()
            
        compressed = gzip.compress(
            content,
            compresslevel=PerformanceConfig().compression.compress_level
        )
        
        with open(f"{path}.gz", "wb") as f_out:
            f_out.write(compressed)

class CacheMiddleware:
    """缓存中间件"""
    
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.config = PerformanceConfig().cache
        self.cache_manager = CacheManager()
        
    def __call__(self, request: HttpRequest) -> HttpResponse:
        context = CacheContext(
            request=request,
            response=None,
            config=self.config,
            cache_manager=self.cache_manager
        )
        
        if not self._is_cacheable(context):
            return self.get_response(request)
            
        cache_key = self._get_cache_key(context)
        response = self.cache_manager.get(cache_key)
        
        if response is not None:
            return response
            
        response = self.get_response(request)
        context.response = response
        
        if self._should_cache(context):
            self._set_cache_headers(context)
            timeout = get_max_age(response) or self.config.default_timeout
            self.cache_manager.set(cache_key, response, timeout=timeout)
            
        return response
        
    def _is_cacheable(self, context: CacheContext) -> bool:
        """检查请求是否可缓存"""
        return (
            context.request.method in ("GET", "HEAD")
            and not context.request.user.is_authenticated
            and not context.request.COOKIES
            and not context.request.session.accessed
        )
        
    def _get_cache_key(self, context: CacheContext) -> str:
        """获取缓存键"""
        key_prefix = settings.CACHE_MIDDLEWARE_KEY_PREFIX
        cache_key = hashlib.md5(force_bytes(
            f"{key_prefix}:{context.request.path}:{context.request.GET.urlencode()}"
        )).hexdigest()
        return f"view:{cache_key}"
        
    def _should_cache(self, context: CacheContext) -> bool:
        """检查是否应该缓存"""
        response = context.response
        if not response:
            return False
            
        return (
            response.status_code == 200
            and not response.streaming
            and not response.has_header("Cache-Control")
            and not response.has_header("Vary")
            and not response.has_header("Expires")
        )
        
    def _set_cache_headers(self, context: CacheContext) -> None:
        """设置缓存头"""
        if not context.response:
            return
            
        patch_response_headers(context.response)
        patch_cache_control(
            context.response,
            **{"public": True, "max_age": context.config.default_timeout}
        )
        patch_vary_headers(context.response, context.config.vary_headers)

class CompressionMiddleware:
    """压缩中间件"""
    
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.config = PerformanceConfig().compression
        self.gzip_middleware = GZipMiddleware(get_response)
        
    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        context = CompressionContext(
            request=request,
            response=response,
            config=self.config
        )
        
        if self._should_compress(context):
            return self.gzip_middleware(request)
            
        return response
        
    def _should_compress(self, context: CompressionContext) -> bool:
        """检查是否需要压缩"""
        ae = context.request.META.get("HTTP_ACCEPT_ENCODING", "")
        if not re.search(r"\bgzip\b", ae):
            return False
            
        ct = context.response.get("Content-Type", "").split(";")[0]
        if ct not in context.config.content_types:
            return False
            
        cl = len(context.response.content)
        if cl < context.config.min_length:
            return False
            
        return True

def cache_view(
    timeout: Optional[int] = None,
    cache_control: Optional[Dict[str, Any]] = None,
    key_prefix: Optional[str] = None
) -> Callable[[T], T]:
    """视图缓存装饰器"""
    def decorator(view_func: T) -> T:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            if key_prefix:
                cache_key = f"{key_prefix}:{request.path}:{request.GET.urlencode()}"
            else:
                cache_key = f"view:{request.path}:{request.GET.urlencode()}"
                
            cache_manager = CacheManager()
            response = cache_manager.get(cache_key)
            
            if response is None:
                response = view_func(request, *args, **kwargs)
                
                if cache_control:
                    patch_cache_control(response, **cache_control)
                    
                cache_manager.set(
                    cache_key,
                    response,
                    timeout=timeout or PerformanceConfig().cache.default_timeout
                )
                
            return response
        return cast(T, wrapper)
    return decorator

def etag_processor(request: HttpRequest, *args: Any, **kwargs: Any) -> str:
    """ETag处理器"""
    content = force_bytes(f"{request.path}:{request.GET.urlencode()}")
    return hashlib.md5(content).hexdigest()

def last_modified_processor(
    request: HttpRequest,
    *args: Any,
    **kwargs: Any
) -> Optional[int]:
    """Last-Modified处理器"""
    return None

def conditional_get(
    etag_func: Optional[Callable] = None,
    last_modified_func: Optional[Callable] = None
) -> Callable[[T], T]:
    """条件GET装饰器"""
    def decorator(view_func: T) -> T:
        @condition(
            etag_func=etag_func or etag_processor,
            last_modified_func=last_modified_func or last_modified_processor
        )
        @wraps(view_func)
        def wrapper(*args: Any, **kwargs: Any) -> HttpResponse:
            return view_func(*args, **kwargs)
        return cast(T, wrapper)
    return decorator

# 使用示例
"""
# 1. 在settings.py中配置性能选项
PERFORMANCE_CONFIG = {
    "STATIC": {
        "CACHE_CONTROL": "public, max-age=31536000",
        "GZIP_TYPES": {
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "text/html",
            "text/xml",
            "application/xml",
        },
        "VERSIONING": True,
        "MANIFEST": True,
    },
    "CACHE": {
        "DEFAULT_TIMEOUT": 300,
        "CACHE_CONTROL": "public, max-age=300",
        "VARY_HEADERS": ["Accept", "Accept-Encoding", "Accept-Language"],
    },
    "COMPRESSION": {
        "MIN_LENGTH": 200,
        "COMPRESS_LEVEL": 6,
        "CONTENT_TYPES": {
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "text/xml",
            "application/xml",
        },
    },
}

# 2. 配置静态文件存储
STATICFILES_STORAGE = "apps.core.performance.OptimizedStaticStorage"

# 3. 配置中间件
MIDDLEWARE = [
    "apps.core.performance.CompressionMiddleware",
    "apps.core.performance.CacheMiddleware",
    ...
]

# 4. 在视图中使用缓存装饰器
@cache_view(timeout=3600, cache_control={"public": True, "max_age": 3600})
def my_view(request):
    return JsonResponse({"message": "Hello, World!"})

# 5. 使用条件GET装饰器
@conditional_get()
def static_view(request):
    return JsonResponse({"message": "Static content"})

# 6. 使用ETag和Last-Modified
@conditional_get(
    etag_func=lambda request, *args, **kwargs: hashlib.md5(
        force_bytes(request.path)
    ).hexdigest(),
    last_modified_func=lambda request, *args, **kwargs: timezone.now()
)
def dynamic_view(request):
    return JsonResponse({"message": "Dynamic content"})

# 7. 使用流式响应
def stream_view(request):
    def generate_content():
        for i in range(100):
            yield f"data: {i}\\n\\n"
            
    response = StreamingHttpResponse(
        generate_content(),
        content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    return response
""" 