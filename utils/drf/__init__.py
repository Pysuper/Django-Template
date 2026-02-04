"""
DRF Enhanced Wrappers / DRF增强封装

This module provides enhanced wrappers for Django REST Framework with:
此模块提供Django REST Framework的增强封装：

- Unified base classes / 统一的基类
- Type hints / 类型提示
- Fixed caching / 修复的缓存
- Performance optimization / 性能优化
- Extension hooks / 扩展钩子

Usage / 使用:
    from utils.drf import viewsets, serializers, filters, pagination

    class MyViewSet(viewsets.BaseViewSet):
        queryset = MyModel.objects.all()
        serializer_class = MySerializer
"""

# Convenience imports / 便捷导入
from .base import BaseEntity
from .serializers import (
    BaseSerializer,
    DynamicFieldsSerializer,
    TreeSerializer,
    BulkActionSerializer,
)
from .viewsets import BaseViewSet, ReadOnlyViewSet
from .filters import BaseFilterSet, CommonFilterMixin
from .pagination import (
    StandardPageNumberPagination,
    LargeResultSetPagination,
    CursorPagination,
)
from .mixins import (
    CacheMixin,
    ExportMixin,
    AuditMixin,
    BulkActionMixin,
)
from .validators import (
    validate_text_field,
    validate_email_field,
    validate_phone_field,
)

__all__ = [
    # Base classes / 基类
    "BaseEntity",
    # Serializers / 序列化器
    "BaseSerializer",
    "DynamicFieldsSerializer",
    "TreeSerializer",
    "BulkActionSerializer",
    # ViewSets / 视图集
    "BaseViewSet",
    "ReadOnlyViewSet",
    # Filters / 过滤器
    "BaseFilterSet",
    "CommonFilterMixin",
    # Pagination / 分页
    "StandardPageNumberPagination",
    "LargeResultSetPagination",
    "CursorPagination",
    # Mixins / 混入
    "CacheMixin",
    "ExportMixin",
    "AuditMixin",
    "BulkActionMixin",
    # Validators / 验证器
    "validate_text_field",
    "validate_email_field",
    "validate_phone_field",
]
