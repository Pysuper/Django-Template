import os
import time

import django_filters.rest_framework
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models import TextField
from django.http.response import FileResponse
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.fields import CharField
from rest_framework.filters import OrderingFilter, SearchFilter

from utils.custom import LargePagination
from utils.log.logger import logger
from utils.other.excel import pandas_download_excel
from utils.response import JsonResult


# class DynamicMeta(type):
#     """
#     元类，用于动态设置Meta选项
#     """
#
#     def __new__(cls, name, bases, attrs):
#         # 创建类时动态设置Meta选项
#         if "Meta" not in attrs:
#
#             class Meta:
#                 ordering = ["id"]
#                 verbose_name = name
#                 verbose_name_plural = name
#
#             attrs["Meta"] = Meta
#         else:
#             # 如果Meta类已经存在，动态设置verbose_name和verbose_name_plural
#             attrs["Meta"].verbose_name = name
#             attrs["Meta"].verbose_name_plural = name
#         return super().__new__(cls, name, bases, attrs)
#
# class BaseEntity(models.Model, metaclass=DynamicMeta):


class BaseEntity(models.Model):
    """
    抽象基类，用于提供创建人、更新时间等公共字段
    增加了索引优化和更多实用方法
    """

    # name = None
    update_date = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_index=True)
    status = models.BooleanField(default=True, editable=False, verbose_name="状态", db_index=True)
    del_flag = models.BooleanField(default=False, editable=False, verbose_name="删除", db_index=True)
    remark = models.CharField(max_length=500, null=True, blank=True, verbose_name="备注")
    name = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="名称", db_index=True)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="编码", db_index=True)
    create_date = models.DateTimeField(auto_now_add=True, editable=False, db_index=True, verbose_name="创建时间")
    create_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="创建人",
        related_name="%(class)s_created",
        db_index=True,
    )
    update_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="更新人",
        related_name="%(class)s_updated",
        db_index=True,
    )

    class Meta:
        ordering = ["-create_date", "-id"]  # 默认按创建时间和ID降序排列
        abstract = True
        indexes = [
            models.Index(fields=["create_date", "status"]),
            models.Index(fields=["update_date", "status"]),
        ]

    def __str__(self):
        """默认返回name，如果name为空则返回code"""
        return self.name or self.code or f"{self.__class__.__name__}_{self.id}"

    def remove(self):
        """标记对象为已删除"""
        self.del_flag = True
        self.save(update_fields=["del_flag", "update_date"])

    def restore(self):
        """恢复被标记为已删除的对象"""
        self.del_flag = False
        self.save(update_fields=["del_flag", "update_date"])

    def toggle_status(self):
        """切换状态"""
        self.status = not self.status
        self.save(update_fields=["status", "update_date"])

    def update_fields(self, **kwargs):
        """批量更新字��"""
        for field, value in kwargs.items():
            if hasattr(self, field):
                setattr(self, field, value)
        self.save(update_fields=list(kwargs.keys()) + ["update_date"])

    @property
    def is_active(self):
        """检查对象是否处于活动状态"""
        return self.status and not self.del_flag

    def save(self, *args, **kwargs):
        """重写save方法，在保存时自动清理缓存"""
        from django.core.cache import cache

        cache_key = f"{self.__class__.__name__}_{self.pk}"
        cache.delete(cache_key)
        super().save(*args, **kwargs)

    def __init_subclass__(cls, **kwargs):
        """动态设置Meta选项"""
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "Meta"):

            class Meta:
                ordering = ["id"]
                verbose_name = cls.__name__
                verbose_name_plural = cls.__name__

            cls.Meta = Meta
        else:
            if not hasattr(cls.Meta, "verbose_name"):
                cls.Meta.verbose_name = cls.__name__
            if not hasattr(cls.Meta, "verbose_name_plural"):
                cls.Meta.verbose_name_plural = cls.__name__


class BaseSerializer(serializers.ModelSerializer):
    """
    自定义序列化器基类，���于序列化 BaseEntity 中的公共字段
    增加了更多序列化功能和字段处理
    """

    id = serializers.IntegerField(read_only=True)
    create_time = serializers.DateTimeField(source="create_date", read_only=True, format="%Y-%m-%d %H:%M:%S")
    update_time = serializers.DateTimeField(source="update_date", read_only=True, format="%Y-%m-%d %H:%M:%S")
    create_by_name = serializers.CharField(source="create_by.username", read_only=True)
    update_by_name = serializers.CharField(source="update_by.username", read_only=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "id",
            "name",
            "code",
            "status",
            "status_display",
            "remark",
            "create_time",
            "update_time",
            "create_by_name",
            "update_by_name",
        ]
        read_only_fields = ["id", "create_time", "update_time", "create_by_name", "update_by_name"]

    def get_status_display(self, obj):
        """获取状态的显示值"""
        return "启用" if obj.status else "禁用"

    def to_representation(self, instance):
        """重写返回值中的公共字段"""
        data = super().to_representation(instance)
        # 移除None值字段
        return {k: v for k, v in data.items() if v is not None}

    def validate_name(self, value):
        """验证name字段"""
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("名称不能为空白字符")
        return value.strip() if value else value

    def validate_code(self, value):
        """验证code字段"""
        if value and len(value.strip()) == 0:
            raise serializers.ValidationError("编码不能为空白字符")
        return value.strip().upper() if value else value

    def validate(self, attrs):
        """通用验证"""
        if not attrs.get("name") and not attrs.get("code"):
            raise serializers.ValidationError("名称和编码不能同时为空")
        return attrs

    @property
    def errors_messages(self):
        """获取格式化的错误信息"""
        if not hasattr(self, "_errors"):
            return {}
        error_messages = []
        for field, messages in self.errors.items():
            if field == "non_field_errors":
                error_messages.extend(messages)
            else:
                error_messages.extend([f"{field}: {msg}" for msg in messages])
        return {"detail": " ".join(error_messages)}


class QueryFilter(django_filters.rest_framework.FilterSet):
    """
    自定义查询过滤器，增加常用功能
    增加了更多过滤选项和高级搜索功能
    """

    # 基础字段过滤
    del_flag = django_filters.BooleanFilter(field_name="del_flag", lookup_expr="exact", required=False)
    status = django_filters.BooleanFilter(field_name="status", lookup_expr="exact", required=False)

    # 时间范围过滤
    create_date = django_filters.DateTimeFromToRangeFilter(
        field_name="create_date", label="创建日期范围", help_text="格式：YYYY-MM-DD HH:MM:SS"
    )
    update_date = django_filters.DateTimeFromToRangeFilter(
        field_name="update_date", label="更新日期范围", help_text="格式：YYYY-MM-DD HH:MM:SS"
    )

    # 高级搜索
    search = django_filters.CharFilter(method="filter_by_all_fields", label="模糊搜索")
    name_search = django_filters.CharFilter(field_name="name", lookup_expr="icontains", label="名称搜索")
    code_search = django_filters.CharFilter(field_name="code", lookup_expr="icontains", label="编码搜索")

    # 创建人和更新人过滤
    create_by = django_filters.NumberFilter(field_name="create_by_id", label="创建人ID")
    update_by = django_filters.NumberFilter(field_name="update_by_id", label="更新人ID")

    class Meta:
        model = BaseEntity
        fields = {
            "del_flag": ["exact"],
            "status": ["exact"],
            "create_date": ["gte", "lte"],
            "update_date": ["gte", "lte"],
            "name": ["exact", "icontains"],
            "code": ["exact", "icontains"],
        }

    def filter_queryset(self, queryset):
        """重写过滤方法，添加缓存支持"""
        # 获取请求参数
        params = self.request.query_params.dict() if hasattr(self, "request") else {}

        # 生成缓存key
        cache_key = f"filter__{self.request.path}__{hash(frozenset(params.items()))}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        # 默认过滤已删除数据
        queryset = queryset.filter(del_flag=False)
        queryset = super().filter_queryset(queryset)

        # 缓存结果（5分钟）
        cache.set(cache_key, queryset, timeout=300)
        return queryset

    def filter_by_all_fields(self, queryset, name, value):
        """增强的模糊搜索，支持多字段组合查询"""
        if not value:
            return queryset

        search_fields = []
        # 获取所有CharField和TextField字段
        for field in self.Meta.model._meta.fields:
            if isinstance(field, (CharField, TextField)):
                search_fields.append(models.Q(**{f"{field.name}__icontains": value}))

        # 如果没有可搜索字段，直接返回
        if not search_fields:
            return queryset

        # 使用Q对象组合多个搜索条件（OR关系）
        query = search_fields.pop()
        for item in search_fields:
            query |= item

        return queryset.filter(query).distinct()

    @property
    def qs(self):
        """重写qs属性，添加排序支持"""
        queryset = super().qs

        # 获取排序参数
        ordering = self.request.query_params.get("ordering", "-create_date")
        if ordering:
            ordering_fields = [field.strip() for field in ordering.split(",")]
            queryset = queryset.order_by(*ordering_fields)

        return queryset.distinct()


class CoreViewSet(viewsets.ModelViewSet):
    """
    增删改查API基类，提供基本的CRUD操作和自定义响应
    增加了缓存、日志、权限等高级功能
    """

    # 基础配置
    queryset = None
    serializer_class = None
    permission_classes = []
    filter_class = QueryFilter
    pagination_class = LargePagination
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    )

    # 缓存配置
    cache_time = 300  # 默认缓存5分钟
    use_cache = True  # 是否使用缓存

    # 日志配置
    enable_logging = True  # 是否启用日志
    log_methods = ["POST", "PUT", "DELETE"]  # 需要记录日志的方法

    def get_cache_key(self, **kwargs):
        """获取缓存key"""
        request = self.request
        if not request:
            return None

        params = request.query_params.dict()
        params.update(kwargs)
        return f"{self.__class__.__name__}__{request.method}__{request.path}__{hash(frozenset(params.items()))}"

    def get_from_cache(self, cache_key):
        """从缓存获取数据"""
        if not self.use_cache or not cache_key:
            return None
        return cache.get(cache_key)

    def set_to_cache(self, cache_key, data):
        """设置数据到缓存"""
        if self.use_cache and cache_key:
            cache.set(cache_key, data, self.cache_time)

    def log_operation(self, request, action, instance=None, detail=None):
        """记录操作日志"""
        if not self.enable_logging or request.method not in self.log_methods:
            return

        try:
            log_data = {
                "user": request.user.username,
                "action": action,
                "model": self.queryset.model.__name__,
                "object_id": instance.id if instance else None,
                "detail": detail or "",
                "ip": request.META.get("REMOTE_ADDR"),
                "method": request.method,
                "path": request.path,
            }
            logger.info(f"Operation Log: {log_data}")
        except Exception as e:
            logger.error(f"Log operation failed: {str(e)}")

    def create(self, request, *args, **kwargs):
        """创建对象"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save(create_by=request.user)
            self.log_operation(request, "create", instance)
            return JsonResult(data=serializer.data, msg="创建成功", code=201)
        return JsonResult(msg=serializer.errors_messages.get("detail", "创建失败"), code=400)

    def update(self, request, *args, **kwargs):
        """更新对象"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        # 清除相关缓存
        cache_key = self.get_cache_key(pk=instance.pk)
        if cache_key:
            cache.delete(cache_key)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            instance = serializer.save(update_by=request.user)
            self.log_operation(request, "update", instance)
            return JsonResult(data=serializer.data, msg="更新成功", code=200)
        return JsonResult(msg=serializer.errors_messages.get("detail", "更新失败"), code=400)

    def destroy(self, request, *args, **kwargs):
        """删除对象"""
        instance = self.get_object()

        # 清除相关缓存
        cache_key = self.get_cache_key(pk=instance.pk)
        if cache_key:
            cache.delete(cache_key)

        instance.remove()  # 使用软删除
        self.log_operation(request, "delete", instance)
        return JsonResult(msg="删除成功", code=204)

    def list(self, request, *args, **kwargs):
        """获取对象列表"""
        cache_key = self.get_cache_key()
        response_data = self.get_from_cache(cache_key)

        if response_data is None:
            queryset = self.filter_queryset(self.get_queryset())
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                response_data = self.get_paginated_response(serializer.data)
            else:
                serializer = self.get_serializer(queryset, many=True)
                response_data = JsonResult(data=serializer.data, msg="获取成功", code=200)

            self.set_to_cache(cache_key, response_data)

        return response_data

    def retrieve(self, request, *args, **kwargs):
        """获取单个对象"""
        instance = self.get_object()
        cache_key = self.get_cache_key(pk=instance.pk)
        response_data = self.get_from_cache(cache_key)

        if response_data is None:
            serializer = self.get_serializer(instance)
            response_data = JsonResult(data=serializer.data, msg="获取成功", code=200)
            self.set_to_cache(cache_key, response_data)

        return response_data

    @action(methods=["DELETE"], detail=False)
    def batch_delete(self, request):
        """批量删除"""
        ids = request.data.get("ids", [])
        if not ids:
            return JsonResult(msg="请选择要删除的数据", code=400)

        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.count()

        if count == 0:
            return JsonResult(msg="未找到要删除的数据", code=400)

        for instance in queryset:
            instance.remove()
            self.log_operation(request, "batch_delete", instance)

        return JsonResult(data={"count": count}, msg="批量删除成功", code=200)

    @action(methods=["POST"], detail=False)
    def batch_update(self, request):
        """批量更新"""
        ids = request.data.get("ids", [])
        update_data = request.data.get("data", {})

        if not ids or not update_data:
            return JsonResult(msg="参数错误", code=400)

        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.update(**update_data, update_by=request.user)

        if count > 0:
            # 清除相关缓存
            for instance in queryset:
                cache_key = self.get_cache_key(pk=instance.pk)
                if cache_key:
                    cache.delete(cache_key)
                self.log_operation(request, "batch_update", instance)

        return JsonResult(data={"count": count}, msg="批量更新成功", code=200)

    @action(methods=["POST"], detail=False)
    def export(self, request):
        """导出数据"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        # 获取要导出的字段
        fields = request.data.get("fields", None)
        if fields:
            data = [{k: v for k, v in item.items() if k in fields} for item in serializer.data]
        else:
            data = serializer.data

        # 导出为Excel
        return pandas_download_excel(
            data=data,
            filename=f"{self.queryset.model.__name__}_{time.strftime('%Y%m%d%H%M%S')}.xlsx",
        )

    @action(methods=["POST"], detail=False)
    def templates(self, request):
        """根据不同模型类，下载不同的板文件"""
        class_name = self.__class__.__name__
        file_name = f"{class_name.lower().replace('viewset', '')}.xlsx"
        file_path = os.path.join(settings.MEDIA_ROOT, "excels", file_name)

        if not os.path.exists(file_path):
            logger.error(f"模板文件不存在: {file_name}")
            return JsonResult(msg="模板文件不存在", code=404, status=status.HTTP_404_NOT_FOUND)

        try:
            response = FileResponse(open(file_path, "rb"), content_type="application/msexcel")
            response["Content-Disposition"] = f"attachment;filename={file_name}"
            logger.info(f"模板文件下载成功: {file_name}")
            return response
        except Exception as e:
            logger.error(f"模板文件下载失败: {str(e)}")
            return JsonResult(
                msg=f"模板文件下载失败: {str(e)}",
                code=500,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
