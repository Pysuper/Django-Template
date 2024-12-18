import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.db.models import Model, Q, QuerySet
from django.http import HttpRequest
from rest_framework import permissions
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .cache import CacheManager
from .exceptions import PermissionError
from .logging import log_timing

logger = logging.getLogger(__name__)

User = get_user_model()
T = TypeVar("T", bound=Callable[..., Any])

class BaseObjectPermission(BasePermission):
    """基础对象权限类"""
    
    def has_permission(self, request: Request, view: Any) -> bool:
        """检查是否有权限访问视图"""
        return True
        
    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        """检查是否有权限访问对象"""
        return True

class IsOwner(BaseObjectPermission):
    """对象所有者权限"""
    
    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        """检查是否是对象所有者"""
        # 获取对象的所有者字段
        owner_field = getattr(view, "owner_field", "user")
        
        # 获取对象所有者
        owner = getattr(obj, owner_field, None)
        
        return bool(owner == request.user)

class IsAdmin(BasePermission):
    """管理员权限"""
    
    def has_permission(self, request: Request, view: Any) -> bool:
        """检查是否是管理员"""
        return bool(request.user and request.user.is_staff)

class IsSuperUser(BasePermission):
    """超级管理员权限"""
    
    def has_permission(self, request: Request, view: Any) -> bool:
        """检查是否是超级管理员"""
        return bool(request.user and request.user.is_superuser)

class HasRole(BasePermission):
    """角色权限"""
    
    def __init__(self, role: Union[str, List[str]]):
        self.roles = [role] if isinstance(role, str) else role
        
    def has_permission(self, request: Request, view: Any) -> bool:
        """检查是否有指定角色"""
        if not request.user or not request.user.is_authenticated:
            return False
            
        return bool(
            request.user.groups.filter(name__in=self.roles).exists()
        )

class HasPermission(BasePermission):
    """权限检查"""
    
    def __init__(self, perm: Union[str, List[str]]):
        self.perms = [perm] if isinstance(perm, str) else perm
        
    def has_permission(self, request: Request, view: Any) -> bool:
        """检查是否有指定权限"""
        return bool(
            request.user and request.user.has_perms(self.perms)
        )

class RoleBasedPermission(BasePermission):
    """基于角色的权限"""
    
    def get_required_roles(self, view: Any) -> Set[str]:
        """获取所需角色"""
        return set(getattr(view, "required_roles", []))
        
    def has_permission(self, request: Request, view: Any) -> bool:
        """检查是否有所需角色"""
        required_roles = self.get_required_roles(view)
        
        if not required_roles:
            return True
            
        if not request.user or not request.user.is_authenticated:
            return False
            
        user_roles = set(
            request.user.groups.values_list("name", flat=True)
        )
        
        return bool(required_roles & user_roles)

class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.cache_manager = CacheManager(prefix="permissions")
        
    @log_timing()
    def get_user_permissions(self, user: User) -> Set[str]:
        """获取用户权限"""
        cache_key = f"user_permissions:{user.pk}"
        
        # 尝试从缓存获取
        permissions = self.cache_manager.get(cache_key)
        
        if permissions is None:
            # 获取用户所有权限
            permissions = set(
                user.user_permissions.values_list("codename", flat=True)
            )
            
            # 获取用户组权限
            group_permissions = Permission.objects.filter(
                group__user=user
            ).values_list("codename", flat=True)
            
            permissions.update(group_permissions)
            
            # 缓存权限
            self.cache_manager.set(cache_key, permissions)
            
        return permissions
        
    @log_timing()
    def get_user_roles(self, user: User) -> Set[str]:
        """获取用户角色"""
        cache_key = f"user_roles:{user.pk}"
        
        # 尝试从缓存获取
        roles = self.cache_manager.get(cache_key)
        
        if roles is None:
            # 获取用户所有角色
            roles = set(
                user.groups.values_list("name", flat=True)
            )
            
            # 缓存角色
            self.cache_manager.set(cache_key, roles)
            
        return roles
        
    def clear_user_cache(self, user: User) -> None:
        """清除用户缓存"""
        self.cache_manager.delete(f"user_permissions:{user.pk}")
        self.cache_manager.delete(f"user_roles:{user.pk}")
        
    def assign_role(self, user: User, role: str) -> None:
        """分配角色"""
        group, _ = Group.objects.get_or_create(name=role)
        user.groups.add(group)
        self.clear_user_cache(user)
        
    def remove_role(self, user: User, role: str) -> None:
        """移除角色"""
        try:
            group = Group.objects.get(name=role)
            user.groups.remove(group)
            self.clear_user_cache(user)
        except Group.DoesNotExist:
            pass
            
    def assign_permission(self, user: User, perm: str) -> None:
        """分配权限"""
        app_label, codename = perm.split(".")
        permission = Permission.objects.get(
            content_type__app_label=app_label,
            codename=codename
        )
        user.user_permissions.add(permission)
        self.clear_user_cache(user)
        
    def remove_permission(self, user: User, perm: str) -> None:
        """移除权限"""
        try:
            app_label, codename = perm.split(".")
            permission = Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename
            )
            user.user_permissions.remove(permission)
            self.clear_user_cache(user)
        except Permission.DoesNotExist:
            pass

def permission_required(
    perm: Union[str, List[str]],
    raise_exception: bool = True
) -> Callable[[T], T]:
    """权限要求装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            perms = [perm] if isinstance(perm, str) else perm
            
            if not request.user.has_perms(perms):
                if raise_exception:
                    raise PermissionError(
                        detail=f"Missing required permissions: {', '.join(perms)}"
                    )
                return None
                
            return func(request, *args, **kwargs)
        return cast(T, wrapper)
    return decorator

def role_required(
    role: Union[str, List[str]],
    raise_exception: bool = True
) -> Callable[[T], T]:
    """角色要求装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            roles = [role] if isinstance(role, str) else role
            
            if not request.user.groups.filter(name__in=roles).exists():
                if raise_exception:
                    raise PermissionError(
                        detail=f"Missing required roles: {', '.join(roles)}"
                    )
                return None
                
            return func(request, *args, **kwargs)
        return cast(T, wrapper)
    return decorator

class ObjectPermissionManager:
    """对象权限管理器"""
    
    def __init__(self, model: Type[Model]):
        self.model = model
        self.cache_manager = CacheManager(prefix=f"object_permissions:{model._meta.label}")
        
    def get_objects_for_user(
        self,
        user: User,
        perms: Union[str, List[str]],
        any_perm: bool = False
    ) -> QuerySet:
        """获取用户有权限的对象"""
        if isinstance(perms, str):
            perms = [perms]
            
        # 构建权限过滤条件
        filters = None
        for perm in perms:
            q = Q(**{f"{perm}__user": user})
            if filters is None:
                filters = q
            elif any_perm:
                filters |= q
            else:
                filters &= q
                
        return self.model.objects.filter(filters)
        
    def assign_perm(
        self,
        perm: str,
        user: User,
        obj: Model
    ) -> None:
        """分配对象权限"""
        from guardian.shortcuts import assign_perm
        assign_perm(perm, user, obj)
        self.clear_cache(obj)
        
    def remove_perm(
        self,
        perm: str,
        user: User,
        obj: Model
    ) -> None:
        """移除对象权限"""
        from guardian.shortcuts import remove_perm
        remove_perm(perm, user, obj)
        self.clear_cache(obj)
        
    def clear_cache(self, obj: Model) -> None:
        """清除对象缓存"""
        self.cache_manager.delete(f"perms:{obj.pk}")
        
    def get_perms(self, user: User, obj: Model) -> Set[str]:
        """获取用户对对象的权限"""
        from guardian.shortcuts import get_perms
        return set(get_perms(user, obj))

# 使用示例
"""
# 1. 在视图中使用权限类
from rest_framework.views import APIView

class ExampleView(APIView):
    permission_classes = [IsOwner | IsAdmin]
    
    def get(self, request):
        return Response({"message": "Hello, World!"})

# 2. 使用装饰器
@permission_required("app.view_model")
def my_view(request):
    return JsonResponse({"message": "Hello, World!"})

# 3. 使用角色装饰器
@role_required("admin")
def admin_view(request):
    return JsonResponse({"message": "Admin only!"})

# 4. 使用权限管理器
permission_manager = PermissionManager()
user_permissions = permission_manager.get_user_permissions(user)
user_roles = permission_manager.get_user_roles(user)

# 5. 使用对象权限管理器
class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        permissions = (
            ("view_post", "Can view post"),
            ("edit_post", "Can edit post"),
        )
        
post_permissions = ObjectPermissionManager(Post)
user_posts = post_permissions.get_objects_for_user(
    user,
    ["view_post", "edit_post"]
)

# 6. 在settings.py中配置权限
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "apps.core.permissions.RoleBasedPermission",
    ]
}

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)
""" 