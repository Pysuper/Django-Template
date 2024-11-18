from django.contrib import admin
from .models import *


# 可选：自定义 ModelAdmin 类
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "is_active")  # 显示字段
    search_fields = ("username", "email")  # 搜索字段


class PermAdmin(admin.ModelAdmin):
    list_display = ("name", "method")  # 显示字段
    search_fields = ("name",)  # 搜索字段


class DeptAdmin(admin.ModelAdmin):
    list_display = ("name",)  # 显示字段
    search_fields = ("name",)  # 搜索字段


class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)  # 显示字段
    search_fields = ("name",)  # 搜索字段


class MenuAdmin(admin.ModelAdmin):
    list_display = ("name", "path")  # 显示字段
    search_fields = ("name",)  # 搜索字段


# 注册模型及其自定义的 ModelAdmin
models_to_register = {
    User: UserAdmin,
    Perm: PermAdmin,
    Dept: DeptAdmin,
    Role: RoleAdmin,
    Menu: MenuAdmin,
}

for model, admin_class in models_to_register.items():
    admin.site.register(model, admin_class)
