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
        """
        # 导入信号处理器
        from utils.signals import create_default_login_properties, create_user
        from django.db.models.signals import post_migrate, post_save
        from django.contrib.auth import get_user_model

        # 注册数据库迁移后的信号处理
        post_migrate.connect(create_default_login_properties, sender=self)

        # 注册用户模型的保存信号处理
        User = get_user_model()
        post_save.connect(create_user, sender=User)

        # 初始化缓存
        from django.core.cache import cache

        cache.clear()

        # 加载系统配置
        try:
            from django.conf import settings

            settings.INSTALLED_APPS
        except ImportError:
            pass

        # 输出应用启动日志
        import logging

        logger = logging.getLogger(__name__)
        logger.info("用户管理应用初始化完成")
