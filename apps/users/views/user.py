from operator import itemgetter

from django.contrib.auth import authenticate
from django.contrib.auth.hashers import check_password
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from utils.baseDRF import CoreViewSet
from utils.custom import RbacPermission
from utils.error import ErrorCode
from utils.response import JsonResult
from ..models import Menu, User
from ..serializers.dept import UserSerializer
from ..serializers.menu import MenuSerializer
from ..serializers.user import UserCreateSerializer, UserInfoListSerializer, UserListSerializer, UserModifySerializer

jwt_payload_handler = api_settings.ACCESS_TOKEN_LIFETIME
jwt_encode_handler = api_settings.REFRESH_TOKEN_LIFETIME


class UserAuthView(APIView):
    """
    用户登录认证
    """

    # 设置这里的接口，不需要用户登录
    permission_classes = [AllowAny]

    # 添加排序功能
    # ordering_fields = ["id", "depression", "anxiety", "bipolar_disorder"] + [f"personality_{i}" for i in range(5)]
    # ordering = ["id"]  # 默认排序
    # 前端需要提供的参数
    # 为了使用排序功能，前端需要通过查询参数提供 'sort' 字段，其值应为 'ordering_fields' 中定义的任何字段名。
    # 例如，要按 'depression' 降序排序，前端应发送请求带参数 'sort=-depression'。
    # 如果需要按多个字段进行排序，可以通过逗号分隔字段名来指定。例如，按 'depression' 降序和 'anxiety' 升序排序，
    # 前端应发送请求带参数 'sort=-depression,anxiety'。
    # 对于 'personality' 中的某个值进行排序，例如按 'personality_0' 升序排序，前端应发送请求带参数 'sort=personality_0'。
    # 如果需要组合排序，例如按 'personality_0' 升序和 'personality_1' 降序排序，前端应发送请求带参数 'sort=personality_0,-personality_1'。

    @classmethod
    def get_permission_from_role(cls, request):
        """
        获取当前用户的权限
        :param request: 请求对象
        :return: 权限列表
        """
        user = getattr(request, "user", None)
        if user:
            return list(user.roles.values_list("perms__method", flat=True).distinct())
        return None

    def post(self, request, *args, **kwargs):
        """
        用户登录认证
        :param request: 请求对象
        :param args:
        :param kwargs:
        """
        username = request.data.get("userName")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            ref_token = str(RefreshToken.for_user(user).access_token)
            return JsonResult(
                status=ErrorCode.OK,
                data={
                    "refreshToken": ref_token,
                    "token": ref_token,
                },
            )
        return JsonResult("用户名或密码错误!", status=403)

    def get(self, request):
        """
        获取当前用户信息
        :param request:
        :return:
        """
        if request.user.id is not None:
            perms = self.get_permission_from_role(request)
            data = {
                "userId": request.user.id,
                "userName": request.user.username,
                "perm": perms,
                # "roles": request.user.roles.values_list("name", flat=True),
                # "buttons": request.user.roles.btns.values_list("name", flat=True),
                "roles": ["R_ADMIN", "R_SUPER"],
                "buttons": ["B_CODE1", "B_CODE2", "B_CODE3"],
            }
            return JsonResult(data=data, status=ErrorCode.OK)
        return JsonResult("用户名或密码错误!", status=ErrorCode.FORBIDDEN)


class UserViewSet(CoreViewSet):
    """
    用户管理
    """

    role_type = "user"
    ordering_fields = ("id",)
    queryset = User.objects.all().select_related("dept")
    serializer_class = UserListSerializer
    permission_classes = (RbacPermission,)
    authentication_classes = (JWTAuthentication,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filter_fields = ["is_active", "department"]
    filterset_fields = {"status": ["in", "exact"], "gender": ["exact"]}
    search_fields = ["username", "name", "nick_name", "email", "roles__name"]

    def get_serializer_class(self):
        """
        根据 action 决定返回的 serializer
        """
        serializer_map = {"create": UserCreateSerializer, "list": UserListSerializer}
        return serializer_map.get(self.action, UserModifySerializer)

    def create(self, request, *args, **kwargs):
        """
        重写create方法，为新创建的用户添加初始密码
        """
        request.data["password"] = "123456"
        return super().create(request, *args, **kwargs)

    @action(methods=["post"], detail=True, permission_classes=[IsAuthenticated])
    def set_password(self, request, pk=None):
        """
        修改密码
        """
        user = User.objects.get(id=pk)
        new_password1 = request.data.get("new_password1")
        new_password2 = request.data.get("new_password2")
        old_password = request.data.get("old_password")

        # 检查权限
        if (
            "admin" in UserAuthView.get_permission_from_role(request)
            or "user_all" in UserAuthView.get_permission_from_role(request)
            or request.user.is_superuser
        ):
            if new_password1 != new_password2:
                return Response({"detail": "新密码两次输入不一致!"}, status=ErrorCode.BAD_REQUEST)
            user.set_password(new_password2)
            user.save()
            return Response({"detail": "密码修改成功!"})

        # 检查旧密码
        if not check_password(old_password, user.password):
            return Response({"detail": "旧密码错误!"}, status=ErrorCode.BAD_REQUEST)

        if new_password1 != new_password2:
            return Response({"detail": "新密码两次输入不一致!"}, status=ErrorCode.BAD_REQUEST)

        user.set_password(new_password2)
        user.save()
        return Response({"detail": "密码修改成功!"})

    @action(detail=False, methods=["GET"])
    def export(self, request):
        """导出用户数据为Excel文件"""
        import pandas as pd
        from django.http import HttpResponse

        users = User.objects.all()
        # 序列化查询集为列表

        user_data = UserSerializer(users, many=True).data  # 将查询集转换为列表以确保序列化

        # 创建DataFrame
        df = pd.DataFrame(user_data)

        # 设置响应内容
        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response["Content-Disposition"] = 'attachment; filename="用户数据.xlsx"'

        # 将DataFrame写入Excel文件
        with pd.ExcelWriter(response, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="用户数据")

        return response


class UserBuildMenuView(APIView):
    """绑定当前用户菜单信息"""

    def get_menu_from_role(self, request):
        """根据用户角色获取菜单信息"""
        if request.user:
            menu_dict = {}
            # 获取用户角色下的所有菜单
            menus = request.user.roles.values(
                "menus__id",
                "menus__name",
                "menus__path",
                "menus__is_frame",
                "menus__is_show",
                "menus__component",
                "menus__icon",
                "menus__sort",
                "menus__pid",
            ).distinct()
            for item in menus:
                if item["menus__pid"] is None:  # 顶级菜单
                    top_menu = {
                        "id": item["menus__id"],
                        "path": item["menus__path"],
                        "component": "Layout",
                        "children": [
                            {
                                "path": item["menus__path"],
                                "meta": {
                                    "title": item["menus__name"],
                                    "icon": item["menus__icon"],
                                },
                            }
                        ],
                        "pid": item["menus__pid"],
                        "sort": item["menus__sort"],
                    }
                    menu_dict[item["menus__id"]] = top_menu
                else:  # 子菜单
                    children_menu = {
                        "id": item["menus__id"],
                        "name": item["menus__name"],
                        "path": item["menus__path"],
                        "component": item["menus__component"],
                        "meta": {
                            "title": item["menus__name"],
                            "icon": item["menus__icon"],
                        },
                        "pid": item["menus__pid"],
                        "sort": item["menus__sort"],
                        "hidden": not item["menus__is_show"],  # 根据是否显示设置hidden属性
                    }
                    menu_dict[item["menus__id"]] = children_menu
            return menu_dict

    def get_all_menu_dict(self):
        """获取所有菜单数据，重组结构"""
        menus = Menu.objects.all()
        serializer = MenuSerializer(menus, many=True)
        tree_dict = {}
        for item in serializer.data:
            if item["pid"] is None:  # 顶级菜单
                top_menu = {
                    "id": item["id"],
                    "name": item["name"],
                    "path": "/" + item["path"],
                    "redirect": "noredirect",
                    "component": "Layout",
                    "alwaysShow": True,
                    "meta": {
                        "title": item["name"],
                        "icon": item["icon"],
                    },
                    "pid": item["pid"],
                    "sort": item["sort"],
                    "children": [],
                }
                tree_dict[item["id"]] = top_menu
            else:  # 子菜单
                children_menu = {
                    "id": item["id"],
                    "name": item["name"],
                    "path": item["path"],
                    "component": item["component"],
                    "meta": {
                        "title": item["name"],
                        "icon": item["icon"],
                        "noCache": not item["is_show"],  # 根据是否显示设置noCache属性
                    },
                    "hidden": not item["is_show"],  # 根据是否显示设置hidden属性
                    "pid": item["pid"],
                    "sort": item["sort"],
                }
                tree_dict[item["id"]] = children_menu
        return tree_dict

    def get_all_menus(self, request):
        """获取所有菜单，依据用户权限进行过滤"""
        perms = UserAuthView.get_permission_from_role(request)
        tree_data = []
        if "admin" in perms or request.user.is_superuser:
            tree_dict = self.get_all_menu_dict()  # 管理员获取所有菜单
        else:
            tree_dict = self.get_menu_from_role(request)  # 普通用户根据角色获取菜单
        for i in tree_dict:
            if tree_dict[i]["pid"]:  # 如果有父级菜单
                pid = tree_dict[i]["pid"]
                parent = tree_dict[pid]
                parent.setdefault("redirect", "noredirect")
                parent.setdefault("alwaysShow", True)
                parent.setdefault("children", []).append(tree_dict[i])
                parent["children"] = sorted(parent["children"], key=itemgetter("sort"))  # 根据排序字段排序
            else:
                tree_data.append(tree_dict[i])  # 顶级菜单
        return tree_data

    def get(self, request):
        """处理GET请求，返回用户菜单数据"""
        if request.user.id is not None:
            menu_data = self.get_all_menus(request)
            return Response(menu_data, status=ErrorCode.OK)
        return Response({"detail": "请登录后访问!"}, status=ErrorCode.FORBIDDEN)


class UserListView(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserInfoListSerializer
    permission_classes = (IsAuthenticated,)
    authentication_classes = (JWTAuthentication,)
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_fields = ("name",)  # 使用 filterset_fields 替代 filter_fields
    ordering_fields = ("id",)
