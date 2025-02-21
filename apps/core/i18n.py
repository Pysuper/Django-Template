import functools
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from django.utils.translation.trans_real import DjangoTranslation, language_code_re

from .cache import CacheManager

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

class TranslationManager:
    """翻译管理器"""
    
    def __init__(self):
        # 加载配置
        self.config = getattr(settings, "I18N_CONFIG", {})
        
        # 默认语言
        self.default_language = self.config.get(
            "DEFAULT_LANGUAGE",
            settings.LANGUAGE_CODE
        )
        
        # 支持的语言
        self.languages = self.config.get(
            "LANGUAGES",
            getattr(settings, "LANGUAGES", [])
        )
        
        # 翻译目录
        self.locale_dir = Path(self.config.get(
            "LOCALE_DIR",
            settings.LOCALE_PATHS[0] if settings.LOCALE_PATHS else None
        ))
        
        # 缓存管理器
        self.cache_manager = CacheManager(prefix="i18n")
        
    def get_language_info(self, language: str) -> Dict[str, Any]:
        """获取语言信息"""
        # 验证语言代码
        if not language_code_re.match(language):
            raise ValueError(f"Invalid language code: {language}")
            
        # 获取语言名称
        with translation.override(language):
            name = _(translation.get_language_info(language)["name"])
            
        return {
            "code": language,
            "name": name,
            "name_local": translation.get_language_info(language)["name_local"],
            "bidi": translation.get_language_info(language)["bidi"],
        }
        
    def get_translations(
        self,
        language: str,
        domain: str = "django"
    ) -> Dict[str, str]:
        """获取翻译字典"""
        cache_key = f"translations:{language}:{domain}"
        
        # 尝试从缓存获取
        translations = self.cache_manager.get(cache_key)
        
        if translations is None:
            # 加载翻译
            trans = DjangoTranslation(language, domain=domain)
            translations = {}
            
            # 获取所有翻译
            catalog = getattr(trans, "_catalog", {})
            for message_id, message_str in catalog.items():
                if isinstance(message_id, str):
                    translations[message_id] = message_str
                    
            # 缓存翻译
            self.cache_manager.set(cache_key, translations)
            
        return translations
        
    def translate(
        self,
        text: str,
        language: Optional[str] = None,
        domain: str = "django"
    ) -> str:
        """翻译文本"""
        if language is None:
            language = translation.get_language() or self.default_language
            
        translations = self.get_translations(language, domain)
        return translations.get(text, text)
        
    def clear_cache(self) -> None:
        """清除缓存"""
        pattern = "translations:*"
        self.cache_manager.clear(pattern)

class LocaleMiddleware:
    """本地化中间件"""
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
        self.translation_manager = TranslationManager()
        
    def __call__(self, request: HttpRequest) -> HttpResponse:
        # 获取语言代码
        language = self.get_language(request)
        
        # 激活语言
        translation.activate(language)
        request.LANGUAGE_CODE = language
        
        response = self.get_response(request)
        
        # 添加语言Cookie
        if hasattr(response, "set_cookie"):
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                language,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
            
        return response
        
    def get_language(self, request: HttpRequest) -> str:
        """获取语言代码"""
        # 从会话获取
        if hasattr(request, "session"):
            language = request.session.get(translation.LANGUAGE_SESSION_KEY)
            if language in self.translation_manager.languages:
                return language
                
        # 从Cookie获取
        if settings.LANGUAGE_COOKIE_NAME in request.COOKIES:
            language = request.COOKIES[settings.LANGUAGE_COOKIE_NAME]
            if language in self.translation_manager.languages:
                return language
                
        # 从Accept-Language头获取
        accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
        for accept_lang, _ in translation.parse_accept_lang_header(accept):
            if accept_lang in self.translation_manager.languages:
                return accept_lang
                
        # 使用默认语言
        return self.translation_manager.default_language

def translate_model(model: Type[Any]) -> Type[Any]:
    """模型翻译装饰器"""
    class TranslatedModel(model):
        """翻译后的模型"""
        
        def __init__(self, *args: Any, **kwargs: Any):
            super().__init__(*args, **kwargs)
            self._translation_fields = getattr(
                self._meta, "translation_fields", []
            )
            
        def __getattribute__(self, name: str) -> Any:
            """获取属性"""
            try:
                attr = super().__getattribute__(name)
                if name in super().__getattribute__("_translation_fields"):
                    if isinstance(attr, str):
                        return _(attr)
                return attr
            except AttributeError:
                return super().__getattribute__(name)
                
    return TranslatedModel

def translate_field(field: str) -> Callable[[T], T]:
    """字段翻译装饰器"""
    def decorator(cls: T) -> T:
        if not hasattr(cls._meta, "translation_fields"):
            cls._meta.translation_fields = set()
        cls._meta.translation_fields.add(field)
        return cls
    return decorator

def with_locale(language: str) -> Callable[[T], T]:
    """本地化装饰器"""
    def decorator(func: T) -> T:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 保存当前语言
            current_language = translation.get_language()
            
            try:
                # 激活新语言
                translation.activate(language)
                return func(*args, **kwargs)
            finally:
                # 恢复原语言
                translation.activate(current_language)
        return cast(T, wrapper)
    return decorator

class LazyI18N:
    """延迟国际化"""
    
    def __init__(self, message: str):
        self.message = message
        
    def __str__(self) -> str:
        return str(_(self.message))
        
    def __repr__(self) -> str:
        return f"LazyI18N({self.message})"

def generate_translations(
    domain: str = "django",
    locale: Optional[str] = None,
    include_paths: Optional[List[str]] = None,
    exclude_paths: Optional[List[str]] = None,
) -> None:
    """生成翻译文件"""
    from django.core.management import call_command
    
    # 设置包含路径
    if include_paths:
        os.environ["DJANGO_MAKEMESSAGES_INCLUDE"] = ";".join(include_paths)
        
    # 设置排除路径
    if exclude_paths:
        os.environ["DJANGO_MAKEMESSAGES_EXCLUDE"] = ";".join(exclude_paths)
        
    # 生成翻译文件
    call_command(
        "makemessages",
        domain=domain,
        locale=[locale] if locale else None,
        all=locale is None,
        ignore_patterns=["venv/*", "*.pyc", "*.pyo"],
        verbosity=1,
    )

def compile_translations(locale: Optional[str] = None) -> None:
    """编译翻译文件"""
    from django.core.management import call_command
    
    # 编译翻译文件
    call_command(
        "compilemessages",
        locale=[locale] if locale else None,
        verbosity=1,
    )

# 使用示例
"""
# 1. 在settings.py中配置国际化
I18N_CONFIG = {
    "DEFAULT_LANGUAGE": "en",
    "LANGUAGES": [
        ("en", "English"),
        ("zh-hans", "简体中文"),
        ("ja", "日本語"),
    ],
    "LOCALE_DIR": os.path.join(BASE_DIR, "locale"),
}

MIDDLEWARE = [
    'django.middleware.locale.LocaleMiddleware',
    'apps.core.i18n.LocaleMiddleware',
]

LANGUAGE_CODE = 'en'
LANGUAGES = [
    ('en', _('English')),
    ('zh-hans', _('Simplified Chinese')),
    ('ja', _('Japanese')),
]

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

USE_I18N = True
USE_L10N = True
USE_TZ = True

# 2. 在模型中使用翻译装饰器
@translate_field("name")
@translate_field("description")
class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

# 3. 使用本地化装饰器
@with_locale("zh-hans")
def send_chinese_email(user, subject, message):
    # 发送中文邮件
    pass

# 4. 使用延迟国际化
error_message = LazyI18N("Invalid input")
print(error_message)  # 会根据当前语言环境翻译

# 5. 在视图中使用翻译
from django.utils.translation import gettext as _

def my_view(request):
    message = _("Hello, World!")
    return JsonResponse({"message": message})

# 6. 在模板中使用翻译
{% load i18n %}
<h1>{% trans "Welcome" %}</h1>
<p>{% blocktrans %}This is a translated paragraph.{% endblocktrans %}</p>

# 7. 生成和编译翻译文件
generate_translations(locale='zh-hans')
compile_translations()
""" 