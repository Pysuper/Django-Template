"""
Email Configuration Module

This module contains all email-related settings including SMTP configuration
and email backend settings.
"""

from environs import Env

env = Env()


# Email Backend
EMAIL_BACKEND = env.str(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend"
)

# SMTP Configuration
EMAIL_HOST = env.str("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)

# Email Authentication
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD", default="")

# Email Settings
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=5)
EMAIL_SUBJECT_PREFIX = env.str("EMAIL_SUBJECT_PREFIX", default="[Django] ")
EMAIL_FROM = env.str("EMAIL_FROM", default="noreply@example.com")
ADMIN_EMAIL = env.str("ADMIN_EMAIL", default="admin@example.com")

# Server Email
SERVER_EMAIL = env.str("SERVER_EMAIL", default="server@example.com")

# Email Console Backend (for development)
if env.bool("EMAIL_CONSOLE_BACKEND", default=False):
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Aliyun SMS Configuration
ALIYUN_SMS = {
    "ACCESS_KEY_ID": env.str("ALI_SMS_ACCESS_KEY_ID", default=""),
    "ACCESS_KEY_SECRET": env.str("ALI_SMS_ACCESS_KEY_SECRET", default=""),
    "REGION_ID": env.str("ALI_SMS_REGION_ID", default="cn-hangzhou"),
    "ENDPOINT": env.str("ALI_SMS_ENDPOINT", default="dysmsapi.aliyuncs.com"),
    "SIGN_NAME": env.str("ALI_SMS_SIGN_NAME", default=""),
    "TEMPLATE_CODE": env.str("ALI_SMS_CODE_TEMPLATE", default=""),
}

# SMS Code Configuration
SMS_CODE_EXPIRE = env.int("SMS_CODE_EXPIRE", default=600)  # 10 minutes
SMS_CODE_LENGTH = env.int("SMS_CODE_LENGTH", default=6)

# Verification Code Configuration
LOGIN_CODE_TYPE = env.str("LOGIN_CODE_TYPE", default="ARITHMETIC")  # ARITHMETIC or CHINESE
LOGIN_CODE_LENGTH = env.int("LOGIN_CODE_LENGTH", default=4)
LOGIN_CODE_WIDTH = env.int("LOGIN_CODE_WIDTH", default=120)
LOGIN_CODE_HEIGHT = env.int("LOGIN_CODE_HEIGHT", default=40)
LOGIN_CODE_FONT_SIZE = env.int("LOGIN_CODE_FONT_SIZE", default=20)
EXPIRATION_DELTA = env.int("EXPIRATION_DELTA", default=2)
