"""
Pagination Classes / 分页类

提供统一的分页器实现
"""

from typing import Any, Dict
from rest_framework.pagination import PageNumberPagination, CursorPagination, LimitOffsetPagination
from rest_framework.response import Response
from collections import OrderedDict


class StandardPageNumberPagination(PageNumberPagination):
    """
    标准页码分页器
    Standard page number pagination

    Features / 特性:
    - 可配置的页大小 / Configurable page size
    - 页大小限制 / Page size limit
    - 标准响应格式 / Standard response format

    Usage / 使用:
        class MyViewSet(BaseViewSet):
            pagination_class = StandardPageNumberPagination
    """

    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000
    page_query_param = 'page'

    def get_paginated_response(self, data: Any) -> Response:
        """
        返回分页响应
        Return paginated response with standard format

        Args:
            data: Paginated data

        Returns:
            Response with pagination info
        """
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('page_size', self.page.paginator.per_page),
            ('current_page', self.page.paginator.number),
            ('total_pages', self.page.paginator.num_pages),
            ('results', data)
        ]))


class LargeResultSetPagination(PageNumberPagination):
    """
    大结果集分页器
    Large result set pagination

    用于需要更大页大小的场景
    For scenarios requiring larger page sizes
    """

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 5000
    page_query_param = 'page'


class SmallResultSetPagination(PageNumberPagination):
    """
    小结果集分页器
    Small result set pagination

    用于移动端或需要小页大小的场景
    For mobile or small page size scenarios
    """

    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'


class LimitOffsetPagination(LimitOffsetPagination):
    """
    Limit/Offset分页器
    Limit/Offset pagination

    使用limit和offset进行分页，更灵活
    Use limit and offset for pagination, more flexible

    Query params / 查询参数:
    - limit: 每页数量
    - offset: 偏移量

    Example / 示例:
        /api/items/?limit=20&offset=40
    """

    default_limit = 10
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 1000

    def get_paginated_response(self, data: Any) -> Response:
        """
        返回分页响应
        Return paginated response

        Args:
            data: Paginated data

        Returns:
            Response with pagination info
        """
        return Response(OrderedDict([
            ('count', self.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class CursorPagination(CursorPagination):
    """
    游标分页器
    Cursor pagination

    适用于大数据集和时间线场景
    Suitable for large datasets and timeline scenarios

    Benefits / 优势:
    - 性能更好 / Better performance
    - 一致的数据顺序 / Consistent data order
    - 避免数据重复/遗漏 / Avoid duplicates/misses

    Query params / 查询参数:
    - cursor: 游标值
    - page_size: 每页数量

    Example / 示例:
        class TimeLineViewSet(BaseViewSet):
            pagination_class = CursorPagination
            ordering = '-create_date'
    """

    page_size = 20
    cursor_query_param = 'cursor'
    page_size_query_param = 'page_size'
    ordering = '-create_date'  # 子类需要覆盖

    def get_paginated_response(self, data: Any) -> Response:
        """
        返回分页响应
        Return paginated response

        Args:
            data: Paginated data

        Returns:
            Response with pagination info
        """
        return Response(OrderedDict([
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class InfiniteScrollPagination(PageNumberPagination):
    """
    无限滚动分页器
    Infinite scroll pagination

    适用于前端无限滚动加载
    Suitable for frontend infinite scroll loading

    Features / 特性:
    - 简化的响应格式 / Simplified response format
    - 高性能 / High performance
    - 移动端友好 / Mobile-friendly

    Example / 示例:
        class ProductViewSet(BaseViewSet):
            pagination_class = InfiniteScrollPagination
    """

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data: Any) -> Response:
        """
        返回简化的分页响应
        Return simplified paginated response

        Args:
            data: Paginated data

        Returns:
            Simplified response
        """
        return Response(OrderedDict([
            ('has_more', self.page.has_next()),
            ('page', self.page.number),
            ('results', data)
        ]))
