from typing import Any, Dict, Optional, Type

from django.db import models
from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.pagination import StandardResultsSetPagination
from apps.core.serializers import BaseModelSerializer


class BaseViewSet(viewsets.ModelViewSet):
    """
    基础视图集
    提供标准的CRUD操作
    包含分页、权限等通用功能
    """
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self) -> QuerySet:
        """
        获取查询集，支持软删除过滤
        """
        queryset = super().get_queryset()
        if hasattr(self.queryset.model, 'is_deleted'):
            return queryset.filter(is_deleted=False)
        return queryset

    def perform_destroy(self, instance: models.Model) -> None:
        """
        执行删除操作，支持软删除
        """
        if hasattr(instance, 'is_deleted'):
            instance.delete()
        else:
            instance.delete()

    def get_serializer_class(self) -> Type[BaseModelSerializer]:
        """
        根据action获取对应的序列化器
        """
        if self.action in ['create', 'update', 'partial_update']:
            return getattr(self, 'write_serializer_class', self.serializer_class)
        return self.serializer_class


class ReadOnlyViewSet(mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     viewsets.GenericViewSet):
    """
    只读视图集
    只提供列表和检索功能
    """
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]


class CreateListRetrieveViewSet(mixins.CreateModelMixin,
                               mixins.ListModelMixin,
                               mixins.RetrieveModelMixin,
                               viewsets.GenericViewSet):
    """
    创建列表检索视图集
    提供创建、列表和检索功能
    """
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]


class NoDeleteViewSet(mixins.CreateModelMixin,
                     mixins.ListModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    """
    无删除视图集
    提供除删除外的所有标准功能
    """
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]


class HistoryViewSet(BaseViewSet):
    """
    历史记录视图集
    支持数据历史版本管理
    """
    def get_history(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        获取对象的历史记录
        """
        instance = self.get_object()
        if not hasattr(instance, 'history'):
            return Response({'detail': '该对象不支持历史记录'})
            
        history_records = instance.history.all()
        data = []
        
        for record in history_records:
            data.append({
                'id': record.history_id,
                'date': record.history_date,
                'user': record.history_user.username if record.history_user else None,
                'type': record.history_type,
                'changes': record.diff_against(record.prev_record).changes if record.prev_record else [],
            })
            
        return Response(data) 