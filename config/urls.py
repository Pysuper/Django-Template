from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views import defaults as default_views
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from users.views import dept, menu, perm, role, user

# 创建默认路由器
router = routers.DefaultRouter()

# 注册RBAC相关的视图集
router.register(r"menus", menu.MenuViewSet)  # 菜单管理
router.register(r"users", user.UserViewSet)  # 用户管理
router.register(r"depts", dept.DeptViewSet)  # 部门管理
router.register(r"roles", role.RoleViewSet)  # 角色管理

# 主要URL配置
urlpatterns = [
    # API基础URL
    path("", include(router.urls)),
    # 用户认证相关URL
    path("auth/", include("users.urls")),
    # 树形结构API，根据实际情况修改这里的书结构生成方式
    path("api/perm/tree/", perm.PermTreeView.as_view(), name="perm_tree"),  # 权限树形结构
    path("api/dept/tree/", dept.DeptTreeView.as_view(), name="dept_tree"),  # 部门树形结构
    path("api/menu/tree/", menu.MenuTreeView.as_view(), name="menus_tree"),  # 菜单树形结构
    path("api/dept/user/tree/", dept.DeptUserTreeView.as_view(), name="dept_user_tree"),  # 部门用户树形结构
] + static(
    settings.MEDIA_URL, document_root=settings.MEDIA_ROOT  # 媒体文件服务
)

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()

# API URL配置
urlpatterns += [
    # 后台管理
    path(settings.ADMIN_URL, admin.site.urls),
    # API基础路由
    path("api/", include("utils.router.api")),
    # DRF认证令牌
    path("auth-token/", obtain_auth_token),
    # API文档相关
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),  # API模式
    # Swagger文档
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# 开发环境错误页面
if settings.DEBUG:
    # # 定义错误代码和对应的视图函数及异常信息
    # error_paths = {
    #     "400": ("bad_request", "Bad Request!"),
    #     "401": ("permission_denied", "Unauthorized"),
    #     "403": ("permission_denied", "Permission Denied"),
    #     "404": ("page_not_found", "Page not Found"),
    #     "405": ("bad_request", "Method Not Allowed"),
    #     "408": ("bad_request", "Request Timeout"),
    #     "429": ("bad_request", "Too Many Requests"),
    #     "500": ("server_error", None),
    #     "502": ("server_error", "Bad Gateway"),
    #     "503": ("server_error", "Service Unavailable"),
    #     "504": ("server_error", "Gateway Timeout"),
    # }
    # # 使用字典自动生成路径
    # urlpatterns += [
    #     path(f"{code}/", getattr(default_views, view), kwargs={"exception": Exception(msg)} if msg else {})
    #     for code, (view, msg) in error_paths.items()
    # ]
    # 错误页面路由
    urlpatterns += [
        # 400 - 错误请求
        path("400/", default_views.bad_request, kwargs={"exception": Exception("Bad Request!")}),
        # 401 - 未授权
        path("401/", default_views.permission_denied, kwargs={"exception": Exception("Unauthorized")}),
        # 403 - 禁止访问
        path("403/", default_views.permission_denied, kwargs={"exception": Exception("Permission Denied")}),
        # 404 - 页面未找到
        path("404/", default_views.page_not_found, kwargs={"exception": Exception("Page not Found")}),
        # 405 - 方法不允许
        path("405/", default_views.bad_request, kwargs={"exception": Exception("Method Not Allowed")}),
        # 408 - 请求超时
        path("408/", default_views.bad_request, kwargs={"exception": Exception("Request Timeout")}),
        # 429 - 请求过多
        path("429/", default_views.bad_request, kwargs={"exception": Exception("Too Many Requests")}),
        # 500 - 服务器错误
        path("500/", default_views.server_error),
        # 502 - 网关错误
        path("502/", default_views.server_error, kwargs={"exception": Exception("Bad Gateway")}),
        # 503 - 服务不可用
        path("503/", default_views.server_error, kwargs={"exception": Exception("Service Unavailable")}),
        # 504 - 网关超时
        path("504/", default_views.server_error, kwargs={"exception": Exception("Gateway Timeout")}),
    ]
    # 调试工具栏配置
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
