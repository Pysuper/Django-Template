from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from django.db.models import Model
from django.http import FileResponse, StreamingHttpResponse
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.serializers import Serializer


class ResponseCode(Enum):
    """响应状态码枚举"""

    SUCCESS = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    INTERNAL_ERROR = 500
    SERVICE_UNAVAILABLE = 503


class ApiResponse(Response):
    """
    统一API响应格式
    支持更多数据类型和更灵活的响应格式
    """

    def __init__(
        self,
        data: Any = None,
        message: str = None,
        code: int = ResponseCode.SUCCESS.value,
        status_code: int = None,
        headers: dict = None,
        exception: bool = False,
        **kwargs,
    ):
        """
        初始化API响应
        :param data: 响应数据
        :param message: 响应消息
        :param code: 业务状态码
        :param status_code: HTTP状态码
        :param headers: 响应头
        :param exception: 是否异常响应
        :param kwargs: 其他参数
        """
        # 处理响应数据
        response_data = self._process_response_data(data, message, code, **kwargs)

        # 设置HTTP状态码
        if status_code is None:
            status_code = code if 100 <= code < 600 else status.HTTP_200_OK

        super().__init__(data=response_data, status=status_code, headers=headers)
        self.exception = exception

    def _process_response_data(self, data: Any, message: str, code: int, **kwargs) -> dict:
        """处理响应数据"""
        # 基础响应结构
        response = {
            "code": code,
            "message": message or self._get_default_message(code),
            "data": self._serialize_data(data),
        }

        # 处理分页数据
        if "paginator" in kwargs and kwargs["paginator"] is not None:
            paginator = kwargs["paginator"]
            response["data"] = {
                "list": response["data"],
                "pagination": {
                    "current": paginator.page.number,
                    "size": paginator.page.paginator.per_page,
                    "total": paginator.page.paginator.count,
                    "pages": paginator.page.paginator.num_pages,
                },
            }

        # 添加其他元数据
        if "meta" in kwargs:
            response["meta"] = kwargs["meta"]

        return response

    def _serialize_data(self, data: Any) -> Any:
        """序列化数据"""
        if data is None:
            return None

        if isinstance(data, (str, int, float, bool)):
            return data

        if isinstance(data, (datetime, date, time, Decimal, UUID)):
            return str(data)

        if isinstance(data, Enum):
            return data.value

        if isinstance(data, (list, tuple, set)):
            return [self._serialize_data(item) for item in data]

        if isinstance(data, dict):
            return {key: self._serialize_data(value) for key, value in data.items()}

        if isinstance(data, Model):
            return self._serialize_model(data)

        if isinstance(data, Serializer):
            return data.data

        return data

    def _serialize_model(self, instance: Model) -> dict:
        """序列化模型实例"""
        if hasattr(instance, "to_dict"):
            return instance.to_dict()

        return {field.name: self._serialize_data(getattr(instance, field.name)) for field in instance._meta.fields}

    def _get_default_message(self, code: int) -> str:
        """获取默认消息"""
        messages = {
            ResponseCode.SUCCESS.value: "操作成功",
            ResponseCode.CREATED.value: "创建成功",
            ResponseCode.ACCEPTED.value: "请求已受理",
            ResponseCode.NO_CONTENT.value: "无内容",
            ResponseCode.BAD_REQUEST.value: "请求参数错误",
            ResponseCode.UNAUTHORIZED.value: "未授权",
            ResponseCode.FORBIDDEN.value: "禁止访问",
            ResponseCode.NOT_FOUND.value: "资源不存在",
            ResponseCode.METHOD_NOT_ALLOWED.value: "方法不允许",
            ResponseCode.CONFLICT.value: "资源冲突",
            ResponseCode.INTERNAL_ERROR.value: "服务器内部错误",
            ResponseCode.SERVICE_UNAVAILABLE.value: "服务不可用",
        }
        return messages.get(code, "未知状态")


class ApiJsonRenderer(JSONRenderer):
    """
    自定义JSON渲染器
    支持更多数据类型的序列化
    """

    def render(
        self,
        data: Any,
        accepted_media_type: str = None,
        renderer_context: dict = None,
    ) -> bytes:
        """
        渲染响应数据为JSON
        :param data: 响应数据
        :param accepted_media_type: 接受的媒体类型
        :param renderer_context: 渲染上下文
        :return: JSON字节串
        """
        if renderer_context is None:
            renderer_context = {}

        # 获取响应对象
        response = renderer_context.get("response")

        if response is not None:
            if not isinstance(data, dict):
                data = {"data": data}

            # 如果状态码大于等于400，处理错误信息
            if response.status_code >= 400:
                data = {
                    "code": response.status_code,
                    "message": data.get("detail", "请求处理失败"),
                    "errors": data if "detail" not in data else None,
                }

        return super().render(data, accepted_media_type, renderer_context)


def success_response(
    data: Any = None,
    message: str = "操作成功",
    code: int = ResponseCode.SUCCESS.value,
    **kwargs,
) -> ApiResponse:
    """
    成功响应
    :param data: 响应数据
    :param message: 响应消息
    :param code: 状态码
    :param kwargs: 其他参数
    :return: ApiResponse
    """
    return ApiResponse(data=data, message=message, code=code, **kwargs)


def error_response(
    message: str = "操作失败",
    code: int = ResponseCode.BAD_REQUEST.value,
    data: Any = None,
    **kwargs,
) -> ApiResponse:
    """
    错误响应
    :param message: 错误消息
    :param code: 错误码
    :param data: 错误数据
    :param kwargs: 其他参数
    :return: ApiResponse
    """
    return ApiResponse(data=data, message=message, code=code, **kwargs)


def file_response(
    file_path: str,
    filename: str = None,
    content_type: str = None,
    as_attachment: bool = True,
) -> FileResponse:
    """
    文件响应
    :param file_path: 文件路径
    :param filename: 文件名
    :param content_type: 内容类型
    :param as_attachment: 是否作为附件下载
    :return: FileResponse
    """
    response = FileResponse(open(file_path, "rb"), content_type=content_type)
    if filename and as_attachment:
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def stream_response(
    streaming_content: Any,
    content_type: str = None,
    filename: str = None,
    as_attachment: bool = True,
) -> StreamingHttpResponse:
    """
    流式响应
    :param streaming_content: 流式内容
    :param content_type: 内容类型
    :param filename: 文件名
    :param as_attachment: 是否作为附件下载
    :return: StreamingHttpResponse
    """
    response = StreamingHttpResponse(streaming_content, content_type=content_type)
    if filename and as_attachment:
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
