"""
Authentication Configuration Module

This module contains authentication-related settings including user model,
authentication backends, and JWT configuration.
"""

from datetime import timedelta
from environs import Env

env = Env()


# Authentication Backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Custom User Model
AUTH_USER_MODEL = "users.User"

# Login URLs
LOGIN_REDIRECT_URL = "users:redirect"
LOGIN_URL = "account_login"
LOGOUT_REDIRECT_URL = "/"

# Password Hashers
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# JWT Configuration
JWT_AUTH = {
    "JWT_SECRET_KEY": env.str("DJANGO_BASE64_SECRET_KEY", default=""),
    "JWT_ALGORITHM": "HS256",
    "JWT_VERIFY": True,
    "JWT_VERIFY_EXPIRATION": True,
    "JWT_EXPIRATION_DELTA": timedelta(days=env.int("JWT_EXPIRATION_DELTA", default=100)),
    "JWT_REFRESH_EXPIRATION_DELTA": timedelta(days=30),
    "JWT_AUTH_HEADER_PREFIX": env.str("JWT_AUTH_HEADER_PREFIX", default="Bearer"),
    "JWT_ALLOW_REFRESH": True,
}

# Simple JWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("ACCESS_TOKEN_LIFETIME", default=150)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("REFRESH_TOKEN_LIFETIME", default=1)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env.str("DJANGO_BASE64_SECRET_KEY", default=""),
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "LEEWAY": 0,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=env.int("TOKEN_LIFETIME", default=3600)),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=env.int("TOKEN_RENEW_PERIOD", default=3600)),
    "TOKEN_DETECT_LIFETIME": timedelta(minutes=env.int("TOKEN_DETECT", default=1800)),
}

# Token Lifetime Settings
TOKEN_LIFETIME = env.int("TOKEN_LIFETIME", default=3600)
TOKEN_DETECT = env.int("TOKEN_DETECT", default=1800)
TOKEN_RENEW_PERIOD = env.int("TOKEN_RENEW_PERIOD", default=3600)

# Allauth Settings
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", default=True)
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_USERNAME_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_VERIFICATION = "none"

# MFA Settings
MFA_ENABLED = env.bool("MFA_ENABLED", default=False)
MFA_ISSUER_NAME = env.str("MFA_ISSUER_NAME", default="DjangoApp")
