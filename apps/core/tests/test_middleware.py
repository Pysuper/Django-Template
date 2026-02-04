"""
Middleware Tests / 中间件测试

测试apps/core中的所有中间件
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponse
import json

from apps.core.middleware.performance import (
    ResponseTimeMiddleware,
    RequestLogMiddleware,
)
from apps.core.middleware.security import SecurityMiddleware

User = get_user_model()


class ResponseTimeMiddlewareTest(TestCase):
    """响应时间中间件测试"""

    def setUp(self):
        """设置测试"""
        self.factory = RequestFactory()
        self.get_response = lambda request: HttpResponse()

    def test_adds_response_time_header(self):
        """测试添加响应时间头"""
        middleware = ResponseTimeMiddleware(self.get_response)
        request = self.factory.get('/')
        response = middleware(request)

        self.assertIn('X-Response-Time', response)
        self.assertIsInstance(response['X-Response-Time'], str)

    def test_response_time_format(self):
        """测试响应时间格式"""
        middleware = ResponseTimeMiddleware(self.get_response)
        request = self.factory.get('/')
        response = middleware(request)

        # 响应时间应该是毫秒数
        response_time = int(response['X-Response-Time'])
        self.assertGreaterEqual(response_time, 0)
        self.assertLess(response_time, 10000)  # 应该小于10秒


class RequestLogMiddlewareTest(TestCase):
    """请求日志中间件测试"""

    def setUp(self):
        """设置测试"""
        self.factory = RequestFactory()
        self.get_response = lambda request: HttpResponse()

    def test_adds_start_time(self):
        """测试添加开始时间"""
        middleware = RequestLogMiddleware(self.get_response)
        request = self.factory.get('/')
        response = middleware(request)

        self.assertTrue(hasattr(request, 'start_time'))

    def test_logs_anonymous_user(self):
        """测试匿名用户日志"""
        middleware = RequestLogMiddleware(self.get_response)
        request = self.factory.get('/')
        response = middleware(request)

        # 中间件应该正常处理匿名用户
        self.assertEqual(response.status_code, 200)


class SecurityMiddlewareTest(TestCase):
    """安全中间件测试"""

    def setUp(self):
        """设置测试"""
        self.factory = RequestFactory()
        self.get_response = lambda request: HttpResponse()

    def test_adds_security_headers(self):
        """测试添加安全头"""
        middleware = SecurityMiddleware(self.get_response)
        request = self.factory.get('/')
        response = middleware(request)

        # 检查安全头
        self.assertIn('X-Frame-Options', response)
        self.assertIn('X-Content-Type-Options', response)
        self.assertIn('X-XSS-Protection', response)
        self.assertIn('Referrer-Policy', response)
        self.assertIn('Content-Security-Policy', response)

    def test_security_header_values(self):
        """测试安全头值"""
        middleware = SecurityMiddleware(self.get_response)
        request = self.factory.get('/')
        response = middleware(request)

        self.assertEqual(response['X-Frame-Options'], 'DENY')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_adds_hsts_for_https(self):
        """测试HTTPS请求添加HSTS头"""
        middleware = SecurityMiddleware(self.get_response)
        request = self.factory.get('/', secure=True)
        response = middleware(request)

        self.assertIn('Strict-Transport-Security', response)
