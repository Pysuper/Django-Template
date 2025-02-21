# -*- coding: utf-8 -*-
from typing import Any, Optional, Type, Union

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.migrations.state import ModelState
from django.utils.module_loading import import_string

# 从settings中获取数据库配置
DATABASE_MAPPING = getattr(settings, "DATABASE_APPS_MAPPING", {})
DATABASE_REPLICATION = getattr(settings, "DATABASE_REPLICATION", {})
DATABASE_CACHE_TTL = getattr(settings, "DATABASE_CACHE_TTL", 300)  # 缓存5分钟


class BaseDBRouter:
    """基础数据库路由器"""

    def __init__(self):
        self.cache_enabled = getattr(settings, "DATABASE_ROUTER_CACHE", True)
        self.cache_prefix = "db_router"
        self.cache_ttl = DATABASE_CACHE_TTL

    def _get_cache_key(self, prefix: str, *args) -> str:
        """获取缓存键"""
        return f"{self.cache_prefix}:{prefix}:{'_'.join(str(arg) for arg in args)}"

    def _get_from_cache(self, key: str) -> Optional[Any]:
        """从缓存获取"""
        if not self.cache_enabled:
            return None
        return cache.get(key)

    def _set_to_cache(self, key: str, value: Any) -> None:
        """设置缓存"""
        if not self.cache_enabled:
            return
        cache.set(key, value, self.cache_ttl)

    def _get_app_label(self, model: Union[Type[models.Model], ModelState]) -> str:
        """获取应用标签"""
        if isinstance(model, ModelState):
            return model.app_label
        return model._meta.app_label

    def _get_model_name(self, model: Union[Type[models.Model], ModelState]) -> str:
        """获取模型名称"""
        if isinstance(model, ModelState):
            return model.name
        return model._meta.model_name


class ReplicationRouter(BaseDBRouter):
    """读写分离路由器"""

    def db_for_read(self, model: Type[models.Model], **hints) -> Optional[str]:
        """处理读操作路由"""
        # 检查是否强制主库读取
        if hints.get("force_master"):
            return self.db_for_write(model)

        # 获取应用标签
        app_label = self._get_app_label(model)

        # 检查是否配置了从库
        if app_label in DATABASE_REPLICATION:
            replicas = DATABASE_REPLICATION[app_label].get("replicas", [])
            if replicas:
                from random import choice

                return choice(replicas)

        # 返回主库
        return self.db_for_write(model)

    def db_for_write(self, model: Type[models.Model], **hints) -> Optional[str]:
        """处理写操作路由"""
        app_label = self._get_app_label(model)
        if app_label in DATABASE_REPLICATION:
            return DATABASE_REPLICATION[app_label].get("master")
        return None


class MappingRouter(BaseDBRouter):
    """应用映射路由器"""

    def db_for_read(self, model: Type[models.Model], **hints) -> Optional[str]:
        """处理读操作路由"""
        app_label = self._get_app_label(model)
        cache_key = self._get_cache_key("read", app_label)

        # 尝试从缓存获取
        db = self._get_from_cache(cache_key)
        if db is not None:
            return db

        # 从配置获取
        db = DATABASE_MAPPING.get(app_label)
        if db:
            self._set_to_cache(cache_key, db)

        return db

    def db_for_write(self, model: Type[models.Model], **hints) -> Optional[str]:
        """处理写操作路由"""
        app_label = self._get_app_label(model)
        cache_key = self._get_cache_key("write", app_label)

        # 尝试从缓存获取
        db = self._get_from_cache(cache_key)
        if db is not None:
            return db

        # 从配置获取
        db = DATABASE_MAPPING.get(app_label)
        if db:
            self._set_to_cache(cache_key, db)

        return db

    def allow_relation(self, obj1: models.Model, obj2: models.Model, **hints) -> Optional[bool]:
        """判断是否允许关系"""
        # 获取两个对象的数据库
        db1 = DATABASE_MAPPING.get(self._get_app_label(obj1.__class__))
        db2 = DATABASE_MAPPING.get(self._get_app_label(obj2.__class__))

        if db1 and db2:
            return db1 == db2
        return None

    def allow_migrate(self, db: str, app_label: str, model_name: Optional[str] = None, **hints) -> Optional[bool]:
        """控制迁移操作"""
        # 处理特定模型的迁移
        if "model" in hints:
            model = hints["model"]
            if isinstance(model, (models.Model, ModelState)):
                app_label = self._get_app_label(model)

        # 检查是否允许迁移
        if db in DATABASE_MAPPING.values():
            return DATABASE_MAPPING.get(app_label) == db
        elif app_label in DATABASE_MAPPING:
            return False

        return None


class ShardingRouter(BaseDBRouter):
    """分片路由器"""

    def __init__(self):
        super().__init__()
        self.sharding_config = getattr(settings, "DATABASE_SHARDING", {})
        self.shard_key_func = self._get_shard_key_func()

    def _get_shard_key_func(self) -> callable:
        """获取分片键函数"""
        func_path = getattr(settings, "DATABASE_SHARD_KEY_FUNC", None)
        if func_path:
            return import_string(func_path)

        # 默认分片函数
        return lambda key: hash(str(key)) % len(self.sharding_config)

    def _get_shard_for_key(self, key: Any) -> Optional[str]:
        """获取分片数据库"""
        if not self.sharding_config:
            return None

        shard_index = self.shard_key_func(key)
        return self.sharding_config.get(shard_index)

    def db_for_read(self, model: Type[models.Model], **hints) -> Optional[str]:
        """处理读操作路由"""
        # 检查是否提供了分片键
        shard_key = hints.get("shard_key")
        if shard_key is not None:
            return self._get_shard_for_key(shard_key)
        return None

    def db_for_write(self, model: Type[models.Model], **hints) -> Optional[str]:
        """处理写操作路由"""
        # 检查是否提供了分片键
        shard_key = hints.get("shard_key")
        if shard_key is not None:
            return self._get_shard_for_key(shard_key)
        return None

    def allow_relation(self, obj1: models.Model, obj2: models.Model, **hints) -> Optional[bool]:
        """判断是否允许关系"""
        # 分片数据库之间不允许关系
        return False

    def allow_migrate(self, db: str, app_label: str, model_name: Optional[str] = None, **hints) -> Optional[bool]:
        """控制迁移操作"""
        # 允许所有分片数据库进行迁移
        return db in self.sharding_config.values()


class DatabaseRouter(BaseDBRouter):
    """数据库路由器"""

    def __init__(self):
        super().__init__()
        self.routers = [ReplicationRouter(), MappingRouter(), ShardingRouter()]

    def _route_to_database(self, method_name: str, *args, **hints) -> Optional[str]:
        """路由到数据库"""
        for router in self.routers:
            if hasattr(router, method_name):
                result = getattr(router, method_name)(*args, **hints)
                if result is not None:
                    return result
        return None

    def db_for_read(self, model: Type[models.Model], **hints) -> Optional[str]:
        """处理读操作路由"""
        return self._route_to_database("db_for_read", model, **hints)

    def db_for_write(self, model: Type[models.Model], **hints) -> Optional[str]:
        """处理写操作路由"""
        return self._route_to_database("db_for_write", model, **hints)

    def allow_relation(self, obj1: models.Model, obj2: models.Model, **hints) -> Optional[bool]:
        """判断是否允许关系"""
        return self._route_to_database("allow_relation", obj1, obj2, **hints)

    def allow_migrate(self, db: str, app_label: str, model_name: Optional[str] = None, **hints) -> Optional[bool]:
        """控制迁移操作"""
        return self._route_to_database("allow_migrate", db, app_label, model_name, **hints)


"""
使用示例：

# 在settings.py中配置

# 应用数据库映射
DATABASE_APPS_MAPPING = {
    'auth': 'auth_db',
    'users': 'users_db',
    'orders': 'orders_db'
}

# 读写分离配置
DATABASE_REPLICATION = {
    'users': {
        'master': 'users_master',
        'replicas': ['users_slave1', 'users_slave2']
    },
    'orders': {
        'master': 'orders_master',
        'replicas': ['orders_slave1', 'orders_slave2']
    }
}

# 分片配置
DATABASE_SHARDING = {
    0: 'shard1',
    1: 'shard2',
    2: 'shard3'
}

# 分片键函数
def get_shard_key(key):
    return hash(str(key)) % 3

DATABASE_SHARD_KEY_FUNC = 'path.to.get_shard_key'

# 在模型中使用
class User(models.Model):
    class Meta:
        app_label = 'users'

# 在视图中使用
User.objects.using('users_slave1').filter(...)  # 强制使用从库
User.objects.filter(...).hints(force_master=True)  # 强制使用主库
User.objects.filter(...).hints(shard_key='user123')  # 使用分片
"""
