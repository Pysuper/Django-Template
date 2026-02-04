"""
Validators / 验证器

提供通用的验证函数和验证器类
"""

from typing import Any, Optional
from rest_framework import serializers
import re


def validate_text_field(
    value: Optional[str],
    field_name: str = "字段",
    min_length: int = 1,
    max_length: int = 200,
    allow_empty: bool = False
) -> Optional[str]:
    """
    通用文本字段验证
    Common text field validation

    Args:
        value: Field value
        field_name: Field name for error message
        min_length: Minimum length
        max_length: Maximum length
        allow_empty: Allow empty string

    Returns:
        Validated and trimmed value

    Raises:
        serializers.ValidationError: If validation fails

    Examples:
        >>> validate_text_field("  hello  ", "name")
        'hello'
        >>> validate_text_field("", "name", allow_empty=True)
        ''
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise serializers.ValidationError(f"{field_name}必须是字符串")

    value = value.strip()

    if not allow_empty and not value:
        raise serializers.ValidationError(f"{field_name}不能为空")

    if value and len(value) < min_length:
        raise serializers.ValidationError(f"{field_name}长度不能少于{min_length}个字符")

    if value and len(value) > max_length:
        raise serializers.ValidationError(f"{field_name}长度不能超过{max_length}个字符")

    return value


def validate_email_field(value: Optional[str]) -> Optional[str]:
    """
    邮箱字段验证
    Email field validation

    Args:
        value: Email value

    Returns:
        Validated email (lowercase)

    Raises:
        serializers.ValidationError: If validation fails

    Examples:
        >>> validate_email_field("User@Example.COM")
        'user@example.com'
    """
    if value is None:
        return None

    value = value.strip().lower()

    if not value:
        raise serializers.ValidationError("邮箱不能为空")

    # 邮箱格式验证
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, value):
        raise serializers.ValidationError("请输入有效的邮箱地址")

    return value


def validate_phone_field(
    value: Optional[str],
    country_code: str = 'CN'
) -> Optional[str]:
    """
    手机号字段验证
    Phone number field validation

    Args:
        value: Phone number value
        country_code: Country code (CN, US, etc.)

    Returns:
        Validated phone number

    Raises:
        serializers.ValidationError: If validation fails

    Examples:
        >>> validate_phone_field("13800138000", "CN")
        '13800138000'
    """
    if value is None:
        return None

    value = value.strip().replace(' ', '').replace('-', '')

    if not value:
        raise serializers.ValidationError("手机号不能为空")

    # 中国手机号验证
    if country_code == 'CN':
        phone_pattern = r'^1[3-9]\d{9}$'
        if not re.match(phone_pattern, value):
            raise serializers.ValidationError("请输入有效的手机号码")

        return value

    # 通用手机号验证（10-15位数字）
    if not value.isdigit() or len(value) < 10 or len(value) > 15:
        raise serializers.ValidationError("请输入有效的手机号码")

    return value


def validate_url_field(value: Optional[str]) -> Optional[str]:
    """
    URL字段验证
    URL field validation

    Args:
        value: URL value

    Returns:
        Validated URL

    Raises:
        serializers.ValidationError: If validation fails
    """
    if value is None:
        return None

    value = value.strip()

    if not value:
        raise serializers.ValidationError("URL不能为空")

    # 简单URL验证
    url_pattern = r'^https?://'
    if not re.match(url_pattern, value):
        raise serializers.ValidationError("请输入有效的URL（必须以http://或https://开头）")

    return value


def validate_code_field(
    value: Optional[str],
    pattern: str = r'^[A-Z0-9_]+$'
) -> Optional[str]:
    """
    编码字段验证
    Code field validation

    Args:
        value: Code value
        pattern: Regex pattern (default: uppercase letters, numbers, underscore)

    Returns:
        Validated code (uppercase)

    Raises:
        serializers.ValidationError: If validation fails
    """
    if value is None:
        return None

    value = value.strip().upper()

    if not value:
        raise serializers.ValidationError("编码不能为空")

    if not re.match(pattern, value):
        raise serializers.ValidationError("编码只能包含字母、数字和下划线")

    return value


def validate_json_field(value: Any) -> Dict:
    """
    JSON字段验证
    JSON field validation

    Args:
        value: JSON value (dict or string)

    Returns:
        Validated dictionary

    Raises:
        serializers.ValidationError: If validation fails
    """
    if value is None:
        raise serializers.ValidationError("JSON不能为空")

    if isinstance(value, str):
        try:
            import json
            return json.loads(value)
        except json.JSONDecodeError:
            raise serializers.ValidationError("请输入有效的JSON字符串")

    if not isinstance(value, dict):
        raise serializers.ValidationError("JSON必须是对象类型")

    return value


class CustomValidator:
    """
    自定义验证器类
    Custom validator class for complex validations

    Example / 示例:
        validator = CustomValidator()

        # 在Serializer中使用
        def validate_field(self, value):
            return validator.validate_password(value)
    """

    @staticmethod
    def validate_password(
        password: str,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True
    ) -> str:
        """
        密码强度验证
        Password strength validation

        Args:
            password: Password to validate
            min_length: Minimum length
            require_uppercase: Require uppercase letter
            require_lowercase: Require lowercase letter
            require_digit: Require digit
            require_special: Require special character

        Returns:
            Validated password

        Raises:
            serializers.ValidationError: If validation fails
        """
        if len(password) < min_length:
            raise serializers.ValidationError(f"密码长度不能少于{min_length}位")

        if require_uppercase and not re.search(r'[A-Z]', password):
            raise serializers.ValidationError("密码必须包含至少一个大写字母")

        if require_lowercase and not re.search(r'[a-z]', password):
            raise serializers.ValidationError("密码必须包含至少一个小写字母")

        if require_digit and not re.search(r'\d', password):
            raise serializers.ValidationError("密码必须包含至少一个数字")

        if require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            raise serializers.ValidationError("密码必须包含至少一个特殊字符")

        return password

    @staticmethod
    def validate_username(username: str) -> str:
        """
        用户名验证
        Username validation

        Args:
            username: Username to validate

        Returns:
            Validated username

        Raises:
            serializers.ValidationError: If validation fails
        """
        username = username.strip()

        if not username:
            raise serializers.ValidationError("用户名不能为空")

        if len(username) < 3:
            raise serializers.ValidationError("用户名长度不能少于3位")

        if len(username) > 20:
            raise serializers.ValidationError("用户名长度不能超过20位")

        # 只允许字母、数字、下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise serializers.ValidationError("用户名只能包含字母、数字和下划线")

        # 不能以数字开头
        if username[0].isdigit():
            raise serializers.ValidationError("用户名不能以数字开头")

        return username.lower()

    @staticmethod
    def validate_ip_address(ip: str) -> str:
        """
        IP地址验证
        IP address validation

        Args:
            ip: IP address string

        Returns:
            Validated IP address

        Raises:
            serializers.ValidationError: If validation fails
        """
        import ipaddress

        ip = ip.strip()

        if not ip:
            raise serializers.ValidationError("IP地址不能为空")

        try:
            ipaddress.ip_address(ip)
            return ip
        except ValueError:
            raise serializers.ValidationError("请输入有效的IP地址")


class UniqueValidator:
    """
    唯一性验证器
    Uniqueness validator

    Example / 示例:
        class MySerializer(BaseSerializer):
            name = serializers.CharField(
                validators=[UniqueValidator(queryset=MyModel.objects, field='name')]
            )
    """

    def __init__(
        self,
        queryset,
        field: str = 'id',
        message: str = "该值已存在"
    ):
        """
        初始化唯一性验证器

        Args:
            queryset: QuerySet to check
            field: Field name to check
            message: Error message
        """
        self.queryset = queryset
        self.field = field
        self.message = message

    def __call__(self, value: Any) -> Any:
        """
        验证唯一性

        Args:
            value: Value to validate

        Returns:
            Validated value

        Raises:
            serializers.ValidationError: If value already exists
        """
        if self.queryset.filter(**{self.field: value}).exists():
            raise serializers.ValidationError(self.message)

        return value


class RangeValidator:
    """
    范围验证器
    Range validator for numeric values

    Example / 示例:
        age = serializers.IntegerField(
            validators=[RangeValidator(min=18, max=120)]
        )
    """

    def __init__(
        self,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        message: str = "值超出允许范围"
    ):
        """
        初始化范围验证器

        Args:
            min_value: Minimum value (inclusive)
            max_value: Maximum value (inclusive)
            message: Error message
        """
        self.min_value = min_value
        self.max_value = max_value
        self.message = message

    def __call__(self, value: float) -> float:
        """
        验证范围

        Args:
            value: Value to validate

        Returns:
            Validated value

        Raises:
            serializers.ValidationError: If value is out of range
        """
        if self.min_value is not None and value < self.min_value:
            raise serializers.ValidationError(f"{self.message}（最小值：{self.min_value}）")

        if self.max_value is not None and value > self.max_value:
            raise serializers.ValidationError(f"{self.message}（最大值：{self.max_value}）")

        return value
