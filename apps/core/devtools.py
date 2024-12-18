import inspect
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from django.db.models import Model
from django.template.loader import render_to_string
from django.utils.text import camel_case_to_spaces, slugify

from .logging import log_timing

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

class CodeGenerator:
    """代码生成器"""
    
    def __init__(self):
        # 加载配置
        self.config = getattr(settings, "GENERATOR_CONFIG", {})
        
        # 模板目录
        self.template_dir = Path(self.config.get(
            "TEMPLATE_DIR",
            settings.BASE_DIR / "templates" / "generators"
        ))
        
        # 输出目录
        self.output_dir = Path(self.config.get(
            "OUTPUT_DIR",
            settings.BASE_DIR / "apps"
        ))
        
        # 创建目录
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_app(self, app_name: str) -> None:
        """生成应用"""
        # 创建应用目录
        app_dir = self.output_dir / app_name
        app_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件
        self._generate_file(app_dir / "__init__.py", "app/__init__.py")
        self._generate_file(app_dir / "apps.py", "app/apps.py", {"app_name": app_name})
        self._generate_file(app_dir / "models.py", "app/models.py", {"app_name": app_name})
        self._generate_file(app_dir / "views.py", "app/views.py", {"app_name": app_name})
        self._generate_file(app_dir / "urls.py", "app/urls.py", {"app_name": app_name})
        self._generate_file(app_dir / "admin.py", "app/admin.py", {"app_name": app_name})
        self._generate_file(app_dir / "serializers.py", "app/serializers.py", {"app_name": app_name})
        
        # 创建测试目录
        test_dir = app_dir / "tests"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        self._generate_file(test_dir / "__init__.py", "app/tests/__init__.py")
        self._generate_file(test_dir / "test_models.py", "app/tests/test_models.py", {"app_name": app_name})
        self._generate_file(test_dir / "test_views.py", "app/tests/test_views.py", {"app_name": app_name})
        self._generate_file(test_dir / "factories.py", "app/tests/factories.py", {"app_name": app_name})
        
    def generate_model(
        self,
        app_name: str,
        model_name: str,
        fields: List[Dict[str, Any]]
    ) -> None:
        """生成模型"""
        # 获取应用目录
        app_dir = self.output_dir / app_name
        
        # 生成模型文件
        self._generate_file(
            app_dir / "models.py",
            "model/model.py",
            {
                "app_name": app_name,
                "model_name": model_name,
                "fields": fields,
            }
        )
        
        # 生成序列化器
        self._generate_file(
            app_dir / "serializers.py",
            "model/serializer.py",
            {
                "app_name": app_name,
                "model_name": model_name,
                "fields": fields,
            }
        )
        
        # 生成视图
        self._generate_file(
            app_dir / "views.py",
            "model/views.py",
            {
                "app_name": app_name,
                "model_name": model_name,
            }
        )
        
        # 生成URL配置
        self._generate_file(
            app_dir / "urls.py",
            "model/urls.py",
            {
                "app_name": app_name,
                "model_name": model_name,
            }
        )
        
        # 生成管理界面
        self._generate_file(
            app_dir / "admin.py",
            "model/admin.py",
            {
                "app_name": app_name,
                "model_name": model_name,
                "fields": fields,
            }
        )
        
        # 生成测试
        test_dir = app_dir / "tests"
        self._generate_file(
            test_dir / "test_models.py",
            "model/tests/test_model.py",
            {
                "app_name": app_name,
                "model_name": model_name,
                "fields": fields,
            }
        )
        self._generate_file(
            test_dir / "test_views.py",
            "model/tests/test_views.py",
            {
                "app_name": app_name,
                "model_name": model_name,
            }
        )
        self._generate_file(
            test_dir / "factories.py",
            "model/tests/factory.py",
            {
                "app_name": app_name,
                "model_name": model_name,
                "fields": fields,
            }
        )
        
    def generate_api(
        self,
        app_name: str,
        model_name: str,
        actions: List[str]
    ) -> None:
        """生成API"""
        # 获取应用目录
        app_dir = self.output_dir / app_name
        
        # 生成视图
        self._generate_file(
            app_dir / "views.py",
            "api/views.py",
            {
                "app_name": app_name,
                "model_name": model_name,
                "actions": actions,
            }
        )
        
        # 生成URL配置
        self._generate_file(
            app_dir / "urls.py",
            "api/urls.py",
            {
                "app_name": app_name,
                "model_name": model_name,
                "actions": actions,
            }
        )
        
        # 生成序列化器
        self._generate_file(
            app_dir / "serializers.py",
            "api/serializers.py",
            {
                "app_name": app_name,
                "model_name": model_name,
            }
        )
        
        # 生成测试
        test_dir = app_dir / "tests"
        self._generate_file(
            test_dir / "test_views.py",
            "api/tests/test_views.py",
            {
                "app_name": app_name,
                "model_name": model_name,
                "actions": actions,
            }
        )
        
    def _generate_file(
        self,
        output_file: Path,
        template_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """生成文件"""
        # 渲染模板
        content = render_to_string(
            f"generators/{template_name}",
            context or {}
        )
        
        # 写入文件
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.info(f"Generated file: {output_file}")

class Debugger:
    """调试器"""
    
    def __init__(self):
        # 加载配置
        self.config = getattr(settings, "DEBUGGER_CONFIG", {})
        
        # 是否启用调试
        self.enabled = self.config.get("ENABLED", settings.DEBUG)
        
        # 调试级别
        self.level = self.config.get("LEVEL", "INFO")
        
        # 输出格式
        self.format = self.config.get("FORMAT", "text")
        
    def debug(
        self,
        obj: Any,
        level: str = "INFO",
        format: Optional[str] = None
    ) -> None:
        """调��对象"""
        if not self.enabled:
            return
            
        # 检查级别
        if not self._check_level(level):
            return
            
        # 格式化输出
        output = self._format_output(obj, format or self.format)
        
        # 输出调试信息
        logger.log(
            getattr(logging, level),
            output,
            extra={"data": {"object": obj}}
        )
        
    def inspect(self, obj: Any) -> Dict[str, Any]:
        """检查对象"""
        info = {
            "type": type(obj).__name__,
            "module": getattr(obj, "__module__", None),
            "doc": inspect.getdoc(obj),
            "file": inspect.getfile(obj.__class__),
            "attributes": {},
            "methods": {},
        }
        
        # 获取属性
        for name, value in inspect.getmembers(obj):
            if name.startswith("_"):
                continue
                
            if inspect.ismethod(value):
                info["methods"][name] = {
                    "doc": inspect.getdoc(value),
                    "signature": str(inspect.signature(value)),
                }
            else:
                info["attributes"][name] = {
                    "type": type(value).__name__,
                    "value": str(value),
                }
                
        return info
        
    def trace(self, func: T) -> T:
        """跟踪装饰器"""
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 记录调用信息
            logger.debug(
                f"Calling {func.__name__}",
                extra={
                    "data": {
                        "args": args,
                        "kwargs": kwargs,
                        "caller": inspect.stack()[1].function,
                    }
                }
            )
            
            try:
                result = func(*args, **kwargs)
                
                # 记录返回值
                logger.debug(
                    f"Returned from {func.__name__}",
                    extra={
                        "data": {
                            "result": result,
                        }
                    }
                )
                
                return result
            except Exception as e:
                # 记录异常
                logger.error(
                    f"Error in {func.__name__}",
                    extra={
                        "data": {
                            "error": str(e),
                            "traceback": inspect.trace(),
                        }
                    },
                    exc_info=True
                )
                raise
        return cast(T, wrapper)
        
    def _check_level(self, level: str) -> bool:
        """检查调试级别"""
        levels = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
        }
        return levels.get(level, 0) >= levels.get(self.level, 0)
        
    def _format_output(self, obj: Any, format: str) -> str:
        """格式化输出"""
        if format == "json":
            return json.dumps(obj, indent=2, ensure_ascii=False)
        elif format == "repr":
            return repr(obj)
        else:
            return str(obj)

class CommandGenerator:
    """命令生成器"""
    
    def __init__(self):
        # 加载配置
        self.config = getattr(settings, "COMMAND_CONFIG", {})
        
        # 命令目录
        self.command_dir = Path(self.config.get(
            "COMMAND_DIR",
            settings.BASE_DIR / "apps" / "core" / "management" / "commands"
        ))
        
        # 创建目录
        self.command_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_command(
        self,
        name: str,
        description: str,
        arguments: List[Dict[str, Any]]
    ) -> None:
        """生成命令"""
        # 生成命令文件
        command_file = self.command_dir / f"{name}.py"
        
        # 渲染模板
        content = render_to_string(
            "generators/command/command.py",
            {
                "name": name,
                "description": description,
                "arguments": arguments,
            }
        )
        
        # 写入文件
        with open(command_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        logger.info(f"Generated command: {command_file}")

class SchemaGenerator:
    """模式生成器"""
    
    def __init__(self):
        # 加载配置
        self.config = getattr(settings, "SCHEMA_CONFIG", {})
        
        # 输出目录
        self.output_dir = Path(self.config.get(
            "OUTPUT_DIR",
            settings.BASE_DIR / "schemas"
        ))
        
        # 创建目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_model_schema(self, model: Type[Model]) -> Dict[str, Any]:
        """生成模型模式"""
        schema = {
            "name": model.__name__,
            "app_label": model._meta.app_label,
            "db_table": model._meta.db_table,
            "fields": [],
            "relations": [],
            "indexes": [],
            "constraints": [],
        }
        
        # 获取字段
        for field in model._meta.fields:
            field_schema = {
                "name": field.name,
                "type": field.get_internal_type(),
                "null": field.null,
                "blank": field.blank,
                "default": field.get_default(),
                "help_text": str(field.help_text),
                "verbose_name": str(field.verbose_name),
                "unique": field.unique,
            }
            
            if field.is_relation:
                field_schema.update({
                    "related_model": field.related_model.__name__,
                    "related_name": field.related_query_name(),
                    "on_delete": field.remote_field.on_delete.__name__,
                })
                schema["relations"].append(field_schema)
            else:
                schema["fields"].append(field_schema)
                
        # 获取索引
        for index in model._meta.indexes:
            schema["indexes"].append({
                "name": index.name,
                "fields": [field_name for field_name in index.fields],
                "unique": index.unique,
            })
            
        # 获取约束
        for constraint in model._meta.constraints:
            schema["constraints"].append({
                "name": constraint.name,
                "type": constraint.__class__.__name__,
            })
            
        return schema
        
    def generate_app_schema(self, app_label: str) -> Dict[str, Any]:
        """生成应用模式"""
        app = apps.get_app_config(app_label)
        schema = {
            "name": app.name,
            "label": app.label,
            "models": {},
        }
        
        # 获取模型
        for model in app.get_models():
            schema["models"][model.__name__] = self.generate_model_schema(model)
            
        return schema
        
    def generate_project_schema(self) -> Dict[str, Any]:
        """生成项目模式"""
        schema = {
            "name": settings.ROOT_URLCONF.split(".")[0],
            "apps": {},
        }
        
        # 获取应用
        for app in apps.get_app_configs():
            schema["apps"][app.label] = self.generate_app_schema(app.label)
            
        return schema
        
    def export_schema(self, schema: Dict[str, Any], format: str = "json") -> None:
        """导出模式"""
        if format == "json":
            output_file = self.output_dir / "schema.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {format}")
            
        logger.info(f"Exported schema: {output_file}")

# 使用示例
"""
# 1. 代码生成器
generator = CodeGenerator()

# 生成应用
generator.generate_app("blog")

# 生成模型
generator.generate_model("blog", "Post", [
    {"name": "title", "type": "CharField", "max_length": 100},
    {"name": "content", "type": "TextField"},
    {"name": "author", "type": "ForeignKey", "to": "User"},
])

# 生成API
generator.generate_api("blog", "Post", [
    "list",
    "create",
    "retrieve",
    "update",
    "delete",
])

# 2. 调试器
debugger = Debugger()

# 调试对象
@debugger.trace
def my_function():
    result = perform_calculation()
    debugger.debug(result, level="INFO", format="json")
    return result

# 检查对象
info = debugger.inspect(my_object)
print(json.dumps(info, indent=2))

# 3. 命令生成器
command_generator = CommandGenerator()

# 生成命令
command_generator.generate_command(
    "import_data",
    "Import data from CSV file",
    [
        {"name": "file", "type": "str", "help": "CSV file path"},
        {"name": "model", "type": "str", "help": "Model name"},
    ]
)

# 4. 模式生成器
schema_generator = SchemaGenerator()

# 生成模型模式
model_schema = schema_generator.generate_model_schema(Post)

# 生成应用模式
app_schema = schema_generator.generate_app_schema("blog")

# 生成项目模式
project_schema = schema_generator.generate_project_schema()

# 导出模式
schema_generator.export_schema(project_schema, format="json")
""" 