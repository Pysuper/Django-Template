import base64
import os
import random
import re
import string
import uuid
from datetime import datetime, timedelta
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

import qrcode
from PIL import Image
from cryptography.exceptions import InvalidKey
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

# 导入配置参数
from config.settings.base import JWT_AUTH_HEADER_PREFIX


class CodeBiEnum(Enum):
    """验证码业务场景枚举"""

    EMAIL_CHANGE = (1, "旧邮箱修改邮箱")
    PASSWORD_RESET = (2, "通过邮箱修改密码")
    PHONE_CHANGE = (3, "修改手机号码")
    ACCOUNT_VERIFY = (4, "账号验证")
    TWO_FACTOR_AUTH = (5, "两步验证")

    def __init__(self, code: int, description: str):
        self._value_ = code
        self.description = description

    @classmethod
    def find(cls, code: int) -> Optional["CodeBiEnum"]:
        """根据代码查找对应的枚举"""
        return next((value for value in cls if value.value == code), None)


class DataScopeEnum(Enum):
    """数据权限范围枚举"""

    ALL = ("ALL", "全部数据权限")
    DEPT = ("DEPT", "本部门数据权限")
    DEPT_AND_CHILD = ("DEPT_AND_CHILD", "本部门及以下数据权限")
    CUSTOMIZE = ("CUSTOMIZE", "自定义数据权限")
    SELF = ("SELF", "仅本人数据权限")

    def __init__(self, code: str, description: str):
        self._value_ = code
        self.description = description

    @classmethod
    def find(cls, code: str) -> Optional["DataScopeEnum"]:
        """根据代码查找对应的枚举"""
        return next((scope for scope in cls if scope.value == code), None)


class SecurityUtils:
    """安全工具类"""

    @staticmethod
    def get_current_user(request) -> Any:
        """获取当前登录用户"""
        # 增加对request是否有user属性的检查
        if not hasattr(request, 'user'):
            raise AuthenticationFailed(_("请求对象没有user属性"))
        user = request.user
        if user.is_authenticated:
            return user
        raise AuthenticationFailed(_("当前登录状态已过期"))

    @staticmethod
    def get_current_username(request) -> str:
        """获取当前用户名"""
        return SecurityUtils.get_current_user(request).username

    @staticmethod
    def get_current_user_id(request) -> int:
        """获取当前用户ID"""
        return SecurityUtils.get_current_user(request).id

    @staticmethod
    def get_current_user_data_scope(request) -> List[str]:
        """获取当前用户数据权限范围"""
        return SecurityUtils.get_current_user(request).data_scopes

    @staticmethod
    def get_token(user) -> Dict[str, str]:
        """获取用户Token"""
        refresh = RefreshToken.for_user(user)
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "token_type": JWT_AUTH_HEADER_PREFIX,
        }

    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        salt = os.urandom(32)
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return f"{base64.urlsafe_b64encode(salt).decode()}${key.decode()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            salt, key = hashed.split("$")
            salt = base64.urlsafe_b64decode(salt.encode())
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend()
            )
            kdf.verify(password.encode(), base64.urlsafe_b64decode(key.encode()))
            return True
        # 避免使用裸的except语句，应捕获具体的异常
        except (ValueError, base64.binascii.Error, InvalidKey):
            return False


class CryptoUtils:
    """加密工具类"""

    @staticmethod
    def generate_key() -> bytes:
        """生成Fernet密钥"""
        return Fernet.generate_key()

    @staticmethod
    def encrypt(data: Union[str, bytes], key: bytes) -> str:
        """加密数据"""
        f = Fernet(key)
        if isinstance(data, str):
            data = data.encode()
        return f.encrypt(data).decode()

    @staticmethod
    def decrypt(token: Union[str, bytes], key: bytes) -> str:
        """解密数据"""
        f = Fernet(key)
        if isinstance(token, str):
            token = token.encode()
        return f.decrypt(token).decode()

    @staticmethod
    def generate_random_string(length: int = 32) -> str:
        """生成随机字符串"""
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class FileUtils:
    """文件工具类"""

    @staticmethod
    def save_file(file, directory: str = "uploads") -> str:
        """保存文件"""
        ext = os.path.splitext(file.name)[1]
        filename = f"{uuid.uuid4().hex}{ext}"
        path = os.path.join(directory, filename)
        return default_storage.save(path, file)

    @staticmethod
    def get_file_url(path: str) -> str:
        """获取文件URL"""
        return default_storage.url(path)

    @staticmethod
    def delete_file(path: str) -> bool:
        """删除文件"""
        try:
            default_storage.delete(path)
            return True
        # 避免使用裸的except语句，应捕获具体的异常
        except FileNotFoundError:
            return False

    @staticmethod
    def get_file_size(path: str) -> int:
        """获取文件大小"""
        return default_storage.size(path)

    @staticmethod
    def get_file_content_type(filename: str) -> str:
        """获取文件Content-Type"""
        import mimetypes

        return mimetypes.guess_type(filename)[0] or "application/octet-stream"


class ImageUtils:
    """图片工具类"""

    @staticmethod
    def generate_thumbnail(image, size: Tuple[int, int]) -> Image:
        """生成缩略图"""
        if isinstance(image, str):
            # 增加对文件是否存在的检查，避免Image.open方法可能抛出的异常
            if not os.path.exists(image):
                raise FileNotFoundError(f"文件 {image} 不存在")
            image = Image.open(image)
        image.thumbnail(size)
        return image

    @staticmethod
    def convert_to_webp(image, quality: int = 80) -> bytes:
        """转换为WebP格式"""
        if isinstance(image, str):
            # 增加对文件是否存在的检查，避免Image.open方法可能抛出的异常
            if not os.path.exists(image):
                raise FileNotFoundError(f"文件 {image} 不存在")
            image = Image.open(image)
        buffer = BytesIO()
        image.save(buffer, format="WebP", quality=quality)
        return buffer.getvalue()

    @staticmethod
    def generate_qrcode(data: str, size: int = 200) -> Image:
        """生成二维码"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white").resize((size, size))


class EmailUtils:
    """邮件工具类"""

    @staticmethod
    def send_email(
        subject: str,
        to_email: Union[str, List[str]],
        template_name: str,
        context: Dict[str, Any],
        from_email: Optional[str] = None,
    ) -> bool:
        """发送邮件"""
        try:
            html_content = render_to_string(template_name, context)
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=from_email or settings.DEFAULT_FROM_EMAIL,
                to=[to_email] if isinstance(to_email, str) else to_email,
            )
            email.content_subtype = "html"
            email.send()
            return True
        except Exception as e:
            print(f"发送邮件失败: {str(e)}")
            return False


class ValidationUtils:
    """验证工具类"""
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    PHONE_PATTERN = re.compile(r"^1[3-9]\d{9}$")
    USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{4,16}$")

    @staticmethod
    def is_valid_email(email: str) -> bool:
        """验证邮箱格式"""
        return bool(ValidationUtils.EMAIL_PATTERN.match(email))

    @staticmethod
    def is_valid_phone(phone: str) -> bool:
        """验证手机号格式（中国大陆）"""
        return bool(ValidationUtils.PHONE_PATTERN.match(phone))

    @staticmethod
    def is_valid_username(username: str) -> bool:
        """验证用户名格式"""
        return bool(ValidationUtils.USERNAME_PATTERN.match(username))

    @staticmethod
    def is_valid_password(password: str) -> bool:
        """验证密码强度"""
        if len(password) < 8:
            return False
        if not re.search(r"[A-Z]", password):
            return False
        if not re.search(r"[a-z]", password):
            return False
        if not re.search(r"\d", password):
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        return True


class DateTimeUtils:
    """日期时间工具类"""

    @staticmethod
    def format_datetime(dt: Optional[datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化日期时间"""
        if dt is None:
            dt = timezone.now()
        return dt.strftime(fmt)

    @staticmethod
    def parse_datetime(dt_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        """解析日期时间字符串"""
        return datetime.strptime(dt_str, fmt)

    @staticmethod
    def get_date_range(days: int) -> Tuple[datetime, datetime]:
        """获取日期范围"""
        end = timezone.now()
        start = end - timedelta(days=days)
        return start, end

    @staticmethod
    def is_expired(dt: datetime, minutes: int = 30) -> bool:
        """检查是否过期"""
        return timezone.now() > dt + timedelta(minutes=minutes)
