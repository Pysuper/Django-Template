# -*- coding: utf-8 -*-
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from django.conf import settings
from django.http import HttpRequest
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.schemas.openapi import SchemaGenerator
from rest_framework.views import APIView

from .cache import CacheManager

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

@dataclass
class APIEndpoint:
    """API端点数据类"""
    path: str
    method: str
    name: str
    description: str
    parameters: List[Dict[str, Any]]
    request_body: Optional[Dict[str, Any]]
    responses: Dict[str, Dict[str, Any]]
    tags: List[str]
    deprecated: bool = False

class APIDocumentationGenerator:
    """API文档生成器"""

    def __init__(self):
        # 加载配置
        self.config = getattr(settings, "API_DOCS_CONFIG", {})

        # 文档标题
        self.title = self.config.get("TITLE", "API Documentation")

        # 文档描述
        self.description = self.config.get("DESCRIPTION", "")

        # API版本
        self.version = self.config.get("VERSION", "1.0.0")

        # 缓存管理器
        self.cache_manager = CacheManager(prefix="api_docs")

        # 模式生成器
        self.schema_generator = SchemaGenerator(
            title=self.title,
            description=self.description,
            version=self.version,
        )

    def get_api_endpoints(self) -> List[APIEndpoint]:
        """获取API端点"""
        cache_key = "endpoints"
        endpoints = self.cache_manager.get(cache_key)

        if endpoints is None:
            endpoints = []
            patterns = get_resolver().url_patterns

            for pattern in patterns:
                endpoints.extend(self._get_pattern_endpoints(pattern))

            self.cache_manager.set(cache_key, endpoints)

        return endpoints

    def _get_pattern_endpoints(
        self,
        pattern: Union[URLPattern, URLResolver],
        prefix: str = ""
    ) -> List[APIEndpoint]:
        """获取URL模式的端点"""
        endpoints = []

        if isinstance(pattern, URLResolver):
            for sub_pattern in pattern.url_patterns:
                endpoints.extend(
                    self._get_pattern_endpoints(
                        sub_pattern,
                        prefix + pattern.pattern.regex.pattern
                    )
                )
        elif isinstance(pattern, URLPattern):
            if hasattr(pattern.callback, "cls"):
                view = pattern.callback.cls
                if issubclass(view, APIView):
                    endpoints.extend(
                        self._get_view_endpoints(
                            view,
                            prefix + pattern.pattern.regex.pattern
                        )
                    )

        return endpoints

    def _get_view_endpoints(
        self,
        view: Type[APIView],
        path: str
    ) -> List[APIEndpoint]:
        """获取视图的端点"""
        endpoints = []

        # 获取视图方法
        for method in view.http_method_names:
            if method == "options":
                continue

            handler = getattr(view, method, None)
            if handler:
                endpoint = self._create_endpoint(view, method, path, handler)
                endpoints.append(endpoint)

        return endpoints

    def _create_endpoint(
        self,
        view: Type[APIView],
        method: str,
        path: str,
        handler: Callable
    ) -> APIEndpoint:
        """创建端点"""
        # 获取文档字符串
        docstring = inspect.getdoc(handler) or ""

        # 获取视图名称
        name = getattr(view, "name", view.__name__)

        # 获取参数
        parameters = self._get_parameters(view, handler)

        # 获取请求体
        request_body = self._get_request_body(view)

        # 获取响应
        responses = self._get_responses(view, handler)

        # 获取标签
        tags = getattr(view, "tags", [view.__module__.split(".")[-2]])

        # 获取废弃状态
        deprecated = getattr(handler, "deprecated", False)

        return APIEndpoint(
            path=path,
            method=method.upper(),
            name=name,
            description=docstring,
            parameters=parameters,
            request_body=request_body,
            responses=responses,
            tags=tags,
            deprecated=deprecated,
        )

    def _get_parameters(
        self,
        view: Type[APIView],
        handler: Callable
    ) -> List[Dict[str, Any]]:
        """获取参数"""
        parameters = []

        # 获取路径参数
        if hasattr(view, "lookup_field"):
            parameters.append({
                "name": view.lookup_field,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            })

        # 获取查询参数
        if hasattr(view, "filter_fields"):
            for field in view.filter_fields:
                parameters.append({
                    "name": field,
                    "in": "query",
                    "required": False,
                    "schema": {"type": "string"},
                })

        # 获取分页参数
        if hasattr(view, "pagination_class"):
            parameters.extend([
                {
                    "name": "page",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer"},
                },
                {
                    "name": "page_size",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer"},
                },
            ])

        return parameters

    def _get_request_body(self, view: Type[APIView]) -> Optional[Dict[str, Any]]:
        """获取请求体"""
        if hasattr(view, "serializer_class"):
            serializer = view.serializer_class()
            return {
                "content": {
                    "application/json": {
                        "schema": self._get_serializer_schema(serializer)
                    }
                }
            }
        return None

    def _get_responses(
        self,
        view: Type[APIView],
        handler: Callable
    ) -> Dict[str, Dict[str, Any]]:
        """获取响应"""
        responses = {
            "200": {
                "description": "Successful response",
            }
        }

        # 获取序列化器响应
        if hasattr(view, "serializer_class"):
            serializer = view.serializer_class()
            responses["200"]["content"] = {
                "application/json": {
                    "schema": self._get_serializer_schema(serializer)
                }
            }

        # 获取错误响应
        responses.update({
            "400": {"description": "Bad request"},
            "401": {"description": "Unauthorized"},
            "403": {"description": "Forbidden"},
            "404": {"description": "Not found"},
            "500": {"description": "Internal server error"},
        })

        return responses

    def _get_serializer_schema(
        self,
        serializer: serializers.Serializer
    ) -> Dict[str, Any]:
        """获取序列化器模式"""
        schema = {
            "type": "object",
            "properties": {},
            "required": [],
        }

        for field_name, field in serializer.fields.items():
            field_schema = self._get_field_schema(field)
            schema["properties"][field_name] = field_schema

            if field.required:
                schema["required"].append(field_name)

        return schema

    def _get_field_schema(self, field: serializers.Field) -> Dict[str, Any]:
        """获取字段模式"""
        schema = {}

        if isinstance(field, serializers.IntegerField):
            schema["type"] = "integer"
        elif isinstance(field, serializers.FloatField):
            schema["type"] = "number"
        elif isinstance(field, serializers.BooleanField):
            schema["type"] = "boolean"
        elif isinstance(field, serializers.ListField):
            schema["type"] = "array"
            schema["items"] = self._get_field_schema(field.child)
        elif isinstance(field, serializers.DictField):
            schema["type"] = "object"
        elif isinstance(field, serializers.Serializer):
            schema = self._get_serializer_schema(field)
        else:
            schema["type"] = "string"

        if field.help_text:
            schema["description"] = str(field.help_text)

        return schema

    def generate_openapi_schema(self) -> Dict[str, Any]:
        """生成OpenAPI模式"""
        cache_key = "openapi_schema"
        schema = self.cache_manager.get(cache_key)

        if schema is None:
            schema = self.schema_generator.get_schema()
            self.cache_manager.set(cache_key, schema)

        return schema

    def generate_swagger_ui(self) -> str:
        """生成Swagger UI"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3/swagger-ui.css">
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
            <script>
                const ui = SwaggerUIBundle({{
                    url: "{settings.API_SCHEMA_URL}",
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    deepLinking: true
                }})
            </script>
        </body>
        </html>
        """

def api_docs(
    title: Optional[str] = None,
    description: Optional[str] = None,
    version: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Callable[[T], T]:
    """API文档装饰器"""
    def decorator(cls: T) -> T:
        if title:
            cls.title = title
        if description:
            cls.description = description
        if version:
            cls.version = version
        if tags:
            cls.tags = tags
        return cls
    return decorator

def api_deprecated(func: T) -> T:
    """API废弃装饰器"""
    func.deprecated = True
    return func

def api_response(
    status_code: int = status.HTTP_200_OK,
    description: str = "",
    schema: Optional[Type[serializers.Serializer]] = None,
) -> Callable[[T], T]:
    """API响应装饰器"""
    def decorator(func: T) -> T:
        if not hasattr(func, "_responses"):
            func._responses = {}
        func._responses[status_code] = {
            "description": description,
            "schema": schema,
        }
        return func
    return decorator

def swagger_view(request: HttpRequest) -> Response:
    """Swagger视图"""
    generator = APIDocumentationGenerator()
    return Response(generator.generate_swagger_ui())

def openapi_schema_view(request: HttpRequest) -> Response:
    """OpenAPI模式视图"""
    generator = APIDocumentationGenerator()
    return Response(generator.generate_openapi_schema())

# 使用示例
"""
# 1. 在settings.py中配置API文档
API_DOCS_CONFIG = {
    "TITLE": "My API",
    "DESCRIPTION": "My API description",
    "VERSION": "1.0.0",
}

API_SCHEMA_URL = "/api/docs/schema/"

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.openapi.AutoSchema',
}

# 2. 在urls.py中添加文档路由
urlpatterns = [
    path('docs/', swagger_view, name='swagger-ui'),
    path('docs/schema/', openapi_schema_view, name='openapi-schema'),
]

# 3. 在视图中使用装饰器
@api_docs(
    title="User API",
    description="User management API",
    tags=["users"]
)
class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()

    @api_deprecated
    def list(self, request):
        # 已废弃的列表接口
        pass

    @api_response(
        status_code=status.HTTP_201_CREATED,
        description="User created successfully",
        schema=UserSerializer
    )
    def create(self, request):
        # 创建用户接口
        pass

# 4. 使用序列化器
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email')

    def validate_email(self, value):
        # 自定义验证
        return value

    @swagger_serializer_method(serializer_or_field=serializers.ListField)
    def get_friends(self, obj):
        # 自定义字段
        return obj.friends.all()

# 5. 使用视图集
@api_docs(tags=["auth"])
class AuthViewSet(viewsets.ViewSet):
    @api_response(
        status_code=status.HTTP_200_OK,
        description="Login successful",
        schema=TokenSerializer
    )
    def login(self, request):
        # 登录接口
        pass

    @api_response(
        status_code=status.HTTP_204_NO_CONTENT,
        description="Logout successful"
    )
    def logout(self, request):
        # 登出接口
        pass
"""
