import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models.signals import post_migrate, post_save, pre_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

User = get_user_model()


# 注册信号,在创建用户时自动加密密码
@receiver(post_save, sender=User)
def create_user(sender, instance=None, created=False, **kwargs):
    """
    用户创建时的信号处理
    - 对新建用户的密码进行加密
    - 记录用户创建日志
    """
    if created:
        password = instance.password
        instance.set_password(password)
        instance.save()
        logger.info(f"新用户创建成功: {instance.username}")


# 用户数据变更前的处理
@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, **kwargs):
    """
    用户数据更新前的信号处理
    - 清除用户相关缓存
    - 记录变更日志
    """
    if instance.pk:
        cache.delete(f"user_{instance.pk}")
        old_instance = sender.objects.get(pk=instance.pk)
        logger.info(f"用户信息变更: {old_instance.username} -> {instance.username}")


# 用户删除前的处理
@receiver(pre_delete, sender=User)
def user_pre_delete(sender, instance, **kwargs):
    """
    用户删除前的信号处理
    - 清理用户相关数据
    - 记录删除日志
    """
    cache.delete(f"user_{instance.pk}")
    logger.info(f"用户删除: {instance.username}")


@receiver(post_migrate)
def create_default_login_properties(sender, **kwargs):
    """
    系统初始化时创建默认登录配置
    - 创建超级管理员账号
    - 初始化基础权限
    - 设置默认角色
    """
    try:
        # 检查是否需要创建超级管理员
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin", password="admin123", email="admin@example.com", phone="13800000000"
            )
            logger.info("成功创建超级管理员账号")

        # 初始化其他默认配置
        from apps.users.models import Role, Permission

        # 创建默认角色(如果不存在)
        if not Role.objects.filter(code="admin").exists():
            Role.objects.create(name="超级管理员", code="admin", level=1, description="系统超级管理员")
            logger.info("成功创建默认角色")

    except Exception as e:
        logger.error(f"初始化默认配置失败: {str(e)}")
