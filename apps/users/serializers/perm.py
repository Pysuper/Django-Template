from rest_framework import serializers
from ..models import Perm


class PermListSerializer(serializers.ModelSerializer):
    """权限列表序列化"""

    menu_name = serializers.ReadOnlyField(source="menus.name")

    class Meta:
        model = Perm
        fields = [
            "id",
            "name",
            "method",
            "menu_name",
            "pid",
        ]
