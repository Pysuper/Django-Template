import logging
import os
import socket
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import psutil
from celery.app.control import Control
from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from redis.exceptions import ConnectionError

from .cache import CacheManager
from .logging import log_timing

logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """健康状态数据类"""
    status: str
    message: str
    details: Dict[str, Any]
    timestamp: str = timezone.now().isoformat()

class HealthCheck:
    """健康检查类"""
    
    STATUS_OK = "ok"
    STATUS_WARNING = "warning"
    STATUS_ERROR = "error"
    
    def __init__(self):
        self.cache_manager = CacheManager(prefix="health")
        
    @log_timing()
    def check_database(self) -> Tuple[str, str, Dict[str, Any]]:
        """检查数据库连接"""
        try:
            for alias in connections:
                connections[alias].cursor().execute("SELECT 1")
            return self.STATUS_OK, "Database is healthy", {}
        except Exception as e:
            logger.error("Database health check failed", exc_info=True)
            return self.STATUS_ERROR, f"Database error: {str(e)}", {"error": str(e)}
            
    @log_timing()
    def check_cache(self) -> Tuple[str, str, Dict[str, Any]]:
        """检查缓存服务"""
        try:
            test_key = "health_check_test"
            cache.set(test_key, "test", 10)
            cache.get(test_key)
            cache.delete(test_key)
            return self.STATUS_OK, "Cache is healthy", {}
        except ConnectionError as e:
            logger.error("Cache health check failed", exc_info=True)
            return self.STATUS_ERROR, f"Cache error: {str(e)}", {"error": str(e)}
            
    @log_timing()
    def check_celery(self) -> Tuple[str, str, Dict[str, Any]]:
        """检查Celery服务"""
        try:
            from celery.app import current_app
            control = Control(current_app)
            workers = control.ping()
            
            if not workers:
                return self.STATUS_WARNING, "No Celery workers found", {}
                
            active_workers = [w for w in workers if w]
            return (
                self.STATUS_OK,
                f"Found {len(active_workers)} active workers",
                {"workers": active_workers}
            )
        except Exception as e:
            logger.error("Celery health check failed", exc_info=True)
            return self.STATUS_ERROR, f"Celery error: {str(e)}", {"error": str(e)}
            
    @log_timing()
    def check_system(self) -> Tuple[str, str, Dict[str, Any]]:
        """检查系统资源"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage("/")
            disk_percent = disk.percent
            
            details = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "hostname": socket.gethostname(),
                "pid": os.getpid(),
            }
            
            # 判断状态
            status = self.STATUS_OK
            message = "System resources are healthy"
            
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = self.STATUS_WARNING
                message = "High resource usage detected"
                
            return status, message, details
        except Exception as e:
            logger.error("System health check failed", exc_info=True)
            return self.STATUS_ERROR, f"System error: {str(e)}", {"error": str(e)}
            
    @log_timing()
    def check_redis(self) -> Tuple[str, str, Dict[str, Any]]:
        """检查Redis服务"""
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            redis_info = redis_conn.info()
            
            # 检查内存使用率
            memory_percent = (
                redis_info["used_memory"] / redis_info["maxmemory"] * 100
                if "maxmemory" in redis_info and redis_info["maxmemory"] > 0
                else 0
            )
            
            details = {
                "version": redis_info["redis_version"],
                "memory_percent": memory_percent,
                "connected_clients": redis_info["connected_clients"],
                "uptime_days": redis_info["uptime_in_days"],
            }
            
            status = self.STATUS_OK
            message = "Redis is healthy"
            
            if memory_percent > 90:
                status = self.STATUS_WARNING
                message = "High Redis memory usage"
                
            return status, message, details
        except Exception as e:
            logger.error("Redis health check failed", exc_info=True)
            return self.STATUS_ERROR, f"Redis error: {str(e)}", {"error": str(e)}
            
    def get_status(self) -> HealthStatus:
        """获取整体健康状态"""
        checks = {
            "database": self.check_database(),
            "cache": self.check_cache(),
            "celery": self.check_celery(),
            "system": self.check_system(),
            "redis": self.check_redis(),
        }
        
        # 汇总状态
        overall_status = self.STATUS_OK
        messages = []
        details = {}
        
        for service, (status, message, service_details) in checks.items():
            details[service] = {
                "status": status,
                "message": message,
                "details": service_details,
            }
            
            if status == self.STATUS_ERROR:
                overall_status = self.STATUS_ERROR
                messages.append(f"{service}: {message}")
            elif status == self.STATUS_WARNING and overall_status != self.STATUS_ERROR:
                overall_status = self.STATUS_WARNING
                messages.append(f"{service}: {message}")
                
        return HealthStatus(
            status=overall_status,
            message=" | ".join(messages) if messages else "All systems are healthy",
            details=details,
        )

class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.cache_manager = CacheManager(prefix="metrics")
        
    def collect_request_metrics(self, request: HttpRequest, response_time: float) -> None:
        """收集请求指标"""
        metrics_key = f"request_metrics:{timezone.now().strftime('%Y-%m-%d:%H')}"
        
        # 获取当前指标
        metrics = self.cache_manager.get(metrics_key, {})
        
        # 更新指标
        path = request.path
        metrics.setdefault(path, {
            "count": 0,
            "total_time": 0,
            "avg_time": 0,
            "status_codes": {},
        })
        
        metrics[path]["count"] += 1
        metrics[path]["total_time"] += response_time
        metrics[path]["avg_time"] = (
            metrics[path]["total_time"] / metrics[path]["count"]
        )
        
        status_code = str(getattr(response, "status_code", 500))
        metrics[path]["status_codes"][status_code] = (
            metrics[path]["status_codes"].get(status_code, 0) + 1
        )
        
        # 保存指标
        self.cache_manager.set(metrics_key, metrics, timeout=3600 * 24)
        
    def collect_system_metrics(self) -> None:
        """收集系统指标"""
        metrics_key = f"system_metrics:{timezone.now().strftime('%Y-%m-%d:%H')}"
        
        # 收集系统指标
        metrics = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory": dict(psutil.virtual_memory()._asdict()),
            "disk": dict(psutil.disk_usage("/")._asdict()),
            "network": dict(psutil.net_io_counters()._asdict()),
            "timestamp": timezone.now().isoformat(),
        }
        
        # 保存指标
        self.cache_manager.set(metrics_key, metrics, timeout=3600 * 24)
        
    def get_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """获取指标数据"""
        metrics = {
            "request_metrics": {},
            "system_metrics": [],
        }
        
        # 获取时间范围
        now = timezone.now()
        for i in range(hours):
            hour = now - timezone.timedelta(hours=i)
            hour_str = hour.strftime("%Y-%m-%d:%H")
            
            # 获���请求指标
            request_key = f"request_metrics:{hour_str}"
            request_metrics = self.cache_manager.get(request_key, {})
            for path, data in request_metrics.items():
                metrics["request_metrics"].setdefault(path, {
                    "count": 0,
                    "total_time": 0,
                    "avg_time": 0,
                    "status_codes": {},
                })
                path_metrics = metrics["request_metrics"][path]
                path_metrics["count"] += data["count"]
                path_metrics["total_time"] += data["total_time"]
                path_metrics["avg_time"] = (
                    path_metrics["total_time"] / path_metrics["count"]
                )
                for status_code, count in data["status_codes"].items():
                    path_metrics["status_codes"][status_code] = (
                        path_metrics["status_codes"].get(status_code, 0) + count
                    )
                    
            # 获取系统指标
            system_key = f"system_metrics:{hour_str}"
            system_metrics = self.cache_manager.get(system_key)
            if system_metrics:
                metrics["system_metrics"].append(system_metrics)
                
        return metrics

def health_check_view(request: HttpRequest) -> JsonResponse:
    """健康检查视图"""
    health_checker = HealthCheck()
    status = health_checker.get_status()
    
    return JsonResponse({
        "status": status.status,
        "message": status.message,
        "details": status.details,
        "timestamp": status.timestamp,
    })

def metrics_view(request: HttpRequest) -> JsonResponse:
    """指标视图"""
    hours = int(request.GET.get("hours", 24))
    collector = MetricsCollector()
    metrics = collector.get_metrics(hours=hours)
    
    return JsonResponse({
        "metrics": metrics,
        "timestamp": timezone.now().isoformat(),
    })

# 使用示例
"""
# 1. 在urls.py中添加健康检查和指标路由
urlpatterns = [
    path("health/", health_check_view, name="health_check"),
    path("metrics/", metrics_view, name="metrics"),
]

# 2. 在中间件中收集请求指标
class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.collector = MetricsCollector()
        
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        response_time = time.time() - start_time
        
        self.collector.collect_request_metrics(request, response_time)
        return response

# 3. 在Celery任务中收集系统指标
@periodic_task(run_every=timedelta(minutes=5))
def collect_system_metrics():
    collector = MetricsCollector()
    collector.collect_system_metrics()
""" 