"""
Core Models / 核心模型

提供项目的基础模型类，包括时间戳和软删除功能
"""

from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    时间戳模型 / Time Stamped Model

    抽象基类模型，提供创建时间和更新时间字段
    Abstract base model providing created and updated timestamps

    Attributes:
        created_at: 创建时间 / Creation timestamp
        updated_at: 更新时间 / Last update timestamp

    Example:
        >>> class MyModel(TimeStampedModel):
        ...     name = models.CharField(max_length=100)
        >>> obj = MyModel.objects.create(name="Test")
        >>> obj.created_at
        datetime.datetime(2023, 1, 1, 0, 0, 0)
    """

    created_at = models.DateTimeField(
        _("创建时间"),
        default=timezone.now,
        editable=False,
        db_index=True,
        help_text=_("记录创建时间")
    )
    updated_at = models.DateTimeField(
        _("更新时间"),
        auto_now=True,
        db_index=True,
        help_text=_("记录最后更新时间")
    )

    class Meta:
        abstract = True
        verbose_name = "时间戳模型"
        verbose_name_plural = "时间戳模型"


class SoftDeleteModel(models.Model):
    """
    软删除模型 / Soft Delete Model

    抽象基类模型，提供软删除功能
    Abstract base model providing soft delete functionality

    Attributes:
        is_deleted: 是否删除 / Deletion flag
        deleted_at: 删除时间 / Deletion timestamp

    Example:
        >>> class MyModel(SoftDeleteModel):
        ...     name = models.CharField(max_length=100)
        >>> obj = MyModel.objects.create(name="Test")
        >>> obj.delete()  # 软删除 / Soft delete
        >>> obj.is_deleted
        True
        >>> MyModel.objects.filter(is_deleted=False).count()
        0
    """

    is_deleted = models.BooleanField(
        _("是否删除"),
        default=False,
        db_index=True,
        help_text=_("标记是否已删除")
    )
    deleted_at = models.DateTimeField(
        _("删除时间"),
        null=True,
        blank=True,
        help_text=_("记录删除时间")
    )

    class Meta:
        abstract = True
        verbose_name = "软删除模型"
        verbose_name_plural = "软删除模型"

    def delete(
        self,
        using: Optional[str] = None,
        keep_parents: bool = False
    ) -> None:
        """
        软删除方法 / Soft delete method

        Args:
            using: 数据库别名 / Database alias
            keep_parents: 是否保留父模型 / Whether to keep parent models

        Note:
            此方法实现软删除，不会真正删除数据库记录
            This method implements soft delete, does not actually delete the record
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)

    def hard_delete(
        self,
        using: Optional[str] = None,
        keep_parents: bool = False
    ) -> None:
        """
        硬删除方法 / Hard delete method

        Args:
            using: 数据库别名 / Database alias
            keep_parents: 是否保留父模型 / Whether to keep parent models

        Note:
            此方法会真正删除数据库记录
            This method actually deletes the record from database
        """
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self) -> None:
        """
        恢复已删除的对象 / Restore deleted object

        Example:
            >>> obj = MyModel.objects.get(pk=1)
            >>> obj.restore()
            >>> obj.is_deleted
            False
        """
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class BaseModel(TimeStampedModel, SoftDeleteModel):
    """
    基础模型 / Base Model

    项目通用基础模型，包含时间戳和软删除功能
    Common base model with timestamp and soft delete functionality

    This model combines TimeStampedModel and SoftDeleteModel to provide
    a complete base model with audit trails and soft delete capability.

    Example:
        >>> from apps.core.models import BaseModel
        >>>
        >>> class Product(BaseModel):
        ...     name = models.CharField(max_length=100)
        ...     price = models.DecimalField(max_digits=10, decimal_places=2)
        >>>
        >>> product = Product.objects.create(name="Laptop", price=999.99)
        >>> product.created_at  # 自动设置 / Auto-set
        datetime.datetime(2023, 1, 1, 0, 0, 0)
        >>>
        >>> product.delete()  # 软删除 / Soft delete
        >>> product.is_deleted
        True
        >>>
        >>> Product.objects.filter(is_deleted=False).count()
        0
        >>>
        >>> product.restore()  # 恢复 / Restore
        >>> product.is_deleted
        False
    """

    class Meta:
        abstract = True
        verbose_name = "基础模型"
        verbose_name_plural = "基础模型"


class AuditModel(models.Model):
    """
    审计模型 / Audit Model

    提供创建者和修改者追踪功能
    Provides creator and modifier tracking

    Attributes:
        created_by: 创建者 / Creator
        modified_by: 修改者 / Modifier

    Example:
        >>> class MyModel(AuditModel):
        ...     name = models.CharField(max_length=100)
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_created',
        verbose_name=_("创建者"),
        help_text=_("创建此记录的用户")
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(app_label)s_%(class)s_modified',
        verbose_name=_("修改者"),
        help_text=_("最后修改此记录的用户")
    )

    class Meta:
        abstract = True
        verbose_name = "审计模型"
        verbose_name_plural = "审计模型"


class ActivableModel(models.Model):
    """
    可激活模型 / Activable Model

    提供启用/禁用状态功能
    Provides enable/disable status functionality

    Attributes:
        is_active: 是否激活 / Active status

    Example:
        >>> class MyModel(ActivableModel):
        ...     name = models.CharField(max_length=100)
        >>>
        >>> obj = MyModel.objects.create(name="Test", is_active=True)
        >>> MyModel.objects.filter(is_active=True)
    """

    is_active = models.BooleanField(
        _("是否激活"),
        default=True,
        db_index=True,
        help_text=_("是否启用此记录")
    )

    class Meta:
        abstract = True
        verbose_name = "可激活模型"
        verbose_name_plural = "可激活模型"

    def activate(self) -> None:
        """激活对象 / Activate object"""
        self.is_active = True
        self.save()

    def deactivate(self) -> None:
        """停用对象 / Deactivate object"""
        self.is_active = False
        self.save()


class StatusModel(models.Model):
    """
    状态模型 / Status Model

    提供状态管理功能
    Provides status management functionality

    Attributes:
        status: 状态 / Status
        status_changed_at: 状态变更时间 / Status change timestamp

    Example:
        >>> class MyModel(StatusModel):
        ...     name = models.CharField(max_length=100)
    """

    class StatusChoices(models.TextChoices):
        """状态选项 / Status choices"""
        DRAFT = 'draft', _('草稿')
        PUBLISHED = 'published', _('已发布')
        ARCHIVED = 'archived', _('已归档')
        DELETED = 'deleted', _('已删除')

    status = models.CharField(
        _("状态"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        db_index=True,
        help_text=_("记录状态")
    )
    status_changed_at = models.DateTimeField(
        _("状态变更时间"),
        null=True,
        blank=True,
        help_text=_("最后状态变更时间")
    )

    class Meta:
        abstract = True
        verbose_name = "状态模型"
        verbose_name_plural = "状态模型"

    def change_status(self, new_status: str) -> None:
        """
        更改状态 / Change status

        Args:
            new_status: 新状态 / New status
        """
        self.status = new_status
        self.status_changed_at = timezone.now()
        self.save()


class VersionModel(models.Model):
    """
    版本模型 / Version Model

    提供版本管理功能
    Provides version management functionality

    Attributes:
        version: 版本号 / Version number
        version_comment: 版本说明 / Version comment

    Example:
        >>> class MyModel(VersionModel):
        ...     name = models.CharField(max_length=100)
    """

    version = models.PositiveIntegerField(
        _("版本号"),
        default=1,
        help_text=_("记录版本号")
    )
    version_comment = models.TextField(
        _("版本说明"),
        blank=True,
        help_text=_("版本变更说明")
    )

    class Meta:
        abstract = True
        verbose_name = "版本模型"
        verbose_name_plural = "版本模型"

    def increment_version(self, comment: str = "") -> None:
        """
        递增版本号 / Increment version

        Args:
            comment: 版本说明 / Version comment
        """
        self.version += 1
        self.version_comment = comment
        self.save()
