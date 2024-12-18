from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """
    用户保存后的信号处理
    """
    if created:
        # 新用户创建后的处理
        # 例如：发送欢迎邮件、创建用户配置等
        pass
