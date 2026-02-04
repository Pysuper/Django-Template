"""
Mixin Classes / 混入类

提供可复用的功能混入类
"""

from typing import Any, Dict, List, Optional
from rest_framework import status
from rest_framework.decorators import action
from django.core.cache import cache
from django.db import transaction
from django.http import StreamingHttpResponse


class CacheMixin:
    """
    缓存混入类
    Cache mixin for viewsets

    提供缓存相关的通用方法
    Provides common caching methods

    Example / 示例:
        class MyViewSet(CacheMixin, BaseViewSet):
            cache_timeout = 600  # 10分钟
    """

    cache_timeout = 300  # 5分钟
    cache_prefix = 'view'

    def get_cache_key(self, *args, **kwargs) -> str:
        """
        生成缓存键
        Generate cache key

        Returns:
            Cache key string
        """
        import hashlib
        params = str(hash(frozenset(self.request.query_params.items())))
        return f"{self.cache_prefix}:{self.__class__.__name__}:{self.action}:{params}"

    def get_cached_data(self, cache_key: str) -> Optional[Any]:
        """
        从缓存获取数据
        Get data from cache

        Args:
            cache_key: Cache key

        Returns:
            Cached data or None
        """
        return cache.get(cache_key)

    def set_cached_data(self, cache_key: str, data: Any) -> None:
        """
        设置数据到缓存
        Set data to cache

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        cache.set(cache_key, data, self.cache_timeout)

    def clear_cache(self, pattern: str = None) -> None:
        """
        清除缓存
        Clear cache by pattern

        Args:
            pattern: Cache key pattern (optional)
        """
        if pattern:
            keys = cache.keys(f"{pattern}*")
            if keys:
                cache.delete_many(keys)
        else:
            cache.delete_many([self.get_cache_key()])


class ExportMixin:
    """
    导出混入类
    Export mixin for viewsets

    支持导出为Excel、CSV等格式
    Supports export to Excel, CSV, etc.

    Example / 示例:
        class MyViewSet(ExportMixin, BaseViewSet):
            export_formats = ['xlsx', 'csv']
    """

    export_formats = ['xlsx', 'csv']
    export_filename_prefix = 'export'
    export_timeout = 300  # 5分钟超时

    def export_data(self, data: List[Dict[str, Any]]) -> StreamingHttpResponse:
        """
        导出数据
        Export data based on format

        Args:
            data: Data to export

        Returns:
            StreamingHttpResponse with file
        """
        export_format = self.request.query_params.get('format', 'xlsx')

        if export_format == 'csv':
            return self._export_csv(data)
        elif export_format == 'xlsx':
            return self._export_xlsx(data)
        else:
            raise ValueError(f"不支持的导出格式: {export_format}")

    def _export_csv(self, data: List[Dict[str, Any]]) -> StreamingHttpResponse:
        """
        导出为CSV
        Export to CSV format

        Args:
            data: Data to export

        Returns:
            CSV file response
        """
        import csv
        from io import StringIO
        from datetime import datetime

        output = StringIO()
        if data:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)

            # 添加BOM以支持Excel中文
            output.write('\ufeff')
            writer.writeheader()
            writer.writerows(data)

        response = StreamingHttpResponse(
            output.getvalue().encode('utf-8'),
            content_type='text/csv; charset=utf-8'
        )

        filename = f"{self.export_filename_prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def _export_xlsx(self, data: List[Dict[str, Any]]) -> StreamingHttpResponse:
        """
        导出为Excel
        Export to Excel format

        Args:
            data: Data to export

        Returns:
            Excel file response
        """
        try:
            import xlsxwriter
            from io import BytesIO
            from datetime import datetime

            output = BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet('Data')

            # 写入数据
            if data:
                # 表头
                headers = list(data[0].keys())
                for col, header in enumerate(headers):
                    worksheet.write(0, col, header)

                # 数据行
                for row_idx, row_data in enumerate(data, start=1):
                    for col_idx, value in enumerate(row_data.values()):
                        worksheet.write(row_idx, col_idx, value)

            workbook.close()
            output.seek(0)

            response = StreamingHttpResponse(
                output.read(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

            filename = f"{self.export_filename_prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        except ImportError:
            raise ValueError("xlsxwriter未安装，请使用: pip install xlsxwriter")

    @action(detail=False, methods=['get'])
    def export(self, request: Any) -> StreamingHttpResponse:
        """
        导出数据
        Export data endpoint

        Query params / 查询参数:
            - format: 导出格式 (csv, xlsx)
            - fields: 要导出的字段 (逗号分隔，可选)

        Returns:
            File response
        """
        queryset = self.filter_queryset(self.get_queryset())

        # 限制导出数量
        max_export = 10000
        count = queryset.count()
        if count > max_export:
            raise ValueError(f"导出数据量过大，最多支持{max_export}条")

        # 获取数据
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        # 字段过滤
        fields = request.query_params.get('fields')
        if fields:
            field_list = fields.split(',')
            data = [{k: v for k, v in item.items() if k in field_list} for item in data]

        return self.export_data(data)


class AuditMixin:
    """
    审计混入类
    Audit mixin for logging operations

    记录所有重要操作
    Log all important operations

    Example / 示例:
        class MyViewSet(AuditMixin, BaseViewSet):
            pass
    """

    enable_audit_log = True
    audit_log_methods = ['create', 'update', 'destroy', 'bulk_delete', 'bulk_update']

    def _log_action(
        self,
        action: str,
        instance: Any = None,
        detail: str = ""
    ) -> None:
        """
        记录操作日志
        Log action for audit

        Args:
            action: Action name
            instance: Model instance (optional)
            detail: Additional detail (optional)
        """
        if not self.enable_audit_log:
            return

        import logging
        logger = logging.getLogger(f"{self.__class__.__name__}.audit")

        log_data = {
            'action': action,
            'user': str(self.request.user) if self.request.user.is_authenticated else 'Anonymous',
            'ip': self.request.META.get('REMOTE_ADDR'),
            'path': self.request.path,
            'method': self.request.method,
            'timestamp': str(timezone.now()),
        }

        if instance:
            log_data['model'] = instance.__class__.__name__
            log_data['object_id'] = instance.pk

        if detail:
            log_data['detail'] = detail

        logger.info(f"Audit: {log_data}")


class BulkActionMixin:
    """
    批量操作混入类
    Bulk action mixin for viewsets

    提供批量操作的通用实现
    Provides common bulk operations

    Example / 示例:
        class MyViewSet(BulkActionMixin, BaseViewSet):
            max_bulk_size = 100
    """

    max_bulk_size = 1000
    allow_bulk_create = False
    allow_bulk_update = True
    allow_bulk_delete = True

    def _validate_bulk_action(self, ids: List[int]) -> None:
        """
        验证批量操作
        Validate bulk action

        Args:
            ids: List of IDs

        Raises:
            ValueError: If validation fails
        """
        if not ids:
            raise ValueError("ID列表不能为空")

        if len(ids) > self.max_bulk_size:
            raise ValueError(f"批量操作最多支持{self.max_bulk_size}条记录")

    @action(detail=False, methods=['post'])
    def bulk_create(self, request: Any) -> Any:
        """
        批量创建
        Bulk create objects

        Request body:
            {
                "items": [
                    {"name": "Item 1"},
                    {"name": "Item 2"}
                ]
            }

        Returns:
            Response with created objects
        """
        if not self.allow_bulk_create:
            raise ValueError("批量创建未启用")

        items = request.data.get('items', [])
        if not items:
            raise ValueError("items不能为空")

        self._validate_bulk_action(items)

        created_objects = []
        with transaction.atomic():
            for item_data in items:
                serializer = self.get_serializer(data=item_data)
                serializer.is_valid(raise_exception=True)
                instance = serializer.save()
                created_objects.append(serializer.data)

        return self._to_response(
            {'count': len(created_objects), 'results': created_objects},
            message=f"成功创建{len(created_objects)}条记录"
        )

    @action(detail=False, methods=['post'])
    def bulk_partial_update(self, request: Any) -> Any:
        """
        批量部分更新
        Bulk partial update (PATCH)

        Request body:
            {
                "ids": [1, 2, 3],
                "data": {"status": True}
            }

        Returns:
            Response with updated count
        """
        ids = request.data.get('ids', [])
        update_data = request.data.get('data', {})

        if not ids or not update_data:
            raise ValueError("请提供ids和data")

        self._validate_bulk_action(ids)

        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.update(**update_data)

        return self._to_response(
            {'count': count},
            message=f"成功更新{count}条记录"
        )


class RateLimitMixin:
    """
    限流混入类
    Rate limit mixin for viewsets

    提供基于用户的请求限流
    Provides rate limiting based on user

    Example / 示例:
        class MyViewSet(RateLimitMixin, BaseViewSet):
            rate_limit = '100/hour'
    """

    rate_limit = '1000/day'  # 默认限制
    rate_limit_per_user = True  # 是否每个用户单独限制

    def check_rate_limit(self) -> bool:
        """
        检查请求是否超过限流
        Check if request exceeds rate limit

        Returns:
            True if within limit, False otherwise
        """
        from django.core.cache import cache
        from django.utils import timezone

        if not self.rate_limit_per_user or not self.request.user.is_authenticated:
            return True

        user_id = self.request.user.id
        limit, period = self.rate_limit.split('/')

        cache_key = f"ratelimit:{self.__class__.__name__}:user:{user_id}:{period}"
        current_count = cache.get(cache_key, 0)

        if current_count >= int(limit):
            return False

        # 增加计数
        cache.set(cache_key, current_count + 1, timeout=3600)
        return True

    def dispatch(self, request, *args, **kwargs):
        """
        重写dispatch以应用限流
        Override dispatch to apply rate limiting
        """
        if not self.check_rate_limit():
            from rest_framework.exceptions import Throttled
            raise Throttled(f"请求过于频繁，请稍后再试 / Too many requests")

        return super().dispatch(request, *args, **kwargs)
