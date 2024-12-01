# -*- coding: utf-8 -*-
import sys
from typing import List

from alibabacloud_dysmsapi20170525 import models
from alibabacloud_dysmsapi20170525.client import Client
from alibabacloud_tea_openapi import models as openapi_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
from django.conf import settings
from django.core.cache import cache

from utils.error import Created
from utils.other.tools import code_number

# 有时间可以优化一下，把参数和配置分离，不用写在代码里


class AliSmsParams:
    """
    阿里云 SMS API 参数
    https://dysms.console.aliyun.com/domestic/text
    """

    ACCESS_KEY_ID = settings.ALI_SMS_ACCESS_KEY_ID
    ACCESS_KEY_SECRET = settings.ALI_SMS_ACCESS_KEY_SECRET
    REGION_ID = settings.ALI_SMS_REGION_ID
    ENDPOINT = settings.ALI_SMS_ENDPOINT
    SIGN_NAME = settings.ALI_SMS_SIGN_NAME
    TEMPLATE_CODE = settings.ALI_SMS_TEMPLATE_CODE
    # 上面几个参数都是固定的，可以根据您的需求修改。
    PHONE_NUMBERS = "12345678901"
    # TEMPLATE_PARAM = '{"code":"1234", "time":"3"}'


class AliYunSMS:
    """
    使用阿里云 SMS API 发送短信
    https://next.api.aliyun.com/api/Dysmsapi/2017-05-25/SendSms?RegionId=cn-hangzhou
    """

    def __init__(self):
        pass

    @staticmethod
    def create_client() -> Client:
        """
        使用AccessKey初始化账号Client
        @return: Client
        @throws Exception
        """
        config = openapi_models.Config(
            access_key_id=AliSmsParams.ACCESS_KEY_ID,
            access_key_secret=AliSmsParams.ACCESS_KEY_SECRET,
        )
        config.endpoint = AliSmsParams.ENDPOINT
        return Client(config)

    @staticmethod
    def main(args: List[str], code: str, time: str) -> None:
        client = AliYunSMS.create_client()
        send_sms_request = models.SendSmsRequest(
            sign_name=AliSmsParams.SIGN_NAME,
            template_code=AliSmsParams.TEMPLATE_CODE,
            phone_numbers=AliSmsParams.PHONE_NUMBERS,
            template_param=f'{{"code":"{code}", "time":"{time}"}}',
        )
        runtime = util_models.RuntimeOptions()
        try:
            response = client.send_sms_with_options(send_sms_request, runtime)
            # pprint(response.__dict__)
            # pprint(response.body.__dict__)
            if response.body.message != "OK":
                print("短信发送失败")
        except Exception as error:
            print(error.message)
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)

    @staticmethod
    async def main_async(args: List[str], code: str, time: str) -> None:
        client = AliYunSMS.create_client()
        send_sms_request = models.SendSmsRequest(
            sign_name=AliSmsParams.SIGN_NAME,
            template_code=AliSmsParams.TEMPLATE_CODE,
            phone_numbers=AliSmsParams.PHONE_NUMBERS,
            template_param=f'{{"code":"{code}", "time":"{time}"}}',
        )
        runtime = util_models.RuntimeOptions()
        try:
            await client.send_sms_with_options_async(send_sms_request, runtime)
        except Exception as error:
            print(error.message)
            print(error.data.get("Recommend"))
            UtilClient.assert_as_string(error.message)


class SendSms:
    """
    发送短信
    """

    sms_key = settings.SMS_CODE_KEY
    sms_cache_key = "SmsCode_"
    expire = settings.SMS_CODE_EXPIRE  # 验证码过期时间

    def __init__(self):
        pass

    def check_code(self, verify_code: str, phone: str) -> bool:
        """
        短信验证码校验
        :param verify_code: 短信验证码
        :param phone: 手机号
        :return: bool
        """
        # 获取redis中的验证码
        code = cache.get(self.sms_cache_key + phone)
        # 比对验证码
        if code and verify_code == code:
            cache.delete(self.sms_cache_key + phone)
            return True
        # 获取缓存中验证码
        return False

    def send_code(self, phone: str) -> None:
        """
        发送短信验证码，对是否发送的校验在这之前处理
        :param phone:
        :return:
        """
        # 查询是否发送过验证码
        is_send = cache.get(self.sms_cache_key)
        if is_send:
            raise Created(f"手机号 {phone} 已发送过验证码，若未收到短信，请{self.expire}分钟后重试!")

        # 生成验证码
        code = code_number(6)
        # 发送验证码
        AliYunSMS.main(sys.argv[1:], code, "3")


# if __name__ == "__main__":
#     code = str(random.randint(100000, 999999))
#     time = "3"
#     AliYunSMS.main(sys.argv[1:], code, time)
