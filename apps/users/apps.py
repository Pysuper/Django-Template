from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "users"
    verbose_name = "用户管理"
    orderIndex = 10

    def ready(self):
        """
        Django应用程序准备就绪时执行的初始化操作
        主要用于:
        1. 注册信号处理器
        2. 导入模型类
        3. 初始化缓存
        4. 加载配置等

        Django app initialization operations when ready:
        1. Register signal handlers
        2. Import model classes
        3. Initialize cache
        4. Load configurations
        """
        # Import signal handlers / 导入信号处理器
        # This triggers the @receiver decorators to register signals
        # 这会触发 @receiver 装饰器注册信号
        import apps.users.signals

        # Initialize cache / 初始化缓存
        from django.core.cache import cache
        cache.clear()

        # Load system configuration / 加载系统配置
        try:
            from django.conf import settings
            settings.INSTALLED_APPS
        except ImportError:
            pass

        # Log app initialization / 记录应用初始化日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info("User management app initialized successfully / 用户管理应用初始化完成")
