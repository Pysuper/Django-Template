from collections import OrderedDict
from typing import List, Optional

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response


class CorePagination(PageNumberPagination):
    """分页设置"""

    page_size = 10
    page_size_query_param = "size"
    max_page_size = 100


class LargePagination(PageNumberPagination):
    """自定义分页类，支持动态页面大小"""

    # 定义前端分页参数名称
    page_query_params = "current"

    # 允许通过 URL 查询参数 'size' 动态设置页面大小
    page_size = 10
    page_size_query_param = "size"
    max_page_size = 100

    def get_paginated_response(self, data):
        """返回分页后的响应，包含自定义的响应格式"""
        # 使用三元表达式简化 code 和 msg 的赋值逻辑
        code = 200 if data else 404
        msg = "请求成功" if data else "数据请求失败"

        # TODO： 自定义ViewSet分页响应
        return Response(
            OrderedDict(
                [
                    ("code", code),
                    ("msg", msg),
                    (
                        "data",
                        OrderedDict(
                            [
                                ("records", data),
                                ("current", self.page.number),
                                ("size", self.page_size),
                                ("total", self.page.paginator.count),
                            ]
                        ),
                    ),
                ]
            )
        )

    # 动态获取前端分页参数名称
    def get_page_query_param(self):
        """
        获取 URL 上的 'current' 参数，如果没有 'current' 参数，返回 'current' 作为默认值
        :return:
        """
        return self.page_query_params or "current"


class RbacPermission(BasePermission):
    """
    自定义权限类，基于用户角色权限控制。
    """

    @classmethod
    def get_permission_from_role(cls, request) -> Optional[List[str]]:
        """
        获取用户角色的权限，去重
        :param request: 请求对象
        :return: 权限列表或 None
        """
        if not request.user.is_authenticated:
            return None
        return list(request.user.roles.values_list("perms__method", flat=True).distinct())

    def has_permission(self, request, view) -> bool:
        """
        权限校验逻辑
        :param request: 请求对象
        :param view: 视图对象
        :return: 是否有权限
        """
        perms = self.get_permission_from_role(request) or []

        if "admin" in perms:
            return True  # 管理员直接拥有所有权限

        # 如果视图没有权限映射，直接返回有权限
        if not hasattr(view, "perms_map"):
            return True

        # 获取请求方法
        method = request.method.lower()

        # 校验权限
        return any(
            (method == method_key or method_key == "*") and alias in perms
            for perm_map in view.perms_map
            for method_key, alias in perm_map.items()
        )

    '''
    @classmethod
    def get_permission_from_role(self, request):
        """
        根据用户角色获取权限列表，返回字典，路径为键，允许的HTTP方法为值。
        """
        if request.user:
            try:
                perms_dict = defaultdict(set)
                # 获取用户角色的所有权限信息，并去重
                perms = request.user.roles.values(
                    "permissions__menus__path",  # 权限对应的菜单路径
                    "permissions__method",  # 权限允许的HTTP方法（如GET、POST、PUT等）
                ).distinct()

                # 遍历权限数据，为用户的每个菜单路径设置对应的允许方法
                for item in perms:
                    # 获取权限中的HTTP方法，如GET、POST、PUT等
                    method = item["permissions__method"].split("_")[
                        -1
                    ]  # 处理权限方法名称（从类似"PERM_GET"中获取"GET"）

                    if method == "ALL":  # 如果权限方法是"ALL"，表示允许所有操作
                        perms_dict[item["permissions__menus__path"]].update(
                            {"GET", "POST", "PUT", "DELETE"}
                        )  # 允许所有HTTP方法
                    else:
                        perms_dict[item["permissions__menus__path"]].add(method)  # 向对应菜单路径添加指定的HTTP方法

                return perms_dict  # 返回包含路径和允许方法的权限字典
            except AttributeError:
                # 处理用户角色或权限不存在的情况，返回None
                return None
        return None

    def has_permission(self, request, view):
        """
        核心权限检查逻辑，判断当前用户是否有权限访问请求的视图。
        """
        # 获取当前用户的权限信息
        self.get_permission_from_role(request)

        # TODO: 这里可以添加实际的权限校验逻辑，当前逻辑默认返回True，允许所有请求。
        # 获取当前用户的权限信息
        # request_perms = self.get_permission_from_role(request)
        # 可以根据实际需求将注释部分取消注释，添加实际权限判断逻辑：
        # if request_perms:
        #     # 提取请求URL路径，进行权限匹配
        #     request_url = request._request.path_info.split('/')[2]  # 这里假设路径是 "/api/路径/..." 格式，提取第二段作为菜单路径
        #
        #     # SAFEMETHOD 定义了一些不需要权限的安全方法，如HEAD、OPTIONS
        #     SAFEMETHOD = ('HEAD', 'OPTIONS')
        #
        #     # 如果用户有ADMIN权限，默认允许所有操作
        #     if 'ADMIN' in request_perms[None]:
        #         return True
        #     # 如果用户有访问请求URL的权限，允许访问
        #     elif request._request.method in request_perms[request_url]:
        #         return True
        #     # 如果请求的是安全方法，允许访问
        #     elif request._request.method in SAFEMETHOD:
        #         return True

        # 目前默认返回True，表示允许所有请求
        return True

    @classmethod
    def get_permission_from_role(cls, request) -> Optional[List[str]]:
        """
        从用户角色中获取权限
        :param request: 请求对象
        :return: 权限列表或 None
        """
        try:
            # 获取用户角色的权限，去重
            return [p["perm__method"] for p in request.user.roles.values("perm__method").distinct()]
        except AttributeError:
            return None

    def has_permission(self, request, view) -> bool:
        """
        权限校验逻辑
        :param request: 请求对象
        :param view: 视图对象
        :return: 是否有权限
        """
        perms = self.get_permission_from_role(request) or []

        if "admin" in perms:
            return True  # 管理员直接拥有所有权限

        # 如果视图没有权限映射，直接返回有权限
        if not hasattr(view, "perms_map"):
            return True

        # 获取请求方法
        method = request.method.lower()

        # 校验权限
        return any(
            (method == method_key or method_key == "*") and alias in perms
            for perm_map in view.perms_map
            for method_key, alias in perm_map.items()
        )

    '''


class ObjPermission(BasePermission):
    """密码管理对象级权限控制"""

    def has_object_permission(self, request, view, obj) -> bool:
        """
        检查用户是否有权限访问特定对象
        :param request: 请求对象
        :param view: 视图对象
        :param obj: 要检查的对象
        :return: 是否有权限
        """
        # 获取用户角色的权限
        user_perms = RbacPermission.get_permission_from_role(request) or []

        # 管理员拥有所有权限
        if "admin" in user_perms:
            return True

        # 检查用户是否有权限访问特定对象
        return request.user.id == obj.uid_id
