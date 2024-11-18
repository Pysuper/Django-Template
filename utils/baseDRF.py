import os
import time

import django_filters.rest_framework
from django.conf import settings
from django.core.cache import cache
from django.db import models, transaction
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
    """

    # name = None
    update_date = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    status = models.BooleanField(default=True, editable=False, verbose_name="状态")
    del_flag = models.BooleanField(default=False, editable=False, verbose_name="删除")
    remark = models.CharField(max_length=500, null=True, blank=True, verbose_name="备注")
    name = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="名称")
    code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="编码")
    create_date = models.DateTimeField(auto_now_add=True, editable=False, db_index=True, verbose_name="创建时间")
    create_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="创建人",
        related_name="%(class)s_created",
    )
    update_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="更新人",
        related_name="%(class)s_updated",
    )

    class Meta:
        ordering = ["-id"]  # 默认按 ID 降序排列
        abstract = True  # 声明为抽象类，不会在数据库中创建表

    def __str__(self):
        """默认就是name，不是name的就自定义"""
        return self.name

    def remove(self):
        """标记对象为已删除"""
        self.del_flag = True
        self.save()

    def restore(self):
        """恢复被标记为已删除的对象"""
        self.del_flag = False
        self.save()

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
    自定义序列化器基类，用于序列化 BaseEntity 中的公共字段
    """

    def to_representation(self, instance):
        """重写返回值中的公共字段"""
        res = super().to_representation(instance)
        # 这里直接用instance，就不需要序列化器中增加这个字段
        res["createBy"] = instance.username if instance.create_by else None
        res["updateBy"] = instance.username if instance.update_by else None
        # 格式化时间：年月日 时分秒
        res["createTime"] = instance.create_date.strftime("%Y-%m-%d")
        res["updateTime"] = instance.update_date.strftime("%Y-%m-%d")
        # 当前对象的状态
        res["status"] = "1" if res.pop("status") else "2"
        # 自定义返回的字段
        return res


class QueryFilter(django_filters.rest_framework.FilterSet):
    """
    自定义查询过滤器，增加常用功能
    """

    del_flag = django_filters.rest_framework.BooleanFilter(field_name="del_flag", lookup_expr="exact", required=False)
    create_date = django_filters.rest_framework.DateFromToRangeFilter(field_name="create_date", label="创建日期范围")
    update_date = django_filters.rest_framework.DateFromToRangeFilter(field_name="update_date", label="更新日期范围")
    search = django_filters.rest_framework.CharFilter(method="filter_by_all_fields", label="模糊搜索")

    class Meta:
        model = BaseEntity
        fields = ["del_flag", "create_date", "update_date"]  # 定义需要查询的字段

    def filter_queryset(self, queryset):
        """重写 filter_queryset 方法，自动过滤 del_flag=True 的数据"""
        queryset = queryset.filter(del_flag=False)
        queryset = super().filter_queryset(queryset)
        return queryset

    def filter_by_all_fields(self, queryset, name, value):
        """模糊搜索，搜索所有文本字段"""
        for field in self.Meta.model._meta.fields:
            if isinstance(field, (CharField, TextField)):
                queryset = queryset.filter(**{f"{field.name}__icontains": value})
        return queryset


class CoreViewSet(viewsets.ModelViewSet):
    """
    增删改查API基类，提供基本的CRUD操作和自定义响应
    """

    # 自定义权限标识符
    role_type = ""

    # 查询集，定义视图集操作的数据集
    queryset = ""

    # 针对外键的表进行预加载
    # queryset = User.objects.all().select_related("dept")

    # 针对1对多和多对多的预加载
    # queryset = queryset.prefetch_related("roles")

    # 过滤字段，定义允许过滤的字段列表
    filter_fields = []
    # 1. status在数据库中是布尔值, 但序列化器会转换为"1"/"2"字符串
    # 2. gender在数据库中是1/2整数, 前端传入"1"/"2"字符串
    # filter_fields只能处理完全相等的情况,无法处理字符串和整数/布尔值的转换
    # 所以status需要用filterset_fields,而gender可以保留在filter_fields中
    # filterset_fields 提供了更灵活的过滤配置，允许自定义过滤行为，而 filter_fields 只支持简单的直接字段匹配
    filterset_fields = []

    # 搜索字段，定义允许搜索的字段列表
    # search_fields用于模糊搜索,不适合status和gender这种精确匹配的字段
    # search_fields 是依赖 ?search= 参数来工作的，前端没有search=参数则无法使用模糊搜索
    search_fields = []

    # 序列化类，定义用于序列化数据的类
    serializer_class = ""

    # 权限类，定义访问此视图集的权限
    permission_classes = []

    # 过滤器类，自定义查询过滤器
    # filter_class = QueryFilter

    # 分页类，定义用于分页的类
    pagination_class = LargePagination

    # 过滤后端，定义支持的过滤和排序后端
    filter_backends = (
        django_filters.rest_framework.DjangoFilterBackend,  # 提供基本的过滤功能，并实现了filter_queryset方法。
        SearchFilter,  # 提供排序功能，不负责过滤查询集。
        OrderingFilter,  # 提供全文搜索功能，可以与其他过滤器结合使用
    )

    # 允许的HTTP方法，限制只允许的请求方法
    # http_method_names = ["POST", "DELETE", "PUT", "GET"]

    # 设置缓存的Key
    # cache_key = f"{self.__class__.__name__}_{request.user.id}_list_cache"

    # 解析器类，定义请求内容解析器的类型列表
    # parser_classes = []

    # 渲染器类，定义用于响应的渲染器的类型列表
    # renderer_classes = []

    # 验证类，定义用于请求的身份验证的类型列表
    # authentication_classes = []

    # 视图名称，定义用于界面展示的名称
    # view_name = ""

    # 分页大小查询参数，允许客户端指定分页大小的参数名
    # pagination_query_param = "page_size"

    # 排序字段，允许查询集基于该字段进行默认排序
    # ordering = []

    # 排序字段选项，允许客户端基于这些字段指定排序顺序
    # ordering_fields = []

    # 动作映射，定义 HTTP 方法与动作的对应关系
    # action_map = {}

    # 查询集类，定义如何获取查询集的类
    # queryset_class = None

    # 访问频率限制
    # throttle_classes = [UserRateThrottle]

    # 自定义元数据类
    # metadata_class = CustomMetadata

    # 默认序列化类
    # default_serializer_class = DefaultSerializer

    # 不同动作使用不同的序列化类
    # action_serializers = {
    #     "list": ListSerializer,
    #     "retrieve": RetrieveSerializer,
    #     "create": CreateSerializer,
    #     "update": UpdateSerializer,
    # }

    @property
    def perms_map(self):
        if self.role_type is None:
            return ()  # 如果未设置 role_type，返回空权限映射
        return (
            {"*": "admin"},
            {"*": self.role_type + "_all"},
            {"get": self.role_type + "_list"},
            {"post": self.role_type + "_create"},
            {"put": self.role_type + "_edit"},
            {"delete": self.role_type + "_delete"},
        )

    def create(self, request, *args, **kwargs):
        """
        创建新的对象，并设置创建人和更新人
        """
        # 设置创建人、更新人
        request.data.update({"create_by": request.user.id, "update_by": request.user.id})

        # 校验数据，保存对象
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        logger.info(f"创建成功: {serializer.data}")
        return JsonResult(data=serializer.data, code=201, msg="创建成功", status=status.HTTP_200_OK, headers=headers)

    def destroy(self, request, *args, **kwargs):
        """
        删除指定的对象
        """
        instance = self.get_object()
        try:
            self.perform_destroy(instance)  # 执行删除操作
            logger.info(f"删除成功: {instance}")
            return JsonResult(data={}, msg="删除成功", code=200, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"删除失败: {str(e)}")
            return JsonResult(data={}, msg=f"删除失败：{e}", code=400, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        更新指定的对象，并设置更新人
        """
        instance = self.get_object()
        request.data["update_by"] = request.user.id
        # 获取序列化器并传入实例和请求数据， partial=True 允许部分更新
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        # TODO: 这里是否需要通过这种方式处理？
        if "status" in request.data:
            # 由于状态字段的特殊性，不能直接通过序列化器更新，需要单独处理
            instance.status = request.data["status"]
            instance.save(update_fields=["status"])

        # 验证数据是否有效
        if serializer.is_valid(raise_exception=False):
            # 执行更新操作
            self.perform_update(serializer)

            # 判断实例是否有预取对象缓存
            if hasattr(instance, "_prefetched_objects_cache"):  # 清除实例的预取缓存
                instance._prefetched_objects_cache = {}

            logger.info(f"更新成功: {serializer.data}")
            return JsonResult(data=serializer.data, msg="更新成功", code=200, status=status.HTTP_200_OK)
        else:
            # 处理验证失败的情况
            errors = serializer.errors
            error_messages = []
            for field, messages in errors.items():
                for message in messages:
                    error_messages.append(f"{field}: {message}")
            logger.error("更新失败: 数据验证未通过，错误信息: " + ", ".join(error_messages))
            return JsonResult(
                data={}, msg="更新失败：" + ", ".join(error_messages), code=400, status=status.HTTP_400_BAD_REQUEST
            )

    def list(self, request, *args, **kwargs):
        """
        列出所有对象，支持分页和过滤
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return JsonResult(data=serializer.data, msg="获取成功", code=200, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """
        根据ID检索单个对象
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return JsonResult(data=serializer.data, msg="获取成功", code=200, status=status.HTTP_200_OK)

    def get_queryset(self):
        """
        获取对象的查询集，支持根据日期范围过滤、搜索和排序
        """
        cache_key = self.get_cache_key()
        cached_queryset = cache.get(cache_key)
        if cached_queryset:
            return cached_queryset

        # 处理查询参数，支持日期范围和其他过滤条件
        query_params = self.request.query_params
        range_filters = {}
        other_filters = {}

        # 动态获取分页参数的key
        # pagination_keys = []
        # if hasattr(self, "pagination_class") and self.pagination_class is not None:
        #     pagination_keys = list(self.pagination_class.page_query_params)

        for item in query_params:
            # 跳过分页参数
            if item in ["page", "current", "size", "page_size"]:
                continue

            params = query_params.get(item, None)
            # 处理日期时间范围查询
            if "date" in item or "time" in item:
                if "," in params:
                    range_filters[item + "__range"] = params.split(",")  # 添加范围过滤
                else:
                    range_filters[item] = params
            # 处理其他查询参数
            elif params:
                # other_filters[item] = params    # 精准搜索
                other_filters[f"{item}__icontains"] = params  # 模糊搜索

        # 过滤已标记为删除的对象,并添加其他过滤条件
        queryset = super().get_queryset().filter(del_flag=False)
        if range_filters:
            queryset = queryset.filter(**range_filters)
        if other_filters:
            # 这里的搜索是匹配搜索，而不是模糊搜索
            queryset = queryset.filter(**other_filters)
        # cache.set(cache_key, queryset, timeout=60 * 5)  # 缓存5分钟
        return queryset

    # def get_serializer_class(self):
    #     """根据不同的动作选择不同的序列化器，常与 action_serializers 一起使用"""
    #     return self.action_serializers.get(self.action, self.default_serializer_class)

    # def get_permissions(self):
    #     """动态获取权限类，允许为不同的操作设置不同的权限要求"""
    #     if self.action == "list":
    #         return [IsAuthenticated()]
    #     elif self.action in ["create", "update", "destroy"]:
    #         return [IsAdminUser()]
    #     return super().get_permissions()

    def get_object(self):
        """在检索和更新操作中获取单个对象，可以自定义此方法以增加权限检查、日志记录等"""
        obj = super().get_object()
        # 自定义逻辑，例如记录访问日志
        logger.info(f"获取对象: {obj}")
        return obj

    # def get_paginated_response(self, data):
    #     """重写分页响应方法，以支持自定义响应格式"""
    #     return JsonResult(data=data, msg="分页获取成功", code=200, status=status.HTTP_200_OK)

    # def filter_queryset(self, queryset):
    #     """自定义查询集过滤逻辑，用于基于不同的用户、权限或参数执行动态过滤"""
    #     queryset = super().filter_queryset(queryset)
    #     # 例如基于用户权限的过滤
    #     if self.request.user.is_superuser:
    #         return queryset
    #     return queryset.filter(visible_to=self.request.user)

    def get_cache_key(self):
        """用于构造缓存键的辅助方法，结合用户或查询条件生成唯一键"""
        return f"{self.__class__.__name__}_{self.request.user.id}_cache"

    @action(methods=["DELETE"], detail=False)
    def batch_delete(self, request):
        """通用批量删除"""
        ids = request.data.get("ids", [])
        queryset = self.get_queryset().filter(id__in=ids)
        # TODO：自定义 批量删除
        queryset.delete()
        logger.info(f"批量删除成功: {ids}")
        return JsonResult("数据删除成功！", code=200, status=status.HTTP_200_OK)

    @transaction.atomic
    @action(methods=["POST"], detail=False)
    def batch_update(self, request):
        """通用批量更新"""
        ids = request.data.get("ids", [])
        update_data = request.data.get("update_data", {})

        if not ids or not update_data:
            return JsonResult(msg="缺少必要的参数", code=400, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset().filter(id__in=ids)

        if not queryset.exists():
            return JsonResult(msg="未找到匹配的记录", code=404, status=status.HTTP_404_NOT_FOUND)

        updated_count = queryset.update(**update_data)
        logger.info(f"批量更新成功: {ids} with {update_data}, 更新数量: {updated_count}")

        return JsonResult(f"数据更新成功，更新数量: {updated_count}", code=200, status=status.HTTP_200_OK)

    @transaction.atomic
    @action(methods=["POST"], detail=False)
    def upload(self, request):
        """上传文件并保存"""
        file = request.FILES.get("file")
        if not file:
            return JsonResult(msg="未提供文件", code=400, status=status.HTTP_400_BAD_REQUEST)
        return self.save(request, file)

    @staticmethod
    def save(request, file):
        """保存文件到指定位置，并返回成功响应。"""
        try:
            # 生成文件名称并保存路径
            file_name = f"{file.name}_{request.user.username}_{int(time.time() * 1000)}.xlsx"
            file_path = os.path.join(settings.MEDIA_ROOT, "excels", file_name)
            with open(file_path, "wb") as f:
                for chunk in file.chunks():
                    f.write(chunk)
            logger.info(f"文件上传成功: {file_name}")
            return JsonResult("上传任务数据成功", status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            return JsonResult(msg=f"文件保存失败: {str(e)}", code=500, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=["POST"], detail=False)
    def download(self, request):
        """下载当前模型类的数据"""
        # TODO: 自定义 下载数据
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return pandas_download_excel(serializer.data)

    @action(methods=["POST"], detail=False)
    def templates(self, request):
        """根据不同模型类，下载不同的模板文件"""
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
            return JsonResult(msg=f"模板文件下载失败: {str(e)}", code=500, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
