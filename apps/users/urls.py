from django.urls import path

from users.views import user

urlpatterns = [
    # 登录接口
    path("login", user.UserAuthView.as_view()),
    # 获取用户信息接口
    path("user_info", user.UserAuthView.as_view()),
    # 获取验证码接口
    # path("get_captcha", user.CaptchaView.as_view()),
    # 退出登录接口
    # path("logout", user.LogoutView.as_view()),
    # 构建菜单
    path("build_menus", user.UserBuildMenuView.as_view()),
]
