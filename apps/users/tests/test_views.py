"""
Tests for User Views / 用户视图测试

Test suite for user-related views and API endpoints.
测试用户相关视图和API端点。
"""

import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.tests.factories import (
    AdminUserFactory,
    DefaultRoleFactory,
    RoleFactory,
    UserFactory,
)


class UserViewSetTest(TestCase):
    """Test User ViewSet / 测试用户视图集"""

    def setUp(self):
        """Set up test fixtures / 设置测试夹具"""
        self.client = APIClient()
        self.admin_user = AdminUserFactory()
        self.client.force_authenticate(user=self.admin_user)

        self.regular_user = UserFactory()

    def test_list_users(self):
        """Test listing all users / 测试列出所有用户"""
        url = reverse("users:user-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_user(self):
        """Test creating a new user / 测试创建新用户"""
        url = reverse("users:user-list")
        data = {
            "username": "newuser",
            "password": "newpass123",
            "email": "newuser@example.com",
            "phone": "13900139000",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "newuser")

    def test_retrieve_user(self):
        """Test retrieving a specific user / 测试获取特定用户"""
        url = reverse("users:user-detail", kwargs={"pk": self.regular_user.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.regular_user.username)

    def test_update_user(self):
        """Test updating a user / 测试更新用户"""
        url = reverse("users:user-detail", kwargs={"pk": self.regular_user.pk})
        data = {
            "username": self.regular_user.username,
            "email": "updated@example.com",
        }
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, "updated@example.com")

    def test_delete_user(self):
        """Test deleting a user / 测试删除用户"""
        url = reverse("users:user-detail", kwargs={"pk": self.regular_user.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            UserFactory._meta.model.objects.filter(
                pk=self.regular_user.pk
            ).exists()
        )

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access user endpoints / 测试未认证用户无法访问"""
        self.client.force_authenticate(user=None)
        url = reverse("users:user-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RoleViewSetTest(TestCase):
    """Test Role ViewSet / 测试角色视图集"""

    def setUp(self):
        """Set up test fixtures / 设置测试夹具"""
        self.client = APIClient()
        self.admin_user = AdminUserFactory()
        self.client.force_authenticate(user=self.admin_user)

        self.role = RoleFactory()

    def test_list_roles(self):
        """Test listing all roles / 测试列出所有角色"""
        url = reverse("users:role-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_role(self):
        """Test creating a new role / 测试创建新角色"""
        url = reverse("users:role-list")
        data = {
            "name": "New Role",
            "code": "new_role",
            "level": 1,
            "description": "New role description",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Role")

    def test_role_code_unique(self):
        """Test that role code must be unique / 测试角色代码必须唯一"""
        url = reverse("users:role-list")
        data = {
            "name": "Duplicate Role",
            "code": self.role.code,  # Duplicate code
            "level": 1,
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserAuthenticationTest(TestCase):
    """Test user authentication endpoints / 测试用户认证端点"""

    def setUp(self):
        """Set up test fixtures / 设置测试夹具"""
        self.client = APIClient()
        self.user = UserFactory(password="testpass123")

    def test_user_login(self):
        """Test user login / 测试用户登录"""
        url = reverse("authentication:login")
        data = {
            "username": self.user.username,
            "password": "testpass123",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data or {})
        self.assertIn("user", response.data or {})

    def test_user_login_invalid_credentials(self):
        """Test user login with invalid credentials / 测试无效凭据登录"""
        url = reverse("authentication:login")
        data = {
            "username": self.user.username,
            "password": "wrongpassword",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_logout(self):
        """Test user logout / 测试用户登出"""
        # First login / 先登录
        self.client.force_authenticate(user=self.user)

        # Then logout / 然后登出
        url = reverse("authentication:logout")
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserPermissionTest(TestCase):
    """Test user permissions / 测试用户权限"""

    def setUp(self):
        """Set up test fixtures / 设置测试夹具"""
        self.client = APIClient()
        self.admin_user = AdminUserFactory()
        self.regular_user = UserFactory()

    def test_regular_user_cannot_create_user(self):
        """Test that regular users cannot create other users / 测试普通用户不能创建其他用户"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse("users:user-list")
        data = {
            "username": "newuser",
            "password": "newpass123",
        }
        response = self.client.post(url, data)

        # Should be forbidden / 应该被禁止
        self.assertIn(
            response.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
        )

    def test_admin_can_create_user(self):
        """Test that admin users can create users / 测试管理员可以创建用户"""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("users:user-list")
        data = {
            "username": "newuser",
            "password": "newpass123",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


@pytest.mark.django_db
class TestUserAPI:
    """Pytest-style user API tests / Pytest风格的用户API测试"""

    @pytest.fixture
    def api_client(self):
        """API client fixture / API客户端夹具"""
        from rest_framework.test import APIClient
        return APIClient()

    @pytest.fixture
    def admin_user(self):
        """Admin user fixture / 管理员用户夹具"""
        return AdminUserFactory()

    @pytest.fixture
    def regular_user(self):
        """Regular user fixture / 普通用户夹具"""
        return UserFactory()

    def test_user_can_update_own_profile(self, api_client, regular_user):
        """Test that users can update their own profile / 测试用户可以更新自己的资料"""
        api_client.force_authenticate(user=regular_user)
        url = reverse("users:user-detail", kwargs={"pk": regular_user.pk})
        data = {"email": "mynewemail@example.com"}
        response = api_client.patch(url, data)

        assert response.status_code == status.HTTP_200_OK
        regular_user.refresh_from_db()
        assert regular_user.email == "mynewemail@example.com"

    def test_user_cannot_delete_own_account(self, api_client, regular_user):
        """Test that users cannot delete their own account / 测试用户不能删除自己的账户"""
        api_client.force_authenticate(user=regular_user)
        url = reverse("users:user-detail", kwargs={"pk": regular_user.pk})
        response = api_client.delete(url)

        # Should be forbidden / 应该被禁止
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST
        ]
