from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.authentication.models import LoginHistory, VerificationCode

User = get_user_model()


class UserModelTests(TestCase):
    """用户模型测试"""

    def setUp(self):
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "phone": "13800138000"
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_create_user(self):
        """测试创建用户"""
        self.assertEqual(self.user.username, self.user_data["username"])
        self.assertEqual(self.user.email, self.user_data["email"])
        self.assertEqual(self.user.phone, self.user_data["phone"])
        self.assertTrue(self.user.check_password(self.user_data["password"]))
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.user.is_active)

    def test_create_superuser(self):
        """测试创建超级用户"""
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin123"
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)

    def test_user_str(self):
        """测试用户字符串表示"""
        self.assertEqual(str(self.user), self.user_data["username"])

    def test_mfa_functionality(self):
        """测试MFA功能"""
        # 测试生成MFA密钥
        secret = self.user.generate_mfa_secret()
        self.assertIsNotNone(secret)
        self.assertEqual(len(secret), 32)

        # 测试验证MFA代码
        self.assertFalse(self.user.verify_mfa_code("123456"))

        # 测试获取MFA二维码URL
        qr_url = self.user.get_mfa_qr_url()
        self.assertIn(self.user.email, qr_url)
        self.assertIn(self.user.mfa_secret, qr_url)


class LoginHistoryTests(TestCase):
    """登录历史测试"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.login_history = LoginHistory.objects.create(
            user=self.user,
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0",
            location="Local"
        )

    def test_create_login_history(self):
        """测试创建登录历史"""
        self.assertEqual(self.login_history.user, self.user)
        self.assertEqual(self.login_history.ip_address, "127.0.0.1")
        self.assertEqual(self.login_history.user_agent, "Mozilla/5.0")
        self.assertEqual(self.login_history.location, "Local")
        self.assertTrue(self.login_history.status)

    def test_login_history_str(self):
        """测试登录历史字符串表示"""
        expected = f"{self.user.username} - {self.login_history.created_at}"
        self.assertEqual(str(self.login_history), expected)


class VerificationCodeTests(TestCase):
    """验证码测试"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.verification_code = VerificationCode.objects.create(
            user=self.user,
            type="email",
            purpose="register",
            target="test@example.com",
            code="123456",
            expired_at=timezone.now() + timedelta(minutes=5)
        )

    def test_create_verification_code(self):
        """测试创建验证码"""
        self.assertEqual(self.verification_code.user, self.user)
        self.assertEqual(self.verification_code.type, "email")
        self.assertEqual(self.verification_code.purpose, "register")
        self.assertEqual(self.verification_code.target, "test@example.com")
        self.assertEqual(self.verification_code.code, "123456")
        self.assertFalse(self.verification_code.is_used)

    def test_verification_code_str(self):
        """测试验证码字符串表示"""
        expected = f"{self.verification_code.target} - {self.verification_code.code}"
        self.assertEqual(str(self.verification_code), expected)

    def test_verification_code_expiration(self):
        """测试验证码过期"""
        # 创建一个已过期的验证码
        expired_code = VerificationCode.objects.create(
            type="email",
            purpose="register",
            target="test2@example.com",
            code="654321",
            expired_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertTrue(expired_code.expired_at < timezone.now()) 