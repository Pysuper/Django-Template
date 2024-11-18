from rest_framework import serializers

from ..models import User


class UserListSerializer(serializers.ModelSerializer):
    """
    用户列表的序列化
    """

    status = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "gender", "nick_name", "phone", "email", "roles", "status"]

    def get_roles(self, obj):
        """获取用户角色列表"""
        return list(obj.roles.values_list("id", flat=True))

    def get_status(self, obj):
        """获取用户状态"""
        return "1" if obj.status else "2"

    def get_gender(self, obj):
        """获取用户性别"""
        return "1" if obj.gender == 1 else "2"


class UserModifySerializer(serializers.ModelSerializer):
    """
    用户编辑的序列化
    """

    # 自定义校验字段
    # mobile = serializers.CharField(max_length=11)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "phone",
            "email",
            "gender",
            "nick_name",
            "status",
            # "image",
            # "department",
            # "position",
            # "superior",
            # "is_active",
            "roles",
        ]

    # 自定义验证
    # def validate_mobile(self, mobile):
    #     REGEX_MOBILE = "^1[358]\d{9}$|^147\d{8}$|^176\d{8}$"
    #     if not re.match(REGEX_MOBILE, mobile):
    #         raise serializers.ValidationError("手机号码不合法")
    #     return mobile


class UserCreateSerializer(serializers.ModelSerializer):
    """
    创建用户序列化
    """

    username = serializers.CharField(required=True, allow_blank=False)
    # mobile = serializers.CharField(max_length=11)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "name",
            "phone",
            "email",
            "dept",
            "position",
            "is_active",
            "roles",
            "password",
        ]

    def validate_username(self, username):
        if User.objects.filter(username=username):
            raise serializers.ValidationError(username + " 账号已存在")
        return username

    # def validate_mobile(self, mobile):
    #     REGEX_MOBILE = "^1[358]\d{9}$|^147\d{8}$|^176\d{8}$"
    #     if not re.match(REGEX_MOBILE, mobile):
    #         raise serializers.ValidationError("手机号码不合法")
    #     if User.objects.filter(mobile=mobile):
    #         raise serializers.ValidationError("手机号已经被注册")
    #     return mobile


class UserInfoListSerializer(serializers.ModelSerializer):
    """
    公共users
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "phone",
            "email",
            "position",
        ]
