from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.authentication.models import VerificationCode
from apps.authentication.serializers import (ChangePasswordSerializer,
                                          LoginSerializer, MFASerializer,
                                          RegisterSerializer,
                                          ResetPasswordSerializer,
                                          UserSerializer)

User = get_user_model()


class UserSerializerTests(TestCase):
    """用户序列化器测试"""

    def setUp(self):
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "phone": "13800138000"
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_user_serialization(self):
        """测试用户序列化"""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data["username"], self.user_data["username"])
        self.assertEqual(data["email"], self.user_data["email"])
        self.assertEqual(data["phone"], self.user_data["phone"])
        self.assertFalse(data["is_email_verified"])
        self.assertFalse(data["is_phone_verified"])
        self.assertFalse(data["is_mfa_enabled"])


class RegisterSerializerTests(TestCase):
    """注册序列化器测试"""

    def setUp(self):
        self.valid_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!",
            "password2": "NewPass123!",
            "email_code": "123456"
        }
        # 创建验证码
        self.verification_code = VerificationCode.objects.create(
            type="email",
            purpose="register",
            target="new@example.com",
            code="123456",
            expired_at=timezone.now() + timedelta(minutes=5)
        )

    def test_valid_registration(self):
        """测试有效注册"""
        serializer = RegisterSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_password_mismatch(self):
        """测试密码不匹配"""
        data = self.valid_data.copy()
        data["password2"] = "different"
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_weak_password(self):
        """测试弱密码"""
        data = self.valid_data.copy()
        data["password"] = "123"
        data["password2"] = "123"
        serializer = RegisterSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)


class LoginSerializerTests(TestCase):
    """登录序列化器测试"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        self.valid_data = {
            "username": "testuser",
            "password": "TestPass123!"
        }

    def test_valid_login(self):
        """测试有效登录"""
        serializer = LoginSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["user"], self.user)

    def test_invalid_credentials(self):
        """测试无效凭据"""
        data = self.valid_data.copy()
        data["password"] = "wrong"
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_mfa_required(self):
        """测试MFA要求"""
        self.user.is_mfa_enabled = True
        self.user.save()
        
        serializer = LoginSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("mfa_required", serializer.errors)


class ChangePasswordSerializerTests(TestCase):
    """修改密码序列化器测试"""

    def setUp(self):
        self.valid_data = {
            "old_password": "OldPass123!",
            "new_password": "NewPass123!",
            "new_password2": "NewPass123!"
        }

    def test_valid_password_change(self):
        """测试有效密码修改"""
        serializer = ChangePasswordSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_password_mismatch(self):
        """测试新密码不匹配"""
        data = self.valid_data.copy()
        data["new_password2"] = "different"
        serializer = ChangePasswordSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)


class ResetPasswordSerializerTests(TestCase):
    """重置密码序列化器测试"""

    def setUp(self):
        self.valid_data = {
            "email": "test@example.com",
            "code": "123456",
            "new_password": "NewPass123!",
            "new_password2": "NewPass123!"
        }

    def test_valid_password_reset(self):
        """测试有效密码重置"""
        serializer = ResetPasswordSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_password_mismatch(self):
        """测试新密码不匹配"""
        data = self.valid_data.copy()
        data["new_password2"] = "different"
        serializer = ResetPasswordSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("new_password", serializer.errors)


class MFASerializerTests(TestCase):
    """MFA序列化器测试"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.user.generate_mfa_secret()
        self.valid_data = {
            "code": "123456"
        }

    def test_invalid_mfa_code(self):
        """测试无效MFA代码"""
        serializer = MFASerializer(
            data=self.valid_data,
            context={"request": type("Request", (), {"user": self.user})}
        )
        self.assertFalse(serializer.is_valid()) 