import os
import uuid
from typing import Any, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible


@deconstructible
class PathAndRename:
    """
    文件重命名工具类
    使用方法：
    class MyModel(models.Model):
        file = models.FileField(upload_to=PathAndRename('path/to/upload'))
    """

    def __init__(self, sub_path: str):
        self.path = sub_path

    def __call__(self, instance: Any, filename: str) -> str:
        ext = filename.split('.')[-1]
        filename = f'{uuid.uuid4().hex}.{ext}'
        return os.path.join(self.path, filename)


def validate_file_size(value: Any) -> None:
    """
    文件大小验证器
    默认最大文件大小为 5MB
    """
    max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 5 * 1024 * 1024)
    # 增加对value是否有size属性的检查，以避免潜在的AttributeError
    if not hasattr(value, 'size'):
        raise ValidationError('传入的对象没有size属性')
    if value.size > max_size:
        raise ValidationError(f'文件大小不能超过 {max_size / 1024 / 1024}MB')


def get_client_ip(request: Any) -> Optional[str]:
    """
    获取客户端IP地址
    """
    # 增加对request是否有META属性的检查，同时处理x_forwarded_for为空字符串的情况
    if not hasattr(request, 'META'):
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for and x_forwarded_for.strip():
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def mask_sensitive_data(data: str, start: int = 3, end: int = 3) -> str:
    """
    敏感数据脱敏
    例如：mask_sensitive_data('13812345678') -> '138****5678'
    """
    # 增加对start和end参数的合法性检查，确保它们不会导致索引越界
    if not data:
        return data
    length = len(data)
    if start < 0 or end < 0 or start + end >= length:
        return '*' * length
    return f'{data[:start]}{"*" * (length - start - end)}{data[-end:]}'
