import pyotp
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.logging import ModelLogger
from apps.core.models import BaseModel


class User(AbstractUser, BaseModel):
    """
    用户模型
    扩展Django默认用户模型
    """

    email = models.EmailField(_("邮箱"), unique=True)
    phone = models.CharField(_("手机号"), max_length=11, unique=True, null=True, blank=True)
    avatar = models.ImageField(_("头像"), upload_to="avatars/", null=True, blank=True)
    is_email_verified = models.BooleanField(_("邮箱是否验证"), default=False)
    is_phone_verified = models.BooleanField(_("手机是否验证"), default=False)
    mfa_secret = models.CharField(_("MFA密钥"), max_length=32, null=True, blank=True)
    is_mfa_enabled = models.BooleanField(_("是否启用MFA"), default=False)
    last_login_ip = models.GenericIPAddressField(_("最后登录IP"), null=True, blank=True)
    last_login_user_agent = models.CharField(_("最后登录UA"), max_length=255, null=True, blank=True)

    logger = ModelLogger(model_class=__class__)

    class Meta:
        verbose_name = _("用户")
        verbose_name_plural = _("用户")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.username

    def generate_mfa_secret(self) -> str:
        """
        生成MFA密钥
        """
        self.mfa_secret = pyotp.random_base32()
        self.save(update_fields=["mfa_secret"])
        return self.mfa_secret

    def verify_mfa_code(self, code: str) -> bool:
        """
        验证MFA验证码
        """
        if not self.mfa_secret:
            return False
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(code)

    def get_mfa_qr_url(self) -> str:
        """
        获取MFA二维码URL
        """
        if not self.mfa_secret:
            self.generate_mfa_secret()
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.provisioning_uri(name=self.email, issuer_name=settings.SITE_NAME)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not is_new:
            old_instance = self.__class__.objects.get(pk=self.pk)
            changed_fields = {
                field.name: (getattr(old_instance, field.name), getattr(self, field.name))
                for field in self._meta.fields
                if getattr(old_instance, field.name) != getattr(self, field.name)
            }
            super().save(*args, **kwargs)
            if changed_fields:
                self.logger.log_update(self, changed_fields)
        else:
            super().save(*args, **kwargs)
            self.logger.log_create(self)

    def delete(self, *args, **kwargs):
        self.logger.log_delete(self)
        super().delete(*args, **kwargs)


class LoginHistory(BaseModel):
    """
    登录历史记录
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("用户"), related_name="login_history")
    ip_address = models.GenericIPAddressField(_("IP地址"))
    user_agent = models.CharField(_("User Agent"), max_length=255)
    location = models.CharField(_("登录地点"), max_length=100, null=True, blank=True)
    status = models.BooleanField(_("是否成功"), default=True)
    failure_reason = models.CharField(_("失败原因"), max_length=100, null=True, blank=True)

    logger = ModelLogger(model_class=__class__)

    class Meta:
        verbose_name = _("登录历史")
        verbose_name_plural = _("登录历史")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not is_new:
            old_instance = self.__class__.objects.get(pk=self.pk)
            changed_fields = {
                field.name: (getattr(old_instance, field.name), getattr(self, field.name))
                for field in self._meta.fields
                if getattr(old_instance, field.name) != getattr(self, field.name)
            }
            super().save(*args, **kwargs)
            if changed_fields:
                self.logger.log_update(self, changed_fields)
        else:
            super().save(*args, **kwargs)
            self.logger.log_create(self)

    def delete(self, *args, **kwargs):
        self.logger.log_delete(self)
        super().delete(*args, **kwargs)


class VerificationCode(BaseModel):
    """
    验证码
    支持邮箱和短信验证码
    """

    TYPE_CHOICES = (
        ("email", _("邮箱")),
        ("sms", _("短信")),
    )
    PURPOSE_CHOICES = (
        ("register", _("注册")),
        ("login", _("登录")),
        ("reset_password", _("重置密码")),
        ("bind", _("绑定")),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name=_("用户"), related_name="verification_codes", null=True, blank=True
    )
    type = models.CharField(_("类型"), max_length=10, choices=TYPE_CHOICES)
    purpose = models.CharField(_("用途"), max_length=20, choices=PURPOSE_CHOICES)
    target = models.CharField(_("目标"), max_length=100)  # 邮箱或手机号
    code = models.CharField(_("验证码"), max_length=6)
    is_used = models.BooleanField(_("是否已使用"), default=False)
    expired_at = models.DateTimeField(_("过期时间"))

    logger = ModelLogger(model_class=__class__)

    class Meta:
        verbose_name = _("验证码")
        verbose_name_plural = _("验证码")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.target} - {self.code}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not is_new:
            old_instance = self.__class__.objects.get(pk=self.pk)
            changed_fields = {
                field.name: (getattr(old_instance, field.name), getattr(self, field.name))
                for field in self._meta.fields
                if getattr(old_instance, field.name) != getattr(self, field.name)
            }
            super().save(*args, **kwargs)
            if changed_fields:
                self.logger.log_update(self, changed_fields)
        else:
            super().save(*args, **kwargs)
            self.logger.log_create(self)

    def delete(self, *args, **kwargs):
        self.logger.log_delete(self)
        super().delete(*args, **kwargs)
