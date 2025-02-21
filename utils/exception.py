import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Union

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpRequest, JsonResponse
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.views import exception_handler as drf_exception_handler

from utils.error import (
    BaseError,
    BusinessError,
    DatabaseError,
    ErrorCode,
    ErrorLevel,
    SystemError,
    ValidationError as CustomValidationError,
)

logger = logging.getLogger(__name__)


class ExceptionData:
    """异常数据类，用于格式化异常信息"""

    def __init__(
        self,
        exc: Exception,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: int = ErrorCode.SYSTEM_ERROR.code,
        message: str = None,
        level: ErrorLevel = ErrorLevel.ERROR,
        data: Any = None,
    ):
        self.exc = exc
        self.status_code = status_code
        self.code = code
        self.message = message or str(exc)
        self.level = level
        self.data = data
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        error_dict = {
            "code": self.code,
            "message": self.message,
            "level": self.level.value,
            "timestamp": self.timestamp,
        }

        if settings.DEBUG:
            error_dict.update({"exception": self.exc.__class__.__name__, "traceback": traceback.format_exc()})

        if self.data is not None:
            error_dict["data"] = self.data

        return error_dict


class ExceptionHandler:
    """统一异常处理器"""

    def __init__(self):
        # 异常映射表
        self.exception_mappings = {
            Http404: self._handle_404,
            PermissionDenied: self._handle_permission_denied,
            ValidationError: self._handle_validation_error,
            AuthenticationFailed: self._handle_authentication_failed,
            BaseError: self._handle_base_error,
            Exception: self._handle_generic_exception,
        }

    def __call__(self, exc: Exception, context: dict) -> JsonResponse:
        """处理异常"""
        # 首先尝试使用DRF的异常处理
        response = drf_exception_handler(exc, context)
        if response is not None:
            return response

        # 获取请求对象
        request = context.get("request")

        # 记录异常日志
        self._log_exception(request, exc)

        # 查找对应的异常处理方法
        handler = self._get_exception_handler(exc)

        # 处理异常
        exc_data = handler(exc, request)

        # 返回JSON响应
        return JsonResponse(data=exc_data.to_dict(), status=exc_data.status_code)

    def _get_exception_handler(self, exc: Exception) -> callable:
        """获取异常处理方法"""
        for exc_class, handler in self.exception_mappings.items():
            if isinstance(exc, exc_class):
                return handler
        return self._handle_generic_exception

    def _log_exception(self, request: Optional[HttpRequest], exc: Exception) -> None:
        """记录异常日志"""
        if not isinstance(exc, (Http404, PermissionDenied)):
            logger.error(
                f"Exception in {request.method if request else 'Unknown'} "
                f"{request.path if request else 'Unknown'}: {str(exc)}",
                exc_info=True,
                extra={"status_code": getattr(exc, "status_code", 500), "request": request},
            )

    def _handle_404(self, exc: Http404, request: Optional[HttpRequest] = None) -> ExceptionData:
        """处理404错误"""
        return ExceptionData(
            exc=exc,
            status_code=status.HTTP_404_NOT_FOUND,
            code=ErrorCode.RESOURCE_NOT_FOUND.code,
            message=_("Resource not found"),
            level=ErrorLevel.WARNING,
        )

    def _handle_permission_denied(self, exc: PermissionDenied, request: Optional[HttpRequest] = None) -> ExceptionData:
        """处理权限拒绝错误"""
        return ExceptionData(
            exc=exc,
            status_code=status.HTTP_403_FORBIDDEN,
            code=ErrorCode.PERMISSION_DENIED.code,
            message=_("Permission denied"),
            level=ErrorLevel.WARNING,
        )

    def _handle_validation_error(
        self, exc: Union[ValidationError, CustomValidationError], request: Optional[HttpRequest] = None
    ) -> ExceptionData:
        """处理验证错误"""
        if hasattr(exc, "message_dict"):
            message = exc.message_dict
        elif hasattr(exc, "message"):
            message = exc.message
        else:
            message = str(exc)

        return ExceptionData(
            exc=exc,
            status_code=status.HTTP_400_BAD_REQUEST,
            code=ErrorCode.PARAM_ERROR.code,
            message=message,
            level=ErrorLevel.WARNING,
        )

    def _handle_authentication_failed(
        self, exc: AuthenticationFailed, request: Optional[HttpRequest] = None
    ) -> ExceptionData:
        """处理认证失败错误"""
        return ExceptionData(
            exc=exc,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code=ErrorCode.UNAUTHORIZED.code,
            message=str(exc),
            level=ErrorLevel.WARNING,
        )

    def _handle_base_error(self, exc: BaseError, request: Optional[HttpRequest] = None) -> ExceptionData:
        """处理基础错误"""
        return ExceptionData(
            exc=exc,
            status_code=exc.status_code,
            code=exc.error_code.code,
            message=exc.message,
            level=exc.level,
            data=exc.data,
        )

    def _handle_generic_exception(self, exc: Exception, request: Optional[HttpRequest] = None) -> ExceptionData:
        """处理通用异常"""
        return ExceptionData(
            exc=exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code=ErrorCode.SYSTEM_ERROR.code,
            message=_("Internal server error"),
            level=ErrorLevel.ERROR,
        )


# 创建全局异常处理器实例
exception_handler = ExceptionHandler()


def custom_exception_handler(exc: Exception, context: dict) -> JsonResponse:
    """
    自定义异常处理函数
    :param exc: 异常对象
    :param context: 上下文信息
    :return: JsonResponse
    """
    return exception_handler(exc, context)


# 异常装饰器
def handle_exceptions(error_code: ErrorCode = None, error_message: str = None):
    """
    异常处理装饰器
    :param error_code: 错误码
    :param error_message: 错误消息
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
                if isinstance(e, BaseError):
                    raise e
                raise SystemError(
                    error_code=error_code or ErrorCode.SYSTEM_ERROR,
                    message=error_message or str(e),
                    data={"function": func.__name__},
                )

        return wrapper

    return decorator


# 业务异常处理装饰器
def handle_business_exceptions(error_code: ErrorCode = None, error_message: str = None):
    """
    业务异常处理装饰器
    :param error_code: 错误码
    :param error_message: 错误消息
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Business error in {func.__name__}: {str(e)}")
                if isinstance(e, BaseError):
                    raise e
                raise BusinessError(
                    error_code=error_code or ErrorCode.OPERATION_FAILED,
                    message=error_message or str(e),
                    data={"function": func.__name__},
                )

        return wrapper

    return decorator


# 数据库异常处理装饰器
def handle_db_exceptions(error_code: ErrorCode = None, error_message: str = None):
    """
    数据库异常处理装饰器
    :param error_code: 错误码
    :param error_message: 错误消息
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Database error in {func.__name__}: {str(e)}", exc_info=True)
                if isinstance(e, BaseError):
                    raise e
                raise DatabaseError(
                    error_code=error_code or ErrorCode.DB_ERROR,
                    message=error_message or str(e),
                    data={"function": func.__name__},
                )

        return wrapper

    return decorator
