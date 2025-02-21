import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from django.conf import settings
from django.core.exceptions import (ObjectDoesNotExist, PermissionDenied,
                                  ValidationError)
from django.db import DatabaseError, transaction
from django.http import Http404, HttpRequest, JsonResponse
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

from utils.error import (BusinessError, DatabaseError as CustomDatabaseError,
                        ErrorCode, SystemError)
from utils.log.logger import logger
from utils.response import ApiResponse, error_response


class ExceptionData:
    """异常数据类"""
    
    def __init__(
        self,
        exc: Exception,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: int = ErrorCode.SYSTEM_ERROR.code,
        message: str = None,
        data: Any = None
    ):
        self.exc = exc
        self.status_code = status_code
        self.code = code
        self.message = message or str(exc)
        self.data = data
        self.timestamp = datetime.now().isoformat()
        self.traceback = self._get_traceback()

    def _get_traceback(self) -> Optional[str]:
        """获取异常堆栈"""
        if settings.DEBUG:
            return ''.join(traceback.format_exception(*sys.exc_info()))
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        error_dict = {
            'code': self.code,
            'message': self.message,
            'timestamp': self.timestamp
        }
        
        if settings.DEBUG:
            error_dict.update({
                'exception': self.exc.__class__.__name__,
                'traceback': self.traceback
            })
            
        if self.data is not None:
            error_dict['data'] = self.data
            
        return error_dict


class BaseExceptionHandler:
    """基础异常处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def handle_exception(self, request: HttpRequest, exc: Exception) -> ApiResponse:
        """处理异常"""
        # 记录异常日志
        self._log_exception(request, exc)
        
        # 获取异常数据
        exc_data = self._get_exception_data(exc)
        
        # 发送告警通知
        self._send_alert(request, exc_data)
        
        # 返回错误响应
        return error_response(
            message=exc_data.message,
            code=exc_data.code,
            data=exc_data.data,
            status_code=exc_data.status_code
        )

    def _log_exception(self, request: HttpRequest, exc: Exception) -> None:
        """记录异常日志"""
        log_data = {
            'exception': exc.__class__.__name__,
            'message': str(exc),
            'path': request.path,
            'method': request.method,
            'user': request.user.username if request.user.is_authenticated else 'anonymous',
            'ip': request.META.get('REMOTE_ADDR'),
            'data': {
                'GET': dict(request.GET),
                'POST': dict(request.POST),
                'FILES': dict(request.FILES)
            }
        }
        
        if isinstance(exc, (BusinessError, ValidationError)):
            self.logger.warning(f"业务异常: {log_data}")
        else:
            self.logger.error(f"系统异常: {log_data}", exc_info=True)

    def _get_exception_data(self, exc: Exception) -> ExceptionData:
        """获取异常数据"""
        if isinstance(exc, BusinessError):
            return ExceptionData(
                exc=exc,
                status_code=exc.status_code,
                code=exc.error_code.code,
                message=exc.message,
                data=exc.data
            )
            
        if isinstance(exc, ValidationError):
            return ExceptionData(
                exc=exc,
                status_code=status.HTTP_400_BAD_REQUEST,
                code=ErrorCode.PARAM_ERROR.code,
                message=_("参数验证错误"),
                data=exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )
            
        if isinstance(exc, PermissionDenied):
            return ExceptionData(
                exc=exc,
                status_code=status.HTTP_403_FORBIDDEN,
                code=ErrorCode.PERMISSION_DENIED.code,
                message=_("权限不足")
            )
            
        if isinstance(exc, Http404):
            return ExceptionData(
                exc=exc,
                status_code=status.HTTP_404_NOT_FOUND,
                code=ErrorCode.RESOURCE_NOT_FOUND.code,
                message=_("资源不存在")
            )
            
        if isinstance(exc, DatabaseError):
            return ExceptionData(
                exc=exc,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                code=ErrorCode.DB_ERROR.code,
                message=_("数据库错误")
            )
            
        # 默认系统错误
        return ExceptionData(exc=exc)

    def _send_alert(self, request: HttpRequest, exc_data: ExceptionData) -> None:
        """发送告警通知"""
        if not settings.DEBUG and exc_data.status_code >= 500:
            alert_data = {
                'system': settings.SYSTEM_NAME,
                'environment': settings.ENVIRONMENT,
                'exception': exc_data.exc.__class__.__name__,
                'message': exc_data.message,
                'path': request.path,
                'timestamp': exc_data.timestamp,
                'traceback': exc_data.traceback
            }
            
            # TODO: 实现告警通知（邮件、钉钉、企业微信等）
            pass


class DRFExceptionHandler(BaseExceptionHandler):
    """DRF异常处理器"""
    
    def __call__(self, exc: Exception, context: dict) -> ApiResponse:
        """处理DRF异常"""
        # 获取请求对象
        request = context.get('request')
        
        # 如果是APIException，使用DRF的异常处理
        if isinstance(exc, APIException):
            response = exception_handler(exc, context)
            if response is not None:
                return error_response(
                    message=self._get_error_message(response),
                    code=response.status_code,
                    status_code=response.status_code
                )
                
        # 使用基础异常处理
        return self.handle_exception(request, exc)

    def _get_error_message(self, response: Response) -> str:
        """获取错误消息"""
        if hasattr(response, 'data'):
            if isinstance(response.data, dict):
                return response.data.get('detail', str(response.data))
            if isinstance(response.data, list):
                return response.data[0] if response.data else _("未知错误")
            return str(response.data)
        return _("未知错误")


class AsyncExceptionHandler(BaseExceptionHandler):
    """异步异常处理器"""
    
    async def handle_exception(self, request: HttpRequest, exc: Exception) -> ApiResponse:
        """处理异常"""
        # 异步记录日志
        await self._async_log_exception(request, exc)
        
        # 获取异常数据
        exc_data = self._get_exception_data(exc)
        
        # 异步发送告警
        await self._async_send_alert(request, exc_data)
        
        # 返回错误响应
        return error_response(
            message=exc_data.message,
            code=exc_data.code,
            data=exc_data.data,
            status_code=exc_data.status_code
        )

    async def _async_log_exception(self, request: HttpRequest, exc: Exception) -> None:
        """异步记录异常日志"""
        # TODO: 实现异步日志记录
        pass

    async def _async_send_alert(self, request: HttpRequest, exc_data: ExceptionData) -> None:
        """异步发送告警通知"""
        # TODO: 实现异步告警通知
        pass


# 创建异常处理器实例
drf_exception_handler = DRFExceptionHandler()
async_exception_handler = AsyncExceptionHandler()


def handle_exception(func: Callable) -> Callable:
    """异常处理装饰器"""
    @wraps(func)
    def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
        try:
            return func(request, *args, **kwargs)
        except Exception as exc:
            return drf_exception_handler.handle_exception(request, exc)
    return wrapper


def handle_async_exception(func: Callable) -> Callable:
    """异步异常处理装饰器"""
    @wraps(func)
    async def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
        try:
            return await func(request, *args, **kwargs)
        except Exception as exc:
            return await async_exception_handler.handle_exception(request, exc)
    return wrapper
