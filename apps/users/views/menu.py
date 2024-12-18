from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.baseDRF import CoreViewSet
from utils.custom import RolePermission
from utils.error import ErrorCode
from utils.response import ApiResponse
from utils.views import TreeAPIView
from ..models import Menu
from ..serializers.menu import MenuSerializer


class MenuViewSet(CoreViewSet, TreeAPIView):
    """菜单管理：增删改查"""

    role_type = "menu"
    search_fields = ("name", "routeName")
    ordering_fields = ("sort", "id")
    queryset = Menu.objects.all()
    serializer_class = MenuSerializer
    permission_classes = (RolePermission,)
    authentication_classes = (JWTAuthentication,)

    @action(methods=["GET"], detail=False)
    def pages(self, request):
        return ApiResponse(
            data=[
                "home",
                "403",
                "404",
                "405",
                "function_multi-tab",
                "function_tab",
                "exception_403",
                "exception_404",
                "exception_500",
                "multi-menu_first_child",
                "multi-menu_second_child_home",
                "manage_user",
                "manage_role",
                "manage_menu",
                "manage_user-detail",
                "about",
            ],
            status=ErrorCode.SUCCESS,
        )


class MenuTreeView(TreeAPIView):
    """菜单树"""

    queryset = Menu.objects.all()
