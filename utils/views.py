import os

from django.db import transaction
from django.db.models.query import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.baseDRF import CoreViewSet
from utils.serializer import TreeSerializer


class FileViewSet(CoreViewSet):
    """
    公共附件管理视图集: 增删改查
    """

    queryset = ""
    serializer_class = ""
    search_fields = ()
    filter_fields = ()
    ordering_fields = ("id",)
    # permission_classes = (RolePermission,)
    authentication_classes = (JWTAuthentication,)
    filter_backends = (DjangoFilterBackend, SearchFilter, OrderingFilter)

    def __init__(self, model, attachment_url="url", **kwargs):
        """
        初始化 FileViewSet。

        :param model: 附件模型
        :param attachment_url: 附件 URL 字段名
        """
        super().__init__(**kwargs)
        self.model = model  # 附件模型
        self.attachment_url = attachment_url  # 附件 URL 字段名

    def get_queryset(self):
        """获取所有附件的查询集"""
        return self.model.objects.all()

    def get_serializer_class(self):
        """
        动态获取序列化器类，根据附件模型生成序列化器
        """
        return type(
            "AttachmentSerializer",
            (serializers.ModelSerializer,),
            {"Meta": type("Meta", (object,), {"model": self.model, "fields": "__all__"})},
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """
        删除指定的附件，包括物理文件的删除
        """
        pk = kwargs.get("pk")  # 从 URL 参数获取附件 ID
        attachment = self.model.objects.get(id=pk)  # 获取附件实例

        # 构建文件的完整路径
        url = f"../media/{str(getattr(attachment, self.attachment_url))}"

        # 检查文件是否存在并删除
        if os.path.exists(url):
            os.remove(url)
            print("文件已删除")
        else:
            print("你要删除的文件不存在")

        return super().destroy(request, *args, **kwargs)  # 调用父类的 destroy 方法


class TreeAPIView(APIView):
    """
    自定义树结构View
    """

    queryset = None  # 默认查询集为None
    permission_classes = (AllowAny,)  # 只有认证用户可以访问
    authentication_classes = (JWTAuthentication,)  # 使用JWT认证
    # permission_classes = (IsAuthenticated,)  # 只有认证用户可以访问

    def get_queryset(self):
        """获取查询集，如果未定义，则抛出异常"""
        assert self.queryset is not None, f"Check {self.__class__.__name__} `queryset` & `get_queryset()`"
        if isinstance(self.queryset, QuerySet):
            # 如果查询集是QuerySet类型，则返回所有记录
            return self.queryset.all()
        return self.queryset

    def get(self, request):
        """
        处理GET请求，返回树形结构数据
        """
        data = self.get_queryset()  # 获取数据
        serializer = TreeSerializer(data, many=True)  # 序列化数据

        tree_dict = {}
        tree_data = []

        # 将序列化后的数据存储在字典中，方便后续查找
        for item in serializer.data:
            tree_dict[item["id"]] = item
            tree_dict[item["id"]]["children"] = []  # 初始化子节点列表

        # 构建树形结构
        for item in tree_dict.values():
            if item["pid"] is None:  # 如果没有父节点，则为根节点
                tree_data.append(item)
            else:
                # 如果有父节点，则将当前节点添加到其父节点的children中
                parent = tree_dict.get(item["pid"])
                if parent:  # 确保父节点存在
                    parent["children"].append(item)

        return Response(tree_data)  # 返回构建好的树形结构


class TreeTwoAPIView(ListAPIView):
    """自定义树结构View"""

    serializer_class = TreeSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        serializer = self.get_serializer(queryset, many=True)
        tree_data = self.build_tree(serializer.data)

        return self.get_paginated_response(tree_data) if page is not None else Response(tree_data)

    def build_tree(self, data: list) -> list:
        """构建树结构数据"""
        tree_dict = {item["id"]: {**item, "children": []} for item in data}
        tree_data = []

        for item in data:
            pid = item["pid"]
            if pid in tree_dict:
                tree_dict[pid]["children"].append(tree_dict[item["id"]])
            else:
                tree_data.append(tree_dict[item["id"]])

        return tree_data
