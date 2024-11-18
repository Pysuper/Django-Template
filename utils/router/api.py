from django.conf import settings
from django.urls import path
from rest_framework.documentation import include_docs_urls
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import DefaultRouter, SimpleRouter

"""
根据项目的 DEBUG 模式配置 REST Framework 的路由对象
并将生成的路由 URL 列表赋值给 urlpatterns，用于 Django 的 URL 路由配置
用于管理 API 路由和文档生成

if settings.DEBUG:
    # 在 DEBUG 模式下使用 DefaultRouter，它会自动为根 URL 添加一个可浏览的 API 文档（在浏览器中访问时会显示 API 根目录）
    router = DefaultRouter()
else:
    # 在非 DEBUG 模式（如生产环境）中使用 SimpleRouter，不会添加根 URL 的 API 浏览视图
    router = SimpleRouter()

# 在 Django 项目中为该路由配置命名空间，便于在其他地方引用该 URL 路由时使用 reverse("api:route_name") 的方式来生成 URL
app_name = "api"

# 将 router 中注册的路由列表赋值给 urlpatterns，供 Django 项目的主 URL 配置使用
urlpatterns = router.urls
"""


class APIRouter:
    """API路由管理类"""

    def __init__(self):
        # 根据DEBUG模式选择路由器类型
        self.router = DefaultRouter() if settings.DEBUG else SimpleRouter()

    def register_viewset(self, prefix, viewset, basename=None):
        """
        注册视图集到路由
        :param prefix: URL前缀
        :param viewset: 视图集类
        :param basename: 基础名称(可选)
        """
        self.router.register(prefix, viewset, basename=basename)

    def get_urls(self):
        """
        获取所有注册的URL模式
        :return: URL模式列表
        """
        # API文档URL配置
        api_doc_urls = (
            [path("docs/", include_docs_urls(title="API文档", permission_classes=[IsAuthenticated]))]
            if settings.DEBUG
            else []
        )

        # 合并所有URL
        return api_doc_urls + self.router.urls


# 创建路由实例
router = APIRouter()

# 配置命名空间
app_name = "api"

# 生成URL模式列表
urlpatterns = router.get_urls()

"""
使用示例:
from myapp.views import UserViewSet

# 注册视图集
router.register_viewset('users', UserViewSet, basename='user')

# 在views.py中创建视图集
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
"""
