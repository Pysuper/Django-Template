import functools
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

from django.conf import settings
from django.core.cache import cache
from django.db import connection, models, transaction
from django.db.models import Model, QuerySet
from django.db.models.signals import post_delete, post_save
from django.utils.module_loading import import_string

from .cache import CacheManager
from .logging import log_timing

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

class CacheableQuerySet(models.QuerySet):
    """可缓存的查询集"""
    
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.cache_manager = CacheManager(
            prefix=f"queryset:{self.model._meta.label}"
        )
        self.cache_timeout = getattr(settings, "QUERYSET_CACHE_TIMEOUT", 3600)
        
    def cache_key(self, suffix: str = "") -> str:
        """生成缓存键"""
        query_key = self.query.__str__()
        return f"{self.model._meta.label}:{query_key}:{suffix}"
        
    def get_or_create_from_cache(
        self,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> tuple:
        """从缓存获取或创建对象"""
        cache_key = self.cache_key(f"get_or_create:{kwargs}")
        result = self.cache_manager.get(cache_key)
        
        if result is None:
            obj, created = super().get_or_create(defaults=defaults, **kwargs)
            result = (obj, created)
            self.cache_manager.set(cache_key, result, timeout=self.cache_timeout)
            
        return result
        
    def update_or_create_from_cache(
        self,
        defaults: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> tuple:
        """从缓存更新或创建对象"""
        cache_key = self.cache_key(f"update_or_create:{kwargs}")
        result = self.cache_manager.get(cache_key)
        
        if result is None:
            obj, created = super().update_or_create(defaults=defaults, **kwargs)
            result = (obj, created)
            self.cache_manager.set(cache_key, result, timeout=self.cache_timeout)
            
        return result
        
    def bulk_create_from_cache(
        self,
        objs: List[Model],
        batch_size: Optional[int] = None,
        ignore_conflicts: bool = False
    ) -> List[Model]:
        """从缓存批量创建对象"""
        cache_key = self.cache_key("bulk_create")
        result = self.cache_manager.get(cache_key)
        
        if result is None:
            result = super().bulk_create(
                objs,
                batch_size=batch_size,
                ignore_conflicts=ignore_conflicts
            )
            self.cache_manager.set(cache_key, result, timeout=self.cache_timeout)
            
        return result
        
    def bulk_update_from_cache(
        self,
        objs: List[Model],
        fields: List[str],
        batch_size: Optional[int] = None
    ) -> None:
        """从缓存批量更新对象"""
        cache_key = self.cache_key("bulk_update")
        result = self.cache_manager.get(cache_key)
        
        if result is None:
            result = super().bulk_update(
                objs,
                fields,
                batch_size=batch_size
            )
            self.cache_manager.set(cache_key, result, timeout=self.cache_timeout)
            
        return result

class CacheableModel(models.Model):
    """可缓存的模型"""
    
    class Meta:
        abstract = True
        
    objects = CacheableQuerySet.as_manager()
    
    def cache_key(self) -> str:
        """生成缓存键"""
        return f"{self._meta.label}:{self.pk}"
        
    def save(self, *args: Any, **kwargs: Any) -> None:
        """保存对象并清除缓存"""
        super().save(*args, **kwargs)
        self.clear_cache()
        
    def delete(self, *args: Any, **kwargs: Any) -> tuple:
        """删除对象并清除缓存"""
        result = super().delete(*args, **kwargs)
        self.clear_cache()
        return result
        
    def clear_cache(self) -> None:
        """清除缓存"""
        cache_manager = CacheManager(prefix=f"model:{self._meta.label}")
        cache_manager.delete(self.cache_key())
        
    @classmethod
    def from_cache(cls, pk: Any) -> Optional["CacheableModel"]:
        """从缓存获取对象"""
        cache_manager = CacheManager(prefix=f"model:{cls._meta.label}")
        cache_key = f"{cls._meta.label}:{pk}"
        
        obj = cache_manager.get(cache_key)
        if obj is None:
            try:
                obj = cls.objects.get(pk=pk)
                cache_manager.set(cache_key, obj)
            except cls.DoesNotExist:
                return None
                
        return obj

def cache_model(timeout: Optional[int] = None) -> Callable[[Type[Model]], Type[Model]]:
    """模型缓存装饰器"""
    def decorator(cls: Type[Model]) -> Type[Model]:
        # 设置缓存超时
        cls.cache_timeout = timeout or getattr(
            settings, "MODEL_CACHE_TIMEOUT", 3600
        )
        
        # 添加缓存管理器
        cls.cache_manager = CacheManager(prefix=f"model:{cls._meta.label}")
        
        # 保存原始方法
        original_save = cls.save
        original_delete = cls.delete
        
        @functools.wraps(original_save)
        def save(self: Model, *args: Any, **kwargs: Any) -> None:
            """保存并更新缓存"""
            original_save(self, *args, **kwargs)
            cache_key = f"{self._meta.label}:{self.pk}"
            self.cache_manager.set(cache_key, self, timeout=self.cache_timeout)
            
        @functools.wraps(original_delete)
        def delete(self: Model, *args: Any, **kwargs: Any) -> tuple:
            """删除并清除缓存"""
            result = original_delete(self, *args, **kwargs)
            cache_key = f"{self._meta.label}:{self.pk}"
            self.cache_manager.delete(cache_key)
            return result
            
        cls.save = save
        cls.delete = delete
        
        return cls
    return decorator

def cache_method(
    timeout: Optional[int] = None,
    key_prefix: Optional[str] = None
) -> Callable[[T], T]:
    """方法缓存装饰���"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            # 生成缓存键
            cache_key = (
                f"{key_prefix or func.__name__}:"
                f"{self.__class__._meta.label}:{self.pk}:"
                f"{args}:{kwargs}"
            )
            
            # 获取缓存管理器
            cache_manager = CacheManager(
                prefix=f"method:{self.__class__._meta.label}"
            )
            
            # 尝试从缓存获取
            result = cache_manager.get(cache_key)
            
            if result is None:
                result = func(self, *args, **kwargs)
                cache_manager.set(
                    cache_key,
                    result,
                    timeout=timeout or getattr(
                        settings, "METHOD_CACHE_TIMEOUT", 3600
                    )
                )
                
            return result
        return cast(T, wrapper)
    return decorator

def clear_model_cache(sender: Type[Model], **kwargs: Any) -> None:
    """清除模型缓存"""
    instance = kwargs.get("instance")
    if instance:
        cache_manager = CacheManager(prefix=f"model:{sender._meta.label}")
        cache_key = f"{sender._meta.label}:{instance.pk}"
        cache_manager.delete(cache_key)

def setup_model_cache_signals() -> None:
    """设置模型缓存信号"""
    for model in models.get_models():
        post_save.connect(clear_model_cache, sender=model)
        post_delete.connect(clear_model_cache, sender=model)

class DatabaseRouter:
    """数据库路由器"""
    
    def db_for_read(self, model: Type[Model], **hints: Any) -> Optional[str]:
        """读操作路由"""
        return getattr(model, "_read_db", "default")
        
    def db_for_write(self, model: Type[Model], **hints: Any) -> Optional[str]:
        """写操作路由"""
        return getattr(model, "_write_db", "default")
        
    def allow_relation(
        self,
        obj1: Model,
        obj2: Model,
        **hints: Any
    ) -> Optional[bool]:
        """是否允许关联"""
        return True
        
    def allow_migrate(
        self,
        db: str,
        app_label: str,
        model_name: Optional[str] = None,
        **hints: Any
    ) -> Optional[bool]:
        """是否允许迁移"""
        return True

class ReadWriteModel(models.Model):
    """读写分离模型"""
    
    class Meta:
        abstract = True
        
    _read_db = "read"
    _write_db = "write"
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """保存到写库"""
        with transaction.atomic(using=self._write_db):
            super().save(*args, **kwargs)
            
    def delete(self, *args: Any, **kwargs: Any) -> tuple:
        """从写库删除"""
        with transaction.atomic(using=self._write_db):
            return super().delete(*args, **kwargs)

@log_timing()
def optimize_queryset(queryset: QuerySet) -> QuerySet:
    """优化查询集"""
    model = queryset.model
    
    # 获取所有关联字段
    related_fields = []
    for field in model._meta.get_fields():
        if (
            isinstance(field, (models.ForeignKey, models.OneToOneField))
            or (
                isinstance(field, models.ManyToManyField)
                and not field.remote_field.through._meta.auto_created
            )
        ):
            related_fields.append(field.name)
            
    # 添加select_related
    if related_fields:
        queryset = queryset.select_related(*related_fields)
        
    # 添加prefetch_related
    m2m_fields = [
        field.name
        for field in model._meta.get_fields()
        if isinstance(field, models.ManyToManyField)
    ]
    if m2m_fields:
        queryset = queryset.prefetch_related(*m2m_fields)
        
    return queryset

def analyze_queries() -> List[Dict[str, Any]]:
    """分析查询"""
    return [
        {
            "sql": query["sql"],
            "time": query["time"],
            "vendor": connection.vendor,
        }
        for query in connection.queries
    ]

# 使用示例
"""
# 1. 使用可缓存的模型
class Article(CacheableModel):
    title = models.CharField(max_length=100)
    content = models.TextField()
    
    @cache_method(timeout=3600)
    def get_comments(self):
        return self.comments.all()

# 2. 使用模型缓存装饰器
@cache_model(timeout=3600)
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

# 3. 使用读写分离模型
class User(ReadWriteModel):
    username = models.CharField(max_length=100)
    email = models.EmailField()

# 4. 优化查询集
articles = optimize_queryset(Article.objects.all())

# 5. 分析查询
from django.db import connection
from django.db import reset_queries

reset_queries()
# 执行一些查询
queries = analyze_queries()
for query in queries:
    print(f"SQL: {query['sql']}")
    print(f"Time: {query['time']}")

# 6. 在settings.py中配置数据库路由
DATABASE_ROUTERS = ['apps.core.db.DatabaseRouter']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'default_db',
    },
    'read': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'read_db',
    },
    'write': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'write_db',
    }
}

# 7. 设置缓存
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://localhost:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# 8. 设置信号
from django.apps import AppConfig

class CoreConfig(AppConfig):
    name = 'apps.core'
    
    def ready(self):
        setup_model_cache_signals()
""" 