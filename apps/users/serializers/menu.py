from rest_framework import serializers

from ..models import Menu


class MenuSerializer(serializers.ModelSerializer):
    """菜单序列化器"""

    children = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    parent_id = serializers.SerializerMethodField()
    menuName = serializers.CharField(source='name')
    routeName = serializers.CharField(source='name')
    routePath = serializers.CharField(source='path')
    order = serializers.IntegerField(source='sort')

    class Meta:
        model = Menu
        exclude = ['pid']
        extra_kwargs = {
            'name': {
                'required': True,
                'error_messages': {
                    'required': '必须填写菜单名'
                }
            }
        }

    def get_children(self, obj):
        """获取子菜单"""
        children = Menu.objects.filter(pid=obj)
        return MenuSerializer(children, many=True).data

    def get_status(self, obj):
        """获取菜单状态"""
        return '2' if obj.del_flag else '1'

    def get_parent_id(self, obj):
        """获取父菜单ID"""
        return obj.pid.id if obj.pid else None

    def to_representation(self, instance):
        """自定义序列化输出"""
        data = super().to_representation(instance)
        # 添加固定字段
        data.update({
            'menuType': '1',
            'i18nKey': 'route.function',
            'icon': 'icon-park-outline:all-application',
            'iconType': '1'
        })
        return data
