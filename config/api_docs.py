from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.plumbing import build_bearer_security_scheme_object


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    JWT认证方案
    """
    target_class = 'rest_framework_simplejwt.authentication.JWTAuthentication'
    name = 'JWT'
    match_subclasses = True
    priority = 1

    def get_security_definition(self, auto_schema):
        return build_bearer_security_scheme_object(
            header_name='Authorization',
            token_prefix='Bearer',
            bearer_format='JWT'
        )


SPECTACULAR_SETTINGS = {
    'TITLE': '项目API文档',
    'DESCRIPTION': '''
    # API接口文档
    
    ## 认证方式
    - JWT Token认证
    - 在请求头中添加 `Authorization: Bearer <token>`
    
    ## 错误处理
    - 所有接口统一返回格式
    - 错误码和错误信息标准化
    
    ## 版本控制
    - API版本通过URL前缀控制
    - 当前版本: v1
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SCHEMA_PATH_PREFIX': '/api/v[0-9]',
    'SCHEMA_PATH_PREFIX_TRIM': True,
    
    # 认证和权限
    'SECURITY': [{'Bearer': []}],
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'JWT Token，格式：Bearer <token>'
        }
    },
    
    # 标签排序
    'TAGS': [
        {'name': 'auth', 'description': '认证相关'},
        {'name': 'users', 'description': '用户相关'},
    ],
    
    # 组件设置
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': False,
    
    # 扩展设置
    'ENUM_NAME_OVERRIDES': {
        'VerificationCodeTypeEnum': 'apps.authentication.models.VerificationCode.TYPE_CHOICES',
        'VerificationCodePurposeEnum': 'apps.authentication.models.VerificationCode.PURPOSE_CHOICES',
    },
    
    # 示例和默认值
    'EXAMPLES': {
        'LoginRequest': {
            'value': {
                'username': 'test_user',
                'password': 'test_password',
                'mfa_code': '123456'
            }
        }
    },
    
    # 文档界面设置
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
    
    # 响应处理
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
    'DEFAULT_RESPONSE_CLASS': 'rest_framework.response.Response',
    'POSTPROCESSING_HOOKS': [],
} 