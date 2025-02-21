import datetime
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, TypeVar, Union, cast

import psutil
from django.conf import settings
from django.core.mail import mail_admins
from django.core.management import call_command
from django.db import connections
from django.utils import timezone

from .cache import CacheManager
from .logging import log_timing

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Callable[..., Any])

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        # 加载配置
        self.config = getattr(settings, "MONITOR_CONFIG", {})
        
        # 告警阈值
        self.thresholds = self.config.get("THRESHOLDS", {
            "cpu_percent": 80,
            "memory_percent": 80,
            "disk_percent": 80,
            "connection_count": 1000,
            "response_time": 1.0,
        })
        
        # 检查间隔（秒）
        self.check_interval = self.config.get("CHECK_INTERVAL", 60)
        
        # ���存管理器
        self.cache_manager = CacheManager(prefix="monitor")
        
    def check_system(self) -> Dict[str, Any]:
        """检查系统状态"""
        status = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "connection_count": len(psutil.net_connections()),
            "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()),
            "processes": len(psutil.pids()),
        }
        
        # 记录状态
        self.cache_manager.set(
            f"system_status:{timezone.now().isoformat()}",
            status,
            timeout=86400
        )
        
        # 检查告警
        self._check_alerts(status)
        
        return status
        
    def check_database(self) -> Dict[str, Any]:
        """检查数据库状态"""
        status = {}
        
        for alias in connections:
            connection = connections[alias]
            with connection.cursor() as cursor:
                # 检查连接
                cursor.execute("SELECT 1")
                
                # 获取数据库状态
                if connection.vendor == "postgresql":
                    cursor.execute("""
                        SELECT
                            count(*) as connection_count,
                            max(now() - xact_start) as max_transaction_time,
                            max(now() - query_start) as max_query_time
                        FROM pg_stat_activity
                        WHERE state != 'idle'
                    """)
                    row = cursor.fetchone()
                    status[alias] = {
                        "connection_count": row[0],
                        "max_transaction_time": row[1],
                        "max_query_time": row[2],
                    }
                elif connection.vendor == "mysql":
                    cursor.execute("SHOW STATUS")
                    rows = cursor.fetchall()
                    status[alias] = dict(rows)
                    
        # 记录状态
        self.cache_manager.set(
            f"database_status:{timezone.now().isoformat()}",
            status,
            timeout=86400
        )
        
        return status
        
    def check_cache(self) -> Dict[str, Any]:
        """检查缓存状态"""
        status = {}
        
        # 检查Redis
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection("default")
            info = redis.info()
            status["redis"] = {
                "used_memory": info["used_memory"],
                "used_memory_peak": info["used_memory_peak"],
                "connected_clients": info["connected_clients"],
                "uptime_in_seconds": info["uptime_in_seconds"],
            }
        except Exception as e:
            logger.error(f"Redis check failed: {e}")
            status["redis"] = {"error": str(e)}
            
        # 记录状态
        self.cache_manager.set(
            f"cache_status:{timezone.now().isoformat()}",
            status,
            timeout=86400
        )
        
        return status
        
    def check_celery(self) -> Dict[str, Any]:
        """检查Celery状态"""
        status = {}
        
        try:
            from celery.app import current_app
            
            # 获取队列状态
            inspect = current_app.control.inspect()
            status.update({
                "active": inspect.active() or {},
                "reserved": inspect.reserved() or {},
                "scheduled": inspect.scheduled() or {},
            })
            
            # 获取工作节点
            status["workers"] = []
            for worker in current_app.control.ping() or []:
                status["workers"].append({
                    "name": worker["name"],
                    "status": "online",
                })
        except Exception as e:
            logger.error(f"Celery check failed: {e}")
            status["error"] = str(e)
            
        # 记录状态
        self.cache_manager.set(
            f"celery_status:{timezone.now().isoformat()}",
            status,
            timeout=86400
        )
        
        return status
        
    def _check_alerts(self, status: Dict[str, Any]) -> None:
        """检查告警"""
        alerts = []
        
        # 检查CPU使用率
        if status["cpu_percent"] > self.thresholds["cpu_percent"]:
            alerts.append(
                f"CPU使用率过高: {status['cpu_percent']}%"
            )
            
        # 检查内存使用率
        if status["memory_percent"] > self.thresholds["memory_percent"]:
            alerts.append(
                f"内存使用率过高: {status['memory_percent']}%"
            )
            
        # 检查磁盘使用率
        if status["disk_percent"] > self.thresholds["disk_percent"]:
            alerts.append(
                f"磁盘使用率过高: {status['disk_percent']}%"
            )
            
        # 检查连接数
        if status["connection_count"] > self.thresholds["connection_count"]:
            alerts.append(
                f"连接数过多: {status['connection_count']}"
            )
            
        # 发送告警
        if alerts:
            self._send_alert("\n".join(alerts))
            
    def _send_alert(self, message: str) -> None:
        """发送告警"""
        logger.error(f"System alert: {message}")
        
        # 发送邮件
        mail_admins(
            "系统告警",
            message,
            fail_silently=True
        )
        
        # 记录告警
        self.cache_manager.set(
            f"alert:{timezone.now().isoformat()}",
            message,
            timeout=86400
        )

class BackupManager:
    """备份管理器"""
    
    def __init__(self):
        # 加载配置
        self.config = getattr(settings, "BACKUP_CONFIG", {})
        
        # 备份目录
        self.backup_dir = Path(self.config.get(
            "BACKUP_DIR",
            settings.BASE_DIR / "backups"
        ))
        
        # 保留天数
        self.retention_days = self.config.get("RETENTION_DAYS", 30)
        
        # 压缩级别
        self.compression_level = self.config.get("COMPRESSION_LEVEL", 6)
        
        # 创建备份目录
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def backup_database(self) -> Path:
        """备份数据库"""
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        
        for alias in connections:
            connection = connections[alias]
            
            # 获取数据库配置
            db_settings = settings.DATABASES[alias]
            
            # 创建备份文件
            backup_file = self.backup_dir / f"{alias}_{timestamp}.sql"
            
            if connection.vendor == "postgresql":
                # PostgreSQL备份
                env = os.environ.copy()
                env["PGPASSWORD"] = db_settings["PASSWORD"]
                
                subprocess.run([
                    "pg_dump",
                    "-h", db_settings["HOST"],
                    "-p", str(db_settings["PORT"]),
                    "-U", db_settings["USER"],
                    "-d", db_settings["NAME"],
                    "-f", str(backup_file),
                ], env=env, check=True)
            elif connection.vendor == "mysql":
                # MySQL备份
                subprocess.run([
                    "mysqldump",
                    "-h", db_settings["HOST"],
                    "-P", str(db_settings["PORT"]),
                    "-u", db_settings["USER"],
                    f"-p{db_settings['PASSWORD']}",
                    db_settings["NAME"],
                    "-r", str(backup_file),
                ], check=True)
                
            # 压缩备份文件
            import gzip
            with open(backup_file, "rb") as f_in:
                with gzip.open(f"{backup_file}.gz", "wb", self.compression_level) as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    
            # 删除未压缩文件
            backup_file.unlink()
            
            logger.info(f"Database backup created: {backup_file}.gz")
            
        return backup_file
        
    def backup_media(self) -> Path:
        """备份媒体文件"""
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        media_dir = Path(settings.MEDIA_ROOT)
        
        # 创建备份文件
        backup_file = self.backup_dir / f"media_{timestamp}.tar.gz"
        
        # 压缩媒体文件
        subprocess.run([
            "tar",
            "-czf",
            str(backup_file),
            "-C",
            str(media_dir.parent),
            media_dir.name,
        ], check=True)
        
        logger.info(f"Media backup created: {backup_file}")
        
        return backup_file
        
    def cleanup_old_backups(self) -> None:
        """清理旧备份"""
        cutoff_date = timezone.now() - datetime.timedelta(
            days=self.retention_days
        )
        
        for backup_file in self.backup_dir.glob("*"):
            # 获取文件时间戳
            try:
                timestamp = datetime.datetime.strptime(
                    backup_file.stem.split("_")[1],
                    "%Y%m%d_%H%M%S"
                )
                
                # 删除过期文件
                if timestamp < cutoff_date:
                    backup_file.unlink()
                    logger.info(f"Deleted old backup: {backup_file}")
            except (IndexError, ValueError):
                continue

class DeploymentManager:
    """部署管理器"""
    
    def __init__(self):
        # 加载配置
        self.config = getattr(settings, "DEPLOYMENT_CONFIG", {})
        
        # 项目目录
        self.project_dir = Path(settings.BASE_DIR)
        
        # 静态文件目录
        self.static_dir = Path(settings.STATIC_ROOT)
        
        # 媒体文件目录
        self.media_dir = Path(settings.MEDIA_ROOT)
        
    def collect_static(self) -> None:
        """收集静态文件"""
        call_command("collectstatic", interactive=False)
        
    def migrate_database(self) -> None:
        """迁移数据库"""
        call_command("migrate")
        
    def create_cache_tables(self) -> None:
        """创建缓存表"""
        call_command("createcachetable")
        
    def compile_messages(self) -> None:
        """编译翻译文件"""
        call_command("compilemessages")
        
    def restart_services(self) -> None:
        """重启服务"""
        # 重启Gunicorn
        subprocess.run([
            "systemctl",
            "restart",
            "gunicorn",
        ], check=True)
        
        # 重启Celery
        subprocess.run([
            "systemctl",
            "restart",
            "celery",
        ], check=True)
        
        # 重启Celery Beat
        subprocess.run([
            "systemctl",
            "restart",
            "celerybeat",
        ], check=True)
        
    def check_services(self) -> Dict[str, bool]:
        """检查服务状态"""
        services = {
            "gunicorn": False,
            "celery": False,
            "celerybeat": False,
            "nginx": False,
            "redis": False,
            "postgresql": False,
        }
        
        for service in services:
            try:
                result = subprocess.run([
                    "systemctl",
                    "is-active",
                    service,
                ], capture_output=True, text=True)
                services[service] = result.stdout.strip() == "active"
            except subprocess.CalledProcessError:
                continue
                
        return services

# 使用示例
"""
# 1. 系统监控
monitor = SystemMonitor()

# 检查系统状态
system_status = monitor.check_system()
print(f"CPU使用率: {system_status['cpu_percent']}%")

# 检���数据库状态
db_status = monitor.check_database()
print(f"数据库连接数: {db_status['default']['connection_count']}")

# 检查缓存状态
cache_status = monitor.check_cache()
print(f"Redis内存使用: {cache_status['redis']['used_memory']}")

# 检查Celery状态
celery_status = monitor.check_celery()
print(f"活动任务数: {len(celery_status['active'])}")

# 2. 备份管理
backup = BackupManager()

# 备份数据库
db_backup = backup.backup_database()
print(f"数据库备份文件: {db_backup}")

# 备份媒体文件
media_backup = backup.backup_media()
print(f"媒体文件备份: {media_backup}")

# 清理旧备份
backup.cleanup_old_backups()

# 3. 部署管理
deployment = DeploymentManager()

# 部署流程
deployment.collect_static()
deployment.migrate_database()
deployment.create_cache_tables()
deployment.compile_messages()

# 重启服务
deployment.restart_services()

# 检查服务状态
service_status = deployment.check_services()
for service, is_active in service_status.items():
    print(f"{service}: {'运行中' if is_active else '已停止'}")
""" 