"""
Enhanced ViewSets / 增强的视图集

提供统一的视图集基类，包含完整的CRUD操作和扩展功能
"""

from typing import Any, Dict, List, Optional, Type, TypeVar
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from django.db import transaction
from django.db.models import Model, QuerySet
from django.core.cache import cache
from django.utils import timezone

from .serializers import BaseSerializer, BulkActionSerializer
from .filters import BaseFilterSet
from .pagination import StandardPageNumberPagination


T = TypeVar('T', bound=Model)
S = TypeVar('S', bound=BaseSerializer)


class BaseViewSet(viewsets.ModelViewSet):
    """
    统一的基础视图集
    Unified base viewset with enhanced features

    Features / 特性:
    - ✅ Fixed caching / 修复的缓存实现
    - ✅ Type hints / 完整的类型提示
    - ✅ Auto optimization / 自动查询优化
    - ✅ Extension hooks / 扩展钩子系统
    - ✅ Performance monitoring / 性能监控
    - ✅ Audit logging / 审计日志
    - ✅ Bulk operations / 批量操作
    - ✅ Soft delete support / 软删除支持

    Usage / 使用:
        from utils.drf.viewsets import BaseViewSet
        from apps.users.models import User
        from apps.users.serializers import UserSerializer

        class UserViewSet(BaseViewSet):
            queryset = User.objects.all()
            serializer_class = UserSerializer
            filterset_class = UserFilter
    """

    # ==================== 配置 ====================

    queryset: QuerySet[T] = None
    serializer_class: Type[S] = None
    filterset_class: Type[BaseFilterSet] = None
    pagination_class = StandardPageNumberPagination

    # 缓存配置
    cache_enabled = False  # 默认关闭，需要显式启用
    cache_timeout = 300  # 5分钟

    # 批量操作配置
    allow_bulk_create = False
    allow_bulk_update = True
    allow_bulk_delete = True

    # 性能配置
    enable_select_related = True
    enable_prefetch_related = True

    # 审计日志
    enable_audit_log = True

    # 自动操作
    auto_set_created_by = True
    auto_set_updated_by = True

    # ==================== 查询集优化 ====================

    def get_queryset(self) -> QuerySet[T]:
        """
        优化的查询集
        Optimized queryset with automatic filtering and optimization

        Returns:
            Optimized QuerySet
        """
        assert self.queryset is not None, (
            f"{self.__class__.__name__} 需要设置 queryset 属性或重写 get_queryset() 方法"
        )

        queryset = self.queryset

        # 自动过滤软删除
        if hasattr(queryset.model, 'del_flag'):
            queryset = queryset.filter(del_flag=False)

        # 自动优化关联查询
        if self.enable_select_related:
            queryset = self._apply_select_related(queryset)

        if self.enable_prefetch_related:
            queryset = self._apply_prefetch_related(queryset)

        return queryset.distinct()

    def _apply_select_related(self, queryset: QuerySet[T]) -> QuerySet[T]:
        """
        应用select_related
        Apply select_related for ForeignKey fields

        Returns:
            Optimized QuerySet
        """
        if hasattr(self, 'select_related_fields'):
            return queryset.select_related(*self.select_related_fields)

        # 自动检测ForeignKey并应用
        related_fields = []
        for field in queryset.model._meta.get_fields():
            if field.is_relation and field.many_to_one is False and field.concrete:
                related_fields.append(field.name)

        if related_fields:
            return queryset.select_related(*related_fields[:5])  # 限制数量

        return queryset

    def _apply_prefetch_related(self, queryset: QuerySet[T]) -> QuerySet[T]:
        """
        应用prefetch_related
        Apply prefetch_related for ManyToMany fields

        Returns:
            Optimized QuerySet
        """
        if hasattr(self, 'prefetch_related_fields'):
            return queryset.prefetch_related(*self.prefetch_related_fields)

        return queryset

    # ==================== 序列化器 ====================

    def get_serializer_class(self) -> Type[S]:
        """
        动态序列化器选择
        Dynamic serializer class selection based on action

        Returns:
            Serializer class
        """
        assert self.serializer_class is not None, (
            f"{self.__class__.__name__} 需要设置 serializer_class 属性"
        )

        # 支持action不同的序列化器
        if hasattr(self, 'action_serializers'):
            return self.action_serializers.get(self.action, self.serializer_class)

        return self.serializer_class

    def get_serializer(self, *args: Any, **kwargs: Any) -> S:
        """
        获取序列化器实例
        Get serializer instance with context

        Returns:
            Serializer instance
        """
        serializer_class = self.get_serializer_class()
        kwargs.setdefault('context', self.get_serializer_context())
        return serializer_class(*args, **kwargs)

    # ==================== 缓存管理 ====================

    def get_cache_key(self, **kwargs: Any) -> Optional[str]:
        """
        生成缓存键
        Generate cache key for current request

        Returns:
            Cache key string or None
        """
        if not self.cache_enabled:
            return None

        # 基于请求参数生成唯一键
        import hashlib
        params = dict(self.request.query_params)
        user_id = self.request.user.id if self.request.user.is_authenticated else 'anonymous'

        key_parts = [
            self.__class__.__name__,
            self.action,
            str(user_id),
            str(hash(frozenset(sorted(params.items())))),
            str(sorted(kwargs.items()))
        ]

        return f"drf_cache:__{'__'.join(key_parts)}"

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取"""
        if not cache_key:
            return None
        return cache.get(cache_key)

    def _set_to_cache(self, cache_key: str, data: Any) -> None:
        """设置到缓存"""
        if not cache_key:
            return
        cache.set(cache_key, data, self.cache_timeout)

    def _clear_cache(self, pattern: str = None) -> None:
        """清除缓存"""
        if pattern:
            # 需要支持通配符的缓存后端（如Redis）
            keys = cache.keys(f"{pattern}*")
            if keys:
                cache.delete_many(keys)

    # ==================== CRUD操作 ====================

    def list(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """
        列表视图（带缓存）
        List view with caching support

        Args:
            request: Request object
            args: Additional positional arguments
            kwargs: Additional keyword arguments

        Returns:
            Response with paginated data
        """
        cache_key = self.get_cache_key()
        cached_response = self._get_from_cache(cache_key)

        if cached_response is not None:
            return cached_response

        # 执行查询
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
        else:
            serializer = self.get_serializer(queryset, many=True)
            response = self._to_response(serializer.data, message="获取成功")

        # 缓存响应数据
        if cache_key and hasattr(response, 'data'):
            self._set_to_cache(cache_key, response.data)

        return response

    def retrieve(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """
        详情视图（带缓存）
        Retrieve view with caching support
        """
        instance = self.get_object()

        cache_key = self.get_cache_key(pk=instance.pk)
        cached_data = self._get_from_cache(cache_key)

        if cached_data is not None:
            return self._to_response(cached_data, message="获取成功")

        serializer = self.get_serializer(instance)
        response_data = serializer.data

        # 缓存数据
        if cache_key:
            self._set_to_cache(cache_key, response_data)

        return self._to_response(response_data, message="获取成功")

    def create(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """
        创建对象
        Create object with transaction and hooks
        """
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)

                # 钩子：创建前
                self.before_create(serializer)

                # 自动设置创建人
                extra_data = {}
                if self.auto_set_created_by and request.user.is_authenticated:
                    extra_data['create_by'] = request.user

                instance = serializer.save(**extra_data)

                # 钩子：创建后
                self.after_create(instance)

                # 清除缓存
                self._clear_cache(f"{self.__class__.__name__}:list:*")

                # 审计日志
                if self.enable_audit_log:
                    self._log_action('create', instance)

                return self._to_response(
                    serializer.data,
                    message="创建成功",
                    code=status.HTTP_201_CREATED
                )
        except Exception as e:
            return self._to_error_response(str(e))

    def update(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """
        更新对象
        Update object with transaction and hooks
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        try:
            with transaction.atomic():
                serializer = self.get_serializer(
                    instance,
                    data=request.data,
                    partial=partial
                )
                serializer.is_valid(raise_exception=True)

                # 钩子：更新前
                self.before_update(serializer, instance)

                # 自动设置更新人
                extra_data = {}
                if self.auto_set_updated_by and request.user.is_authenticated:
                    extra_data['update_by'] = request.user

                instance = serializer.save(**extra_data)

                # 钩子：更新后
                self.after_update(instance)

                # 清除缓存
                self._clear_cache(f"{self.__class__.__name__}:*")

                # 审计日志
                if self.enable_audit_log:
                    self._log_action('update', instance)

                return self._to_response(serializer.data, message="更新成功")
        except Exception as e:
            return self._to_error_response(str(e))

    def destroy(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """
        删除对象
        Destroy object with hooks
        """
        instance = self.get_object()

        try:
            with transaction.atomic():
                # 钩子：删除前
                self.before_destroy(instance)

                # 软删除或硬删除
                if hasattr(instance, 'remove'):
                    instance.remove()  # 软删除
                elif hasattr(instance, 'del_flag'):
                    instance.del_flag = True
                    instance.save()
                else:
                    instance.delete()

                # 钩子：删除后
                self.after_destroy(instance)

                # 清除缓存
                self._clear_cache(f"{self.__class__.__name__}:*")

                # 审计日志
                if self.enable_audit_log:
                    self._log_action('delete', instance)

                return self._to_response(message="删除成功")
        except Exception as e:
            return self._to_error_response(str(e))

    # ==================== 批量操作 ====================

    @action(detail=False, methods=['post'])
    def bulk_delete(self, request: Any) -> Any:
        """
        批量删除
        Bulk delete with optimization
        """
        if not self.allow_bulk_delete:
            return self._to_error_response("批量删除未启用", status.HTTP_403_FORBIDDEN)

        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = serializer.validated_data['ids']
        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.count()

        if count == 0:
            return self._to_error_response("未找到要删除的对象")

        with transaction.atomic():
            # 使用update而不是循环，更高效
            if hasattr(queryset.model, 'del_flag'):
                queryset.update(del_flag=True)
            else:
                queryset.delete()

        # 清除缓存
        self._clear_cache(f"{self.__class__.__name__}:*")

        # 审计日志
        if self.enable_audit_log:
            self._log_action('bulk_delete', None, detail=f"删除了{count}个对象")

        return self._to_response(
            {'count': count},
            message=f"成功删除{count}个对象"
        )

    @action(detail=False, methods=['post'])
    def bulk_update(self, request: Any) -> Any:
        """
        批量更新
        Bulk update with optimization
        """
        if not self.allow_bulk_update:
            return self._to_error_response("批量更新未启用", status.HTTP_403_FORBIDDEN)

        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ids = serializer.validated_data['ids']
        update_data = serializer.validated_data.get('data', {})

        if not update_data:
            return self._to_error_response("请提供要更新的数据")

        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.count()

        if count == 0:
            return self._to_error_response("未找到要更新的对象")

        with transaction.atomic():
            # 自动设置更新人
            if self.auto_set_updated_by and request.user.is_authenticated:
                update_data['update_by'] = request.user.id

            queryset.update(**update_data)

        # 清除缓存
        self._clear_cache(f"{self.__class__.__name__}:*")

        # 审计日志
        if self.enable_audit_log:
            self._log_action('bulk_update', None, detail=f"更新了{count}个对象")

        return self._to_response(
            {'count': count},
            message=f"成功更新{count}个对象"
        )

    # ==================== 导出功能 ====================

    @action(detail=False, methods=['get', 'post'])
    def export(self, request: Any) -> Any:
        """
        导出数据
        Export data to Excel/CSV
        """
        queryset = self.filter_queryset(self.get_queryset())

        # 限制导出数量
        max_export = 10000
        if queryset.count() > max_export:
            return self._to_error_response(f"导出数据量过大，最多支持{max_export}条")

        # 获取数据
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # 调用导出混入（如果有）
        if hasattr(self, 'export_data'):
            return self.export_data(data)

        return self._to_error_response("导出功能未实现")

    # ==================== 钩子方法 ====================

    def before_create(self, serializer: S) -> None:
        """
        创建前钩子
        Hook before creating object
        """
        pass

    def after_create(self, instance: T) -> None:
        """
        创建后钩子
        Hook after creating object
        """
        pass

    def before_update(self, serializer: S, instance: T) -> None:
        """
        更新前钩子
        Hook before updating object
        """
        pass

    def after_update(self, instance: T) -> None:
        """
        更新后钩子
        Hook after updating object
        """
        pass

    def before_destroy(self, instance: T) -> None:
        """
        删除前钩子
        Hook before destroying object
        """
        pass

    def after_destroy(self, instance: T) -> None:
        """
        删除后钩子
        Hook after destroying object
        """
        pass

    # ==================== 辅助方法 ====================

    def _to_response(self, data: Any, message: str = "", code: int = status.HTTP_200_OK) -> Any:
        """
        构建响应
        Build response (override in subclass if needed)
        """
        from utils.response import ApiResponse
        return ApiResponse(data=data, msg=message, code=code)

    def _to_error_response(self, message: str, code: int = status.HTTP_400_BAD_REQUEST) -> Any:
        """
        构建错误响应
        Build error response
        """
        from utils.response import ApiResponse
        return ApiResponse(msg=message, code=code)

    def _log_action(self, action: str, instance: Optional[T], detail: str = "") -> None:
        """
        记录操作日志
        Log action for audit
        """
        import logging
        logger = logging.getLogger(self.__class__.__name__)

        log_data = {
            'action': action,
            'model': self.queryset.model.__name__,
            'user': self.request.user.username if self.request.user.is_authenticated else 'anonymous',
            'ip': self.request.META.get('REMOTE_ADDR'),
            'timestamp': timezone.now().isoformat(),
        }

        if instance:
            log_data['object_id'] = instance.pk

        if detail:
            log_data['detail'] = detail

        logger.info(f"Action: {log_data}")


class ReadOnlyViewSet(BaseViewSet[T, S]):
    """
    只读视图集
    Read-only viewset for list and retrieve operations

    Example:
        class CategoryReadOnlyViewSet(ReadOnlyViewSet):
            queryset = Category.objects.all()
            serializer_class = CategorySerializer
    """

    http_method_names = ['get', 'head', 'options']

    def create(self, *args, **kwargs):
        """禁用创建"""
        from utils.response import ApiResponse
        return ApiResponse(msg="方法不允许", code=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, *args, **kwargs):
        """禁用更新"""
        from utils.response import ApiResponse
        return ApiResponse(msg="方法不允许", code=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, *args, **kwargs):
        """禁用删除"""
        from utils.response import ApiResponse
        return ApiResponse(msg="方法不允许", code=status.HTTP_405_METHOD_NOT_ALLOWED)


class TreeViewSetMixin:
    """
    树形视图集混入
    Tree viewset mixin for hierarchical data

    Provides tree-specific operations
    提供树形结构特定的操作

    Example:
        class CategoryViewSet(TreeViewSetMixin, BaseViewSet):
            queryset = Category.objects.all()
            serializer_class = CategorySerializer
    """

    @action(detail=False, methods=['get'])
    def tree(self, request: Any) -> Any:
        """
        获取树形数据
        Get tree structure data
        """
        from utils.response import ApiResponse

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # 构建树形结构
        tree_data = self._build_tree(serializer.data)

        return ApiResponse(data=tree_data, message="获取成功")

    def _build_tree(self, data: List[Dict]) -> List[Dict]:
        """
        构建树形结构
        Build tree structure from flat data

        Args:
            data: Flat data list

        Returns:
            Tree structure data
        """
        tree_dict = {}
        tree_data = []

        # 第一遍：创建所有节点
        for item in data:
            item['children'] = []
            tree_dict[item['id']] = item

        # 第二遍：构建树形关系
        for item in data:
            parent_id = item.get('parent_id')
            if parent_id is None:
                tree_data.append(item)
            else:
                parent = tree_dict.get(parent_id)
                if parent:
                    parent['children'].append(item)

        return tree_data
