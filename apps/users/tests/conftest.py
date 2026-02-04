"""
Pytest Configuration for User Management Tests / 用户管理测试的Pytest配置

This module contains pytest fixtures for user management tests.
此模块包含用户管理测试的pytest夹具。
"""

import pytest
from apps.users.tests.factories import (
    AdminUserFactory,
    DefaultRoleFactory,
    RoleFactory,
    UserFactory,
)


@pytest.fixture
def user(db):
    """Create a regular user / 创建普通用户"""
    return UserFactory()


@pytest.fixture
def admin_user(db):
    """Create an admin user / 创建管理员用户"""
    return AdminUserFactory()


@pytest.fixture
def role(db):
    """Create a role / 创建角色"""
    return RoleFactory()


@pytest.fixture
def default_role(db):
    """Create a default role / 创建默认角色"""
    return DefaultRoleFactory()


@pytest.fixture
def multiple_users(db):
    """Create multiple users / 创建多个用户"""
    return UserFactory.create_batch(5)


@pytest.fixture
def user_with_role(db, user, role):
    """Create a user with a specific role / 创建带特定角色的用户"""
    user.roles.add(role)
    return user
