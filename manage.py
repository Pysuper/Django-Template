import os
import sys
from pathlib import Path

if __name__ == "__main__":
    # 根据环境变量选择配置文件
    environment = os.getenv("DJANGO_ENV", "local")  # 默认使用 'local'
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{environment}")

    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        try:
            import django
        except ImportError:
            raise ImportError("Couldn't import Django!")
        raise

    current_path = Path(__file__).parent.resolve()
    sys.path.append(str(current_path / "apps"))

    execute_from_command_line(sys.argv)
