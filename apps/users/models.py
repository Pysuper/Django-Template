"""
用户模型 / User Models

提供RBAC权限管理和多租户支持的模型
"""

from typing import Optional, TYPE_CHECKING

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Permission as DjangoPermission
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.drf.base import BaseEntity

if TYPE_CHECKING:
    from django.db.models.manager import Manager


class Tenant(BaseEntity):
    """
    租户 / Tenant

    多租户系统的核心模型，表示一个独立的租户（公司/组织）
    Core model for multi-tenancy, representing an independent tenant (company/organization)

    Attributes:
        name: 租户名称 / Tenant name
        code: 租户代码（唯一） / Tenant code (unique)
        is_active: 是否激活 / Active status
        logo: 租户Logo / Tenant logo
        domain: 租户域名 / Tenant domain
        settings: 租户配置（JSON） / Tenant settings (JSON)

    Example:
        >>> tenant = Tenant.objects.create(
        ...     name="Acme Corp",
        ...     code="acme",
        ...     domain="acme.example.com"
        ... )
        >>> user = User.objects.create_user(
        ...     username="john",
        ...     tenant=tenant
        ... )
    """

    name = models.CharField(
        max_length=200,
        verbose_name=_("租户名称"),
        help_text=_("租户的公司或组织名称")
    )
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("租户代码"),
        help_text=_("租户的唯一标识符")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("是否激活"),
        help_text=_("租户是否处于激活状态")
    )
    logo = models.ImageField(
        upload_to="tenant_logos/%Y/%m",
        null=True,
        blank=True,
        verbose_name=_("租户Logo")
    )
    domain = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        verbose_name=_("租户域名"),
        help_text=_("租户的自定义域名")
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("租户配置"),
        help_text=_("租户特定的配置项")
    )
    max_users = models.PositiveIntegerField(
        default=100,
        verbose_name=_("最大用户数"),
        help_text=_("租户允许的最大用户数")
    )
    expire_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("过期日期"),
        help_text=_("租户订阅过期日期")
    )

    class Meta:
        verbose_name = _("租户")
        verbose_name_plural = _("租户")
        ordering = ["-create_date"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def clean(self) -> None:
        """验证租户数据"""
        # 检查用户数限制
        if self.max_users <= 0:
            raise ValidationError({"max_users": _("最大用户数必须大于0")})

    def get_user_count(self) -> int:
        """获取当前用户数"""
        return self.users.filter(is_active=True).count()

    def is_within_user_limit(self) -> bool:
        """检查是否在用户限制内"""
        return self.get_user_count() < self.max_users

    def is_expired(self) -> bool:
        """检查租户是否过期"""
        if not self.expire_date:
            return False
        from django.utils import timezone
        return timezone.now() > self.expire_date


class Department(BaseEntity):
    """
    部门 / Department

    组织架构中的部门或团队
    Department or team in the organizational structure

    Attributes:
        tenant: 所属租户 / Belonging tenant
        name: 部门名称 / Department name
        code: 部门代码 / Department code
        type: 部门类型 / Department type
        parent: 上级部门 / Parent department
        manager: 部门经理 / Department manager
    """

    class DepartmentType(models.TextChoices):
        """部门类型 / Department type choices"""
        COMPANY = 'company', _('公司')
        DEPARTMENT = 'department', _('部门')
        TEAM = 'team', _('团队')

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='departments',
        verbose_name=_("所属租户"),
        help_text=_("部门所属的租户")
    )
    name = models.CharField(
        max_length=200,
        verbose_name=_("部门名称"),
        help_text=_("部门的名称")
    )
    code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_("部门代码"),
        help_text=_("部门的唯一代码")
    )
    type = models.CharField(
        max_length=20,
        choices=DepartmentType.choices,
        default=DepartmentType.DEPARTMENT,
        verbose_name=_("部门类型")
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("上级部门"),
        help_text=_("父级部门")
    )
    manager = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_departments',
        verbose_name=_("部门经理"),
        help_text=_("部门的负责人")
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("排序"),
        help_text=_("显示排序顺序")
    )

    class Meta:
        verbose_name = _("部门")
        verbose_name_plural = _("部门")
        ordering = ['tenant', 'sort_order', 'id']
        unique_together = [['tenant', 'code']]

    def __str__(self) -> str:
        return f"{self.tenant.name} - {self.name}"

    def get_ancestors(self) -> list:
        """获取所有上级部门"""
        ancestors = []
        parent = self.parent
        while parent:
            ancestors.append(parent)
            parent = parent.parent
        return ancestors

    def get_descendants(self) -> list:
        """获取所有下级部门"""
        descendants = []
        children = self.children.all()
        for child in children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants


class Menu(BaseEntity):
    """
    菜单 / Menu

    系统菜单项，用于前端导航
    System menu items for frontend navigation

    Attributes:
        tenant: 所属租户（null表示全局菜单）/ Tenant (null means global menu)
        title: 菜单标题 / Menu title
        name: 菜单名称（唯一标识）/ Menu name (unique identifier)
        path: 路由路径 / Route path
        component: 组件路径 / Component path
        icon: 图标 / Icon
        sort_order: 排序 / Sort order
        is_visible: 是否可见 / Visibility
        parent: 父菜单 / Parent menu
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='menus',
        verbose_name=_("所属租户"),
        help_text=_("null表示全局菜单，所有租户可见")
    )
    title = models.CharField(
        max_length=100,
        verbose_name=_("菜单标题"),
        help_text=_("菜单显示的标题")
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("菜单名称"),
        help_text=_("菜单的唯一标识符")
    )
    path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("路由路径"),
        help_text=_("前端路由路径")
    )
    component = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name=_("组件路径"),
        help_text=_("Vue组件路径")
    )
    icon = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_("图标"),
        help_text=_("菜单图标")
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_("排序"),
        help_text=_("菜单显示顺序")
    )
    is_visible = models.BooleanField(
        default=True,
        verbose_name=_("是否可见"),
        help_text=_("菜单是否在前端显示")
    )
    is_frame = models.BooleanField(
        default=False,
        verbose_name=_("外部链接"),
        help_text=_("是否为外部链接")
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("父菜单"),
        help_text=_("父级菜单")
    )
    redirect = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("重定向"),
        help_text=_("重定向路径")
    )

    class Meta:
        verbose_name = _("菜单")
        verbose_name_plural = _("菜单")
        ordering = ['tenant', 'sort_order', 'id']
        unique_together = [['tenant', 'name']]

    def __str__(self) -> str:
        tenant_name = self.tenant.name if self.tenant else "Global"
        return f"{tenant_name} - {self.title}"


class Button(BaseEntity):
    """
    按钮 / Button

    页面按钮权限控制
    Page button permission control

    Attributes:
        tenant: 所属租户 / Tenant
        name: 按钮名称 / Button name
        code: 按钮代码（权限标识）/ Button code (permission identifier)
        type: 按钮类型 / Button type
        menu: 关联菜单 / Related menu
    """

    class ButtonType(models.IntegerChoices):
        """按钮类型 / Button type choices"""
        MENU = 1, _('菜单')
        BUTTON = 2, _('按钮')

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='buttons',
        verbose_name=_("所属租户")
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("按钮名称"),
        help_text=_("按钮显示的名称")
    )
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("按钮代码"),
        help_text=_("按钮的唯一权限标识符")
    )
    type = models.IntegerField(
        choices=ButtonType.choices,
        default=ButtonType.BUTTON,
        verbose_name=_("类型")
    )
    menu = models.ForeignKey(
        Menu,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='buttons',
        verbose_name=_("关联菜单"),
        help_text=_("按钮所属的菜单")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("描述"),
        help_text=_("按钮的描述")
    )

    class Meta:
        verbose_name = _("按钮")
        verbose_name_plural = _("按钮")
        ordering = ['tenant', 'id']
        unique_together = [['tenant', 'code']]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Permission(BaseEntity):
    """
    权限 / Permission

    API权限定义
    API permission definition

    Attributes:
        tenant: 所属租户 / Tenant
        name: 权限名称 / Permission name
        code: 权限代码 / Permission code
        method: HTTP方法 / HTTP method
        path: API路径 / API path
        menu: 关联菜单 / Related menu
        parent: 父权限 / Parent permission
        description: 描述 / Description
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='permissions',
        verbose_name=_("所属租户")
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("权限名称"),
        help_text=_("权限的显示名称")
    )
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("权限代码"),
        help_text=_("权限的唯一标识符，如 user:view")
    )
    method = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_("HTTP方法"),
        help_text=_("如 GET, POST, PUT, DELETE")
    )
    path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_("API路径"),
        help_text=_("API的路径，如 /api/users/")
    )
    menu = models.ForeignKey(
        Menu,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='permissions',
        verbose_name=_("关联菜单"),
        help_text=_("权限关联的菜单")
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_("父权限"),
        help_text=_("父级权限")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("描述"),
        help_text=_("权限的详细描述")
    )

    class Meta:
        verbose_name = _("权限")
        verbose_name_plural = _("权限")
        ordering = ['tenant', 'id']
        unique_together = [['tenant', 'code']]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class Role(BaseEntity):
    """
    角色 / Role

    用户角色，用于权限管理
    User role for permission management

    Attributes:
        tenant: 所属租户 / Tenant
        name: 角色名称 / Role name
        code: 角色代码 / Role code
        is_active: 是否激活 / Active status
        permissions: 权限 / Permissions
        menus: 菜单 / Menus
        buttons: 按钮 / Buttons
        description: 描述 / Description
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='roles',
        verbose_name=_("所属租户"),
        help_text=_("角色所属的租户")
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_("角色名称"),
        help_text=_("角色的显示名称")
    )
    code = models.CharField(
        max_length=50,
        verbose_name=_("角色代码"),
        help_text=_("角色的唯一标识符")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("是否激活"),
        help_text=_("角色是否处于激活状态")
    )
    is_default = models.BooleanField(
        default=False,
        verbose_name=_("是否默认角色"),
        help_text=_("新用户的默认角色")
    )
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='roles',
        verbose_name=_("权限"),
        help_text=_("角色拥有的API权限")
    )
    menus = models.ManyToManyField(
        Menu,
        blank=True,
        related_name='roles',
        verbose_name=_("菜单"),
        help_text=_("角色可访问的菜单")
    )
    buttons = models.ManyToManyField(
        Button,
        blank=True,
        related_name='roles',
        verbose_name=_("按钮"),
        help_text=_("角色可操作的按钮")
    )
    data_scope = models.CharField(
        max_length=20,
        choices=[
            ('all', _('全部数据')),
            ('dept', _('本部门数据')),
            ('dept_and_sub', _('本部门及子部门数据')),
            ('self', _('仅本人数据')),
        ],
        default='self',
        verbose_name=_("数据范围"),
        help_text=_("角色可访问的数据范围")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("描述"),
        help_text=_("角色的详细描述")
    )

    class Meta:
        verbose_name = _("角色")
        verbose_name_plural = _("角色")
        ordering = ['tenant', 'id']
        unique_together = [['tenant', 'code']]

    def __str__(self) -> str:
        return f"{self.tenant.name} - {self.name}"

    def has_permission(self, permission_code: str) -> bool:
        """检查角色是否有指定权限"""
        return self.permissions.filter(code=permission_code, del_flag=False).exists()

    def has_menu(self, menu_id: int) -> bool:
        """检查角色是否有指定菜单权限"""
        return self.menus.filter(id=menu_id, del_flag=False).exists()

    def has_button(self, button_code: str) -> bool:
        """检查角色是否有指定按钮权限"""
        return self.buttons.filter(code=button_code, del_flag=False).exists()


class User(AbstractUser, BaseEntity):
    """
    用户 / User

    系统用户模型，支持多租户和RBAC
    System user model with multi-tenancy and RBAC support

    Attributes:
        tenant: 所属租户 / Tenant
        department: 所属部门 / Department
        roles: 角色 / Roles
        phone: 电话 / Phone
        gender: 性别 / Gender
        nickname: 昵称 / Nickname
        avatar: 头像 / Avatar
        is_active: 是否激活 / Active status
    """

    class GenderType(models.IntegerChoices):
        """性别类型 / Gender type choices"""
        MALE = 1, _('男')
        FEMALE = 2, _('女')
        OTHER = 3, _('其他')

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='users',
        verbose_name=_("所属租户"),
        help_text=_("用户所属的租户")
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_("所属部门"),
        help_text=_("用户所属的部门")
    )
    roles = models.ManyToManyField(
        Role,
        blank=True,
        related_name='users',
        verbose_name=_("角色"),
        help_text=_("用户拥有的角色")
    )
    phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_("电话"),
        help_text=_("联系电话")
    )
    gender = models.IntegerField(
        choices=GenderType.choices,
        default=GenderType.MALE,
        verbose_name=_("性别")
    )
    nickname = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name=_("昵称"),
        help_text=_("用户昵称")
    )
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m",
        null=True,
        blank=True,
        verbose_name=_("头像"),
        help_text=_("用户头像图片")
    )
    position = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("职位"),
        help_text=_("用户的职位")
    )
    is_tenant_admin = models.BooleanField(
        default=False,
        verbose_name=_("是否租户管理员"),
        help_text=_("是否为租户的管理员")
    )
    last_login_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("最后登录IP"),
        help_text=_("最后一次登录的IP地址")
    )
    last_login_user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name=_("最后登录UA"),
        help_text=_("最后一次登录的浏览器信息")
    )

    class Meta:
        verbose_name = _("用户")
        verbose_name_plural = _("用户")
        ordering = ['tenant', 'id']

    def __str__(self) -> str:
        return f"{self.tenant.code} - {self.username}"

    def get_full_name(self) -> str:
        """获取用户全名"""
        return self.nickname or self.username

    def has_role(self, role_code: str) -> bool:
        """检查用户是否有指定角色"""
        return self.roles.filter(code=role_code, del_flag=False, is_active=True).exists()

    def has_permission(self, permission_code: str) -> bool:
        """检查用户是否有指定权限"""
        # 租户管理员拥有所有权限
        if self.is_tenant_admin:
            return True

        # 检查角色的权限
        return self.roles.filter(
            permissions__code=permission_code,
            del_flag=False,
            is_active=True
        ).exists()

    def has_menu(self, menu_id: int) -> bool:
        """检查用户是否有指定菜单权限"""
        if self.is_tenant_admin:
            return True

        return self.roles.filter(
            menus__id=menu_id,
            del_flag=False,
            is_active=True
        ).exists()

    def has_button(self, button_code: str) -> bool:
        """检查用户是否有指定按钮权限"""
        if self.is_tenant_admin:
            return True

        return self.roles.filter(
            buttons__code=button_code,
            del_flag=False,
            is_active=True
        ).exists()

    def get_permissions(self) -> list:
        """获取用户所有权限代码列表"""
        if self.is_tenant_admin:
            return ['*']  # 管理员拥有所有权限

        return list(
            Permission.objects.filter(
                roles__users=self,
                del_flag=False,
                status=True
            ).values_list('code', flat=True).distinct()
        )

    def get_menus(self) -> list:
        """获取用户可访问的菜单列表"""
        if self.is_tenant_admin:
            return list(Menu.objects.filter(tenant=self.tenant, del_flag=False))

        return list(
            Menu.objects.filter(
                roles__users=self,
                del_flag=False,
                status=True
            ).distinct()
        )

    def get_data_scope(self) -> str:
        """获取用户的数据访问范围"""
        # 获取最大数据范围
        scopes = self.roles.filter(
            is_active=True,
            del_flag=False
        ).values_list('data_scope', flat=True)

        if 'all' in scopes:
            return 'all'
        elif 'dept_and_sub' in scopes:
            return 'dept_and_sub'
        elif 'dept' in scopes:
            return 'dept'
        else:
            return 'self'


# 设置Django的AUTH_USER_MODEL
# 注意：这应该在settings.py中配置，这里只是文档说明
# AUTH_USER_MODEL = 'users.User'
