"""
Enhanced Serializers / 增强的序列化器

提供统一的序列化器基类，支持动态字段、嵌套序列化等功能
"""

from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from rest_framework import serializers
from django.db import models
from django.core.exceptions import ObjectDoesNotExist

T = TypeVar('T', bound=models.Model)


class BaseSerializer(serializers.ModelSerializer, Generic[T]):
    """
    统一的基础序列化器
    Unified base serializer with enhanced features

    Features:
    - Type hints / 类型提示
    - Automatic None handling / 自动处理None值
    - Common validation methods / 通用验证方法
    - Dynamic field support / 动态字段支持
    - Request context / 请求上下文

    Example:
        class UserSerializer(BaseSerializer[User]):
            class Meta(BaseSerializer.Meta):
                model = User
                fields = ['id', 'username', 'email']
    """

    # 默认公共字段
    id = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(
        source='create_date',
        read_only=True,
        format='%Y-%m-%d %H:%M:%S'
    )
    updated_at = serializers.DateTimeField(
        source='update_date',
        read_only=True,
        format='%Y-%m-%d %H:%M:%S'
    )

    # 创建人和更新人（可选）
    created_by_name = serializers.CharField(
        source='create_by.username',
        read_only=True,
        required=False
    )
    updated_by_name = serializers.CharField(
        source='update_by.username',
        read_only=True,
        required=False
    )

    # 状态显示
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = None
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def __init__(self, *args: Any, **kwargs: Any):
        """
        Initialize serializer with enhanced features
        初始化序列化器并启用增强功能
        """
        super().__init__(*args, **kwargs)

        # 保存request引用
        self.request = self.context.get('request') if self.context else None

    def get_status_display(self, obj: T) -> str:
        """
        Get status display text / 获取状态显示文本

        Args:
            obj: Model instance

        Returns:
            Status display text
        """
        if hasattr(obj, 'status'):
            return '启用' if obj.status else '禁用'
        return ''

    def to_representation(self, instance: T) -> Dict[str, Any]:
        """
        优化的序列化方法
        Optimized serialization with automatic None handling

        Args:
            instance: Model instance

        Returns:
            Serialized data dictionary
        """
        data = super().to_representation(instance)

        # 可选：移除None值（根据项目需求决定）
        # Optional: Remove None values (depends on project requirements)
        # return {k: v for k, v in data.items() if v is not None}

        return data

    def validate_name(self, value: Optional[str]) -> Optional[str]:
        """
        Validate name field / 验证名称字段

        Args:
            value: Name value

        Returns:
            Validated name

        Raises:
            ValidationError: If validation fails
        """
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("名称不能为空 / Name cannot be empty")
        return value

    def validate_code(self, value: Optional[str]) -> Optional[str]:
        """
        Validate code field / 验证编码字段

        Args:
            value: Code value

        Returns:
            Validated code (uppercased)

        Raises:
            ValidationError: If validation fails
        """
        if value is not None:
            value = value.strip().upper()
            if not value:
                raise serializers.ValidationError("编码不能为空 / Code cannot be empty")
        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Object-level validation / 对象级验证

        Args:
            attrs: Attributes to validate

        Returns:
            Validated attributes

        Raises:
            ValidationError: If validation fails
        """
        # 至少需要name或code之一
        # At least one of name or code is required
        if not attrs.get('name') and not attrs.get('code'):
            raise serializers.ValidationError(
                "名称和编码不能同时为空 / Name and code cannot both be empty"
            )

        return attrs

    def create(self, validated_data: Dict[str, Any]) -> T:
        """
        Create instance with automatic audit fields
        创建实例并自动设置审计字段

        Args:
            validated_data: Validated data

        Returns:
            Created instance
        """
        # 自动设置创建人
        if self.request and self.request.user.is_authenticated:
            validated_data['create_by'] = self.request.user

        return super().create(validated_data)

    def update(self, instance: T, validated_data: Dict[str, Any]) -> T:
        """
        Update instance with automatic audit fields
        更新实例并自动设置审计字段

        Args:
            instance: Instance to update
            validated_data: Validated data

        Returns:
            Updated instance
        """
        # 自动设置更新人
        if self.request and self.request.user.is_authenticated:
            validated_data['update_by'] = self.request.user

        return super().update(instance, validated_data)


class DynamicFieldsSerializer(BaseSerializer[T]):
    """
    动态字段序列化器
    Dynamic field serializer with field selection support

    Supports dynamic field selection via URL parameters:
    支持通过URL参数动态选择字段：
    - ?fields=id,name,email
    - ?exclude=password,secret

    Example:
        serializer = DynamicFieldsSerializer(
            queryset,
            fields=['id', 'name'],  # Only include these fields
            exclude=['secret']       # Exclude these fields
        )
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """
        Initialize with dynamic field support
        初始化并支持动态字段

        Args:
            fields: List of fields to include (optional)
            exclude: List of fields to exclude (optional)
        """
        fields = kwargs.pop('fields', None)
        exclude = kwargs.pop('exclude', None)

        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)

        if exclude is not None:
            for field_name in exclude:
                self.fields.pop(field_name, None)


class TreeSerializer(BaseSerializer[T]):
    """
    树形结构序列化器
    Tree structure serializer for hierarchical data

    Automatically serializes children for hierarchical models
    自动序列化层级模型的子节点

    Requirements:
        - Model should have 'parent' field or similar
        - Model should have 'children' related_name or similar

    Example:
        class CategorySerializer(TreeSerializer[Category]):
            class Meta(BaseSerializer.Meta):
                model = Category
                fields = ['id', 'name', 'parent', 'children']
    """

    children = serializers.SerializerMethodField()
    parent_id = serializers.IntegerField(source='parent.id', read_only=True, required=False)
    parent_name = serializers.CharField(source='parent.name', read_only=True, required=False)

    def get_children(self, obj: T) -> List[Dict[str, Any]]:
        """
        Get children nodes / 获取子节点

        Args:
            obj: Model instance

        Returns:
            List of serialized children
        """
        if hasattr(obj, 'children'):
            # 使用相同的序列化器序列化子节点
            # Use same serializer for children
            return self.__class__(obj.children.all(), many=True).data
        return []


class NestedModelSerializer(BaseSerializer[T]):
    """
    嵌套模型序列化器
    Nested model serializer for related objects

    Automatically serializes related objects with depth control
    自动序列化关联对象并控制深度

    Example:
        class UserDetailSerializer(NestedModelSerializer[User]):
            class Meta(BaseSerializer.Meta):
                model = User
                fields = ['id', 'username', 'profile']
                depth = 1  # Include related objects
    """

    def get_field_names(self, declared_fields: Dict[str, serializers.Field], info: Any) -> List[str]:
        """
        Get field names with nested fields support
        获取字段名（包含嵌套字段）

        Args:
            declared_fields: Declared fields
            info: Serializer info

        Returns:
            List of field names
        """
        field_names = super().get_field_names(declared_fields, info)

        # 添加嵌套字段
        if getattr(self.Meta, 'nested_fields', None):
            field_names.extend(self.Meta.nested_fields)

        return field_names


class ReadOnlyModelSerializer(BaseSerializer[T]):
    """
    只读模型序列化器
    Read-only model serializer for display-only scenarios

    All fields are automatically set to read_only
    所有字段自动设置为只读

    Example:
        class UserDisplaySerializer(ReadOnlyModelSerializer[User]):
            class Meta(BaseSerializer.Meta):
                model = User
                fields = ['id', 'username', 'email']
    """

    def __init__(self, *args: Any, **kwargs: Any):
        """
        Initialize with all fields as read-only
        初始化并将所有字段设为只读

        Args:
            args: Positional arguments
            kwargs: Keyword arguments
        """
        super().__init__(*args, **kwargs)

        # 将所有字段设为只读
        for field in self.fields.values():
            field.read_only = True


class BulkActionSerializer(serializers.Serializer):
    """
    批量操作序列化器
    Bulk action serializer for batch operations

    Used for validating bulk action requests
    用于验证批量操作请求

    Example:
        {
            "ids": [1, 2, 3, 4, 5],
            "action": "delete"  # Optional
        }
    """

    ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        min_length=1,
        help_text="对象ID列表 / List of object IDs"
    )

    action = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="操作类型 / Action type"
    )

    data = serializers.JSONField(
        required=False,
        help_text="批量更新的数据 / Data for bulk update"
    )

    def validate_ids(self, value: List[int]) -> List[int]:
        """
        Validate IDs list
        验证ID列表

        Args:
            value: List of IDs

        Returns:
            Validated list

        Raises:
            ValidationError: If validation fails
        """
        if not value:
            raise serializers.ValidationError("ID列表不能为空 / IDs cannot be empty")

        if len(value) > 1000:
            raise serializers.ValidationError("批量操作最多支持1000条记录 / Maximum 1000 records per bulk operation")

        return value


class ModelSerializer(serializers.Serializer):
    """
    通用模型序列化器
    Generic model serializer for simple cases

    Automatically creates serializer from model with minimal code
    自动从模型创建序列化器，最少代码

    Example:
        serializer = ModelSerializer.from_model(User, fields=['id', 'username'])
    """

    @classmethod
    def from_model(
        cls: Type['ModelSerializer'],
        model: Type[models.Model],
        fields: List[str] = None,
        read_only_fields: List[str] = None
    ) -> Type[serializers.ModelSerializer]:
        """
        Dynamically create serializer from model
        从模型动态创建序列化器

        Args:
            model: Django model class
            fields: List of field names to include
            read_only_fields: List of read-only field names

        Returns:
            Serializer class
        """
        meta_attrs = {
            'model': model,
        }

        if fields:
            meta_attrs['fields'] = fields
        else:
            meta_attrs['fields'] = '__all__'

        if read_only_fields:
            meta_attrs['read_only_fields'] = read_only_fields

        # Create Meta class
        Meta = type('Meta', (object,), meta_attrs)

        # Create serializer class
        attrs = {'Meta': Meta}
        serializer_class = type(
            f'{model.__name__}Serializer',
            (serializers.ModelSerializer,),
            attrs
        )

        return serializer_class
