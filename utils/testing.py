from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast
from pydantic import BaseModel, Field, validator
import functools
import json
import logging
import time
from datetime import datetime, timedelta
import threading
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import connection, reset_queries
from django.http import HttpRequest, HttpResponse
from django.test import (
    Client,
    LiveServerTestCase,
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
)
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from factory import Factory, Faker, LazyAttribute, SubFactory
from factory.django import DjangoModelFactory
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .cache import CacheManager
from .logging import log_timing

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])
M = TypeVar("M", bound=DjangoModelFactory)

class TestConfig(BaseModel):
    """测试配置"""
    max_response_time: float = Field(default=1.0, ge=0, description="最大响应时间")
    max_queries: int = Field(default=50, ge=0, description="最大查询数")
    concurrent_users: int = Field(default=10, ge=1, description="并发用户数")
    test_timeout: int = Field(default=30, ge=1, description="测试超时时间")

class TestMetrics(BaseModel):
    """测试指标"""
    name: str = Field(..., description="测试名称")
    start_time: datetime = Field(default_factory=timezone.now, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: float = Field(default=0.0, ge=0, description="持续时间")
    success: bool = Field(default=True, description="是否成功")
    error: Optional[str] = Field(None, description="错误信息")

@dataclass
class TestContext:
    """测试上下文"""
    client: APIClient
    config: TestConfig
    cache_manager: CacheManager
    metrics: List[TestMetrics]

class BaseTestCase(TestCase):
    """基础测试用例"""
    
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()
        self.cache_manager = CacheManager()
        self.config = TestConfig(**(getattr(settings, "TEST_CONFIG", {})))
        self.metrics: List[TestMetrics] = []
        
    def tearDown(self) -> None:
        self.cache_manager.clear()
        super().tearDown()
        
    def assertResponseSuccess(self, response: HttpResponse) -> None:
        """断言响应成功"""
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED]
        )
        
    def assertResponseError(self, response: HttpResponse) -> None:
        """断言响应错误"""
        self.assertGreaterEqual(response.status_code, 400)
        
    def assertQueryCount(self, count: int) -> CaptureQueriesContext:
        """断言查询数量"""
        return self.assertNumQueries(count)
        
    def assertCached(self, key: str) -> None:
        """断言已缓存"""
        self.assertIsNotNone(self.cache_manager.get(key))
        
    def assertNotCached(self, key: str) -> None:
        """断言未缓存"""
        self.assertIsNone(self.cache_manager.get(key))
        
    def login_user(self, user: Any) -> None:
        """登录用户"""
        self.client.force_authenticate(user=user)

class BaseAPITestCase(APITestCase):
    """基础API测试用例"""
    
    def setUp(self) -> None:
        super().setUp()
        self.client = APIClient()
        self.config = TestConfig(**(getattr(settings, "TEST_CONFIG", {})))
        self.metrics: List[TestMetrics] = []
        
    def get_response_data(self, response: HttpResponse) -> Dict[str, Any]:
        """获取响应数据"""
        return json.loads(response.content.decode())
        
    def assertResponseHasKey(
        self,
        response: HttpResponse,
        key: str
    ) -> None:
        """断言响应包含键"""
        data = self.get_response_data(response)
        self.assertIn(key, data)
        
    def assertResponseValue(
        self,
        response: HttpResponse,
        key: str,
        value: Any
    ) -> None:
        """断言响应值"""
        data = self.get_response_data(response)
        self.assertEqual(data[key], value)
        
    def assertResponseList(
        self,
        response: HttpResponse,
        length: Optional[int] = None
    ) -> None:
        """断言响应列表"""
        data = self.get_response_data(response)
        self.assertIsInstance(data, list)
        if length is not None:
            self.assertEqual(len(data), length)
            
    def assertResponsePaginated(
        self,
        response: HttpResponse,
        page_size: Optional[int] = None
    ) -> None:
        """断言响应分页"""
        data = self.get_response_data(response)
        self.assertIn("count", data)
        self.assertIn("results", data)
        if page_size is not None:
            self.assertLessEqual(len(data["results"]), page_size)

class BasePerformanceTestCase(LiveServerTestCase):
    """基础性能测试用例"""
    
    def setUp(self) -> None:
        super().setUp()
        self.client = Client()
        self.config = TestConfig(**(getattr(settings, "TEST_CONFIG", {})))
        self.metrics: List[TestMetrics] = []
        
    def time_request(
        self,
        url: str,
        method: str = "get",
        **kwargs: Any
    ) -> float:
        """计时请求"""
        start_time = timezone.now()
        
        request_method = getattr(self.client, method.lower())
        request_method(url, **kwargs)
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.metrics.append(
            TestMetrics(
                name=f"{method.upper()} {url}",
                start_time=start_time,
                end_time=end_time,
                duration=duration
            )
        )
        
        return duration
        
    def assertResponseTime(
        self,
        url: str,
        max_time: float,
        method: str = "get",
        **kwargs: Any
    ) -> None:
        """断言响应时间"""
        response_time = self.time_request(url, method, **kwargs)
        self.assertLess(
            response_time,
            max_time,
            f"Response time {response_time:.2f}s exceeds maximum {max_time:.2f}s"
        )
        
    def assertAverageResponseTime(
        self,
        url: str,
        max_time: float,
        requests: int = 100,
        method: str = "get",
        **kwargs: Any
    ) -> None:
        """断言平均响应时间"""
        total_time = 0
        for _ in range(requests):
            total_time += self.time_request(url, method, **kwargs)
            
        average_time = total_time / requests
        self.assertLess(
            average_time,
            max_time,
            f"Average response time {average_time:.2f}s exceeds maximum {max_time:.2f}s"
        )
        
    def assertConcurrentUsers(
        self,
        url: str,
        users: int,
        max_time: float,
        method: str = "get",
        **kwargs: Any
    ) -> None:
        """断言并发用户"""
        def make_request() -> None:
            self.time_request(url, method, **kwargs)
            
        threads = []
        start_time = timezone.now()
        
        for _ in range(users):
            thread = threading.Thread(target=make_request)
            thread.start()
            threads.append(thread)
            
        for thread in threads:
            thread.join()
            
        end_time = timezone.now()
        total_time = (end_time - start_time).total_seconds()
        
        self.assertLess(
            total_time,
            max_time,
            f"Concurrent response time {total_time:.2f}s exceeds maximum {max_time:.2f}s"
        )

class BaseFactory(DjangoModelFactory):
    """基础工厂类"""
    
    class Meta:
        abstract = True
        
    @classmethod
    def _create(cls, model_class: Type[Any], *args: Any, **kwargs: Any) -> Any:
        """创建模型实例"""
        instance = super()._create(model_class, *args, **kwargs)
        
        if not hasattr(cls, "_instances"):
            cls._instances = []
        cls._instances.append(instance)
        
        return instance
        
    @classmethod
    def create_batch(cls, size: int, **kwargs: Any) -> List[Any]:
        """批量创建实例"""
        return [cls.create(**kwargs) for _ in range(size)]
        
    @classmethod
    def cleanup(cls) -> None:
        """清理实例"""
        if hasattr(cls, "_instances"):
            for instance in cls._instances:
                instance.delete()
            cls._instances = []

def mock_function(func: T) -> T:
    """模拟函数装饰器"""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with patch(f"{func.__module__}.{func.__name__}") as mock:
            mock.return_value = MagicMock()
            return func(*args, **kwargs)
    return cast(T, wrapper)

def mock_class(cls: Type[Any]) -> Type[Any]:
    """模拟类装饰器"""
    return patch(f"{cls.__module__}.{cls.__name__}", autospec=True).start()

def performance_test(
    max_time: float,
    requests: int = 1,
    concurrent: bool = False
) -> Callable[[T], T]:
    """性能测试装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if concurrent:
                threads = []
                start_time = timezone.now()
                
                for _ in range(requests):
                    thread = threading.Thread(
                        target=func,
                        args=args,
                        kwargs=kwargs
                    )
                    thread.start()
                    threads.append(thread)
                    
                for thread in threads:
                    thread.join()
                    
                end_time = timezone.now()
                total_time = (end_time - start_time).total_seconds()
                
                assert total_time < max_time, (
                    f"Total time {total_time:.2f}s exceeds maximum {max_time:.2f}s"
                )
            else:
                total_time = 0
                for _ in range(requests):
                    start_time = timezone.now()
                    result = func(*args, **kwargs)
                    end_time = timezone.now()
                    total_time += (end_time - start_time).total_seconds()
                    
                average_time = total_time / requests
                assert average_time < max_time, (
                    f"Average time {average_time:.2f}s exceeds maximum {max_time:.2f}s"
                )
                
                return result
        return cast(T, wrapper)
    return decorator

def query_count_test(max_queries: int) -> Callable[[T], T]:
    """查询数量测试装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with CaptureQueriesContext(connection) as context:
                result = func(*args, **kwargs)
                query_count = len(context.captured_queries)
                assert query_count <= max_queries, (
                    f"Query count {query_count} exceeds maximum {max_queries}"
                )
                return result
        return cast(T, wrapper)
    return decorator

def cache_test(key: str) -> Callable[[T], T]:
    """缓存测试装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_manager = CacheManager()
            cache_manager.delete(key)
            
            result1 = func(*args, **kwargs)
            assert cache_manager.get(key) is not None, "Result not cached"
            
            result2 = func(*args, **kwargs)
            assert result1 == result2, "Cached results do not match"
            
            return result2
        return cast(T, wrapper)
    return decorator 