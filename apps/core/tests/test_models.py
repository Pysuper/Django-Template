"""
Models Tests / 模型测试

测试apps/core中的所有模型类
"""

from datetime import datetime, timedelta
from django.db import models
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.core.models import (
    TimeStampedModel,
    SoftDeleteModel,
    BaseModel,
    ActivableModel,
    StatusModel,
)


class TimeStampedModelTest(TestCase):
    """时间戳模型测试"""

    def test_created_at_auto_set(self):
        """测试创建时间自动设置"""

        class TestModel(TimeStampedModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test")
        self.assertIsNotNone(obj.created_at)
        self.assertIsInstance(obj.created_at, datetime)

    def test_updated_at_auto_update(self):
        """测试更新时间自动更新"""

        class TestModel(TimeStampedModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test")
        original_updated_at = obj.updated_at

        # 等待一小段时间
        import time
        time.sleep(0.01)

        obj.name = "Updated"
        obj.save()

        self.assertGreater(obj.updated_at, original_updated_at)


class SoftDeleteModelTest(TestCase):
    """软删除模型测试"""

    def test_soft_delete(self):
        """测试软删除功能"""

        class TestModel(SoftDeleteModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test")
        obj.delete()

        # 刷新对象
        obj.refresh_from_db()

        self.assertTrue(obj.is_deleted)
        self.assertIsNotNone(obj.deleted_at)

    def test_restore(self):
        """测试恢复功能"""

        class TestModel(SoftDeleteModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test")
        obj.delete()
        obj.restore()

        # 刷新对象
        obj.refresh_from_db()

        self.assertFalse(obj.is_deleted)
        self.assertIsNone(obj.deleted_at)

    def test_filter_not_deleted(self):
        """测试过滤未删除对象"""

        class TestModel(SoftDeleteModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj1 = TestModel.objects.create(name="Test1")
        obj2 = TestModel.objects.create(name="Test2")

        obj2.delete()

        # 只应该返回未删除的对象
        queryset = TestModel.objects.filter(is_deleted=False)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().name, "Test1")


class BaseModelTest(TestCase):
    """基础模型测试"""

    def test_base_model_combines_features(self):
        """测试BaseModel组合了时间戳和软删除功能"""

        class TestModel(BaseModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test")

        # 检查时间戳
        self.assertIsNotNone(obj.created_at)
        self.assertIsNotNone(obj.updated_at)

        # 检查软删除
        self.assertFalse(obj.is_deleted)
        self.assertIsNone(obj.deleted_at)

        # 测试删除
        obj.delete()
        obj.refresh_from_db()
        self.assertTrue(obj.is_deleted)
        self.assertIsNotNone(obj.deleted_at)


class ActivableModelTest(TestCase):
    """可激活模型测试"""

    def test_default_active(self):
        """测试默认激活状态"""

        class TestModel(ActivableModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test")
        self.assertTrue(obj.is_active)

    def test_activate(self):
        """测试激活方法"""

        class TestModel(ActivableModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test", is_active=False)
        obj.activate()
        obj.refresh_from_db()
        self.assertTrue(obj.is_active)

    def test_deactivate(self):
        """测试停用方法"""

        class TestModel(ActivableModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test", is_active=True)
        obj.deactivate()
        obj.refresh_from_db()
        self.assertFalse(obj.is_active)


class StatusModelTest(TestCase):
    """状态模型测试"""

    def test_default_status(self):
        """测试默认状态"""

        class TestModel(StatusModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test")
        self.assertEqual(obj.status, StatusModel.StatusChoices.DRAFT)

    def test_change_status(self):
        """测试更改状态"""

        class TestModel(StatusModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = 'core'

        obj = TestModel.objects.create(name="Test")
        obj.change_status(StatusModel.StatusChoices.PUBLISHED)
        obj.refresh_from_db()

        self.assertEqual(obj.status, StatusModel.StatusChoices.PUBLISHED)
        self.assertIsNotNone(obj.status_changed_at)
