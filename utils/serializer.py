from datetime import datetime
from typing import Any, Dict, List, Optional

from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.serializers import ListSerializer, ModelSerializer, Serializer

User = get_user_model()


class BaseModelSerializer(ModelSerializer):
    """基础模型序列化器"""

    class Meta:
        list_serializer_class = ListSerializer

    def __init__(self, instance=None, data=empty, **kwargs):
        super().__init__(instance, data, **kwargs)
        self.request = self.context.get("request")
        self.user = self.request.user if self.request else None

    def create(self, validated_data: Dict[str, Any]) -> models.Model:
        """创建时自动添加创建者信息"""
        if self.user and hasattr(self.Meta.model, "create_by"):
            validated_data["create_by"] = self.user
        return super().create(validated_data)

    def update(self, instance: models.Model, validated_data: Dict[str, Any]) -> models.Model:
        """更新时自动添加更新者信息"""
        if self.user and hasattr(instance, "update_by"):
            validated_data["update_by"] = self.user
        if hasattr(instance, "update_date"):
            validated_data["update_date"] = datetime.now()
        return super().update(instance, validated_data)


class TreeSerializer(BaseModelSerializer):
    """树形结构序列化器"""

    id = serializers.IntegerField(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=None, required=False, allow_null=True)
    children = serializers.SerializerMethodField()
    level = serializers.IntegerField(read_only=True)
    is_leaf = serializers.BooleanField(read_only=True)

    class Meta:
        list_serializer_class = ListSerializer
        fields = ["id", "name", "parent", "children", "level", "is_leaf"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.Meta.model:
            self.fields["parent"].queryset = self.Meta.model.objects.all()

    def get_children(self, obj: models.Model) -> List[Dict[str, Any]]:
        """获取子节点"""
        if hasattr(obj, "get_children"):
            serializer = self.__class__(obj.get_children(), many=True, context=self.context)
            return serializer.data
        return []


class TimestampSerializer(BaseModelSerializer):
    """时间戳序列化器"""

    create_time = serializers.DateTimeField(source="create_date", read_only=True)
    update_time = serializers.DateTimeField(source="update_date", read_only=True)
    create_by_info = serializers.SerializerMethodField()
    update_by_info = serializers.SerializerMethodField()

    class Meta:
        fields = ["create_time", "update_time", "create_by_info", "update_by_info"]

    def get_create_by_info(self, obj: models.Model) -> Optional[Dict[str, Any]]:
        """获取创建者信息"""
        if not hasattr(obj, "create_by") or not obj.create_by:
            return None
        return {
            "id": obj.create_by.id,
            "username": obj.create_by.username,
            "name": getattr(obj.create_by, "name", None),
        }

    def get_update_by_info(self, obj: models.Model) -> Optional[Dict[str, Any]]:
        """获取更新者信息"""
        if not hasattr(obj, "update_by") or not obj.update_by:
            return None
        return {
            "id": obj.update_by.id,
            "username": obj.update_by.username,
            "name": getattr(obj.update_by, "name", None),
        }


class DeletedFilterListSerializer(ListSerializer):
    """已删除对象过滤序列化器"""

    def to_representation(self, data: models.QuerySet) -> List[Dict[str, Any]]:
        """过滤已删除对象"""
        if hasattr(data, "filter") and hasattr(data.model, "del_flag"):
            data = data.filter(del_flag=False)
        return super().to_representation(data)


class RecursiveSerializer(Serializer):
    """递归序列化器"""

    def to_representation(self, instance: Any) -> Dict[str, Any]:
        """递归序列化"""
        serializer = self.parent.parent.__class__(instance, context=self.context)
        return serializer.data


class DynamicFieldsSerializer(BaseModelSerializer):
    """动态字段序列化器"""

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        exclude = kwargs.pop("exclude", None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude is not None:
            for field_name in exclude:
                self.fields.pop(field_name, None)


class NestedModelSerializer(BaseModelSerializer):
    """嵌套模型序列化器"""

    def create(self, validated_data: Dict[str, Any]) -> models.Model:
        """处理嵌套创建"""
        nested_data = {}
        for field_name, field in self.fields.items():
            if isinstance(field, BaseModelSerializer):
                if field_name in validated_data:
                    nested_data[field_name] = validated_data.pop(field_name)

        instance = super().create(validated_data)

        # 处理嵌套数据
        for field_name, data in nested_data.items():
            field = self.fields[field_name]
            if isinstance(data, list):
                [field.create(item) for item in data]
            else:
                field.create(data)

        return instance

    def update(self, instance: models.Model, validated_data: Dict[str, Any]) -> models.Model:
        """处理嵌套更新"""
        nested_data = {}
        for field_name, field in self.fields.items():
            if isinstance(field, BaseModelSerializer):
                if field_name in validated_data:
                    nested_data[field_name] = validated_data.pop(field_name)

        instance = super().update(instance, validated_data)

        # 处理嵌套数据
        for field_name, data in nested_data.items():
            field = self.fields[field_name]
            if isinstance(data, list):
                [field.update(item) for item in data]
            else:
                field.update(data)

        return instance


class BulkCreateUpdateSerializer(BaseModelSerializer):
    """批量创建更新序列化器"""

    def create(self, validated_data: List[Dict[str, Any]]) -> List[models.Model]:
        """批量创建"""
        model_class = self.Meta.model
        instances = [model_class(**item) for item in validated_data]
        return model_class.objects.bulk_create(instances)

    def update(self, instances: List[models.Model], validated_data: List[Dict[str, Any]]) -> List[models.Model]:
        """批量更新"""
        instance_map = {instance.id: instance for instance in instances}

        for item in validated_data:
            instance = instance_map.get(item["id"])
            if instance:
                for key, value in item.items():
                    setattr(instance, key, value)

        model_class = self.Meta.model
        return model_class.objects.bulk_update(instances, validated_data[0].keys())
