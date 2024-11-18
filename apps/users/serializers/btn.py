from rest_framework import serializers

from users.models import Btn


class BtnSerializer(serializers.ModelSerializer):
    """按钮序列化"""

    class Meta:
        model = Btn
        fields = "__all__"
