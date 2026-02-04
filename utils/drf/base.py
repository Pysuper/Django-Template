"""
Base Models / 基础模型

提供统一的BaseEntity模型，包含公共字段和方法
"""

from typing import TYPE_CHECKING

from django.db import models
from django.conf import settings

if TYPE_CHECKING:
    from django.contrib.auth.models import User


class BaseEntity(models.Model):
    """
    统一的基础实体模型
    Unified base entity model with common fields

    Features / 特性:
    - Audit fields (created/updated by/user) / 审计字段
    - Soft delete / 软删除
    - Status field / 状态字段
    - Automatic cache clearing on save / 保存时自动清除缓存
    - Indexes for performance / 性能索引

    Usage / 使用:
        from utils.drf.base import BaseEntity

        class Product(BaseEntity):
            name = models.CharField(max_length=200)
            price = models.DecimalField(max_digits=10, decimal_places=2)
    """

    # ==================== 公共字段 ====================

    # 审计字段 / Audit fields
    create_date = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_index=True,
        verbose_name="创建时间 / Created At"
    )
    update_date = models.DateTimeField(
        auto_now=True,
        editable=False,
        db_index=True,
        verbose_name="更新时间 / Updated At"
    )
    create_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created",
        db_index=True,
        verbose_name="创建人 / Created By"
    )
    update_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated",
        db_index=True,
        verbose_name="更新人 / Updated By"
    )

    # 状态字段 / Status fields
    status = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="状态 / Status"
    )
    del_flag = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="删除标记 / Deleted"
    )

    # 通用字段 / Common fields
    name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="名称 / Name"
    )
    code = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        verbose_name="编码 / Code"
    )
    remark = models.TextField(
        blank=True,
        null=True,
        verbose_name="备注 / Remark"
    )

    class Meta:
        abstract = True
        ordering = ['-create_date', '-id']
        indexes = [
            models.Index(fields=['create_date', 'status']),
            models.Index(fields=['update_date', 'status']),
            models.Index(fields=['del_flag', 'status']),
        ]

    def __str__(self):
        """String representation / 字符串表示"""
        return self.name or self.code or f"{self.__class__.__name__}_{self.pk}"

    # ==================== 实用方法 ====================

    @property
    def is_active(self) -> bool:
        """
        Check if instance is active / 检查实例是否活跃

        Returns:
            True if status is True and not deleted
        """
        return self.status and not self.del_flag

    def soft_delete(self) -> None:
        """
        Soft delete instance / 软删除实例

        Sets del_flag to True instead of actually deleting
        设置del_flag为True而不是真正删除
        """
        self.del_flag = True
        self.save(update_fields=['del_flag', 'update_date'])

    def restore(self) -> None:
        """
        Restore soft deleted instance / 恢复软删除的实例
        """
        self.del_flag = False
        self.save(update_fields=['del_flag', 'update_date'])

    def toggle_status(self) -> bool:
        """
        Toggle status / 切换状态

        Returns:
            New status value
        """
        self.status = not self.status
        self.save(update_fields=['status', 'update_date'])
        return self.status

    def update_fields(self, **kwargs) -> None:
        """
        Batch update fields / 批量更新字段

        Args:
            **kwargs: Field names and values to update

        Example:
            user.update_fields(name="New Name", status=False)
        """
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
        self.save(update_fields=list(kwargs.keys()) + ['update_date'])

    # ==================== 缓存管理 ====================

    def save(self, *args, **kwargs):
        """
        Override save to clear cache / 重写保存以清除缓存

        Automatically clears cache when instance is saved
        保存实例时自动清除缓存
        """
        from django.core.cache import cache

        # Clear cache before saving / 保存前清除缓存
        cache_key = f"{self.__class__.__name__}:{self.pk}"
        cache.delete(cache_key)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Override delete to clear cache / 重写删除以清除缓存

        Clears cache before deleting
        删除前清除缓存
        """
        from django.core.cache import cache

        cache_key = f"{self.__class__.__name__}:{self.pk}"
        cache.delete(cache_key)

        super().delete(*args, **kwargs)

    # ==================== 元类增强 ====================

    @classmethod
    def get_field_names(cls) -> list[str]:
        """
        Get all field names / 获取所有字段名

        Returns:
            List of field names
        """
        return [f.name for f in cls._meta.get_fields()]


class TimeStampedModel(models.Model):
    """
    仅包含时间戳的基础模型
    Base model with only timestamp fields

    Use when you don't need audit fields / 当不需要审计字段时使用
    """

    create_date = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        verbose_name="创建时间 / Created At"
    )
    update_date = models.DateTimeField(
        auto_now=True,
        editable=False,
        verbose_name="更新时间 / Updated At"
    )

    class Meta:
        abstract = True
        ordering = ['-create_date']
