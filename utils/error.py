from rest_framework import status
from rest_framework.exceptions import APIException


# 自定义异常
class CustomExceptionError(APIException):
    pass


class Success(CustomExceptionError):
    status_code = 200
    default_detail = "请求成功"


class Created(CustomExceptionError):
    status_code = 201
    default_detail = "资源已创建"


class NoContent(CustomExceptionError):
    status_code = 204
    default_detail = "无内容"


class ParamError(CustomExceptionError):
    status_code = 400
    default_detail = "请求无效，可能是参数错误"


class Unauthorized(CustomExceptionError):
    status_code = 401
    default_detail = "未经授权，请重新登录"


class PermissionDenied(CustomExceptionError):
    status_code = 403
    default_detail = "拒绝访问，权限不足"


class ObjectNotFound(CustomExceptionError):
    status_code = 404
    default_detail = "请求的资源不存在"


class ServerError(CustomExceptionError):
    status_code = 500
    default_detail = "服务器内部错误"


class GatewayError(CustomExceptionError):
    status_code = 502
    default_detail = "网关错误"


class ServiceUnavailable(CustomExceptionError):
    status_code = 503
    default_detail = "服务不可用，服务器暂时过载或维护中"


class GatewayTimeout(CustomExceptionError):
    status_code = 504
    default_detail = "网关超时"


class SerializerError(CustomExceptionError):
    status_code = 400
    default_detail = "序列化错误"


class ErrorCode:
    """
    自定义 HTTP 状态码和错误码
    """

    # 认证相关 (10000-10999)
    # UNAUTHORIZED = 10000  # 未登录
    PERMISSION_DENIED = 10001  # 无权限
    TOKEN_EXPIRED = 10002  # Token过期
    TOKEN_INVALID = 10003  # Token无效

    # 参数相关 (40000-40999)
    PARAM_ERROR = 40000  # 参数验证错误
    DATA_NOT_FOUND = 40001  # 未找到数据
    DATA_NOT_VALID = 40002  # 数据错误
    REPEAT_POST = 40003  # 重复提交
    PARAM_MISSING = 40004  # 缺少必要参数
    PARAM_FORMAT_ERROR = 40005  # 参数格式错误

    # 业务相关 (50000-50999)
    BUSINESS_ERROR = 50000  # 业务处理失败
    RESOURCE_NOT_FOUND = 50001  # 资源不存在
    RESOURCE_ALREADY_EXIST = 50002  # 资源已存在
    OPERATION_FAILED = 50003  # 操作失败

    # 系统相关 (60000-60999)
    SYSTEM_ERROR = 60000  # 系统错误
    # SERVICE_UNAVAILABLE = 60001  # 服务不可用
    THIRD_PARTY_ERROR = 60002  # 第三方服务错误
    DATABASE_ERROR = 60003  # 数据库错误
    CACHE_ERROR = 60004  # 缓存错误

    OK = status.HTTP_200_OK  # 请求成功
    CREATED = status.HTTP_201_CREATED  # 资源创建成功
    ACCEPTED = status.HTTP_202_ACCEPTED  # 请求已接受，但尚未处理完成
    NO_CONTENT = status.HTTP_204_NO_CONTENT  # 请求成功但无内容返回
    RESET_CONTENT = status.HTTP_205_RESET_CONTENT  # 请求成功，重置视图内容
    PARTIAL_CONTENT = status.HTTP_206_PARTIAL_CONTENT  # 请求部分内容成功

    # 重定向状态码
    MOVED_PERMANENTLY = status.HTTP_301_MOVED_PERMANENTLY  # 资源已永久转移
    FOUND = status.HTTP_302_FOUND  # 资源已临时转移
    SEE_OTHER = status.HTTP_303_SEE_OTHER  # 请使用 GET 方法获取资源
    NOT_MODIFIED = status.HTTP_304_NOT_MODIFIED  # 资源未被修改
    TEMPORARY_REDIRECT = status.HTTP_307_TEMPORARY_REDIRECT  # 临时重定向
    PERMANENT_REDIRECT = status.HTTP_308_PERMANENT_REDIRECT  # 永久重定向

    # 客户端错误状态码
    BAD_REQUEST = status.HTTP_400_BAD_REQUEST  # 请求格式错误
    UNAUTHORIZED = status.HTTP_401_UNAUTHORIZED  # 未认证
    FORBIDDEN = status.HTTP_403_FORBIDDEN  # 无权限
    NOT_FOUND = status.HTTP_404_NOT_FOUND  # 资源未找到
    METHOD_NOT_ALLOWED = status.HTTP_405_METHOD_NOT_ALLOWED  # 请求方法不被允许
    NOT_ACCEPTABLE = status.HTTP_406_NOT_ACCEPTABLE  # 请求内容不可接受
    REQUEST_TIMEOUT = status.HTTP_408_REQUEST_TIMEOUT  # 请求超时
    CONFLICT = status.HTTP_409_CONFLICT  # 请求冲突，例如重复数据
    GONE = status.HTTP_410_GONE  # 资源永久删除
    LENGTH_REQUIRED = status.HTTP_411_LENGTH_REQUIRED  # 需要指定 Content-Length
    PRECONDITION_FAILED = status.HTTP_412_PRECONDITION_FAILED  # 前提条件未满足
    PAYLOAD_TOO_LARGE = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE  # 请求实体过大
    URI_TOO_LONG = status.HTTP_414_REQUEST_URI_TOO_LONG  # URI 过长
    UNSUPPORTED_MEDIA_TYPE = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE  # 不支持的媒体类型
    TOO_MANY_REQUESTS = status.HTTP_429_TOO_MANY_REQUESTS  # 请求过多

    # 服务器错误状态码
    INTERNAL_SERVER_ERROR = status.HTTP_500_INTERNAL_SERVER_ERROR  # 服务器内部错误
    NOT_IMPLEMENTED = status.HTTP_501_NOT_IMPLEMENTED  # 服务器未实现请求功能
    BAD_GATEWAY = status.HTTP_502_BAD_GATEWAY  # 网关错误
    SERVICE_UNAVAILABLE = status.HTTP_503_SERVICE_UNAVAILABLE  # 服务不可用
    GATEWAY_TIMEOUT = status.HTTP_504_GATEWAY_TIMEOUT  # 网关超时
    HTTP_VERSION_NOT_SUPPORTED = status.HTTP_505_HTTP_VERSION_NOT_SUPPORTED  # 不支持的 HTTP 版本
