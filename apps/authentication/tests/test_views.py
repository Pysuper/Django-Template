from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.authentication.models import LoginHistory, VerificationCode

User = get_user_model()


class AuthViewSetTests(APITestCase):
    """认证视图集测试"""

    def setUp(self):
        self.register_url = reverse("authentication:auth-register")
        self.login_url = reverse("authentication:auth-login")
        self.change_password_url = reverse("authentication:auth-change-password")
        self.reset_password_url = reverse("authentication:auth-reset-password")
        self.send_code_url = reverse("authentication:auth-send-code")
        self.mfa_qr_url = reverse("authentication:auth-mfa-qr")
        self.verify_mfa_url = reverse("authentication:auth-verify-mfa")

        # 创建测试用户
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!",
            "phone": "13800138000"
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_register(self):
        """测试注册"""
        # 创建验证码
        verification_code = VerificationCode.objects.create(
            type="email",
            purpose="register",
            target="new@example.com",
            code="123456",
            expired_at=timezone.now() + timedelta(minutes=5)
        )

        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "NewPass123!",
            "password2": "NewPass123!",
            "email_code": "123456"
        }

        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("user", response.data)
        self.assertIn("token", response.data)

        # 验证用户是否创建成功
        self.assertTrue(
            User.objects.filter(username=data["username"]).exists()
        )

    def test_login(self):
        """测试登录"""
        data = {
            "username": self.user_data["username"],
            "password": self.user_data["password"]
        }

        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("token", response.data)

        # 验证登录历史是否创建
        self.assertTrue(
            LoginHistory.objects.filter(user=self.user).exists()
        )

    def test_login_with_mfa(self):
        """测试MFA登录"""
        # 启用MFA
        self.user.is_mfa_enabled = True
        self.user.save()

        data = {
            "username": self.user_data["username"],
            "password": self.user_data["password"]
        }

        # 不提供MFA代码
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("mfa_required", response.data)

        # 提供错误的MFA代码
        data["mfa_code"] = "123456"
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password(self):
        """测试修改密码"""
        self.client.force_authenticate(user=self.user)

        data = {
            "old_password": self.user_data["password"],
            "new_password": "NewPass123!",
            "new_password2": "NewPass123!"
        }

        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 验证密码是否修改成功
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(data["new_password"]))

    def test_reset_password(self):
        """测试重置密码"""
        # 创建验证码
        verification_code = VerificationCode.objects.create(
            type="email",
            purpose="reset_password",
            target=self.user.email,
            code="123456",
            expired_at=timezone.now() + timedelta(minutes=5)
        )

        data = {
            "email": self.user.email,
            "code": "123456",
            "new_password": "NewPass123!",
            "new_password2": "NewPass123!"
        }

        response = self.client.post(self.reset_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 验证密码是否重置成功
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(data["new_password"]))

    def test_send_code(self):
        """测试发送验证码"""
        data = {
            "type": "email",
            "purpose": "register",
            "target": "new@example.com"
        }

        response = self.client.post(self.send_code_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 验证验证码是否创建
        self.assertTrue(
            VerificationCode.objects.filter(
                type=data["type"],
                purpose=data["purpose"],
                target=data["target"]
            ).exists()
        )

    def test_mfa_operations(self):
        """测试MFA操作"""
        self.client.force_authenticate(user=self.user)

        # 获取MFA二维码
        response = self.client.get(self.mfa_qr_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("qr_url", response.data)
        self.assertIn("secret", response.data)

        # 验证MFA
        data = {"code": "123456"}
        response = self.client.post(self.verify_mfa_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # 因为代码是错误的 