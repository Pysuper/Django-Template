"""
Database Configuration Module

This module contains all database-related settings including connection pools,
routers, and database mappings.
"""

from pathlib import Path
from environs import Env

# This assumes env is already initialized in the parent module
# Import ROOT_DIR from the calling context

env = Env()


def get_database_config(root_dir: Path, debug: bool = False) -> dict:
    """
    Get database configuration.

    Args:
        root_dir: The root directory of the project
        debug: Whether debug mode is enabled

    Returns:
        Dictionary containing database configuration
    """

    databases = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": env.str("MYSQL_DATABASE", default="django_db"),
            "USER": env.str("MYSQL_USER", default="root"),
            "PASSWORD": env.str("MYSQL_PASSWORD", default="root"),
            "HOST": env.str("MYSQL_HOST", default="localhost"),
            "PORT": env.str("MYSQL_PORT", default="3306"),
            "CONN_MAX_AGE": env.int("MYSQL_CONN_MAX_AGE", default=60 * 60 * 6),
            "ATOMIC_REQUESTS": True,
            "OPTIONS": {
                "init_command": 'SET sql_mode="STRICT_TRANS_TABLES"',
                "charset": "utf8mb4",
                "use_unicode": True,
                "sql_mode": "traditional",
            },
            "POOL": {
                "name": "default",
                "max_size": env.int("MYSQL_POOL_MAX_SIZE", default=20),
                "min_size": env.int("MYSQL_POOL_MIN_SIZE", default=5),
                "max_overflow": env.int("MYSQL_POOL_MAX_OVERFLOW", default=10),
                "timeout": env.int("MYSQL_POOL_TIMEOUT", default=30),
                "recycle": env.int("MYSQL_POOL_RECYCLE", default=3600),
                "echo": debug,
                "pre_ping": True,
            },
        }
    }

    # Custom database router
    database_routers = ["utils.router.db.DatabaseAppsRouter"]

    # Custom app to database mapping
    database_apps_mapping = {
        # example:
        # 'app_name': 'database_name',
        "indicator": "postkeeper",
    }

    # Default auto field set to BigAutoField
    default_auto_field = "django.db.models.BigAutoField"

    return {
        "DATABASES": databases,
        "DATABASE_ROUTERS": database_routers,
        "DATABASE_APPS_MAPPING": database_apps_mapping,
        "DEFAULT_AUTO_FIELD": default_auto_field,
    }
