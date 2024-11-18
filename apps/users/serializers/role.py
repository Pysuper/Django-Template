from rest_framework import serializers

from ..models import Role


class RoleSerializer(serializers.ModelSerializer):
    """
    角色序列化
    这里针对很少字段的情况
    """

    class Meta:
        model = Role
        fields = ["id", "code", "name"]


class RoleListSerializer(serializers.ModelSerializer):
    """角色列表序列化"""

    status = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ["id", "code", "name", "remark", "status"]

    def get_status(self, obj):
        return "1" if obj.status else "2"


class RoleModifySerializer(serializers.ModelSerializer):
    """角色编辑的序列化"""

    class Meta:
        model = Role
        fields = ["id", "code", "name", "remark", "status"]
        # fields = "__all__"
        # extra_kwargs = {'menus': {'required': True, 'error_messages': {'required': '必须填写菜单名'}}}

    # def validate_menus(self, menus):
    #     if not menus:
    #         raise serializers.ValidationError('必须选择菜单')
    #     return menus
