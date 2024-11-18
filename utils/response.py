import datetime
import decimal
import json
from typing import Any, Dict

from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.serializers import Serializer


def do_response(request, code, msg):
    """
    请求响应
    :param request:
    :param code:
    :param msg:
    :return:
    """
    request.data["code"] = code
    request.data["msg"] = msg
    return Response(data=request.data, status=status.HTTP_200_OK)


def success_response(request, msg):
    """
    请求成功响应
    :param request:
    :param msg:
    :return:
    """
    return do_response(request, 200, msg)


def fail_response(request, msg):
    """
    请求错误响应
    :param request:
    :param msg:
    :return:
    """
    return do_response(request, 400, msg)


def fail_500_response(request, msg):
    """
    请求500响应
    :param request:
    :param msg:
    :return:
    """
    request.data["msg"] = msg
    request.data["code"] = 500
    return Response(data=request.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def pysuper_response(response: Any) -> Dict[str, Any]:
    """
    格式化通知响应。

    :param response: 原始响应
    :return: 格式化后的响应数据
    """
    status_code = response.status_code
    msg = "成功" if status_code < 400 else "失败"

    return {
        "code": status_code,
        "message": msg,
        "detail": response.data,
    }


class BaseResponse(object):
    """
    封装的返回信息类
    """

    def __init__(self):
        self.code = 1000
        self.data = None
        self.error = None

    @property
    def dict(self):
        return self.__dict__


# 自定义响应类
class XopsResponse(Response):
    def __init__(self, data=None, message="success", code=status.HTTP_200_OK, **kwargs):
        # 构造标准响应格式
        response_data = {"code": code, "message": message, "data": data}
        # 调用父类构造函数
        super().__init__(data=response_data, status=code, **kwargs)


class JsonResult(Response):
    """
    自定义响应类 CustomJsonResponse，继承自 DRF 的 Response 类。
    该类用于统一 API 返回格式，包含 code（状态码）、message（消息）和 data（数据）。
    """

    def __init__(
        self,
        data=None,
        code=None,
        msg=None,
        status=None,
        headers=None,
        paginator=None,
        exception=False,
        content_type=None,
        template_name=None,
    ):
        """
        初始化方法，构造自定义 JSON 响应。

        :param data: 响应数据（通常是序列化后的数据）
        :param code: 自定义状态码
        :param msg: 自定义消息
        :param status: HTTP 状态码
        :param headers: HTTP 头部信息
        :param exception: 是否是异常响应
        :param content_type: 内容类型（通常为 application/json）
        """
        # 调用父类 Response 的构造函数
        super().__init__(None, status=status)

        # 检查传入的 data 是否为 Serializer 实例
        if isinstance(data, Serializer):
            raise AssertionError("Use `.data` or `.errors` instead of Serializer instance.")

        # TODO: 自定义ViewSet响应结构体
        self.template_name = template_name
        self.exception = exception
        self.content_type = content_type
        # 处理分页信息
        if paginator is not None:
            data = {
                "records": data,
                "current": paginator.page.number,
                "size": paginator.page.paginator.per_page,
                "total": paginator.page.paginator.count,
            }
        else:
            data = data

        # 设置响应数据
        self.data = {
            "code": status,
            "msg": msg if msg else "成功",
            "data": data,
        }
        # self.data = {
        #     "code": code,
        #     "msg": msg,
        #     "data": {
        #         "records": data,
        #         "current": 1,
        #         "size": 10,
        #         "total": len(data),
        #     },
        # }

        # 设置 HTTP 头部信息
        if headers:
            # 使用 update 方法添加头部信息
            self.headers.update(headers)


class YgJSONRenderer(JSONRenderer):
    """
    自行封装的渲染器
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        如果使用这个render，
        普通的response将会被包装成：
            {"code":200,"data":"X","error":"X"}
        这样的结果
        使用方法：
            - 全局
                REST_FRAMEWORK = {
                'DEFAULT_RENDERER_CLASSES': ('utils.yg_response.YgJSONRenderer', ),
                }
            - 局部
                class UserCountView(APIView):
                    renderer_classes = [YgJSONRenderer]

        :param data: {"detail":"X"}
        :param accepted_media_type:
        :param renderer_context:
        :return: {"code":200,"data":"X","error":"X"}
        """
        response_body = BaseResponse()
        response_body.code = renderer_context.get("response").status_code

        if response_body.code >= 400:
            response_body.error = data.get("detail", {"detail": "没有具体的提示信息"})
        else:
            response_body.data = data

        return super(YgJSONRenderer, self).render(response_body.dict, accepted_media_type, renderer_context)


class DecimalEncoder(json.JSONEncoder):
    """
    json序列化 Decimal 转string
    """

    def default(self, o):
        """

        :param o:
        :return:
        """
        if isinstance(o, decimal.Decimal):
            return str(o)
        elif isinstance(o, datetime.datetime):
            return str(o)
        elif isinstance(o, datetime.date):
            return str(o)

        super(DecimalEncoder, self).default(o)
