from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.baseDRF import CoreViewSet
from utils.custom import RbacPermission
from utils.error import ErrorCode
from utils.response import JsonResult
from utils.views import TreeAPIView
from ..models import Dept
from ..serializers.dept import DeptSerializer, DeptUserTreeSerializer


class DeptViewSet(CoreViewSet, TreeAPIView):
    """组织机构：增删改查"""

    role_type = "dept"
    search_fields = ("name", "type")
    ordering_fields = ("id",)
    queryset = Dept.objects.all()
    serializer_class = DeptSerializer
    permission_classes = (RbacPermission,)
    authentication_classes = (JWTAuthentication,)
    filter_backends = (SearchFilter, OrderingFilter)

    @action(methods=["GET"], detail=False)
    def pages(self, request):
        return JsonResult(
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
            status=ErrorCode.OK,
        )

    @action(methods=["POST"], detail=False)
    def download(self, request):
        pass


class DeptTreeView(TreeAPIView):
    """组织架构树"""

    queryset = Dept.objects.all()


class DeptUserTreeView(APIView):
    """组织架构关联用户树"""

    permission_classes = (AllowAny,)
    authentication_classes = (JWTAuthentication,)

    def get(self, request, format=None):
        depts = Dept.objects.all()
        serializer = DeptUserTreeSerializer(depts, many=True)
        tree_data = []
        tree_dict = {
            f"o{item['id']}": {
                "id": f"o{item['id']}",
                "label": item["label"],
                "pid": item["pid"],
                "children": item["children"],
            }
            for item in serializer.data
        }

        for item in tree_dict.values():
            if item["pid"]:
                parent = tree_dict.get(item["pid"])
                if parent:
                    parent["children"].append(item)
            else:
                tree_data.append(item)

        return Response(tree_data)
