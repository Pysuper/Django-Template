from enum import Enum
from typing import Any, Dict, Optional

from rest_framework import status
from rest_framework.exceptions import APIException


class ErrorLevel(Enum):
    """错误级别枚举"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCode(Enum):
    """错误码枚举"""

    # 成功响应 (2xx)
    SUCCESS = (200, "成功")
    CREATED = (201, "已创建")
    ACCEPTED = (202, "已接受")
    NO_CONTENT = (204, "无内容")

    # 认证和权限 (10xxx)
    UNAUTHORIZED = (10001, "未经授权")
    TOKEN_EXPIRED = (10002, "Token已过期")
    TOKEN_INVALID = (10003, "Token无效")
    PERMISSION_DENIED = (10004, "权限不足")
    LOGIN_REQUIRED = (10005, "需要登录")
    ACCOUNT_DISABLED = (10006, "账号已禁用")
    ACCOUNT_LOCKED = (10007, "账号已锁定")

    # 参数验证 (20xxx)
    PARAM_ERROR = (20001, "参数错误")
    PARAM_MISSING = (20002, "缺少必要参数")
    PARAM_FORMAT = (20003, "参数格式错误")
    PARAM_VALUE = (20004, "参数值错误")
    PARAM_TYPE = (20005, "参数类型错误")

    # 业务逻辑 (30xxx)
    RESOURCE_NOT_FOUND = (30001, "资源不存在")
    RESOURCE_ALREADY_EXISTS = (30002, "资源已存在")
    RESOURCE_EXPIRED = (30003, "资源已过期")
    OPERATION_FAILED = (30004, "操作失败")
    STATUS_ERROR = (30005, "状态错误")

    # 数据库相关 (40xxx)
    DB_ERROR = (40001, "数据库错误")
    DB_CONNECTION_ERROR = (40002, "数据库连接错误")
    DB_DUPLICATE_KEY = (40003, "数据重复")
    DB_INTEGRITY_ERROR = (40004, "数据完整性错误")
    DB_TRANSACTION_ERROR = (40005, "事务处理错误")

    # 第三方服务 (50xxx)
    THIRD_PARTY_ERROR = (50001, "第三方服务错误")
    API_REQUEST_ERROR = (50002, "API请求错误")
    REMOTE_SERVICE_ERROR = (50003, "远程服务错误")
    TIMEOUT_ERROR = (50004, "请求超时")

    # 系统错误 (60xxx)
    SYSTEM_ERROR = (60001, "系统错误")
    CONFIG_ERROR = (60002, "配置错误")
    NETWORK_ERROR = (60003, "网络错误")
    FILE_ERROR = (60004, "文件处理错误")
    CACHE_ERROR = (60005, "缓存错误")

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class BaseError(APIException):
    """基础错误类"""

    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        data: Any = None,
        level: ErrorLevel = ErrorLevel.ERROR,
        status_code: Optional[int] = None,
        **kwargs,
    ):
        """
        初始化错误对象
        :param error_code: 错误码枚举
        :param message: 自定义错误消息
        :param data: 额外数据
        :param level: 错误级别
        :param status_code: HTTP状态码
        :param kwargs: 其他参数
        """
        self.error_code = error_code
        self.message = message or error_code.message
        self.data = data
        self.level = level
        self.status_code = status_code or self._get_status_code()
        self.kwargs = kwargs

        super().__init__(detail=self.to_dict())

    def _get_status_code(self) -> int:
        """获取HTTP状态码"""
        code = self.error_code.code
        if code >= 60000:
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        elif code >= 50000:
            return status.HTTP_502_BAD_GATEWAY
        elif code >= 40000:
            return status.HTTP_500_INTERNAL_SERVER_ERROR
        elif code >= 30000:
            return status.HTTP_400_BAD_REQUEST
        elif code >= 20000:
            return status.HTTP_400_BAD_REQUEST
        elif code >= 10000:
            return status.HTTP_401_UNAUTHORIZED
        return status.HTTP_400_BAD_REQUEST

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        error_dict = {
            "code": self.error_code.code,
            "message": self.message,
            "level": self.level.value,
        }

        if self.data is not None:
            error_dict["data"] = self.data

        if self.kwargs:
            error_dict.update(self.kwargs)

        return error_dict


# 认证相关错误
class AuthenticationError(BaseError):
    """认证相关错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.UNAUTHORIZED, **kwargs):
        super().__init__(error_code=error_code, level=ErrorLevel.WARNING, **kwargs)


class PermissionError(BaseError):
    """权限相关错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.PERMISSION_DENIED, **kwargs):
        super().__init__(error_code=error_code, level=ErrorLevel.WARNING, **kwargs)


# 参数相关错误
class ValidationError(BaseError):
    """参数验证错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.PARAM_ERROR, **kwargs):
        super().__init__(error_code=error_code, level=ErrorLevel.WARNING, **kwargs)


class ResourceError(BaseError):
    """资源相关错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND, **kwargs):
        super().__init__(error_code=error_code, level=ErrorLevel.WARNING, **kwargs)


# 业务相关错误
class BusinessError(BaseError):
    """业务逻辑错误"""

    def __init__(
        self,
        error_code: ErrorCode = ErrorCode.OPERATION_FAILED,
        **kwargs,
    ):
        super().__init__(error_code=error_code, level=ErrorLevel.ERROR, **kwargs)


# 系统相关错误
class SystemError(BaseError):
    """系统错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.SYSTEM_ERROR, **kwargs):
        super().__init__(error_code=error_code, level=ErrorLevel.CRITICAL, **kwargs)


class DatabaseError(BaseError):
    """数据库错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.DB_ERROR, **kwargs):
        super().__init__(error_code=error_code, level=ErrorLevel.CRITICAL, **kwargs)


class ThirdPartyError(BaseError):
    """第三方服务错误"""

    def __init__(self, error_code: ErrorCode = ErrorCode.THIRD_PARTY_ERROR, **kwargs):
        super().__init__(error_code=error_code, level=ErrorLevel.ERROR, **kwargs)


# 使用示例
"""
# 抛出认证错误
raise AuthenticationError(
    error_code=ErrorCode.TOKEN_EXPIRED,
    message="您的登录已过期，请重新登录",
    data={'expired_at': '2023-12-18 12:00:00'}
)

# 抛出参数验证错误
raise ValidationError(
    error_code=ErrorCode.PARAM_MISSING,
    message="缺少必要参数：user_id",
    data={'field': 'user_id'}
)

# 抛出业务错误
raise BusinessError(
    error_code=ErrorCode.OPERATION_FAILED,
    message="订单创建失败：库存不足",
    data={'product_id': 123, 'stock': 0}
)

# 抛出系统错误
raise SystemError(
    error_code=ErrorCode.SYSTEM_ERROR,
    message="系统内部错误",
    data={'trace_id': 'abc123'}
)
"""
