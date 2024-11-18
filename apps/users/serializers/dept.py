from rest_framework import serializers

from ..models import Dept, User


class DeptSerializer(serializers.ModelSerializer):
    """组织架构序列化"""

    type = serializers.ChoiceField(choices=Dept.DEPT_TYPE, default="company")

    class Meta:
        model = Dept
        fields = ["id", "name", "code", "type", "remark", "pid"]
        # exclude = ["id"]  # 排除ID

    def to_representation(self, instance):
        result = super().to_representation(instance)
        result["deptType"] = result.pop("type", None)
        return result


class UserSerializer(serializers.Serializer):
    """用户序列化"""

    class Meta:
        model = User
        fields = "__all__"


class DeptUserTreeSerializer(serializers.ModelSerializer):
    """组织架构树序列化"""

    label = serializers.StringRelatedField(source="name")
    children = UserSerializer(many=True, read_only=True, source="user_set")

    class Meta:
        model = Dept
        fields = ["id", "label", "pid", "children"]
