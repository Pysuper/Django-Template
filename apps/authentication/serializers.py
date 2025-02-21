from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.core.serializers import BaseModelSerializer

User = get_user_model()


@extend_schema_serializer(
    examples=[
        {
            "name": "User Example",
            "value": {
                "id": 1,
                "username": "test_user",
                "email": "test@example.com",
                "phone": "13800138000",
                "is_email_verified": True,
                "is_phone_verified": True,
                "is_mfa_enabled": False,
                "date_joined": "2023-01-01T00:00:00Z",
                "last_login": "2023-01-01T00:00:00Z",
            },
        }
    ]
)
class UserSerializer(BaseModelSerializer):
    """
    用户序列化器
    用于用户信息的序列化和反序列化
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone",
            "avatar",
            "is_email_verified",
            "is_phone_verified",
            "is_mfa_enabled",
            "date_joined",
            "last_login",
            "last_login_ip",
            "last_login_user_agent",
        ]
        read_only_fields = [
            "is_email_verified",
            "is_phone_verified",
            "is_mfa_enabled",
            "date_joined",
            "last_login",
            "last_login_ip",
            "last_login_user_agent",
        ]


@extend_schema_serializer(
    examples=[
        {
            "name": "Register Example",
            "value": {
                "username": "new_user",
                "email": "new@example.com",
                "password": "StrongPass123!",
                "password2": "StrongPass123!",
                "email_code": "123456",
            },
        }
    ]
)
class RegisterSerializer(BaseModelSerializer):
    """
    注册序列化器
    用于用户注册
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        help_text=_("密码必须包含大小写字母、数字和特殊字符"),
    )
    password2 = serializers.CharField(write_only=True, required=True, help_text=_("确认密码"))
    email_code = serializers.CharField(write_only=True, required=True, help_text=_("邮箱验证码"))

    class Meta:
        model = User
        fields = ["username", "password", "password2", "email", "email_code"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": _("两次密码不一致")})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        validated_data.pop("email_code")
        user = User.objects.create_user(**validated_data)
        return user


@extend_schema_serializer(
    examples=[
        {
            "name": "Login Example",
            "value": {"username": "test_user", "password": "StrongPass123!", "mfa_code": "123456"},
        }
    ]
)
class LoginSerializer(serializers.Serializer):
    """
    登录序列化器
    用于用户登录
    """

    username = serializers.CharField(required=True, help_text=_("用户名"))
    password = serializers.CharField(required=True, help_text=_("密码"))
    mfa_code = serializers.CharField(required=False, help_text=_("MFA验证码，如果启用了MFA则必填"))

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")
        mfa_code = attrs.get("mfa_code")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError(_("用户不存在"))

        if not user.check_password(password):
            raise serializers.ValidationError(_("密码错误"))

        if user.is_mfa_enabled and not mfa_code:
            raise serializers.ValidationError({"mfa_required": True})

        if user.is_mfa_enabled and not user.verify_mfa_code(mfa_code):
            raise serializers.ValidationError(_("MFA验证码错误"))

        attrs["user"] = user
        return attrs


@extend_schema_serializer(
    examples=[
        {
            "name": "Change Password Example",
            "value": {"old_password": "OldPass123!", "new_password": "NewPass123!", "new_password2": "NewPass123!"},
        }
    ]
)
class ChangePasswordSerializer(serializers.Serializer):
    """
    修改密码序列化器
    用于修改当前用户的密码
    """

    old_password = serializers.CharField(required=True, help_text=_("原密码"))
    new_password = serializers.CharField(required=True, validators=[validate_password], help_text=_("新密码"))
    new_password2 = serializers.CharField(required=True, help_text=_("确认新密码"))

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password": _("两次密码不一致")})
        return attrs


@extend_schema_serializer(
    examples=[
        {
            "name": "Reset Password Example",
            "value": {
                "email": "test@example.com",
                "code": "123456",
                "new_password": "NewPass123!",
                "new_password2": "NewPass123!",
            },
        }
    ]
)
class ResetPasswordSerializer(serializers.Serializer):
    """
    重置密码序列化器
    用于通过邮箱验证码重置密码
    """

    email = serializers.EmailField(required=True, help_text=_("邮箱地址"))
    code = serializers.CharField(required=True, help_text=_("验证码"))
    new_password = serializers.CharField(required=True, validators=[validate_password], help_text=_("新密码"))
    new_password2 = serializers.CharField(required=True, help_text=_("确认新密码"))

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password2"]:
            raise serializers.ValidationError({"new_password": _("两次密码不一致")})
        return attrs


@extend_schema_serializer(examples=[{"name": "MFA Example", "value": {"code": "123456"}}])
class MFASerializer(serializers.Serializer):
    """
    MFA序列化器
    用于验证MFA验证码
    """

    code = serializers.CharField(required=True, help_text=_("MFA验证码"))

    def validate_code(self, value):
        user = self.context["request"].user
        if not user.verify_mfa_code(value):
            raise serializers.ValidationError(_("验证码错误"))
        return value
