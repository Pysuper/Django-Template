import functools
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, List, Optional, Set, Type, TypeVar, cast

from django.conf import settings
from django.db import (
    DatabaseError,
    IntegrityError,
    connection,
    models,
    transaction,
)
from django.db.models import Model, QuerySet
from django.utils import timezone
from pydantic import BaseModel, Field

from .cache import CacheManager

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])
M = TypeVar("M", bound=Model)

class DatabaseConfig(BaseModel):
    """数据库配置"""
    query_timeout: int = Field(default=30, ge=1, description="查询超时时间（秒）")
    max_query_records: int = Field(default=1000, ge=1, description="最大查询记录数")
    enable_query_cache: bool = Field(default=True, description="是否启用查询缓存")

class QueryMetrics(BaseModel):
    """查询指标"""
    sql: str = Field(..., description="SQL语句")
    time: float = Field(..., ge=0, description="执行时间")
    vendor: str = Field(..., description="数据库类型")
    start_time: datetime = Field(default_factory=timezone.now, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")

@dataclass
class QueryContext:
    """查询上下文"""
    queryset: QuerySet
    model: Type[Model]
    config: DatabaseConfig
    cache_manager: CacheManager

class DatabaseOptimizer:
    """数据库优化器"""

    def __init__(self) -> None:
        self.config = DatabaseConfig(**(getattr(settings, "DATABASE_CONFIG", {})))
        self.cache_manager = CacheManager(prefix="database")

    def optimize_query(self, queryset: QuerySet[M]) -> QuerySet[M]:
        """优化查询"""
        context = QueryContext(
            queryset=queryset,
            model=queryset.model,
            config=self.config,
            cache_manager=self.cache_manager
        )

        queryset = self._add_select_related(context)
        queryset = self._add_prefetch_related(context)
        queryset = self._optimize_fields(context)
        queryset = self._add_index_hints(context)

        return queryset

    def _add_select_related(self, context: QueryContext) -> QuerySet[M]:
        """添加select_related"""
        fields = []

        for field in context.model._meta.fields:
            if field.is_relation and not field.many_to_many:
                fields.append(field.name)

        if fields:
            context.queryset = context.queryset.select_related(*fields)

        return context.queryset

    def _add_prefetch_related(self, context: QueryContext) -> QuerySet[M]:
        """添加prefetch_related"""
        fields = []

        for field in context.model._meta.many_to_many:
            fields.append(field.name)

        for field in context.model._meta.related_objects:
            fields.append(field.get_accessor_name())

        if fields:
            context.queryset = context.queryset.prefetch_related(*fields)

        return context.queryset

    def _optimize_fields(self, context: QueryContext) -> QuerySet[M]:
        """优化字段选择"""
        only_fields = []
        defer_fields = []

        for field in context.model._meta.fields:
            if field.is_relation:
                continue

            if self._is_field_frequently_used(context.model, field.name):
                only_fields.append(field.name)
            else:
                defer_fields.append(field.name)

        if only_fields:
            context.queryset = context.queryset.only(*only_fields)
        elif defer_fields:
            context.queryset = context.queryset.defer(*defer_fields)

        return context.queryset

    def _add_index_hints(self, context: QueryContext) -> QuerySet[M]:
        """添加索引提示"""
        fields = self._get_query_fields(context.queryset)
        indexes = self._get_available_indexes(context.model)
        best_index = self._choose_best_index(indexes, fields)

        if best_index:
            context.queryset = context.queryset.extra(
                hints={connection.alias: f"USE INDEX ({best_index})"}
            )

        return context.queryset

    def _is_field_frequently_used(self, model: Type[Model], field: str) -> bool:
        """检查字段是否经常使用"""
        cache_key = f"field_usage:{model._meta.label}:{field}"
        usage_count = self.cache_manager.get(cache_key, 0)
        return usage_count > 100

    def _get_query_fields(self, queryset: QuerySet) -> Set[str]:
        """获取查询使用的字段"""
        fields = set()

        for where in queryset.query.where.children:
            if hasattr(where, "lhs"):
                fields.add(where.lhs.target.name)

        for order in queryset.query.order_by:
            if order.startswith("-"):
                order = order[1:]
            fields.add(order.split("__")[0])

        return fields

    def _get_available_indexes(self, model: Type[Model]) -> List[str]:
        """获取可用索引"""
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW INDEX FROM {model._meta.db_table}")
            return [row[2] for row in cursor.fetchall()]

    def _choose_best_index(self, indexes: List[str], fields: Set[str]) -> Optional[str]:
        """选择最佳索引"""
        scores = {
            index: sum(1 for field in fields if field in index)
            for index in indexes
        }
        return max(scores.items(), key=lambda x: x[1])[0] if scores else None

class QueryDebugger:
    """查询调试器"""

    def __init__(self) -> None:
        self.queries: List[QueryMetrics] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def __enter__(self) -> "QueryDebugger":
        self.start_time = timezone.now()
        self.queries = []
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.end_time = timezone.now()

        for query in connection.queries:
            self.queries.append(
                QueryMetrics(
                    sql=query["sql"],
                    time=float(query["time"]),
                    vendor=connection.vendor,
                    start_time=self.start_time or timezone.now(),
                    end_time=self.end_time,
                )
            )

        total_time = sum(q.time for q in self.queries)
        logger.info(
            f"执行了{len(self.queries)}个查询，总耗时{total_time:.2f}秒",
            extra={
                "data": {
                    "queries": [q.dict() for q in self.queries],
                    "total_time": total_time,
                    "total_duration": (self.end_time - self.start_time).total_seconds()
                    if self.end_time and self.start_time else 0,
                }
            }
        )

def optimize_query(func: T) -> T:
    """查询优化装饰器"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if isinstance(result, QuerySet):
            optimizer = DatabaseOptimizer()
            result = optimizer.optimize_query(result)
        return result
    return cast(T, wrapper)

def query_debugger(func: T) -> T:
    """查询调试装饰器"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with QueryDebugger():
            return func(*args, **kwargs)
    return cast(T, wrapper)

def transaction_handler(func: T) -> T:
    """事务处理装饰器"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            with transaction.atomic():
                return func(*args, **kwargs)
        except (DatabaseError, IntegrityError) as e:
            logger.error(
                f"事务执行失败: {str(e)}",
                extra={
                    "data": {
                        "function": func.__name__,
                        "args": args,
                        "kwargs": kwargs,
                    }
                },
                exc_info=True
            )
            raise
    return cast(T, wrapper)

class BulkOperationsMixin(models.QuerySet[M]):
    """批量操作混入类"""

    def bulk_create(
        self,
        objs: List[M],
        batch_size: Optional[int] = None,
        ignore_conflicts: bool = False
    ) -> List[M]:
        """批量创建"""
        if not objs:
            return []

        batch_size = batch_size or DatabaseOptimizer().config.max_query_records
        results = []

        for i in range(0, len(objs), batch_size):
            batch = objs[i:i + batch_size]
            results.extend(
                super().bulk_create(
                    batch,
                    batch_size=batch_size,
                    ignore_conflicts=ignore_conflicts
                )
            )

        return results

    def bulk_update(
        self,
        objs: List[M],
        fields: List[str],
        batch_size: Optional[int] = None
    ) -> None:
        """批量更新"""
        if not objs:
            return

        batch_size = batch_size or DatabaseOptimizer().config.max_query_records

        for i in range(0, len(objs), batch_size):
            batch = objs[i:i + batch_size]
            super().bulk_update(batch, fields, batch_size=batch_size)

class CachingQuerySet(models.QuerySet[M]):
    """缓存查询集"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.cache_manager = CacheManager(
            prefix=f"queryset:{self.model._meta.label}"
        )
        self.cache_timeout = getattr(settings, "QUERYSET_CACHE_TIMEOUT", 300)
        self._cache_timeout: Optional[int] = None
        self._cache_prefix: Optional[str] = None

    def cache(
        self,
        timeout: Optional[int] = None,
        prefix: Optional[str] = None
    ) -> "CachingQuerySet[M]":
        """启用缓存"""
        clone = self._clone()
        clone._cache_timeout = timeout or self.cache_timeout
        clone._cache_prefix = prefix
        return clone

    def nocache(self) -> "CachingQuerySet[M]":
        """禁用缓存"""
        clone = self._clone()
        clone._cache_timeout = None
        return clone

    def _clone(self) -> "CachingQuerySet[M]":
        """克隆查询集"""
        clone = super()._clone()
        clone._cache_timeout = getattr(self, "_cache_timeout", None)
        clone._cache_prefix = getattr(self, "_cache_prefix", None)
        return clone

    def _fetch_from_cache(self, cache_key: str) -> Optional[List[M]]:
        """从缓存获取"""
        if not DatabaseOptimizer().config.enable_query_cache:
            return None
        return self.cache_manager.get(cache_key)

    def _store_in_cache(self, cache_key: str, value: List[M]) -> None:
        """存储到缓存"""
        if not DatabaseOptimizer().config.enable_query_cache:
            return
        self.cache_manager.set(
            cache_key,
            value,
            timeout=getattr(self, "_cache_timeout", self.cache_timeout)
        )

    def _get_cache_key(self) -> str:
        """获取缓存键"""
        query_key = self.query.__str__()
        prefix = getattr(self, "_cache_prefix", "")
        return f"{prefix}:{query_key}" if prefix else query_key

    def iterator(self, chunk_size: Optional[int] = None) -> Any:
        """迭代查询结果"""
        if getattr(self, "_cache_timeout", None) is None:
            return super().iterator(chunk_size=chunk_size)

        cache_key = self._get_cache_key()
        results = self._fetch_from_cache(cache_key)

        if results is None:
            results = list(super().iterator(chunk_size=chunk_size))
            self._store_in_cache(cache_key, results)

        return iter(results)

# 使用示例
"""
# 1. 在settings.py中配置数据库选项
DATABASE_CONFIG = {
    "QUERY_TIMEOUT": 30,
    "MAX_QUERY_RECORDS": 1000,
    "ENABLE_QUERY_CACHE": True,
}

# 2. 使用查询优化装饰器
@optimize_query
def get_users():
    return User.objects.all()

# 3. 使用查询调试装饰器
@query_debugger
def complex_query():
    users = User.objects.select_related("profile").all()
    for user in users:
        print(user.profile.bio)

# 4. 使用事务处理装饰器
@transaction_handler
def transfer_money(from_account, to_account, amount):
    from_account.balance -= amount
    from_account.save()
    to_account.balance += amount
    to_account.save()

# 5. 使用批量操作混入类
class CustomQuerySet(BulkOperationsMixin, models.QuerySet):
    pass

class CustomManager(models.Manager):
    def get_queryset(self):
        return CustomQuerySet(self.model, using=self._db)

class Article(models.Model):
    objects = CustomManager()

# 6. 使用缓存查询集
class CachingManager(models.Manager):
    def get_queryset(self):
        return CachingQuerySet(self.model, using=self._db)

class User(models.Model):
    objects = CachingManager()

# 7. 使用查询优化器
def get_optimized_queryset():
    queryset = Article.objects.all()
    optimizer = DatabaseOptimizer()
    return optimizer.optimize_query(queryset)

# 8. 使用查询调试器
def analyze_queries():
    with QueryDebugger() as debugger:
        User.objects.all()
        Article.objects.all()
    return debugger.queries
"""
