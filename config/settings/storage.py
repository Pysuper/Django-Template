"""
Storage Configuration Module

This module contains static files, media files, and general storage settings.
"""

from pathlib import Path
from environs import Env

env = Env()


def get_storage_config(root_dir: Path) -> dict:
    """
    Get storage configuration for static and media files.

    Args:
        root_dir: The root directory of the project

    Returns:
        Dictionary containing storage configuration
    """

    # Static Files Configuration
    static_root = str(root_dir / "staticfiles")
    static_url = "/static/"
    staticfiles_dirs = [str(root_dir / "static")]

    staticfiles_finders = [
        "django.contrib.staticfiles.finders.FileSystemFinder",
        "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    ]

    # Media Files Configuration
    media_root = str(root_dir / "media")
    media_url = "/media/"

    # File Upload Settings
    file_upload_max_memory_size = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE", default=2_621_440)  # 2.5 MB
    file_upload_permissions = env.int("FILE_UPLOAD_PERMISSIONS", default=0o644)
    file_upload_directory_permissions = env.int("FILE_UPLOAD_DIRECTORY_PERMISSIONS", default=0o755)
    data_upload_max_memory_size = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE", default=2_621_440)

    return {
        "STATIC_ROOT": static_root,
        "STATIC_URL": static_url,
        "STATICFILES_DIRS": staticfiles_dirs,
        "STATICFILES_FINDERS": staticfiles_finders,
        "MEDIA_ROOT": media_root,
        "MEDIA_URL": media_url,
        "FILE_UPLOAD_MAX_MEMORY_SIZE": file_upload_max_memory_size,
        "FILE_UPLOAD_PERMISSIONS": file_upload_permissions,
        "FILE_UPLOAD_DIRECTORY_PERMISSIONS": file_upload_directory_permissions,
        "DATA_UPLOAD_MAX_MEMORY_SIZE": data_upload_max_memory_size,
    }
