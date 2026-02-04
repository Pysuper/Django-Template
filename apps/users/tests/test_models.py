"""
Tests for User Models / 用户模型测试

Test suite for user-related models including User, Role, Permission, etc.
测试用户相关模型，包括User、Role、Permission等。
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.users.models import Role, UserSettings

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model / 测试用户模型"""

    def setUp(self):
        """Set up test fixtures / 设置测试夹具"""
        self.user_data = {
            "username": "testuser",
            "password": "testpass123",
            "email": "test@example.com",
            "phone": "13800138000",
        }

    def test_create_user(self):
        """Test creating a regular user / 测试创建普通用户"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        """Test creating a superuser / 测试创建超级用户"""
        user = User.objects.create_superuser(
            username="admin",
            password="admin123",
            email="admin@example.com"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("admin123"))

    def test_user_str_representation(self):
        """Test user string representation / 测试用户字符串表示"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), "testuser")

    def test_user_email_unique(self):
        """Test that email is unique / 测试邮箱唯一性"""
        User.objects.create_user(**self.user_data)
        with self.assertRaises(Exception):
            User.objects.create_user(
                username="testuser2",
                password="testpass123",
                email="test@example.com",  # Same email
                phone="13800138001"
            )


class RoleModelTest(TestCase):
    """Test Role model / 测试角色模型"""

    def setUp(self):
        """Set up test fixtures / 设置测试夹具"""
        self.role_data = {
            "name": "Test Role",
            "code": "test_role",
            "level": 1,
            "description": "Test role description",
        }

    def test_create_role(self):
        """Test creating a role / 测试创建角色"""
        role = Role.objects.create(**self.role_data)
        self.assertEqual(role.name, "Test Role")
        self.assertEqual(role.code, "test_role")
        self.assertEqual(role.level, 1)
        self.assertFalse(role.is_default)

    def test_role_str_representation(self):
        """Test role string representation / 测试角色字符串表示"""
        role = Role.objects.create(**self.role_data)
        self.assertEqual(str(role), "Test Role")

    def test_role_code_unique(self):
        """Test that role code is unique / 测试角色代码唯一性"""
        Role.objects.create(**self.role_data)
        with self.assertRaises(Exception):
            Role.objects.create(**self.role_data)

    def test_default_role(self):
        """Test default role functionality / 测试默认角色功能"""
        role = Role.objects.create(**self.role_data, is_default=True)
        self.assertTrue(role.is_default)

        # Test getting default role / 测试获取默认角色
        default_role = Role.objects.filter(is_default=True).first()
        self.assertIsNotNone(default_role)
        self.assertEqual(default_role.code, "test_role")


class UserSettingsModelTest(TestCase):
    """Test UserSettings model / 测试用户设置模型"""

    def setUp(self):
        """Set up test fixtures / 设置测试夹具"""
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

    def test_create_user_settings(self):
        """Test creating user settings / 测试创建用户设置"""
        settings = UserSettings.objects.create(
            user=self.user,
            theme="dark",
            language="en",
            timezone="UTC"
        )
        self.assertEqual(settings.user, self.user)
        self.assertEqual(settings.theme, "dark")
        self.assertEqual(settings.language, "en")
        self.assertEqual(settings.timezone, "UTC")

    def test_user_settings_default_values(self):
        """Test default values for user settings / 测试用户设置默认值"""
        settings = UserSettings.objects.create(user=self.user)
        self.assertEqual(settings.theme, "light")
        self.assertEqual(settings.language, "zh-hans")
        self.assertEqual(settings.timezone, "Asia/Shanghai")

    def test_user_cascade_delete(self):
        """Test that settings are deleted when user is deleted / 测试用户删除时设置级联删除"""
        settings = UserSettings.objects.create(user=self.user)
        settings_id = settings.id

        user_id = self.user.id
        self.user.delete()

        # Check if settings are deleted / 检查设置是否被删除
        self.assertFalse(
            UserSettings.objects.filter(id=settings_id).exists()
        )


class UserRoleRelationshipTest(TestCase):
    """Test user-role relationships / 测试用户-角色关系"""

    def setUp(self):
        """Set up test fixtures / 设置测试夹具"""
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        self.role = Role.objects.create(
            name="Test Role",
            code="test_role",
            level=1
        )

    def test_assign_role_to_user(self):
        """Test assigning a role to user / 测试为用户分配角色"""
        self.user.roles.add(self.role)
        self.assertEqual(self.user.roles.count(), 1)
        self.assertIn(self.role, self.user.roles.all())

    def test_remove_role_from_user(self):
        """Test removing a role from user / 测试从用户移除角色"""
        self.user.roles.add(self.role)
        self.user.roles.remove(self.role)
        self.assertEqual(self.user.roles.count(), 0)

    def test_user_multiple_roles(self):
        """Test user with multiple roles / 测试用户多个角色"""
        role1 = Role.objects.create(name="Role 1", code="role1", level=1)
        role2 = Role.objects.create(name="Role 2", code="role2", level=2)

        self.user.roles.add(role1, role2)
        self.assertEqual(self.user.roles.count(), 2)


@pytest.mark.django_db
class TestUserSignals:
    """Test user-related signals / 测试用户相关信号"""

    def test_user_settings_created_on_user_creation(self):
        """Test that UserSettings are created when User is created / 测试创建用户时自动创建设置"""
        user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )
        # UserSettings should be created by signal / 信号应创建UserSettings
        self.assertTrue(
            hasattr(user, 'usersettings') or
            UserSettings.objects.filter(user=user).exists()
        )

    def test_default_role_assigned_on_user_creation(self):
        """Test that default role is assigned when User is created / 测试创建用户时分配默认角色"""
        # Create a default role / 创建默认角色
        Role.objects.create(
            name="Default",
            code="default",
            level=1,
            is_default=True
        )

        user = User.objects.create_user(
            username="testuser",
            password="testpass123"
        )

        # User should have default role / 用户应有默认角色
        self.assertTrue(user.roles.exists())
        self.assertTrue(
            any(role.is_default for role in user.roles.all())
        )
