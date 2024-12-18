from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    name = "apps.authentication"
    verbose_name = "认证系统"

    def ready(self):
        try:
            import apps.authentication.signals  # noqa F401
        except ImportError:
            pass
