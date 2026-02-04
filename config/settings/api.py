"""
API Configuration Module

This module contains Django REST Framework and API-related settings including
pagination, throttling, filters, and documentation.
"""

from rest_framework.settings import APISettings
from environs import Env

env = Env()


# REST Framework Configuration
REST_FRAMEWORK = {
    # Authentication
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Permissions
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Throttling
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env.str("DJANGO_THROTTLE_ANON", default="100/day"),
        "user": env.str("DJANGO_THROTTLE_USER", default="1000/day"),
    },
    # Pagination
    "DEFAULT_PAGINATION_CLASS": "utils.pagination.CustomPageNumberPagination",
    "PAGE_SIZE": env.int("DJANGO_PAGE_SIZE", default=10),
    # Filtering
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    # Rendering
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    # Parsers
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    # Versioning
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "VERSIONING_PARAM": "version",
    # Exception Handling
    "EXCEPTION_HANDLER": "utils.exception.custom_exception_handler",
    # Schema
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# API Documentation (drf-spectacular)
REST_FRAMEWORK_SETTINGS = APISettings(
    user_settings=REST_FRAMEWORK,
    defaults=None,
    import_strings=None,
)

SPECTACULAR_SETTINGS = {
    "TITLE": "Django API",
    "DESCRIPTION": "API documentation for Django application",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api",
    "SCHEMA_PATH_PREFIX_TRIM": True,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "Authentication", "description": "User authentication and authorization"},
        {"name": "Users", "description": "User management"},
    ],
    "SERVERS": [
        {"url": "http://localhost:8000", "description": "Local development server"},
        {"url": "https://api.example.com", "description": "Production server"},
    ],
}

# CORS Settings
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# API Versioning
API_VERSION = "v1"
API_PREFIX = "/api/v1"
