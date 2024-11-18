from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from utils.baseDRF import BaseEntity


class Menu(BaseEntity):
    """菜单"""

    # 菜单类型：1：菜单 2：按钮 3: 目录
    # MENU_TYPE = [(1, "菜单"), (2, "按钮"), (3, "目录")]
    # menu_type = models.IntegerField(choices=MENU_TYPE, verbose_name="菜单类型")

    is_frame = models.BooleanField(default=False, verbose_name="外部菜单")
    sort = models.IntegerField(null=True, blank=True, verbose_name="排序标记")
    icon = models.CharField(max_length=50, null=True, blank=True, verbose_name="图标")
    path = models.CharField(max_length=158, null=True, blank=True, verbose_name="链接地址")
    component = models.CharField(max_length=200, null=True, blank=True, verbose_name="组件")
    pid = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        verbose_name="父菜单",
    )

    class Meta:
        # 如果需要特定的排序，可以在这里覆盖
        ordering = ["sort", "id"]


class Btn(BaseEntity):
    """按钮"""

    BTN_TYPE = [(1, "菜单"), (2, "按钮")]
    pid = models.IntegerField(null=True, blank=True, verbose_name="父id")
    type = models.IntegerField(choices=BTN_TYPE, default=1, verbose_name="类型")
    perm = models.CharField(max_length=100, blank=True, null=True, verbose_name="权限")


class Perm(BaseEntity):
    """权限"""

    method = models.CharField(max_length=50, null=True, blank=True, verbose_name="方法")
    menus = models.ForeignKey(
        "Menu",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="perm",
        verbose_name="关联菜单",
    )
    pid = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
        verbose_name="父权限",
    )


class Role(BaseEntity):
    """角色"""

    perms = models.ManyToManyField("Perm", related_name="roles", blank=True, verbose_name="权限")
    btns = models.ManyToManyField("Btn", related_name="roles", blank=True, verbose_name="按钮权限")
    menus = models.ManyToManyField("Menu", related_name="roles", blank=True, verbose_name="菜单权限")


class Dept(BaseEntity):
    """组织架构"""

    DEPT_TYPE = (
        ("company", "公司"),
        ("department", "部门"),
    )
    type = models.CharField(max_length=20, choices=DEPT_TYPE, default="company", verbose_name="类型")
    pid = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="上级部门",
    )


class User(BaseEntity, AbstractUser):
    """用户"""

    GENDERS = [(1, "男"), (2, "女")]
    name = None  # 覆盖name字段，使其不可用
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name="电话")
    gender = models.PositiveIntegerField(choices=GENDERS, default=1, verbose_name="性别")
    nick_name = models.CharField(max_length=150, null=True, blank=True, verbose_name="用户昵称")
    position = models.CharField(max_length=20, choices=settings.USER_TYPE, default="student", verbose_name="职位")
    avatar = models.ImageField(
        upload_to="static/%Y/%m",
        default="image/default.png",
        max_length=100,
        null=True,
        blank=True,
        verbose_name="头像",
    )
    dept = models.ForeignKey(
        "Dept",
        null=True,
        blank=True,
        related_name="users",
        on_delete=models.SET_NULL,
        verbose_name="部门",
    )
    roles = models.ManyToManyField(
        "Role",
        blank=True,
        related_name="users",
        verbose_name="角色",
    )

    def __str__(self):
        return self.username
