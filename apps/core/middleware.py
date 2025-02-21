import json
import time
from typing import Any, Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.core.utils import get_client_ip


class ResponseTimeMiddleware:
    """
    响应时间中间件
    添加X-Response-Time头，记录请求处理时间
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start_time = time.time()
        response = self.get_response(request)
        response_time = time.time() - start_time
        response['X-Response-Time'] = str(int(response_time * 1000))
        return response


class RequestLogMiddleware:
    """
    请求日志中间件
    记录请求的详细信息
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 记录请求开始时间
        request.start_time = time.time()

        # 获取请求信息
        request_data = {
            'path': request.path,
            'method': request.method,
            'ip': get_client_ip(request),
            'user': str(request.user),
            'data': self._get_request_data(request),
        }

        response = self.get_response(request)

        # 记录响应信息
        response_data = {
            'status': response.status_code,
            'time': time.time() - request.start_time,
            'data': self._get_response_data(response),
        }

        # 在这里可以添加日志记录逻辑
        if hasattr(settings, 'REQUEST_LOGGING') and settings.REQUEST_LOGGING:
            print(json.dumps({**request_data, 'response': response_data}, indent=2))

        return response

    def _get_request_data(self, request: HttpRequest) -> dict:
        """获取请求数据"""
        data = {}
        
        # GET参数
        if request.GET:
            data['GET'] = dict(request.GET)
            
        # POST参数
        if request.POST:
            data['POST'] = dict(request.POST)
            
        # Body数据
        if request.body:
            try:
                body_data = json.loads(request.body)
                data['body'] = body_data
            except json.JSONDecodeError:
                data['body'] = request.body.decode('utf-8', errors='ignore')
                
        return data

    def _get_response_data(self, response: HttpResponse) -> Any:
        """获取响应数据"""
        if isinstance(response, JsonResponse):
            return json.loads(response.content.decode('utf-8'))
        return None


class SecurityMiddleware(MiddlewareMixin):
    """
    安全中间件
    添加安全相关的响应头
    """

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        # 添加安全响应头
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # 如果是HTTPS请求，添加HSTS头
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            
        return response 