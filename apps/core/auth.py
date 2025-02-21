from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    MinimumLengthValidator,
    NumericPasswordValidator,
    UserAttributeSimilarityValidator,
)
from django.contrib.sessions.backends.base import SessionBase
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils import timezone
from django.utils.crypto import get_random_string
from pydantic import BaseModel, Field

from .cache import CacheManager

User = get_user_model()

class PasswordPolicyConfig(BaseModel):
    """密码策略配置"""
    min_length: int = Field(default=8, ge=8, description="最小长度")
    max_length: int = Field(default=128, le=128, description="最大长度")
    require_uppercase: bool = Field(default=True, description="必须包含大写字母")
    require_lowercase: bool = Field(default=True, description="必须包含小写字母")
    require_digits: bool = Field(default=True, description="必须包含数字")
    require_special: bool = Field(default=True, description="必须包含特殊字符")
    special_chars: str = Field(
        default="!@#$%^&*()_+-=[]{}|;:,.<>?",
        description="特殊字符列表"
    )
    password_history: int = Field(default=5, ge=0, description="密码历史记录")
    password_expire_days: int = Field(default=90, ge=0, description="密码过期时间（天）")

class SessionPolicyConfig(BaseModel):
    """会话策略配置"""
    session_timeout: int = Field(default=1800, ge=300, description="会话超时时间（秒）")
    max_sessions: int = Field(default=5, ge=1, description="最大会话数")
    allow_concurrent: bool = Field(default=True, description="是否允许并发会话")

class LoginAttemptConfig(BaseModel):
    """登录尝试配置"""
    max_attempts: int = Field(default=5, ge=1, description="最大尝试次数")
    lockout_time: int = Field(default=300, ge=60, description="锁定时间（秒）")
    reset_time: int = Field(default=3600, ge=300, description="重置时间（秒）")

@dataclass
class PasswordValidationContext:
    """密码验证上下文"""
    password: str
    user: Optional[AbstractBaseUser]
    config: PasswordPolicyConfig

@dataclass
class SessionContext:
    """会话上下文"""
    session: SessionBase
    user: AbstractBaseUser
    config: SessionPolicyConfig

@dataclass
class LoginAttemptContext:
    """登录尝试上下文"""
    username: str
    ip_address: str
    success: bool
    config: LoginAttemptConfig

class PasswordPolicy:
    """密码策略"""

    def __init__(self) -> None:
        self.config = PasswordPolicyConfig(**(getattr(settings, "PASSWORD_POLICY", {})))

    def validate_password(
        self,
        password: str,
        user: Optional[AbstractBaseUser] = None
    ) -> None:
        """验证密码"""
        context = PasswordValidationContext(
            password=password,
            user=user,
            config=self.config
        )

        self._check_length(context)
        self._check_complexity(context)
        self._check_user_attributes(context)
        self._check_history(context)

    def is_password_expired(self, user: AbstractBaseUser) -> bool:
        """检查密码是否过期"""
        if not self.config.password_expire_days:
            return False

        last_changed = getattr(user, "password_changed_at", None)
        if not last_changed:
            return True

        expire_date = last_changed + timedelta(days=self.config.password_expire_days)
        return timezone.now() >= expire_date

    def _check_length(self, context: PasswordValidationContext) -> None:
        """检查长度"""
        if len(context.password) < context.config.min_length:
            raise ValidationError(f"密码长度不能小于{context.config.min_length}个字符")

        if len(context.password) > context.config.max_length:
            raise ValidationError(f"密码长度不能大于{context.config.max_length}个字符")

    def _check_complexity(self, context: PasswordValidationContext) -> None:
        """检查复杂度"""
        if context.config.require_uppercase and not any(c.isupper() for c in context.password):
            raise ValidationError("密码必须包含大写字母")

        if context.config.require_lowercase and not any(c.islower() for c in context.password):
            raise ValidationError("密码必须包含小写字母")

        if context.config.require_digits and not any(c.isdigit() for c in context.password):
            raise ValidationError("密码必须包含数字")

        if context.config.require_special and not any(
            c in context.config.special_chars for c in context.password
        ):
            raise ValidationError("密码必须包含特殊字符")

    def _check_user_attributes(self, context: PasswordValidationContext) -> None:
        """检查用户属性"""
        if context.user:
            validators = [
                UserAttributeSimilarityValidator(),
                CommonPasswordValidator(),
                MinimumLengthValidator(context.config.min_length),
                NumericPasswordValidator(),
            ]
            for validator in validators:
                validator.validate(context.password, context.user)

    def _check_history(self, context: PasswordValidationContext) -> None:
        """检查密码历史"""
        if not context.user or not context.config.password_history:
            return

        from .models import PasswordHistory
        history = PasswordHistory.objects.filter(
            user=context.user
        ).order_by("-created_at")[:context.config.password_history]

        for item in history:
            if context.user.check_password(context.password):
                raise ValidationError(
                    f"不能使用最近{context.config.password_history}次使用过的密码"
                )

class SessionManager:
    """会话管理器"""

    def __init__(self) -> None:
        self.config = SessionPolicyConfig(**(getattr(settings, "SESSION_POLICY", {})))
        self.cache_manager = CacheManager(prefix="session")

    def validate_session(
        self,
        request: HttpRequest,
        user: AbstractBaseUser
    ) -> None:
        """验证会话"""
        context = SessionContext(
            session=request.session,
            user=user,
            config=self.config
        )

        self._check_session_expired(context)
        self._check_concurrent_sessions(context)
        self._check_max_sessions(context)
        self._update_session_timestamp(context)

    def create_session(
        self,
        request: HttpRequest,
        user: AbstractBaseUser
    ) -> None:
        """创建会话"""
        session_id = get_random_string(32)
        request.session.cycle_key()

        request.session.update({
            "user_id": user.id,
            "created_at": timezone.now().isoformat(),
            "last_activity": timezone.now().isoformat(),
            "session_id": session_id,
        })

        request.session.set_expiry(self.config.session_timeout)
        self._record_session(session_id, user)

    def destroy_session(
        self,
        request: HttpRequest,
        user: AbstractBaseUser
    ) -> None:
        """销毁会话"""
        session_id = request.session.get("session_id")
        if session_id:
            self._remove_session(session_id, user)
        request.session.flush()

    def _check_session_expired(self, context: SessionContext) -> None:
        """检查会话是否过期"""
        last_activity = context.session.get("last_activity")
        if not last_activity:
            raise ValidationError("会话已过期")

        last_activity_time = datetime.fromisoformat(last_activity)
        if (timezone.now() - last_activity_time).total_seconds() > context.config.session_timeout:
            raise ValidationError("会话已过期")

    def _check_concurrent_sessions(self, context: SessionContext) -> None:
        """检查并发会话"""
        if not context.config.allow_concurrent:
            current_session_id = context.session.get("session_id")
            if not current_session_id:
                return

            active_sessions = Session.objects.filter(
                expire_date__gt=timezone.now(),
                session_data__contains=str(context.user.id)
            ).exclude(session_key=current_session_id)

            if active_sessions.exists():
                raise ValidationError("不允许并发会话")

    def _check_max_sessions(self, context: SessionContext) -> None:
        """检查最大会话数"""
        if context.config.max_sessions > 0:
            active_sessions = Session.objects.filter(
                expire_date__gt=timezone.now(),
                session_data__contains=str(context.user.id)
            )

            if active_sessions.count() >= context.config.max_sessions:
                oldest_session = active_sessions.order_by("last_activity").first()
                if oldest_session:
                    oldest_session.delete()

    def _update_session_timestamp(self, context: SessionContext) -> None:
        """更新会话时间戳"""
        context.session["last_activity"] = timezone.now().isoformat()
        context.session.save()

    def _record_session(self, session_id: str, user: AbstractBaseUser) -> None:
        """记录会话"""
        key = f"user_sessions:{user.id}"
        sessions = self.cache_manager.get(key, set())
        sessions.add(session_id)
        self.cache_manager.set(key, sessions)

    def _remove_session(self, session_id: str, user: AbstractBaseUser) -> None:
        """移除会话记录"""
        key = f"user_sessions:{user.id}"
        sessions = self.cache_manager.get(key, set())
        sessions.discard(session_id)
        self.cache_manager.set(key, sessions)

class LoginAttemptTracker:
    """登录尝试跟踪器"""

    def __init__(self) -> None:
        self.config = LoginAttemptConfig(**(getattr(settings, "LOGIN_ATTEMPT_POLICY", {})))
        self.cache_manager = CacheManager(prefix="login_attempts")

    def record_attempt(
        self,
        username: str,
        ip_address: str,
        success: bool
    ) -> None:
        """记录登录尝试"""
        context = LoginAttemptContext(
            username=username,
            ip_address=ip_address,
            success=success,
            config=self.config
        )

        self._record_user_attempt(context)
        self._record_ip_attempt(context)

    def is_locked_out(self, username: str, ip_address: str) -> bool:
        """检查是否被锁定"""
        context = LoginAttemptContext(
            username=username,
            ip_address=ip_address,
            success=False,
            config=self.config
        )

        return (
            self._check_user_lockout(context) or
            self._check_ip_lockout(context)
        )

    def _record_user_attempt(self, context: LoginAttemptContext) -> None:
        """记录用户尝试"""
        key = f"user:{context.username}"
        attempts = self.cache_manager.get(key, [])
        attempts.append({
            "timestamp": timezone.now().isoformat(),
            "ip_address": context.ip_address,
            "success": context.success,
        })
        self.cache_manager.set(key, attempts, timeout=context.config.reset_time)

    def _record_ip_attempt(self, context: LoginAttemptContext) -> None:
        """记录IP尝试"""
        key = f"ip:{context.ip_address}"
        attempts = self.cache_manager.get(key, [])
        attempts.append({
            "timestamp": timezone.now().isoformat(),
            "username": context.username,
            "success": context.success,
        })
        self.cache_manager.set(key, attempts, timeout=context.config.reset_time)

    def _check_user_lockout(self, context: LoginAttemptContext) -> bool:
        """检查用户锁定"""
        key = f"user:{context.username}"
        attempts = self.cache_manager.get(key, [])
        return self._check_lockout(attempts, context.config)

    def _check_ip_lockout(self, context: LoginAttemptContext) -> bool:
        """检查IP锁定"""
        key = f"ip:{context.ip_address}"
        attempts = self.cache_manager.get(key, [])
        return self._check_lockout(attempts, context.config)

    def _check_lockout(
        self,
        attempts: List[Dict[str, Any]],
        config: LoginAttemptConfig
    ) -> bool:
        """检查锁定状态"""
        if not attempts:
            return False

        recent_attempts = [
            attempt for attempt in attempts
            if (
                timezone.now() -
                datetime.fromisoformat(attempt["timestamp"])
            ).total_seconds() < config.lockout_time
        ]

        failed_attempts = [
            attempt for attempt in recent_attempts
            if not attempt["success"]
        ]

        return len(failed_attempts) >= config.max_attempts

# 使用示例
"""
# 1. 在settings.py中配置密码策略
PASSWORD_POLICY = {
    "MIN_LENGTH": 8,
    "MAX_LENGTH": 128,
    "REQUIRE_UPPERCASE": True,
    "REQUIRE_LOWERCASE": True,
    "REQUIRE_DIGITS": True,
    "REQUIRE_SPECIAL": True,
    "SPECIAL_CHARS": "!@#$%^&*()_+-=[]{}|;:,.<>?",
    "PASSWORD_HISTORY": 5,
    "PASSWORD_EXPIRE_DAYS": 90,
}

# 2. 配置会话策略
SESSION_POLICY = {
    "SESSION_TIMEOUT": 1800,
    "MAX_SESSIONS": 5,
    "ALLOW_CONCURRENT": True,
}

# 3. 配置登录尝试策略
LOGIN_ATTEMPT_POLICY = {
    "MAX_ATTEMPTS": 5,
    "LOCKOUT_TIME": 300,
    "RESET_TIME": 3600,
}

# 4. 在视图中使用密码策略
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

def change_password(request):
    user = request.user
    new_password = request.POST.get("new_password")

    try:
        # 验证新密码
        policy = PasswordPolicy()
        policy.validate_password(new_password, user)

        # 更新密码
        user.set_password(new_password)
        user.save()

        return JsonResponse({"message": "密码已更新"})
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)

# 5. 在视图中使用会话管理
def login_view(request):
    username = request.POST.get("username")
    password = request.POST.get("password")
    ip_address = request.META.get("REMOTE_ADDR")

    # 检查登录尝试
    tracker = LoginAttemptTracker()
    if tracker.is_locked_out(username, ip_address):
        return JsonResponse({"error": "��户已锁定"}, status=403)

    # 验证用户
    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            # 创建会话
            session_manager = SessionManager()
            session_manager.create_session(request, user)

            # 记录成功登录
            tracker.record_attempt(username, ip_address, True)

            return JsonResponse({"message": "登录成功"})
        else:
            # 记录失败登录
            tracker.record_attempt(username, ip_address, False)
            return JsonResponse({"error": "用户名或密码错误"}, status=400)
    except User.DoesNotExist:
        # 记录失败登录
        tracker.record_attempt(username, ip_address, False)
        return JsonResponse({"error": "用户名或密码错误"}, status=400)

# 6. 在中间件中使用会话管理
class SessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.session_manager = SessionManager()

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # 验证会话
                self.session_manager.validate_session(request, request.user)
            except ValidationError:
                # 会话无效，注销用户
                from django.contrib.auth import logout
                logout(request)
                return JsonResponse({"error": "会话已过期"}, status=401)

        response = self.get_response(request)
        return response

# 7. 在模型中使用密码历史
from django.db import models

class PasswordHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
"""
