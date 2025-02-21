import logging
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import LoginHistory, VerificationCode
from apps.authentication.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    MFASerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    UserSerializer,
)
from apps.core.logging import log_exception, log_timing
from apps.core.utils import get_client_ip

User = get_user_model()
logger = logging.getLogger(__name__)


@extend_schema_view(
    register=extend_schema(
        summary="用户注册",
        description="注册新用户，需要提供邮箱验证码",
        responses={
            201: OpenApiResponse(response=UserSerializer, description="用户注册成功，返回用户信息和token"),
            400: OpenApiResponse(description="注册失败，可能原因：验证码无效、用户名已存在等"),
        },
        tags=["auth"],
    ),
    login=extend_schema(
        summary="用户登录",
        description="用户登录，支持MFA双因素认证",
        responses={
            200: OpenApiResponse(response=UserSerializer, description="登录成功，返回用户信息和token"),
            400: OpenApiResponse(description="登录失败，可能原因：用户名或密码错误、MFA验证失败等"),
        },
        tags=["auth"],
    ),
    change_password=extend_schema(
        summary="修改密码",
        description="修改当前用户的密码",
        responses={
            200: OpenApiResponse(description="密码修改成功"),
            400: OpenApiResponse(description="密码修改失败，可能原因：原密码错误等"),
        },
        tags=["auth"],
    ),
    reset_password=extend_schema(
        summary="重置密码",
        description="通过邮箱验证码重置密码",
        responses={
            200: OpenApiResponse(description="密码重置成功"),
            400: OpenApiResponse(description="密码重置失败，可能原因：验证码无效等"),
        },
        tags=["auth"],
    ),
    send_code=extend_schema(
        summary="发送验证码",
        description="发送邮箱或短信验证码",
        parameters=[
            OpenApiParameter(
                name="type", description="验证码类型：email或sms", required=True, type=str, enum=["email", "sms"]
            ),
            OpenApiParameter(
                name="purpose",
                description="验证码用途",
                required=True,
                type=str,
                enum=["register", "login", "reset_password", "bind"],
            ),
            OpenApiParameter(name="target", description="目标（邮箱或手机号）", required=True, type=str),
        ],
        responses={
            200: OpenApiResponse(description="验证码发送成功"),
            400: OpenApiResponse(description="验证码发送失败，可能原因：发送太频繁等"),
        },
        tags=["auth"],
    ),
    mfa_qr=extend_schema(
        summary="获取MFA二维码",
        description="获取MFA二维码和密钥",
        responses={
            200: OpenApiResponse(
                description="返回MFA二维码URL和密钥",
                examples={"application/json": {"qr_url": "otpauth://...", "secret": "ABCDEFGH..."}},
            )
        },
        tags=["auth"],
    ),
    verify_mfa=extend_schema(
        summary="验证MFA",
        description="验证MFA并启用",
        responses={
            200: OpenApiResponse(description="MFA验证成功并启用"),
            400: OpenApiResponse(description="MFA验证失败"),
        },
        tags=["auth"],
    ),
)
class AuthViewSet(viewsets.GenericViewSet):
    """
    认证视图集
    提供注册、登录、修改密码等功能
    """

    permission_classes = [AllowAny]
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == "register":
            return RegisterSerializer
        elif self.action == "login":
            return LoginSerializer
        elif self.action == "change_password":
            return ChangePasswordSerializer
        elif self.action == "reset_password":
            return ResetPasswordSerializer
        elif self.action == "verify_mfa":
            return MFASerializer
        return self.serializer_class

    @log_timing(message="User registration completed")
    @action(methods=["post"], detail=False)
    def register(self, request):
        """用户注册"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # 验证邮箱验证码
            email = serializer.validated_data["email"]
            code = serializer.validated_data["email_code"]
            verification = VerificationCode.objects.filter(
                type="email", purpose="register", target=email, code=code, is_used=False, expired_at__gt=timezone.now()
            ).first()

            if not verification:
                return Response({"email_code": "验证码无效"}, status=status.HTTP_400_BAD_REQUEST)

            # 创建用户
            user = serializer.save()
            verification.is_used = True
            verification.user = user
            verification.save()

            # 生成token
            refresh = RefreshToken.for_user(user)

            logger.info(f"User registered successfully: {user.username}")
            return Response(
                {
                    "user": UserSerializer(user).data,
                    "token": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            log_exception(e, logger, request)
            raise

    @log_timing(message="User login completed")
    @action(methods=["post"], detail=False)
    def login(self, request):
        """用户登录"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = serializer.validated_data["user"]

            # 记录登录历史
            LoginHistory.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                status=True,
            )

            # 更新用户最后登录信息
            user.last_login = timezone.now()
            user.last_login_ip = get_client_ip(request)
            user.last_login_user_agent = request.META.get("HTTP_USER_AGENT", "")
            user.save()

            # 生成token
            refresh = RefreshToken.for_user(user)

            logger.info(f"User logged in successfully: {user.username}")
            return Response(
                {
                    "user": UserSerializer(user).data,
                    "token": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                }
            )
        except Exception as e:
            log_exception(e, logger, request)
            raise

    @log_timing(message="Password change completed")
    @action(methods=["post"], detail=False, permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """修改密码"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = request.user
            if not user.check_password(serializer.validated_data["old_password"]):
                return Response({"old_password": "原密码错误"}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data["new_password"])
            user.save()

            logger.info(f"Password changed successfully for user: {user.username}")
            return Response({"message": _("密码修改成功")})
        except Exception as e:
            log_exception(e, logger, request)
            raise

    @log_timing(message="Password reset completed")
    @action(methods=["post"], detail=False)
    def reset_password(self, request):
        """重置密码"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # 验证邮箱验证码
            email = serializer.validated_data["email"]
            code = serializer.validated_data["code"]
            verification = VerificationCode.objects.filter(
                type="email",
                purpose="reset_password",
                target=email,
                code=code,
                is_used=False,
                expired_at__gt=timezone.now(),
            ).first()

            if not verification:
                return Response({"code": "验证码无效"}, status=status.HTTP_400_BAD_REQUEST)

            # 重置密码
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"email": "用户不存在"}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(serializer.validated_data["new_password"])
            user.save()

            verification.is_used = True
            verification.user = user
            verification.save()

            logger.info(f"Password reset successfully for user: {user.username}")
            return Response({"message": _("密码重置成功")})
        except Exception as e:
            log_exception(e, logger, request)
            raise

    @log_timing(message="Verification code sent")
    @action(methods=["post"], detail=False)
    def send_code(self, request):
        """发送验证码"""
        try:
            type = request.data.get("type")
            purpose = request.data.get("purpose")
            target = request.data.get("target")

            if not all([type, purpose, target]):
                return Response({"message": "参数不完整"}, status=status.HTTP_400_BAD_REQUEST)

            # 检查发送频率
            last_code = VerificationCode.objects.filter(
                type=type, purpose=purpose, target=target, created_at__gt=timezone.now() - timedelta(minutes=1)
            ).first()

            if last_code:
                return Response({"message": "发送太频繁，请稍后再试"}, status=status.HTTP_400_BAD_REQUEST)

            # 生成验证码
            code = "".join([str(random.randint(0, 9)) for _ in range(6)])
            expired_at = timezone.now() + timedelta(minutes=5)

            verification = VerificationCode.objects.create(
                type=type, purpose=purpose, target=target, code=code, expired_at=expired_at
            )

            # 发送验证码
            if type == "email":
                # TODO: 发送邮件
                pass
            elif type == "sms":
                # TODO: 发送短信
                pass

            logger.info(f"Verification code sent successfully: {target}")
            return Response({"message": _("验证码已发送")})
        except Exception as e:
            log_exception(e, logger, request)
            raise

    @log_timing(message="MFA QR code generated")
    @action(methods=["get"], detail=False, permission_classes=[IsAuthenticated])
    def mfa_qr(self, request):
        """获取MFA二维码"""
        try:
            user = request.user
            if not user.mfa_secret:
                user.generate_mfa_secret()
                user.save()

            qr_url = user.get_mfa_qr_url()
            logger.info(f"MFA QR code generated for user: {user.username}")
            return Response({"qr_url": qr_url, "secret": user.mfa_secret})
        except Exception as e:
            log_exception(e, logger, request)
            raise

    @log_timing(message="MFA verification completed")
    @action(methods=["post"], detail=False, permission_classes=[IsAuthenticated])
    def verify_mfa(self, request):
        """验证MFA"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user = request.user
            user.is_mfa_enabled = True
            user.save()

            logger.info(f"MFA enabled for user: {user.username}")
            return Response({"message": _("MFA已启用")})
        except Exception as e:
            log_exception(e, logger, request)
            raise
