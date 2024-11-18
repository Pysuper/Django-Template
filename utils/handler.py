import traceback
from typing import Any, Dict, Optional

from rest_framework.response import Response
from rest_framework.views import exception_handler

from utils.error import ErrorCode, ParamError, CustomExceptionError
from utils.exception import *
from utils.log.logger import logger
from utils.response import pysuper_response


# 带日志记录的异常处理装饰器
def exception_handler_with_logging(func):
    def decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.info(f"---服务器错误: {str(e)}")  # 记录服务器错误信息
            # 处理异常的逻辑，可以使用日志记录错误信息等
            # if settings.IS_SEND_DINGDING:
            #     send_dingding(f"{settings.SYSTEM_ORDER_MARK} 服务器错误: {str(e)}")
            raise ParamError(ErrorCode.PARAM_ERROR)  # 抛出参数错误异常

    return decorator


# 异常拦截器装饰器，用于拦截视图中的异常并记录日志
def view_exception_handler(view_func):
    def decorator(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"---服务器错误: {str(e)}")
            # 这里可以发送通知或记录错误日志
            # if settings.IS_SEND_DINGDING:
            #     send_dingding(f"{settings.SYSTEM_ORDER_MARK} 服务器错误: {str(e)}")
            raise ParamError(ErrorCode.PARAM_ERROR)  # 抛出参数错误异常

    return decorator


# 自定义异常处理器，用于格式化错误响应
def pysuper_ex_handler(exception: Exception, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    自定义异常处理器，用于格式化错误响应。

    :param exception: 引发的异常
    :param context: 上下文信息
    :return: 格式化的响应数据或 None
    """
    response = exception_handler(exception, context)

    # 如果响应存在，则格式化
    return response and pysuper_response(response)


# # 自定义异常处理器，用于处理特定异常并返回标准化的错误响应
# def custom_exception_handler(exc, context):
#     """自定义异常处理器，用于处理特定异常并返回标准化的错误响应"""
#     response = exception_handler(exc, context)
#
#     # 如果异常已由 DRF 默认处理，则直接返回
#     if response is not None:
#         return response
#
#     handler = GlobalExceptionHandler()
#
#     # 根据异常类型调用对应的处理方法
#     if isinstance(exc, BadCredentialsException):
#         return handler.handle_bad_credentials(context["request"], exc)
#     elif isinstance(exc, BadRequestException):
#         return handler.handle_bad_request(context["request"], exc)
#     elif isinstance(exc, EntityExistException):
#         return handler.handle_entity_exist(context["request"], exc)
#     elif isinstance(exc, EntityNotFoundException):
#         return handler.handle_entity_not_found(context["request"], exc)
#     elif isinstance(exc, ValidationError):
#         return handler.handle_validation_error(context["request"], exc)
#     return handler.handle_exception(context["request"], exc)


def custom_exception_handler(exc, context):
    """
    自定义异常处理器
    :param exc: 异常对象
    :param context: 上下文信息
    :return: Response对象
    """
    # 获取DRF默认的异常处理响应
    response = exception_handler(exc, context)

    # TODO：根据实际情况，自定义统一的响应格式
    def format_response(code, message, data=None):
        return Response({"code": code, "message": message, "data": data}, status=code)

    if response is not None:
        # 处理已知异常
        if isinstance(exc, CustomExceptionError):
            return format_response(code=exc.status_code, message=str(exc))

        # 根据异常类型调用对应的处理方法
        for exc_type, handler_method in exception_handlers.items():
            if isinstance(exc, exc_type):
                return handler_method(context["request"], exc)

        # 处理DRF内置异常
        error_code = response.status_code
        error_msg = response.data.get("detail", "未知错误")

        # 定义状态码与错误消息的映射
        status_messages = {
            400: "请求参数错误",
            401: "认证失败",
            403: "权限不足",
            404: "资源不存在",
            405: "请求方法不允许",
            500: "服务器内部错误",
            502: "网关错误",
            503: "服务不可用",
            504: "网关超时",
        }

        if error_code in status_messages:
            error_msg = status_messages[error_code]

        return format_response(
            code=error_code, message=error_msg, data=response.data if hasattr(response, "data") else None
        )

    # 处理未知异常
    logger.error(f"未知异常: {exc}")
    logger.error(traceback.format_exc())
    return format_response(code=500, message=str(exc) or "服务器内部错误")
