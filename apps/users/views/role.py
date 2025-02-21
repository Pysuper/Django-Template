from rest_framework import status
from rest_framework.decorators import action
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.baseDRF import CoreViewSet
from utils.custom import RolePermission
from utils.response import ApiResponse
from ..models import Role
from ..serializers.role import RoleListSerializer, RoleModifySerializer, RoleSerializer


class RoleViewSet(CoreViewSet):
    """角色管理：增删改查"""

    role_type = "role"
    ordering_fields = ("id",)
    search_fields = ("name", "code")
    filterset_fields = ["status"]
    queryset = Role.objects.all()
    serializer_class = RoleListSerializer
    permission_classes = (RolePermission,)
    authentication_classes = (JWTAuthentication,)

    serializer_action_classes = {
        "list": RoleListSerializer,
        "all": RoleSerializer,
    }

    def get_serializer_class(self):
        """
        根据 action 决定返回的 serializer
        """
        return self.serializer_action_classes.get(self.action, RoleModifySerializer)

    def update(self, request, *args, **kwargs):
        """
        修改角色信息
        """
        request.data["status"] = request.data["status"] == "1"
        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=["GET"])
    def all(self, request):
        """
        返回全部的角色信息
        """
        serializer = self.get_serializer(self.queryset, many=True)
        return ApiResponse(
            data=serializer.data,
            msg="获取成功",
            code=200,
            status=status.HTTP_200_OK,
        )
