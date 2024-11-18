from rest_framework import serializers
from rest_framework.serializers import ListSerializer
from rest_framework.serializers import Serializer


# 自定义树形结构序列化器
class TreeSerializer(Serializer):
    """
    自定义树形结构序列化器
    """

    id = serializers.IntegerField()  # 节点ID
    label = serializers.CharField(max_length=20, source="name")  # 节点名称
    pid = serializers.PrimaryKeyRelatedField(read_only=True)  # 父节点ID


# 自定义返回键值对的序列化器
class ResKeySerializer(serializers.Serializer):
    """自定义返回键值对的序列化器"""

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["createBy"] = instance.create_by.username if instance.create_by else ""
        representation["createTime"] = representation.pop("create_date", None)
        representation["updateBy"] = instance.update_by.username if instance.update_by else ""
        representation["updateTime"] = representation.pop("update_date", None)
        representation["status"] = "1" if instance.del_flag else "2"
        return representation


# 过滤掉所有标记为已删除的对象（即 del_flag=True 的对象）
class DeletedFilterListSerializer(ListSerializer):

    """
    使用：确保在批量查询时，自动过滤掉已删除的对象
    class MyModelSerializer(serializers.ModelSerializer):

    class Meta:
        model = MyModel
        fields = '__all__'
        list_serializer_class = DeletedFilterListSerializer
    """

    def to_representation(self, data):
        """
        过滤掉所有标记为已删除的对象（即 del_flag=True 的对象），只返回 del_flag=False 的数据
        主要用处在于对查询结果进行数据筛选，以便在序列化时自动排除被逻辑删除的对象
        :param data:
        :return:
        """
        data = data.filter(del_flag=False)
        return super(DeletedFilterListSerializer, self).to_representation(data)


