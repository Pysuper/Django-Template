from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.baseDRF import CoreViewSet
from utils.custom import CustomPermission
from utils.views import TreeAPIView
from ..models import Btn
from ..serializers.btn import BtnSerializer


class ButtonViewSet(CoreViewSet):
    """按钮管理：增删改查"""

    queryset = Btn.objects.all()
    search_fields = ("name",)
    # filterset_fields 提供了更灵活的过滤配置，允许自定义过滤行为，而 filter_fields 只支持简单的直接字段匹配
    filterset_fields = ("type",)
    ordering_fields = ("id",)
    serializer_class = BtnSerializer
    permission_classes = (CustomPermission,)
    authentication_classes = (JWTAuthentication,)


class BtnTreeView(TreeAPIView):
    """菜单树"""

    queryset = Btn.objects.all().filter(type=1)
