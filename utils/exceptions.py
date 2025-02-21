import functools
import logging
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union, cast

from django.conf import settings
from django.core.mail import mail_admins
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler as drf_exception_handler

from .logging import log_exception

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

@dataclass
class ErrorReport:
    """错误报告数据类"""
    error_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    traceback: str
    request_info: Optional[Dict[str, Any]] = None
    user_info: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None

class BaseAPIException(APIException):
    """基础API异常类"""
    
    def __init__(
        self,
        detail: Optional[Union[str, Dict[str, Any]]] = None,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        error_id: Optional[str] = None,
    ):
        super().__init__(detail, code)
        if status_code is not None:
            self.status_code = status_code
        self.error_id = error_id or self.generate_error_id()
        
    @staticmethod
    def generate_error_id() -> str:
        """生成错误ID"""
        import uuid
        return str(uuid.uuid4())
        
    def get_full_details(self) -> Dict[str, Any]:
        """获取完整错误详情"""
        return {
            "error_id": self.error_id,
            "code": self.get_codes(),
            "message": self.detail,
            "status_code": self.status_code,
            "timestamp": timezone.now().isoformat(),
        }

class ValidationError(BaseAPIException):
    """验证错误"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "validation_error"
    default_detail = "Invalid input."

class AuthenticationError(BaseAPIException):
    """认证错误"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "authentication_error"
    default_detail = "Authentication failed."

class PermissionError(BaseAPIException):
    """权限错误"""
    status_code = status.HTTP_403_FORBIDDEN
    default_code = "permission_error"
    default_detail = "Permission denied."

class NotFoundError(BaseAPIException):
    """未找到错误"""
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"
    default_detail = "Resource not found."

class ConflictError(BaseAPIException):
    """冲突错误"""
    status_code = status.HTTP_409_CONFLICT
    default_code = "conflict"
    default_detail = "Resource conflict."

class ThrottlingError(BaseAPIException):
    """限流错误"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "throttled"
    default_detail = "Request was throttled."

class ServerError(BaseAPIException):
    """服务器错误"""
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = "server_error"
    default_detail = "Internal server error."

class ServiceUnavailableError(BaseAPIException):
    """服务不可用错误"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "service_unavailable"
    default_detail = "Service temporarily unavailable."

def handle_exception(exc: Exception, context: Dict[str, Any]) -> JsonResponse:
    """异常处理器"""
    # 首先尝试使用DRF的异常处理器
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        return response
        
    # 获取请求对象
    request = context.get("request")
    
    # 生成错误报告
    error_report = create_error_report(exc, request)
    
    # 记录错误日志
    log_exception(exc, logger, request, context)
    
    # 发送错误报告
    send_error_report(error_report)
    
    # 返回JSON响应
    if isinstance(exc, BaseAPIException):
        return JsonResponse(
            exc.get_full_details(),
            status=exc.status_code
        )
    else:
        return JsonResponse(
            {
                "error_id": error_report.error_id,
                "message": "An unexpected error occurred.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "timestamp": timezone.now().isoformat(),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def create_error_report(
    exc: Exception,
    request: Optional[HttpRequest] = None
) -> ErrorReport:
    """创建错误报告"""
    # 获取异常信息
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    # 生成错误ID
    error_id = getattr(exc, "error_id", None) or BaseAPIException.generate_error_id()
    
    # 获取请求信息
    request_info = None
    user_info = None
    
    if request:
        request_info = {
            "method": request.method,
            "path": request.path,
            "query_params": dict(request.GET),
            "headers": dict(request.headers),
            "remote_addr": request.META.get("REMOTE_ADDR"),
        }
        
        if hasattr(request, "user") and request.user.is_authenticated:
            user_info = {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
            }
            
    return ErrorReport(
        error_id=error_id,
        timestamp=timezone.now(),
        error_type=exc_type.__name__ if exc_type else "Unknown",
        error_message=str(exc),
        traceback="".join(traceback.format_tb(exc_traceback)) if exc_traceback else "",
        request_info=request_info,
        user_info=user_info,
        context=getattr(exc, "context", None),
    )

def send_error_report(error_report: ErrorReport) -> None:
    """发送错误报告"""
    # 发送邮件通知
    if getattr(settings, "SEND_ERROR_EMAILS", False):
        subject = f"Error Report: {error_report.error_type} [{error_report.error_id}]"
        message = (
            f"Error ID: {error_report.error_id}\n"
            f"Timestamp: {error_report.timestamp}\n"
            f"Error Type: {error_report.error_type}\n"
            f"Error Message: {error_report.error_message}\n\n"
            f"Traceback:\n{error_report.traceback}\n\n"
        )
        
        if error_report.request_info:
            message += f"Request Info:\n{error_report.request_info}\n\n"
            
        if error_report.user_info:
            message += f"User Info:\n{error_report.user_info}\n\n"
            
        if error_report.context:
            message += f"Context:\n{error_report.context}\n"
            
        mail_admins(subject, message, fail_silently=True)
        
    # 记录到日志
    logger.error(
        f"Error Report [{error_report.error_id}]",
        extra={
            "data": {
                "error_id": error_report.error_id,
                "error_type": error_report.error_type,
                "error_message": error_report.error_message,
                "request_info": error_report.request_info,
                "user_info": error_report.user_info,
                "context": error_report.context,
            }
        },
        exc_info=True,
    )

def handle_error(
    error_class: Type[BaseAPIException],
    log_error: bool = True,
    raise_error: bool = True,
) -> Callable[[T], T]:
    """错误处理装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                # 获取请求对象
                request = next(
                    (arg for arg in args if isinstance(arg, HttpRequest)),
                    None
                )
                
                # 创建错误报告
                error_report = create_error_report(exc, request)
                
                if log_error:
                    # 记录错误日志
                    log_exception(exc, logger, request)
                    
                if raise_error:
                    # 抛出API异常
                    raise error_class(
                        detail=str(exc),
                        error_id=error_report.error_id
                    ) from exc
                else:
                    # 返回错误响应
                    return JsonResponse(
                        {
                            "error_id": error_report.error_id,
                            "message": str(exc),
                            "status_code": error_class.status_code,
                            "timestamp": timezone.now().isoformat(),
                        },
                        status=error_class.status_code
                    )
        return cast(T, wrapper)
    return decorator

# 使用示例
"""
# 1. 在视图中使用异常处理装饰器
@handle_error(ValidationError)
def my_view(request):
    # 视图逻辑
    pass

# 2. 在视图中抛出自定义异常
def another_view(request):
    if not request.user.is_authenticated:
        raise AuthenticationError("User not authenticated")
    return JsonResponse({"message": "Success"})

# 3. 在settings.py中配置异常处理
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.core.exceptions.handle_exception"
}

# 4. 在中间件中处理异常
class ErrorHandlingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        try:
            response = self.get_response(request)
            return response
        except Exception as exc:
            return handle_exception(exc, {"request": request})

# 5. 使用错误报告系统
try:
    # 一些可能出错的代码
    raise ValueError("Something went wrong")
except Exception as e:
    error_report = create_error_report(e)
    send_error_report(error_report)
""" 