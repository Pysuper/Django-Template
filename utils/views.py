import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from django.core.cache import cache
from django.db import transaction
from django.db.models import Model, QuerySet
from django.http import FileResponse, HttpRequest, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.baseDRF import CoreViewSet
from utils.decorators import handle_business_exceptions
from utils.error import BusinessError, ErrorCode
from utils.response import ApiResponse, success_response
from utils.serializer import TreeSerializer

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    """标准分页器"""

    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 1000
    page_query_param = "page"


class BaseViewSet(CoreViewSet):
    """基础视图集"""

    pagination_class = StandardPagination
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)

    def get_serializer_context(self) -> Dict[str, Any]:
        """获取序列化器上下文"""
        context = super().get_serializer_context()
        context.update({"request": self.request, "format": self.format_kwarg, "view": self})
        return context

    @handle_business_exceptions()
    def create(self, request: HttpRequest, *args, **kwargs) -> ApiResponse:
        """创建资源"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        return success_response(data=serializer.data, message=_("创建成功"), code=status.HTTP_201_CREATED)

    @handle_business_exceptions()
    def update(self, request: HttpRequest, *args, **kwargs) -> ApiResponse:
        """更新资源"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(data=serializer.data, message=_("更新成功"))

    @handle_business_exceptions()
    def destroy(self, request: HttpRequest, *args, **kwargs) -> ApiResponse:
        """删除资源"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return success_response(message=_("删除成功"))

    def perform_create(self, serializer: serializers.Serializer) -> Model:
        """执行创建"""
        return serializer.save()

    def perform_update(self, serializer: serializers.Serializer) -> Model:
        """执行更新"""
        return serializer.save()

    def perform_destroy(self, instance: Model) -> None:
        """执行删除"""
        instance.delete()


class FileViewSet(BaseViewSet):
    """文件管理视图集"""

    def __init__(self, model: Type[Model], file_field: str = "file", **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.file_field = file_field

    def get_queryset(self) -> QuerySet:
        """获取查询集"""
        return self.model.objects.all()

    def get_serializer_class(self) -> Type[serializers.ModelSerializer]:
        """获取序列化器类"""
        return type(
            "FileSerializer",
            (serializers.ModelSerializer,),
            {"Meta": type("Meta", (object,), {"model": self.model, "fields": "__all__"})},
        )

    @action(detail=True, methods=["get"])
    def download(self, request: HttpRequest, pk: int = None) -> FileResponse:
        """下载文件"""
        instance = self.get_object()
        file_field = getattr(instance, self.file_field)
        if not file_field:
            raise BusinessError(error_code=ErrorCode.RESOURCE_NOT_FOUND, message=_("文件不存在"))

        response = FileResponse(file_field.open())
        response["Content-Type"] = "application/octet-stream"
        response["Content-Disposition"] = f'attachment; filename="{file_field.name}"'
        return response

    @transaction.atomic
    def perform_destroy(self, instance: Model) -> None:
        """执行删除"""
        file_field = getattr(instance, self.file_field)
        if file_field:
            file_path = file_field.path
            if os.path.exists(file_path):
                os.remove(file_path)
        super().perform_destroy(instance)


class TreeAPIView(APIView):
    """树形结构视图"""

    queryset = None
    serializer_class = TreeSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    cache_timeout = 300  # 缓存5分钟

    def get_queryset(self) -> QuerySet:
        """获取查询集"""
        assert self.queryset is not None, f"{self.__class__.__name__} 必须设置 queryset 属性或重写 get_queryset() 方法"
        return self.queryset.all() if isinstance(self.queryset, QuerySet) else self.queryset

    def get_cache_key(self) -> str:
        """获取缓存键"""
        return f"tree_data_{self.__class__.__name__}"

    def get_tree_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """构建树形数据"""
        tree_dict = {}
        tree_data = []

        # 构建节点字典
        for item in data:
            item["children"] = []
            tree_dict[item["id"]] = item

        # 构建树形结构
        for item in data:
            parent_id = item.get("parent_id") or item.get("pid")
            if parent_id is None:
                tree_data.append(item)
            else:
                parent = tree_dict.get(parent_id)
                if parent:
                    parent["children"].append(item)

        return tree_data

    @method_decorator(cache_page(cache_timeout))
    def get(self, request: HttpRequest) -> ApiResponse:
        """获取树形数据"""
        # 尝试从缓存获取
        cache_key = self.get_cache_key()
        tree_data = cache.get(cache_key)

        if tree_data is None:
            # 从数据库获取并构建树形数据
            queryset = self.get_queryset()
            serializer = self.serializer_class(queryset, many=True)
            tree_data = self.get_tree_data(serializer.data)

            # 缓存数据
            cache.set(cache_key, tree_data, self.cache_timeout)

        return success_response(data=tree_data)


class CacheViewMixin:
    """缓存视图混入类"""

    cache_timeout = 300  # 缓存5分钟

    def get_cache_key(self) -> str:
        """获取缓存键"""
        return f"view_data_{self.__class__.__name__}"

    def get_cached_data(self) -> Optional[Any]:
        """获取缓存数据"""
        return cache.get(self.get_cache_key())

    def set_cached_data(self, data: Any) -> None:
        """设置缓存数据"""
        cache.set(self.get_cache_key(), data, self.cache_timeout)


class ExportMixin:
    """导出功能混入类"""

    export_serializer_class = None
    export_filename = "export"
    export_type = "xlsx"

    def get_export_serializer_class(self) -> Type[serializers.Serializer]:
        """获取导出序列化器类"""
        assert self.export_serializer_class is not None, (
            f"{self.__class__.__name__} 必须设置 export_serializer_class 属性"
            "或重写 get_export_serializer_class() 方法"
        )
        return self.export_serializer_class

    def get_export_filename(self) -> str:
        """获取导出文件名"""
        return f"{self.export_filename}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def get_export_data(self, queryset: QuerySet) -> List[Dict[str, Any]]:
        """获取导出数据"""
        serializer_class = self.get_export_serializer_class()
        serializer = serializer_class(queryset, many=True)
        return serializer.data

    @action(detail=False, methods=["get"])
    def export(self, request: HttpRequest) -> StreamingHttpResponse:
        """导出数据"""
        queryset = self.filter_queryset(self.get_queryset())
        data = self.get_export_data(queryset)

        if self.export_type == "xlsx":
            return self.export_xlsx(data)
        elif self.export_type == "csv":
            return self.export_csv(data)
        else:
            raise BusinessError(error_code=ErrorCode.PARAM_ERROR, message=_("不支持的导出类型"))

    def export_xlsx(self, data: List[Dict[str, Any]]) -> StreamingHttpResponse:
        """导出Excel"""
        import xlsxwriter
        from io import BytesIO

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet()

        # 写入表头
        headers = data[0].keys() if data else []
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)

        # 写入数据
        for row, item in enumerate(data, 1):
            for col, value in enumerate(item.values()):
                worksheet.write(row, col, value)

        workbook.close()
        output.seek(0)

        response = StreamingHttpResponse(
            output, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f'attachment; filename="{self.get_export_filename()}.xlsx"'
        return response

    def export_csv(self, data: List[Dict[str, Any]]) -> StreamingHttpResponse:
        """导出CSV"""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys() if data else [])

        # 写入表头
        writer.writeheader()

        # 写入数据
        writer.writerows(data)

        response = StreamingHttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{self.get_export_filename()}.csv"'
        return response
