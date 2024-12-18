from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """
    抽象基类模型，提供创建时间和更新时间字段
    """
    created_at = models.DateTimeField(_("创建时间"), default=timezone.now, editable=False)
    updated_at = models.DateTimeField(_("更新时间"), auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    抽象基类模型，提供软删除功能
    """
    is_deleted = models.BooleanField(_("是否删除"), default=False)
    deleted_at = models.DateTimeField(_("删除时间"), null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)


class BaseModel(TimeStampedModel, SoftDeleteModel):
    """
    项目通用基础模型，包含时间戳和软删除功能
    """
    class Meta:
        abstract = True 