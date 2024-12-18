from typing import Any, Dict, List, Optional, Type

from django.conf import settings
from django.urls import include, path, re_path
from django.utils.module_loading import import_string
from rest_framework import viewsets
from rest_framework.documentation import include_docs_urls
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.routers import DefaultRouter, SimpleRouter
from rest_framework.schemas import get_schema_view
from rest_framework_nested.routers import NestedDefaultRouter

from utils.error import BusinessError, ErrorCode


class CustomRouter(DefaultRouter):
    """自定义路由器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = getattr(settings, "APPEND_SLASH", True)
        self.default_schema_renderers = None if settings.DEBUG else []

    def get_default_basename(self, viewset: Type[viewsets.ViewSet]) -> str:
        """获取默认基础名称"""
        queryset = getattr(viewset, "queryset", None)
        if queryset is not None:
            return queryset.model._meta.object_name.lower()

        if hasattr(viewset, "model"):
            return viewset.model._meta.object_name.lower()

        return viewset.__name__.lower().replace("viewset", "")


class APIRouter:
    """API路由管理器"""

    def __init__(self):
        # 根据DEBUG模式选择路由器类型
        self.router = CustomRouter() if settings.DEBUG else SimpleRouter()
        self.nested_routers = {}
        self.api_version = getattr(settings, "API_VERSION", "v1")
        self.api_title = getattr(settings, "API_TITLE", "API文档")
        self.api_description = getattr(settings, "API_DESCRIPTION", "")

    def register_viewset(
        self,
        prefix: str,
        viewset: Type[viewsets.ViewSet],
        basename: Optional[str] = None,
        parent_prefix: Optional[str] = None,
        parent_lookup: Optional[str] = None,
    ) -> None:
        """
        注册视图集
        :param prefix: URL前缀
        :param viewset: 视图集类
        :param basename: 基础名称
        :param parent_prefix: 父级前缀（用于嵌套路由）
        :param parent_lookup: 父级查找字段（用于嵌套路由）
        """
        try:
            if parent_prefix:
                # 创建嵌套路由
                if parent_prefix not in self.nested_routers:
                    self.nested_routers[parent_prefix] = NestedDefaultRouter(
                        self.router,
                        parent_prefix,
                        lookup=parent_lookup or "pk",
                    )
                self.nested_routers[parent_prefix].register(prefix, viewset, basename=basename)
            else:
                # 注册到主路由
                self.router.register(prefix, viewset, basename=basename)
        except Exception as e:
            raise BusinessError(error_code=ErrorCode.SYSTEM_ERROR, message=f"注册视图集失败: {str(e)}")

    def register_api_view(
        self,
        pattern: str,
        view: Any,
        name: Optional[str] = None,
        initkwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        注册API视图
        :param pattern: URL模式
        :param view: 视图类或函数
        :param name: URL名称
        :param initkwargs: 视图初始化参数
        """
        try:
            # 如果是字符串，尝试导入
            if isinstance(view, str):
                view = import_string(view)

            # 添加到路由
            self.router.urls.append(path(pattern, view.as_view(**(initkwargs or {})), name=name))
        except Exception as e:
            raise BusinessError(error_code=ErrorCode.SYSTEM_ERROR, message=f"注册API视图失败: {str(e)}")

    def get_api_schema_patterns(self) -> List[Any]:
        """获取API文档模式"""
        if not settings.DEBUG:
            return []

        schema_view = get_schema_view(
            title=self.api_title,
            description=self.api_description,
            version=self.api_version,
            public=True,
            permission_classes=[AllowAny],
        )

        return [
            # OpenAPI模式
            path("openapi/", schema_view, name="openapi-schema"),
            # API文档
            path(
                "docs/",
                include_docs_urls(
                    title=self.api_title, description=self.api_description, permission_classes=[IsAuthenticated]
                ),
            ),
            # Swagger文档
            re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
            path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
            # ReDoc文档
            path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
        ]

    def get_urls(self) -> List[Any]:
        """获取所有URL模式"""
        # 获取所有路由URL
        urls = self.router.urls

        # 添加嵌套路由URL
        for nested_router in self.nested_routers.values():
            urls.extend(nested_router.urls)

        # 添加API文档URL
        urls.extend(self.get_api_schema_patterns())

        # 添加API版本前缀
        if self.api_version:
            return [path(f"{self.api_version}/", include((urls, "api"), namespace=self.api_version))]

        return urls

    def get_api_root_dict(self) -> Dict[str, Any]:
        """获取API根目录信息"""
        api_root_dict = {}

        # 添加视图集URL
        viewsets = self.router.registry
        for prefix, viewset, basename in viewsets:
            api_root_dict[prefix] = basename or self.router.get_default_basename(viewset)

        # 添加嵌套视图集URL
        for parent_prefix, nested_router in self.nested_routers.items():
            for prefix, viewset, basename in nested_router.registry:
                key = f"{parent_prefix}/{prefix}"
                api_root_dict[key] = basename or self.router.get_default_basename(viewset)

        return api_root_dict


# 创建路由实例
router = APIRouter()

# 配置命名空间
app_name = "api"

# 生成URL模式列表
urlpatterns = router.get_urls()

"""
使用示例:

# 注册普通视图集
router.register_viewset('users', UserViewSet)

# 注册嵌套视图集
router.register_viewset(
    prefix='posts',
    viewset=PostViewSet,
    parent_prefix='users',
    parent_lookup='user'
)

# 注册API视图
router.register_api_view(
    'auth/login/',
    'apps.users.views.LoginView',
    name='auth-login'
)

# 在views.py中创建视图集
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        # 修改密码逻辑
        pass
"""
