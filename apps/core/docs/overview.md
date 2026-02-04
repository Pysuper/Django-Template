# Apps Core Module / Core模块文档

## 概述 / Overview

`apps/core`模块提供Django项目的核心功能，包括：

- **基础模型** (Models): 时间戳、软删除、审计、状态管理等功能
- **中间件** (Middleware): 性能监控、安全检查、请求日志
- **工具函数** (Utils): 文件处理、IP获取、数据脱敏
- **认证** (Auth): 密码策略、会话管理、登录跟踪
- **权限** (Permissions): 基于角色的权限控制
- **缓存** (Cache): 统一的缓存管理
- **异常** (Exceptions): 自定义异常处理

---

## 目录结构 / Directory Structure

```
apps/core/
├── models.py              # 基础模型
├── utils.py               # 工具函数
├── auth.py                # 认证功能
├── permissions.py         # 权限管理
├── cache.py               # 缓存管理
├── exceptions.py          # 异常处理
├── security.py            # 安全功能
├── middleware/            # 中间件模块
│   ├── __init__.py
│   ├── performance.py     # 性能监控中间件
│   └── security.py        # 安全中间件
├── services/              # 服务模块
├── tests/                 # 测试
│   ├── test_models.py
│   ├── test_utils.py
│   └── test_middleware.py
└── docs/                  # 文档
    ├── overview.md
    └── api.md
```

---

## 模型 / Models

### BaseModel

基础模型，组合了时间戳和软删除功能。

```python
from apps.core.models import BaseModel

class Product(BaseModel):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
```

**功能**:
- 自动记录创建时间和更新时间
- 支持软删除（不真正删除记录）
- 可以恢复已删除的记录

**方法**:
- `delete()`: 软删除
- `hard_delete()`: 真正删除
- `restore()`: 恢复已删除的记录

### TimeStampedModel

仅提供时间戳功能。

```python
from apps.core.models import TimeStampedModel

class LogEntry(TimeStampedModel):
    message = models.TextField()
```

### SoftDeleteModel

仅提供软删除功能。

```python
from apps.core.models import SoftDeleteModel

class TempFile(SoftDeleteModel):
    filename = models.CharField(max_length=255)
```

### ActivableModel

提供启用/禁用功能。

```python
from apps.core.models import ActivableModel

class Feature(ActivableModel):
    name = models.CharField(max_length=100)

# 使用
feature = Feature.objects.create(name="New Feature")
feature.deactivate()  # 停用
feature.activate()    # 激活
```

### StatusModel

提供状态管理功能。

```python
from apps.core.models import StatusModel

class Article(StatusModel):
    title = models.CharField(max_length=200)

# 状态选项
article.change_status(StatusModel.StatusChoices.PUBLISHED)
```

**可用状态**:
- `draft`: 草稿
- `published`: 已发布
- `archived`: 已归档
- `deleted`: 已删除

---

## 中间件 / Middleware

### ResponseTimeMiddleware

记录请求处理时间。

```python
# settings.py
MIDDLEWARE = [
    ...
    'apps.core.middleware.ResponseTimeMiddleware',
    ...
]
```

**功能**:
- 添加`X-Response-Time`响应头（毫秒）
- 记录慢查询（超过1秒）

### RequestLogMiddleware

记录请求详细信息。

```python
# settings.py
MIDDLEWARE = [
    ...
    'apps.core.middleware.RequestLogMiddleware',
    ...
]

REQUEST_LOGGING = True
REQUEST_LOGGING_SENSITIVE_FIELDS = ['password', 'token']
```

### SecurityMiddleware

添加安全相关的HTTP头。

```python
# settings.py
MIDDLEWARE = [
    ...
    'apps.core.middleware.SecurityMiddleware',
    ...
]
```

**添加的安全头**:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy`
- `Strict-Transport-Security` (HTTPS)

---

## 工具函数 / Utils

### PathAndRename

文件上传路径处理。

```python
from apps.core.utils import PathAndRename

path_and_rename = PathAndRename('uploads')

class Document(models.Model):
    file = models.FileField(upload_to=path_and_rename)
```

### validate_file_size

验证文件大小。

```python
from apps.core.utils import validate_file_size

def upload_file(request):
    file = request.FILES['file']
    if not validate_file_size(file, max_size=5):  # 5MB
        raise ValidationError('文件过大')
```

### get_client_ip

获取客户端IP地址。

```python
from apps.core.utils import get_client_ip

def my_view(request):
    ip = get_client_ip(request)
    print(f"Client IP: {ip}")
```

### mask_sensitive_data

敏感数据脱敏。

```python
from apps.core.utils import mask_sensitive_data

# 邮箱
masked = mask_sensitive_data('user@example.com', data_type='email')
# 结果: u***@example.com

# 手机号
masked = mask_sensitive_data('13800138000', data_type='phone')
# 结果: 138***8000

# 身份证
masked = mask_sensitive_data('110101199001011234', data_type='id_card')
# 结果: 110101********1234
```

---

## 认证 / Auth

### 密码策略 / Password Policy

```python
# settings.py
PASSWORD_POLICY = {
    'min_length': 8,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_digits': True,
    'require_special': True,
    'password_expire_days': 90,
}
```

### 会话管理 / Session Management

```python
from apps.core.auth import SessionManager

session_manager = SessionManager()

# 创建会话
session_manager.create_session(request, user)

# 验证会话
session_manager.validate_session(request, user)

# 销毁会话
session_manager.destroy_session(request, user)
```

### 登录尝试跟踪 / Login Attempt Tracking

```python
from apps.core.auth import LoginAttemptTracker

tracker = LoginAttemptTracker()

# 记录尝试
tracker.record_attempt(username, ip_address, success=True)

# 检查是否锁定
if tracker.is_locked_out(username, ip_address):
    raise ValidationError('账户已锁定')
```

---

## 权限 / Permissions

### 权限类 / Permission Classes

```python
from apps.core.permissions import IsOwner, IsAdmin, HasRole

class MyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsOwner | IsAdmin]
```

### 权限管理器 / Permission Manager

```python
from apps.core.permissions import PermissionManager

manager = PermissionManager()

# 获取用户权限
permissions = manager.get_user_permissions(user)

# 获取用户角色
roles = manager.get_user_roles(user)

# 分配角色
manager.assign_role(user, 'admin')

# 移除角色
manager.remove_role(user, 'admin')
```

---

## 缓存 / Cache

### CacheManager

统一的缓存管理器。

```python
from apps.core.cache import CacheManager

cache_manager = CacheManager(prefix='myapp', timeout=3600)

# 设置缓存
cache_manager.set('key', 'value')

# 获取缓存
value = cache_manager.get('key')

# 删除缓存
cache_manager.delete('key')

# 清除缓存
cache_manager.clear()
```

### 缓存装饰器

```python
from apps.core.cache import cached

@cached(timeout=3600, key_prefix='user')
def get_user_data(user_id):
    return User.objects.get(id=user_id)
```

---

## 异常 / Exceptions

### BaseAPIException

基础API异常。

```python
from apps.core.exceptions import BaseAPIException

class MyException(BaseAPIException):
    status_code = 400
    default_detail = 'Something went wrong'
    default_code = 'error'
```

### 使用异常处理装饰器

```python
from apps.core.exceptions import handle_exception

@handle_exception
def my_view(request):
    # 业务逻辑
    pass
```

---

## 最佳实践 / Best Practices

### 1. 模型继承

```python
from apps.core.models import BaseModel

class MyModel(BaseModel):
    """我的模型"""

    class Meta:
        verbose_name = "我的模型"
        verbose_name_plural = "我的模型"
```

### 2. 中间件配置

推荐的中间件顺序：

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    # 自定义中间件
    'apps.core.middleware.SecurityMiddleware',
    'apps.core.middleware.ResponseTimeMiddleware',
    'apps.core.middleware.RequestLogMiddleware',
]
```

### 3. 测试

```python
from django.test import TestCase
from apps.core.models import BaseModel

class MyModelTest(TestCase):
    def test_soft_delete(self):
        obj = MyModel.objects.create(name="Test")
        obj.delete()
        self.assertTrue(obj.is_deleted)
```

---

## 常见问题 / FAQ

### Q: 如何禁用软删除？

A: 使用`hard_delete()`方法：

```python
obj.hard_delete()
```

### Q: 如何查询已删除的记录？

A: 使用`is_deleted=True`：

```python
deleted_objects = MyModel.objects.filter(is_deleted=True)
```

### Q: 如何自定义状态？

A: 继承StatusModel并添加自定义状态：

```python
class MyStatusModel(StatusModel):
    class StatusChoices(models.TextChoices):
        DRAFT = 'draft', _('草稿')
        REVIEW = 'review', _('审核中')
        PUBLISHED = 'published', _('已发布')
```

---

## 相关文档 / Related Docs

- [Django REST Framework封装](../../utils/drf/USAGE_GUIDE.md)
- [安全配置指南](../../../docs/SECURITY.md)
- [部署指南](../../../docs/DEPLOYMENT.md)
