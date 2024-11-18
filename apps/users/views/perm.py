from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.baseDRF import CoreViewSet
from utils.custom import RbacPermission
from utils.views import TreeAPIView
from ..models import Perm
from ..serializers.perm import PermListSerializer


class PermViewSet(CoreViewSet, TreeAPIView):
    """权限：增删改查"""

    role_type = "perm"  # 通用权限配置
    ordering_fields = ("id",)
    search_fields = ("name", "menu_name")  # 支持按菜单名称搜索
    queryset = Perm.objects.all()
    serializer_class = PermListSerializer
    permission_classes = (RbacPermission,)
    authentication_classes = (JWTAuthentication,)


class PermTreeView(TreeAPIView):
    """权限树"""

    queryset = Perm.objects.all()
