"""
Security Configuration Module

This module contains all security-related settings for the Django application.
Centralized security management makes it easier to audit and maintain security practices.
"""

from django.core.exceptions import ImproperlyConfigured
from environs import Env

env = Env()


# Password Validation
# ------------------------------------------------------------------------------
# Django's built-in password validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": env.int("DJANGO_PASSWORD_MIN_LENGTH", default=8),
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Custom password policy configuration
PASSWORD_POLICY = {
    "min_length": env.int("PASSWORD_POLICY_MIN_LENGTH", default=8),
    "max_length": env.int("PASSWORD_POLICY_MAX_LENGTH", default=128),
    "require_uppercase": env.bool("PASSWORD_POLICY_REQUIRE_UPPERCASE", default=True),
    "require_lowercase": env.bool("PASSWORD_POLICY_REQUIRE_LOWERCASE", default=True),
    "require_digits": env.bool("PASSWORD_POLICY_REQUIRE_DIGITS", default=True),
    "require_special": env.bool("PASSWORD_POLICY_REQUIRE_SPECIAL", default=True),
    "special_chars": env.str(
        "PASSWORD_POLICY_SPECIAL_CHARS",
        default="!@#$%^&*()_+-=[]{}|;:,.<>?"
    ),
    "password_history": env.int("PASSWORD_POLICY_HISTORY", default=5),
    "password_expire_days": env.int("PASSWORD_POLICY_EXPIRE_DAYS", default=90),
}

# Session Security
# ------------------------------------------------------------------------------
SESSION_POLICY = {
    "session_timeout": env.int("SESSION_TIMEOUT", default=1800),  # 30 minutes
    "max_sessions": env.int("SESSION_MAX_COUNT", default=5),
    "allow_concurrent": env.bool("SESSION_ALLOW_CONCURRENT", default=True),
}

# Login Attempt Policy
# ------------------------------------------------------------------------------
LOGIN_ATTEMPT_POLICY = {
    "max_attempts": env.int("LOGIN_MAX_ATTEMPTS", default=5),
    "lockout_time": env.int("LOGIN_LOCKOUT_TIME", default=300),  # 5 minutes
    "reset_time": env.int("LOGIN_RESET_TIME", default=3600),  # 1 hour
}

# Security Headers (HTTPS)
# ------------------------------------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS Settings
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=2592000)  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True
)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=True)

# Cookie Security
# ------------------------------------------------------------------------------
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=False)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env.str(
    "DJANGO_SESSION_COOKIE_SAMESITE",
    default="Lax"
)

CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=False)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = env.str(
    "DJANGO_CSRF_COOKIE_SAMESITE",
    default="Lax"
)
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=[]
)

# Content Security
# ------------------------------------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# Secret Key
# ------------------------------------------------------------------------------
def get_secret_key():
    """Get the secret key from environment or raise an error in production."""
    secret_key = env.str("DJANGO_SECRET_KEY", default=None)

    if not secret_key:
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY must be set in environment variables. "
            "Generate one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
        )

    return secret_key


# Security Middleware Settings
# ------------------------------------------------------------------------------
SECURE_REFERRER_POLICY = env.str(
    "DJANGO_SECURE_REFERRER_POLICY",
    default="strict-origin-when-cross-origin"
)


# Validation Functions
# ------------------------------------------------------------------------------
def validate_security_settings(debug: bool = False):
    """
    Validate that security settings are properly configured.

    Raises ImproperlyConfigured if security settings are invalid for production.
    """
    errors = []

    if not debug:
        # Production security checks
        if env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False) is False:
            errors.append(
                "SSL redirect should be enabled in production. "
                "Set DJANGO_SECURE_SSL_REDIRECT=True"
            )

        if env.bool("DJANGO_SESSION_COOKIE_SECURE", default=False) is False:
            errors.append(
                "Session cookies should be secure in production. "
                "Set DJANGO_SESSION_COOKIE_SECURE=True"
            )

        if env.bool("DJANGO_CSRF_COOKIE_SECURE", default=False) is False:
            errors.append(
                "CSRF cookies should be secure in production. "
                "Set DJANGO_CSRF_COOKIE_SECURE=True"
            )

    if errors:
        raise ImproperlyConfigured(
            "Security configuration errors:\n" + "\n".join(f"- {e}" for e in errors)
        )


# Data Masking Configuration
# ------------------------------------------------------------------------------
SENSITIVE_FIELDS = [
    "password",
    "secret",
    "token",
    "key",
    "auth",
    "credit_card",
    "card_number",
    "ssn",
    "social_security",
]

SENSITIVE_DATA_MASK = "******"
