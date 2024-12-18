from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "核心"

    def ready(self):
        try:
            import apps.core.signals  # noqa F401
        except ImportError:
            pass 