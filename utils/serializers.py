from typing import Any, Dict, List, Optional, Type

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """
    基础模型序列化器
    提供通用的序列化功能
    """

    def to_representation(self, instance: Any) -> Dict:
        """
        重写to_representation方法，处理关联字段的序列化
        """
        ret = super().to_representation(instance)
        
        # 处理外键字段
        for field_name, field in self.fields.items():
            if isinstance(field, serializers.PrimaryKeyRelatedField):
                try:
                    if hasattr(instance, field_name):
                        related_instance = getattr(instance, field_name)
                        if related_instance:
                            ret[f"{field_name}_detail"] = {
                                'id': related_instance.id,
                                'str': str(related_instance)
                            }
                except ObjectDoesNotExist:
                    continue
                    
        return ret


class DynamicFieldsModelSerializer(BaseModelSerializer):
    """
    动态字段模型序列化器
    支持通过fields参数动态指定需要序列化的字段
    """

    def __init__(self, *args: Any, **kwargs: Any):
        fields = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class NestedModelSerializer(BaseModelSerializer):
    """
    嵌套模型序列化器
    支持自动序列化嵌套的关联对象
    """

    def get_field_names(self, declared_fields: Dict, info: Any) -> List[str]:
        expanded_fields = super().get_field_names(declared_fields, info)

        if getattr(self.Meta, 'nested_fields', None):
            return expanded_fields + list(self.Meta.nested_fields)
        return expanded_fields

    def build_nested_field(self, field_name: str, relation_info: Dict, nested_depth: int) -> tuple:
        """
        创建嵌套字段
        """
        class NestedSerializer(BaseModelSerializer):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
                fields = '__all__'

        field_class = NestedSerializer
        field_kwargs = {}

        return field_class, field_kwargs


class ReadOnlyModelSerializer(BaseModelSerializer):
    """
    只读模型序列化器
    用于只需要序列化输出的场景
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.read_only = True 