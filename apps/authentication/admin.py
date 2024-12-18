from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.authentication.models import LoginHistory, VerificationCode

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "username",
        "email",
        "phone",
        "is_email_verified",
        "is_phone_verified",
        "is_mfa_enabled",
        "is_staff",
        "is_active",
        "date_joined",
        "last_login",
    ]
    list_filter = [
        "is_staff",
        "is_active",
        "is_email_verified",
        "is_phone_verified",
        "is_mfa_enabled",
    ]
    search_fields = ["username", "email", "phone"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("个人信息"), {"fields": ("email", "phone", "avatar")}),
        (
            _("验证状态"),
            {
                "fields": (
                    "is_email_verified",
                    "is_phone_verified",
                    "is_mfa_enabled",
                    "mfa_secret",
                ),
            },
        ),
        (
            _("权限"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("重要日期"), {"fields": ("last_login", "date_joined")}),
    )


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "ip_address",
        "location",
        "user_agent",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "user__username",
        "user__email",
        "ip_address",
        "location",
    ]
    ordering = ["-created_at"]


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "type",
        "purpose",
        "target",
        "code",
        "is_used",
        "expired_at",
        "created_at",
    ]
    list_filter = [
        "type",
        "purpose",
        "is_used",
        "created_at",
    ]
    search_fields = [
        "user__username",
        "user__email",
        "target",
        "code",
    ]
    ordering = ["-created_at"]
