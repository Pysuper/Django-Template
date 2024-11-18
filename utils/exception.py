from datetime import datetime

from django.http.response import JsonResponse
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed

from utils.log.logger import logger


class ApiError:
    """API 错误类,用于统一处理API错误响应"""

    DEFAULT_STATUS = 400

    def __init__(self, status=DEFAULT_STATUS, message=None):
        """初始化API错误对象"""
        self.status = status
        self.timestamp = int(datetime.now().timestamp() * 1000)
        self.message = message or "未知错误"  # 提供默认错误信息

    @classmethod
    def error(cls, message):
        """使用默认状态码创建错误对象"""
        return cls(message=message)

    @classmethod
    def error_with_status(cls, status, message):
        """使用自定义状态码创建错误对象"""
        return cls(status=status, message=message)

    def to_dict(self):
        """将错误对象转换为字典格式"""
        return {"status": self.status, "message": self.message, "timestamp": self.timestamp}


class BadCredentialsException(AuthenticationFailed):
    """用户凭证无效异常"""

    def __init__(self, detail="用户名或密码不正确", code=None):
        super().__init__(detail, code)


class BadConfigurationException(RuntimeError):
    """统一关于错误配置信息的异常类"""

    def __init__(self, message=None, *args):
        """构造一个新的运行时异常，允许传入错误信息"""
        super().__init__(message, *args)


class BadRequestException(Exception):
    """统一异常处理"""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message  # 错误信息
        self.status_code = status_code  # 状态码
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} (状态码: {self.status_code})"  # 返回错误信息和状态码


class EntityExistException(Exception):
    """实体已存在异常"""

    def __init__(self, entity: str, field: str, value: str):
        """构造一个新的实体已存在异常，包含实体类、字段和对应值"""
        self.message = self.generate_message(entity, field, value)  # 生成异常消息
        super().__init__(self.message)

    @staticmethod
    def generate_message(entity: str, field: str, value: str) -> str:
        """生成异常消息"""
        return f"{entity} 的 {field} '{value}' 已存在"  # 返回实体已存在的消息


class EntityNotFoundException(Exception):
    """实体未找到异常"""

    def __init__(self, entity: str, field: str, value: str):
        """构造一个新的实体未找到异常，包含实体类、字段和对应值"""
        self.message = self.generate_message(entity, field, value)  # 生成异常消息
        super().__init__(self.message)

    @staticmethod
    def generate_message(entity: str, field: str, value: str) -> str:
        """生成异常消息"""
        return f"{entity} 的 {field} '{value}' 不存在"  # 返回实体未找到的消息


class ValidationErrorException(Exception):
    """数据验证错误异常"""

    def __init__(self, message: str):
        """构造一个新的数据验证错误异常"""
        self.message = message  # 错误信息
        super().__init__(self.message)

    def __str__(self):
        return f"验证错误: {self.message}"  # 返回验证错误信息


class UnauthorizedAccessException(Exception):
    """未授权访问异常"""

    def __init__(self, message: str = "未授权访问"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"未授权访问: {self.message}"


class ResourceConflictException(Exception):
    """资源冲突异常"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"资源冲突: {self.message}"


class InternalServerErrorException(Exception):
    """内部服务器错误异常"""

    def __init__(self, message: str = "内部服务器错误"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"内部服务器错误: {self.message}"


class TimeoutException(Exception):
    """请求超时异常"""

    def __init__(self, message: str = "请求超时"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"超时错误: {self.message}"


class ForbiddenException(Exception):
    """禁止访问异常"""

    def __init__(self, message: str = "禁止访问"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"禁止访问: {self.message}"


class NotImplementedException(Exception):
    """未实现异常"""

    def __init__(self, message: str = "功能未实现"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"未实现错误: {self.message}"


# 全局异常处理类
class GlobalExceptionHandler:
    """全局异常处理类"""

    def _create_json_response(self, api_error):
        """创建统一的 JSON 响应"""
        return JsonResponse(
            {
                "status": api_error.status,
                "message": api_error.message,
                "timestamp": api_error.timestamp,
            },
            status=api_error.status,
        )

    def _log_error(self, error, with_traceback=True):
        """统一的错误日志记录"""
        if with_traceback:
            logger.error(str(error), exc_info=True)
        else:
            logger.error(str(error))

    def handle_exception(self, request, e):
        """处理所有未知异常"""
        self._log_error(e)
        return self._create_json_response(ApiError.error(str(e)))

    def handle_bad_credentials(self, request, e):
        """处理认证凭证异常"""
        message = "用户名或密码不正确" if str(e) == "坏的凭证" else str(e)
        self._log_error(message, with_traceback=False)
        return self._create_json_response(ApiError.error(message))

    def handle_bad_request(self, request, e):
        """处理请求错误异常"""
        self._log_error(e)
        return self._create_json_response(ApiError.error_with_status(400, str(e)))

    def handle_entity_exist(self, request, e):
        """处理实体已存在异常"""
        self._log_error(e)
        return self._create_json_response(ApiError.error(str(e)))

    def handle_entity_not_found(self, request, e):
        """处理实体未找到异常"""
        self._log_error(e)
        return self._create_json_response(ApiError.error_with_status(404, str(e)))

    def handle_validation_error(self, request, e):
        """处理参数验证异常"""
        self._log_error(e)
        message = e.detail[0].get("message") if e.detail else "参数验证失败"
        return self._create_json_response(ApiError.error(message))


handler = GlobalExceptionHandler()

# 自定义异常处理映射
exception_handlers = {
    BadCredentialsException: handler.handle_bad_credentials,
    BadRequestException: handler.handle_bad_request,
    EntityExistException: handler.handle_entity_exist,
    EntityNotFoundException: handler.handle_entity_not_found,
    ValidationErrorException: handler.handle_validation_error,
    UnauthorizedAccessException: handler.handle_exception,
    ResourceConflictException: handler.handle_exception,
    InternalServerErrorException: handler.handle_exception,
    TimeoutException: handler.handle_exception,
    ForbiddenException: handler.handle_exception,
    NotImplementedException: handler.handle_exception,
}
