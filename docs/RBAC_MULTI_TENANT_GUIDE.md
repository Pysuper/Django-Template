# RBAC权限管理与多租户系统使用指南

## 目录 / Table of Contents

1. [概述 / Overview](#概述--overview)
2. [快速开始 / Quick Start](#快速开始--quick-start)
3. [多租户配置 / Multi-Tenancy Configuration](#多租户配置--multi-tenancy-configuration)
4. [RBAC权限管理 / RBAC Permission Management](#rbac权限管理--rbac-permission-management)
5. [使用示例 / Usage Examples](#使用示例--usage-examples)
6. [API参考 / API Reference](#api参考--api-reference)
7. [最佳实践 / Best Practices](#最佳实践--best-practices)

---

## 概述 / Overview

### 功能特性 / Features

- ✅ **多租户支持**: 完整的多租户SaaS架构
- ✅ **RBAC权限**: 基于角色的访问控制
- ✅ **数据范围**: 细粒度的数据访问控制
- ✅ **菜单权限**: 前端菜单和按钮权限管理
- ✅ **租户隔离**: 完全的租户数据隔离
- ✅ **可配置**: 所有功能可通过配置开关控制

### 架构说明 / Architecture

```
┌─────────────────────────────────────────────┐
│             Tenant (租户)                    │
│  - name, code, domain                       │
│  - settings, max_users, expire_date         │
└─────────────────────────────────────────────┘
                    │
                    │ 1:N
                    ▼
┌─────────────────────────────────────────────┐
│              User (用户)                     │
│  - username, tenant, department             │
│  - roles, is_tenant_admin                   │
└─────────────────────────────────────────────┘
                    │
                    │ M:N
                    ▼
┌─────────────────────────────────────────────┐
│              Role (角色)                     │
│  - name, code, data_scope                   │
│  - permissions, menus, buttons              │
└─────────────────────────────────────────────┘
         │              │              │
         │ M:N          │ M:N          │ M:N
         ▼              ▼              ▼
    ┌────────┐    ┌─────────┐   ┌─────────┐
    │Permission│  │  Menu   │   │ Button  │
    └────────┘    └─────────┘   └─────────┘
```

---

## 快速开始 / Quick Start

### 1. 启用多租户 / Enable Multi-Tenancy

在 `.env` 文件中添加：

```bash
# 多租户设置
MULTI_TENANT_ENABLED=True
MULTI_TENANT_REQUIRED=False
DEFAULT_MAX_USERS=100

# RBAC设置
RBAC_ENABLED=True
DATA_SCOPE_ENABLED=True
DEFAULT_DATA_SCOPE=self
```

### 2. 配置中间件 / Configure Middleware

在 `settings.py` 中：

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # 多租户和RBAC中间件
    'apps.users.middleware.TenantMiddleware',
    'apps.users.middleware.TenantContextMiddleware',
    'apps.users.middleware.TenantIsolationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',
]
```

### 3. 创建租户 / Create Tenant

```python
from apps.users.services.tenant import tenant_service

# 创建租户
tenant = tenant_service.create_tenant(
    name='Acme Corporation',
    code='acme',
    domain='acme.example.com',
    max_users=200
)
```

### 4. 创建用户并分配角色 / Create User and Assign Role

```python
from apps.users.models import User, Role, Department

# 创建部门
dept = Department.objects.create(
    tenant=tenant,
    name='IT Department',
    type='department'
)

# 创建角色
role = Role.objects.create(
    tenant=tenant,
    name='Manager',
    code='manager',
    data_scope='dept'
)

# 创建用户
user = User.objects.create_user(
    username='john_doe',
    password='SecurePass123!',
    tenant=tenant,
    department=dept,
    email='john@acme.com'
)

# 分配角色
user.roles.add(role)
```

---

## 多租户配置 / Multi-Tenancy Configuration

### 配置选项 / Configuration Options

在 `config/settings/multi_tenant.py` 中配置：

```python
# 是否启用多租户
MULTI_TENANT_ENABLED = True

# 是否必须识别租户
MULTI_TENANT_REQUIRED = False

# 租户识别方式
TENANT_IDENTIFICATION = ['subdomain', 'header', 'query']

# 默认租户代码
DEFAULT_TENANT_CODE = 'default'

# 租户隔离排除的路径
TENANT_ISOLATION_EXCLUDE_PATHS = [
    '/admin/',
    '/health/',
]
```

### 租户识别方式 / Tenant Identification Methods

#### 1. 子域名 / Subdomain

```
http://tenant.example.com/api/users/
```

#### 2. HTTP头 / HTTP Header

```
GET /api/users/
X-Tenant-Code: acme
```

#### 3. 查询参数 / Query Parameter

```
GET /api/users/?tenant=acme
```

### 关闭多租户 / Disable Multi-Tenancy

在 `.env` 中设置：

```bash
MULTI_TENANT_ENABLED=False
```

系统将作为单租户运行，所有租户相关的功能将被禁用。

---

## RBAC权限管理 / RBAC Permission Management

### 核心概念 / Core Concepts

#### 1. 权限 (Permission)

API级别的权限控制

```python
from apps.users.models import Permission

# 创建权限
perm = Permission.objects.create(
    tenant=tenant,
    name='查看用户',
    code='user:view',
    method='GET',
    path='/api/users/'
)

# 分配给角色
role.permissions.add(perm)
```

#### 2. 角色 (Role)

用户角色的集合

```python
from apps.users.models import Role

# 创建角色
role = Role.objects.create(
    tenant=tenant,
    name='管理员',
    code='admin',
    data_scope='all',  # 可访问所有数据
    is_default=False
)

# 分配权限
role.permissions.add(perm1, perm2, perm3)

# 分配菜单
role.menus.add(menu1, menu2)

# 分配按钮
role.buttons.add(btn1, btn2)
```

#### 3. 数据范围 (Data Scope)

控制用户可以访问的数据范围

```python
# 数据范围选项
DATA_SCOPE_CHOICES = [
    ('all', '全部数据'),              # 可访问所有数据
    ('dept_and_sub', '本部门及子部门'),  # 本部门及下级部门
    ('dept', '本部门数据'),          # 仅本部门
    ('self', '仅本人数据'),          # 仅本人创建的数据
]

# 设置角色的数据范围
role.data_scope = 'dept'
role.save()
```

### 权限检查 / Permission Checking

#### 方法1: 使用装饰器

```python
from apps.users.decorators import require_permission, require_role

@require_permission('user:create')
def create_user(request):
    # 只有有 user:create 权限的用户才能访问
    pass

@require_role('admin')
def admin_view(request):
    # 只有管理员角色的用户才能访问
    pass
```

#### 方法2: 使用服务层

```python
from apps.users.services.rbac import rbac_service

def my_view(request):
    # 检查权限
    if rbac_service.has_permission(request.user, 'user:create'):
        # 有权限，执行操作
        pass
    else:
        # 无权限，返回错误
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("权限不足")
```

#### 方法3: 在DRF视图中

```python
from rest_framework import viewsets
from apps.users.decorators import HasPermission, HasRole

class UserViewSet(viewsets.ModelViewSet):
    # 权限类
    permission_classes = [HasPermission]
    required_permission = 'user:view'

    def get_queryset(self):
        # 自动过滤数据范围
        queryset = User.objects.all()

        # 根据用户的数据范围过滤
        queryset = rbac_service.filter_data_by_scope(
            self.request.user,
            queryset
        )

        return queryset
```

---

## 使用示例 / Usage Examples

### 示例1: 创建完整的租户结构

```python
from apps.users.services.tenant import tenant_service
from apps.users.models import User, Role, Department, Permission, Menu

# 1. 创建租户
tenant = tenant_service.create_tenant(
    name='Example Corp',
    code='example',
    max_users=100
)

# 2. 创建部门结构
company_dept = Department.objects.create(
    tenant=tenant,
    name='Example Corp',
    type='company'
)

it_dept = Department.objects.create(
    tenant=tenant,
    name='IT Department',
    type='department',
    parent=company_dept
)

# 3. 创建角色
admin_role = Role.objects.create(
    tenant=tenant,
    name='Administrator',
    code='admin',
    data_scope='all',
    is_tenant_admin=True
)

manager_role = Role.objects.create(
    tenant=tenant,
    name='Manager',
    code='manager',
    data_scope='dept'
)

user_role = Role.objects.create(
    tenant=tenant,
    name='User',
    code='user',
    data_scope='self',
    is_default=True
)

# 4. 创建权限
permissions = [
    Permission.objects.create(
        tenant=tenant,
        name='查看用户',
        code='user:view',
        method='GET',
        path='/api/users/'
    ),
    Permission.objects.create(
        tenant=tenant,
        name='创建用户',
        code='user:create',
        method='POST',
        path='/api/users/'
    ),
    # ... 更多权限
]

# 5. 分配权限给角色
admin_role.permissions.add(*permissions)
manager_role.permissions.add(*permissions[:2])

# 6. 创建菜单
system_menu = Menu.objects.create(
    tenant=tenant,
    title='系统管理',
    name='system',
    icon='setting',
    sort_order=1
)

user_menu = Menu.objects.create(
    tenant=tenant,
    title='用户管理',
    name='user',
    path='/users',
    icon='user',
    sort_order=1,
    parent=system_menu
)

# 7. 分配菜单给角色
admin_role.menus.add(system_menu, user_menu)
manager_role.menus.add(user_menu)

# 8. 创建用户
admin = User.objects.create_user(
    username='admin',
    password='AdminPass123!',
    tenant=tenant,
    department=it_dept,
    is_tenant_admin=True
)

manager = User.objects.create_user(
    username='manager',
    password='ManagerPass123!',
    tenant=tenant,
    department=it_dept
)
manager.roles.add(manager_role)

user = User.objects.create_user(
    username='john',
    password='UserPass123!',
    tenant=tenant,
    department=it_dept
)
user.roles.add(user_role)
```

### 示例2: 在视图中使用权限控制

```python
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.users.decorators import require_permission
from apps.users.services.rbac import rbac_service

class UserViewSet(viewsets.ModelViewSet):

    @action(detail=False, methods=['post'])
    @require_permission('user:bulk_delete')
    def bulk_delete(self, request):
        """批量删除用户 - 需要特定权限"""
        user_ids = request.data.get('user_ids', [])

        # 检查数据范围
        queryset = User.objects.filter(id__in=user_ids)
        queryset = rbac_service.filter_data_by_scope(request.user, queryset)

        count = queryset.update(is_active=False)

        return Response({
            'message': f'成功删除{count}个用户'
        })
```

### 示例3: 根据数据范围过滤数据

```python
from apps.users.services.rbac import rbac_service

def get_document_list(request):
    """获取文档列表 - 根据用户数据范围过滤"""
    queryset = Document.objects.all()

    # 应用数据范围过滤
    filtered_queryset = rbac_service.filter_data_by_scope(
        request.user,
        queryset
    )

    # 获取数据范围信息
    data_scope = rbac_service.get_user_data_scope(request.user)

    return {
        'documents': filtered_queryset,
        'data_scope': data_scope,
        'count': filtered_queryset.count()
    }
```

---

## API参考 / API Reference

### TenantService (租户服务)

```python
from apps.users.services.tenant import tenant_service

# 获取租户
tenant = tenant_service.get_tenant_by_code('acme')
tenant = tenant_service.get_tenant_by_id(1)
tenant = tenant_service.get_tenant_by_domain('acme.example.com')

# 创建租户
tenant = tenant_service.create_tenant(
    name='Acme Corp',
    code='acme',
    domain='acme.example.com',
    max_users=100
)

# 更新租户
tenant = tenant_service.update_tenant(
    tenant,
    name='New Name',
    max_users=200
)

# 激活/停用租户
tenant_service.activate_tenant(tenant)
tenant_service.deactivate_tenant(tenant)

# 检查租户状态
is_active = tenant_service.is_tenant_active(tenant)
can_add = tenant_service.can_add_user(tenant)
user_count = tenant_service.get_tenant_user_count(tenant)

# 过滤查询集
filtered = tenant_service.filter_queryset_by_tenant(user, queryset)
```

### RBACService (RBAC服务)

```python
from apps.users.services.rbac import rbac_service

# 权限检查
has_perm = rbac_service.has_permission(user, 'user:view')
has_role = rbac_service.has_role(user, 'admin')
has_any = rbac_service.has_any_role(user, ['admin', 'manager'])
has_all = rbac_service.has_all_roles(user, ['admin', 'auditor'])

# 获取用户权限和角色
permissions = rbac_service.get_user_permissions(user)
roles = rbac_service.get_user_roles(user)
menus = rbac_service.get_user_menus(user)
data_scope = rbac_service.get_user_data_scope(user)

# 过滤数据
filtered = rbac_service.filter_data_by_scope(user, queryset)

# 角色管理
rbac_service.assign_role(user, role)
rbac_service.remove_role(user, role)
rbac_service.assign_permission(role, permission)
rbac_service.remove_permission(role, permission)
```

---

## 最佳实践 / Best Practices

### 1. 租户设计 / Tenant Design

```python
# ✅ 推荐: 为每个客户创建独立租户
tenant = tenant_service.create_tenant(
    name=customer_name,
    code=customer_code.lower(),
    domain=f'{customer_code.lower()}.app.com'
)

# ❌ 不推荐: 所有客户共享一个租户
```

### 2. 角色设计 / Role Design

```python
# ✅ 推荐: 使用层次化的角色结构
# 系统管理员 -> 部门经理 -> 普通用户

# 创建默认角色
user_role = Role.objects.create(
    tenant=tenant,
    name='普通用户',
    code='user',
    data_scope='self',
    is_default=True  # 新用户默认角色
)

# ❌ 不推荐: 给所有用户分配管理员权限
```

### 3. 数据范围 / Data Scope

```python
# ✅ 推荐: 根据角色职责设置数据范围
Role.objects.create(
    tenant=tenant,
    name='HR经理',
    code='hr_manager',
    data_scope='dept'  # 只能查看本部门数据
)

# ❌ 不推荐: 所有角色都设置为'all'
```

### 4. 权限粒度 / Permission Granularity

```python
# ✅ 推荐: 细粒度的权限控制
permissions = [
    'user:view',
    'user:create',
    'user:update',
    'user:delete',
    'user:export',
    'user:import',
]

# ❌ 不推荐: 过于宽泛的权限
permissions = [
    'user:manage',  # 包含太多操作
]
```

### 5. 缓存策略 / Caching Strategy

```python
# 设置合理的缓存时间
PERMISSION_CACHE_TIMEOUT = 3600  # 1小时
TENANT_CACHE_TIMEOUT = 3600

# 当权限变更时清除缓存
def update_role_permissions(role, permissions):
    role.permissions.set(permissions)
    # 清除所有拥有该角色的用户的缓存
    for user in role.users.all():
        rbac_service._clear_user_cache(user.id)
```

### 6. 错误处理 / Error Handling

```python
# ✅ 推荐: 友好的错误提示
from django.core.exceptions import PermissionDenied

def my_view(request):
    if not rbac_service.has_permission(request.user, 'user:create'):
        raise PermissionDenied(
            "您没有创建用户的权限，请联系管理员"
        )
```

---

## 常见问题 / FAQ

### Q: 如何临时禁用多租户功能？

A: 在 `.env` 文件中设置：
```bash
MULTI_TENANT_ENABLED=False
```

### Q: 如何允许超级管理员访问所有租户的数据？

A: 已经内置支持，`is_superuser=True` 的用户可以访问所有数据。

### Q: 如何自定义租户识别逻辑？

A: 继承 `TenantMiddleware` 并重写 `_identify_tenant` 方法：
```python
class CustomTenantMiddleware(TenantMiddleware):
    def _identify_tenant(self, request):
        # 自定义识别逻辑
        pass
```

### Q: 数据范围过滤会影响性能吗？

A: 影响很小，因为使用了数据库级别的过滤，并且有缓存支持。

### Q: 如何迁移现有数据到多租户结构？

A: 需要创建数据迁移脚本：
```python
def migrate_to_multi_tenant():
    # 1. 创建默认租户
    default_tenant = Tenant.objects.create(
        name='Default',
        code='default'
    )

    # 2. 将现有用户关联到默认租户
    User.objects.update(tenant=default_tenant)
```

---

## 相关文档 / Related Docs

- [DRF封装使用指南](../../utils/drf/USAGE_GUIDE.md)
- [安全配置指南](./SECURITY.md)
- [部署指南](./DEPLOYMENT.md)

---

**文档版本**: 1.0.0
**最后更新**: 2025-02-04
**作者**: Django Template Team
