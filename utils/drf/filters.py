"""
Enhanced Filters / 增强的过滤器

提供统一的过滤器基类和常用过滤器
"""

from typing import Any, Dict, List, Optional, Type
from django.db import models
from django_filters.rest_framework import FilterSet
from django_filters import (
    BooleanFilter,
    CharFilter,
    DateTimeFilter,
    NumberFilter,
    OrderingFilter,
)
import django_filters


class BaseFilterSet(FilterSet):
    """
    统一的过滤器基类
    Unified base filter set with common functionality

    Features:
    - Soft delete filtering / 软删除过滤
    - Date range filtering / 日期范围过滤
    - Search across multiple fields / 跨多字段搜索
    - Automatic optimization / 自动优化

    Example:
        class UserFilter(BaseFilterSet):
            class Meta:
                model = User
                fields = {
                    'username': ['exact', 'icontains'],
                    'email': ['exact', 'icontains'],
                }
    """

    # ==================== 通用过滤 ====================

    # 软删除过滤
    is_deleted = BooleanFilter(
        field_name='del_flag',
        lookup_expr='exact',
        label="是否删除 / Is Deleted"
    )

    # 状态过滤
    is_active = BooleanFilter(
        field_name='status',
        lookup_expr='exact',
        label="是否启用 / Is Active"
    )

    # 日期范围过滤
    created_after = DateTimeFilter(
        field_name='create_date',
        lookup_expr='gte',
        label="创建时间起始 / Created After"
    )

    created_before = DateTimeFilter(
        field_name='create_date',
        lookup_expr='lte',
        label="创建时间结束 / Created Before"
    )

    updated_after = DateTimeFilter(
        field_name='update_date',
        lookup_expr='gte',
        label="更新时间起始 / Updated After"
    )

    updated_before = DateTimeFilter(
        field_name='update_date',
        lookup_expr='lte',
        label="更新时间结束 / Updated Before"
    )

    # 全局搜索
    search = CharFilter(
        method='filter_search',
        label="全局搜索 / Search"
    )

    # 排序
    ordering = OrderingFilter(
        fields=('create_date', 'update_date', 'id', 'name', 'code'),
        field_labels={
            'create_date': '创建时间 / Created Date',
            'update_date': '更新时间 / Updated Date',
            'id': 'ID',
            'name': '名称 / Name',
            'code': '编码 / Code',
        }
    )

    class Meta:
        abstract = True

    def filter_search(self, queryset: models.QuerySet, name: str, value: str) -> models.QuerySet:
        """
        跨多字段搜索
        Search across multiple text fields

        Args:
            queryset: QuerySet to filter
            name: Filter name (unused)
            value: Search value

        Returns:
            Filtered QuerySet
        """
        if not value:
            return queryset

        # 查找模型的所有CharField和TextField
        from django.db.models import Q
        from django.db.models.fields import CharField, TextField

        search_fields = []
        for field in self.Meta.model._meta.get_fields():
            if isinstance(field, (CharField, TextField)):
                search_fields.append(Q(**{f"{field.name}__icontains": value}))

        # 组合查询（OR关系）
        if search_fields:
            query = search_fields.pop()
            for q in search_fields:
                query |= q
            return queryset.filter(query).distinct()

        return queryset


class CommonFilterMixin:
    """
    通用过滤混入类
    Common filter mixin for ViewSets

    Provides automatic filtering and optimization
    提供自动过滤和优化

    Example:
        class MyViewSet(CommonFilterMixin, BaseViewSet):
            queryset = MyModel.objects.all()
    """

    def get_queryset(self) -> models.QuerySet:
        """
        优化的查询集
        Optimized queryset with common filters

        Returns:
            Filtered and optimized QuerySet
        """
        queryset = super().get_queryset()

        # 自动过滤已删除数据
        if hasattr(queryset.model, 'del_flag'):
            queryset = queryset.filter(del_flag=False)

        # 应用自动优化
        queryset = self._auto_optimize(queryset)

        return queryset.distinct()

    def _auto_optimize(self, queryset: models.QuerySet) -> models.QuerySet:
        """
        自动查询优化
        Automatic query optimization

        Args:
            queryset: QuerySet to optimize

        Returns:
            Optimized QuerySet
        """
        # 自动select_related（对于ForeignKey）
        if hasattr(self, 'select_related_fields'):
            queryset = queryset.select_related(*self.select_related_fields)

        # 自动prefetch_related（对于ManyToMany）
        if hasattr(self, 'prefetch_related_fields'):
            queryset = queryset.prefetch_related(*self.prefetch_related_fields)

        return queryset


class LookupFilterMixin:
    """
    查找过滤混入类
    Lookup filter mixin for advanced filtering

    Provides advanced filtering with custom lookups
    提供高级查找过滤

    Example:
        class MyFilter(LookupFilterMixin, BaseFilterSet):
            class Meta:
                model = MyModel
                fields = {
                    'name': ['exact', 'icontains', 'istartswith'],
                    'email': ['exact', 'icontains'],
                }
    """

    @staticmethod
    def filter_range(queryset: models.QuerySet, field_name: str, value: str) -> models.QuerySet:
        """
        范围过滤
        Range filtering

        Args:
            queryset: QuerySet
            field_name: Field name to filter
            value: Range value (format: "min,max")

        Returns:
            Filtered QuerySet
        """
        if ',' in value:
            min_val, max_val = value.split(',', 1)
            lookup = {
                f'{field_name}__gte': min_val.strip(),
                f'{field_name}__lte': max_val.strip(),
            }
            return queryset.filter(**lookup)
        return queryset.filter(**{field_name: value})

    @staticmethod
    def filter_in_list(
        queryset: models.QuerySet,
        field_name: str,
        value: str
    ) -> models.QuerySet:
        """
        列表过滤
        Filter by list of values

        Args:
            queryset: QuerySet
            field_name: Field name
            value: Comma-separated values

        Returns:
            Filtered QuerySet
        """
        values = [v.strip() for v in value.split(',')]
        return queryset.filter(**{f'{field_name}__in': values})


# ==================== 内置过滤器 ====================

class UserFilter(BaseFilterSet):
    """
    用户过滤器
    User filter with common fields

    Example:
        class UserFilter(BaseFilterSet):
            username = CharFilter(lookup_expr='icontains')
            email = CharFilter(lookup_expr='icontains')

            class Meta:
                model = User
                fields = ['username', 'email', 'is_active']
    """

    username = CharFilter(lookup_expr='icontains', label="用户名 / Username")
    email = CharFilter(lookup_expr='icontains', label="邮箱 / Email")
    phone = CharFilter(lookup_expr='icontains', label="手机号 / Phone")

    class Meta:
        model = None  # 子类需要设置
        fields = ['username', 'email', 'phone', 'is_active']


class DateRangeFilter(django_filters.DateRangeFilter):
    """
    日期范围过滤器增强版
    Enhanced date range filter

    Supports additional lookups
    支持额外的查找方式
    """

    def filter(self, qs: models.QuerySet, value: str) -> models.QuerySet:
        """
        Filter with date range
        使用日期范围过滤

        Args:
            qs: QuerySet
            value: Range value (today, week, month, year, or custom range)

        Returns:
            Filtered QuerySet
        """
        from datetime import datetime, timedelta
        import django_filters

        if value == 'today':
            return qs.filter(
                create_date__gte=datetime.now().replace(hour=0, minute=0, second=0),
                create_date__lte=datetime.now().replace(hour=23, minute=59, second=59)
            )
        elif value == 'week':
            week_ago = datetime.now() - timedelta(days=7)
            return qs.filter(create_date__gte=week_ago)
        elif value == 'month':
            month_ago = datetime.now() - timedelta(days=30)
            return qs.filter(create_date__gte=month_ago)
        elif value == 'year':
            year_ago = datetime.now() - timedelta(days=365)
            return qs.filter(create_date__gte=year_ago)

        return super().filter(qs, value)


class EnumFieldFilter(django_filters.ChoiceFilter):
    """
    枚举字段过滤器
    Enum field filter for choice fields

    Example:
        status_filter = EnumFieldFilter(
            field_name='status',
            choices=['active', 'inactive', 'pending']
        )
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """
        Initialize enum filter

        Args:
            args: Positional arguments
            kwargs: Keyword arguments
        """
        kwargs.setdefault('choices', [])
        kwargs.setdefault('null_label', 'All / 全部')
        kwargs.setdefault('null_value', 'all')
        super().__init__(*args, **kwargs)


# ==================== 辅助函数 ====================

def create_filter_from_model(
    model: Type[models.Model],
    fields: Dict[str, List[str]] = None
) -> Type[BaseFilterSet]:
    """
    从模型动态创建过滤器
    Dynamically create FilterSet from model

    Args:
        model: Django model
        fields: Fields to include {field_name: [lookups]}

    Returns:
        FilterSet class

    Example:
        UserFilterSet = create_filter_from_model(
            User,
            fields={
                'username': ['exact', 'icontains'],
                'email': ['exact', 'icontains'],
            }
        )
    """
    if fields is None:
        fields = {}

    meta_attrs = {
        'model': model,
        'fields': fields,
    }

    Meta = type('Meta', (object,), meta_attrs)

    return type(
        f'{model.__name__}FilterSet',
        (BaseFilterSet,),
        {'Meta': Meta}
    )
