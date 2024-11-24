import os
import sys

from typing import List

from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient


class Sample:
    def __init__(self):
        pass

    @staticmethod
    def create_client() -> OpenApiClient:
        """
        使用AK&SK初始化账号Client
        @return: Client
        @throws Exception
        """
        # 工程代码泄露可能会导致 AccessKey 泄露，并威胁账号下所有资源的安全性。以下代码示例仅供参考。
        # 建议使用更安全的 STS 方式，更多鉴权访问方式请参见：https://help.aliyun.com/document_detail/378659.html。
        config = open_api_models.Config(
            # 必填，请确保代码运行环境设置了环境变量 ALIBABA_CLOUD_ACCESS_KEY_ID。,
            access_key_id=os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
            # 必填，请确保代码运行环境设置了环境变量 ALIBABA_CLOUD_ACCESS_KEY_SECRET。,
            access_key_secret=os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"],
        )
        # Endpoint 请参考 https://api.aliyun.com/product/Dysmsapi
        config.endpoint = f"dysmsapi.aliyuncs.com"
        return OpenApiClient(config)

    @staticmethod
    def create_api_info() -> open_api_models.Params:
        """
        API 相关
        @param path: string Path parameters
        @return: OpenApi.Params
        """
        params = open_api_models.Params(
            # 接口名称,
            action="SendSms",
            # 接口版本,
            version="2017-05-25",
            # 接口协议,
            protocol="HTTPS",
            # 接口 HTTP 方法,
            method="POST",
            auth_type="AK",
            style="RPC",
            # 接口 PATH,
            pathname=f"/",
            # 接口请求体内容格式,
            req_body_type="json",
            # 接口响应体内容格式,
            body_type="json",
        )
        return params

    @staticmethod
    def main(
        args: List[str],
    ) -> None:
        client = Sample.create_client()
        params = Sample.create_api_info()
        # query params
        queries = {}
        queries["PhoneNumbers"] = "18895358393"
        queries["SignName"] = "阿里云短信测试"
        queries["TemplateCode"] = "SMS_154950909"
        queries["TemplateParam"] = '{"code":"1234"}'
        # runtime options
        runtime = util_models.RuntimeOptions()
        request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
        # 复制代码运行请自行打印 API 的返回值
        # 返回值实际为 Map 类型，可从 Map 中获得三类数据：响应体 body、响应头 headers、HTTP 返回的状态码 statusCode。
        client.call_api(params, request, runtime)

    @staticmethod
    async def main_async(
        args: List[str],
    ) -> None:
        client = Sample.create_client()
        params = Sample.create_api_info()
        # query params
        queries = {}
        queries["PhoneNumbers"] = "18895358393"
        queries["SignName"] = "阿里云短信测试"
        queries["TemplateCode"] = "SMS_154950909"
        queries["TemplateParam"] = '{"code":"1234"}'
        # runtime options
        runtime = util_models.RuntimeOptions()
        request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
        # 复制代码运行请自行打印 API 的返回值
        # 返回值实际为 Map 类型，可从 Map 中获得三类数据：响应体 body、响应头 headers、HTTP 返回的状态码 statusCode。
        await client.call_api_async(params, request, runtime)


if __name__ == "__main__":
    Sample.main(sys.argv[1:])
