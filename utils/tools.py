import base64
import random
from enum import Enum
from io import BytesIO
from typing import List

from PIL import Image, ImageDraw, ImageFont
from captcha.image import ImageCaptcha
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

# 导入配置参数
from config.settings.base import (
    JWT_AUTH_HEADER_PREFIX,
    LOGIN_CODE_FONT_NAME,
    LOGIN_CODE_FONT_SIZE,
    LOGIN_CODE_HEIGHT,
    LOGIN_CODE_LENGTH,
    LOGIN_CODE_TYPE,
    LOGIN_CODE_WIDTH,
)


class CodeBiEnum(Enum):
    """验证码业务场景枚举"""

    ONE = (1, "旧邮箱修改邮箱")  # 旧邮箱修改邮箱
    TWO = (2, "通过邮箱修改密码")  # 通过邮箱修改密码

    def __init__(self, code: int, description: str):
        self._value_ = code
        self.description = description

    @classmethod
    def find(cls, code: int):
        """根据代码查找对应的枚举"""
        return next((value for value in cls if value.value == code), None)


class CodeEnum(Enum):
    """验证码业务场景对应的Redis键名枚举"""

    PHONE_RESET_EMAIL_CODE = ("phone_reset_email_code_", "通过手机号码重置邮箱")
    EMAIL_RESET_EMAIL_CODE = ("email_reset_email_code_", "通过旧邮箱重置邮箱")
    PHONE_RESET_PWD_CODE = ("phone_reset_pwd_code_", "通过手机号码重置密码")
    EMAIL_RESET_PWD_CODE = ("email_reset_pwd_code_", "通过邮箱重置密码")

    def __init__(self, key: str, description: str):
        self._value_ = key
        self.description = description


class DataScopeEnum(Enum):
    """数据权限范围枚举"""

    ALL = ("全部", "全部的数据权限")  # 全部数据权限
    THIS_LEVEL = ("本级", "自己部门的数据权限")  # 本部门数据权限
    CUSTOMIZE = ("自定义", "自定义的数据权限")  # 自定义数据权限

    def __init__(self, value, description):
        self._value_ = value
        self.description = description

    @classmethod
    def find(cls, val):
        """根据值查找对应的枚举"""
        return next((scope for scope in cls if scope.value == val), None)


class SecurityUtils:
    """安全工具类 - 用于获取当前登录用户信息"""

    @staticmethod
    def get_current_user(request):
        """获取当前登录用户"""
        user = request.user
        if user.is_authenticated:
            return user
        raise AuthenticationFailed("当前登录状态已过期")

    @staticmethod
    def get_current_username(request) -> str:
        """获取当前用户名"""
        return SecurityUtils.get_current_user(request).username

    @staticmethod
    def get_current_user_id(request) -> int:
        """获取当前用户ID"""
        return SecurityUtils.get_current_user(request).id

    @staticmethod
    def get_current_user_data_scope(request) -> List[int]:
        """获取当前用户数据权限范围"""
        return SecurityUtils.get_current_user(request).data_scopes

    @staticmethod
    def get_data_scope_type(request) -> str:
        """获取数据权限级别"""
        data_scopes = SecurityUtils.get_current_user_data_scope(request)
        return "" if data_scopes else DataScopeEnum.ALL.value


class RsaUtils:
    """RSA加解密工具类"""

    @staticmethod
    def generate_key_pair():
        """生成RSA公私钥对"""
        # 生成私钥
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024, backend=default_backend())
        # 获取公钥
        public_key = private_key.public_key()

        # 转换为PEM格式
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
        )
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        return public_key_pem, private_key_pem

    @staticmethod
    def encrypt_by_public_key(public_key_pem, plaintext):
        """使用公钥加密"""
        # 加载公钥
        public_key = serialization.load_pem_public_key(public_key_pem, backend=default_backend())
        # 加密数据
        ciphertext = public_key.encrypt(
            plaintext.encode("utf-8"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return base64.b64encode(ciphertext).decode("utf-8")

    @staticmethod
    def decrypt_by_private_key(private_key_pem, rsa_password, ciphertext):
        """
        使用私钥解密
        :param private_key_pem: PEM格式私钥
        :param rsa_password: 私钥密码(如果有)
        :param ciphertext: Base64编码的密文
        :return: 解密后的明文
        """
        # 加载私钥
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode(),
            password=rsa_password.encode() if rsa_password else None,
            backend=default_backend(),
        )

        # Base64解码密文
        ciphertext_bytes = base64.b64decode(ciphertext)

        # 使用PKCS1v1.5填充方式解密
        plaintext = private_key.decrypt(ciphertext_bytes, padding.PKCS1v15())
        # 使用OAEP解密
        # plaintext = private_key.decrypt(
        #     ciphertext_bytes,
        #     padding.OAEP(
        #         mgf=padding.MGF1(algorithm=hashes.SHA256()),
        #         algorithm=hashes.SHA256(),
        #         label=None
        #     )
        # )

        return plaintext.decode("utf-8")


class CaptchaUtils:
    """验证码生成工具类"""

    @staticmethod
    def generate_captcha():
        """根据配置生成验证码"""
        code_type = LOGIN_CODE_TYPE
        params = {
            "width": LOGIN_CODE_WIDTH,
            "height": LOGIN_CODE_HEIGHT,
            "length": LOGIN_CODE_LENGTH,
            "font_size": LOGIN_CODE_FONT_SIZE,
            "font_name": LOGIN_CODE_FONT_NAME,
        }

        # 验证码生成器映射
        captcha_generators = {
            "ARITHMETIC": CaptchaUtils._generate_arithmetic_captcha,  # 算术验证码
            "CHINESE": CaptchaUtils._generate_chinese_captcha,  # 中文验证码
            "RANDOM": CaptchaUtils._generate_random_captcha,  # 随机字符验证码
        }

        generator = captcha_generators.get(code_type)
        if generator:
            return generator(**params)
        raise ValueError(f"不支持的验证码类型: {code_type}")

    @staticmethod
    def _generate_arithmetic_captcha(width, height, length, font_size, font_name):
        """生成算术验证码"""
        # 生成随机算术表达式
        n1 = random.randint(1, 10)
        n2 = random.randint(1, 10)
        operation = random.choice(["+", "-", "*"])

        # 计算结果
        result = {"+": n1 + n2, "-": n1 - n2, "*": n1 * n2}[operation]

        captcha_value = str(result)
        arithmetic_string = f"{n1} {operation} {n2} = ?"

        # 创建图像
        image = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)

        # 加载字体
        font = ImageFont.truetype(font_name, font_size) if font_name else ImageFont.load_default()

        # 绘制文本
        text_width, text_height = draw.textsize(arithmetic_string, font=font)
        draw.text(
            ((width - text_width) // 2, (height - text_height) // 2),
            arithmetic_string,
            font=font,
            fill=(0, 0, 0),
        )

        # 添加干扰点
        for _ in range(50):
            x = random.randint(0, width)
            y = random.randint(0, height)
            draw.point((x, y), fill=random.choice([(255, 0, 0), (0, 255, 0), (0, 0, 255)]))

        # 转换为Base64
        buffered = BytesIO()
        image.save(buffered, format="PNG", dpi=(300, 300))
        captcha_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return captcha_value, f"data:image/png;base64,{captcha_image}"

    @staticmethod
    def _generate_chinese_captcha(width, height, length, font_size, font_name):
        """生成中文验证码"""
        chinese_chars = "汉字验证码生成测试"
        captcha_value = "".join(random.choices(chinese_chars, k=length))

        # 创建图像
        image = Image.new("RGB", (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype(font_name, font_size) if font_name else ImageFont.load_default()

        # 绘制文本
        text_width, text_height = draw.textsize(captcha_value, font=font)
        draw.text(((width - text_width) // 2, (height - text_height) // 2), captcha_value, font=font, fill=(0, 0, 0))

        # 转换为Base64
        buffered = BytesIO()
        image.save(buffered, format="PNG", dpi=(300, 300))
        captcha_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return captcha_value, f"data:image/png;base64,{captcha_image}"

    @staticmethod
    def _generate_random_captcha(width, height, length, font_size, font_name):
        """生成随机字符验证码"""
        # 创建验证码生成器
        captcha = ImageCaptcha(
            width=width, height=height, fonts=[font_name] if font_name else None, font_sizes=[font_size]
        )

        # 生成随机数字验证码
        captcha_value = "".join(random.choices("0123456789", k=length))

        # 生成图像
        data = captcha.generate(captcha_value)
        image = BytesIO(data.read())

        # 转换为Base64
        captcha_image = base64.b64encode(image.getvalue()).decode("utf-8")

        return captcha_value, f"data:image/png;base64,{captcha_image}"


class TokenProvider:
    """JWT令牌管理工具类"""

    @staticmethod
    def create_token(user):
        """创建用户访问令牌"""
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    @staticmethod
    def get_user_from_token(token):
        """从令牌中获取用户信息"""
        from rest_framework_simplejwt.authentication import JWTAuthentication

        jwt_auth = JWTAuthentication()
        validated_token = jwt_auth.get_validated_token(token)
        return jwt_auth.get_user(validated_token)

    @staticmethod
    def get_token_from_request(request):
        """从请求头中获取令牌"""
        auth = request.headers.get("Authorization", "").split()
        jwt_prefix = JWT_AUTH_HEADER_PREFIX.replace(" ", "").lower()
        if len(auth) == 2 and auth[0].lower() == jwt_prefix:
            return auth[1]
        return None
