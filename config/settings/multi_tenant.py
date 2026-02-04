"""
多租户配置 / Multi-Tenancy Configuration

配置多租户系统的各项参数
"""

from .base import *

# =============================================================================
# 多租户设置 / Multi-Tenancy Settings
# =============================================================================

# 是否启用多租户 / Enable multi-tenancy
# 设置为False可关闭多租户功能，系统将作为单租户运行
# Set to False to disable multi-tenancy, system will run as single-tenant
MULTI_TENANT_ENABLED = env.bool('MULTI_TENANT_ENABLED', default=True)

# 是否必须识别租户 / Whether tenant identification is required
# 如果为True，所有请求必须提供租户信息
# If True, all requests must provide tenant information
MULTI_TENANT_REQUIRED = env.bool('MULTI_TENANT_REQUIRED', default=False)

# 租户识别方式 / Tenant identification methods
# 可以通过以下方式之一识别租户：
# - subdomain: 通过子域名 (tenant.example.com)
# - header: 通过HTTP头 (X-Tenant-Code)
# - query: 通过查询参数 (?tenant=code)
TENANT_IDENTIFICATION = env.list(
    'TENANT_IDENTIFICATION',
    default=['subdomain', 'header', 'query']
)

# 默认租户代码 / Default tenant code
# 当无法识别租户时使用的默认租户
# Default tenant to use when tenant cannot be identified
DEFAULT_TENANT_CODE = env('DEFAULT_TENANT_CODE', default='default')

# 租户隔离排除的路径 / Tenant isolation exclusion paths
# 这些路径不受租户隔离限制
# These paths are not subject to tenant isolation
TENANT_ISOLATION_EXCLUDE_PATHS = [
    '/admin/',
    '/health/',
    '/metrics/',
    '/api/v1/health/',
    '/api/v1/auth/login',
]

# =============================================================================
# 租户默认设置 / Tenant Default Settings
# =============================================================================

# 租户默认最大用户数 / Default maximum users per tenant
DEFAULT_MAX_USERS = env.int('DEFAULT_MAX_USERS', default=100)

# 租户默认过期天数 / Default expiration days for tenant
# 0表示永不过期 / 0 means never expire
DEFAULT_TENANT_EXPIRE_DAYS = env.int('DEFAULT_TENANT_EXPIRE_DAYS', default=0)

# 新租户默认角色代码 / Default role code for new tenant
DEFAULT_TENANT_ROLE_CODE = env('DEFAULT_TENANT_ROLE_CODE', default='user')

# =============================================================================
# RBAC设置 / RBAC Settings
# =============================================================================

# 是否启用RBAC / Enable RBAC
RBAC_ENABLED = env.bool('RBAC_ENABLED', default=True)

# 权限缓存时间 / Permission cache time (seconds)
PERMISSION_CACHE_TIMEOUT = env.int('PERMISSION_CACHE_TIMEOUT', default=3600)

# 是否启用数据范围控制 / Enable data scope control
DATA_SCOPE_ENABLED = env.bool('DATA_SCOPE_ENABLED', default=True)

# 默认数据范围 / Default data scope
# - all: 全部数据 / All data
# - dept_and_sub: 本部门及子部门数据 / Department and sub-department data
# - dept: 本部门数据 / Department data
# - self: 仅本人数据 / Self data only
DEFAULT_DATA_SCOPE = env('DEFAULT_DATA_SCOPE', default='self')

# =============================================================================
# 菜单和按钮权限 / Menu and Button Permissions
# =============================================================================

# 是否启用菜单权限 / Enable menu permissions
MENU_PERMISSION_ENABLED = env.bool('MENU_PERMISSION_ENABLED', default=True)

# 是否启用按钮权限 / Enable button permissions
BUTTON_PERMISSION_ENABLED = env.bool('BUTTON_PERMISSION_ENABLED', default=True)

# 全局菜单（所有租户可见） / Global menus (visible to all tenants)
# 菜单的tenant字段为null的菜单为全局菜单
# Menus with null tenant field are global menus

# =============================================================================
# 安全设置 / Security Settings
# =============================================================================

# 是否允许跨租户访问（仅超级管理员） / Allow cross-tenant access (superuser only)
ALLOW_CROSS_TENANT_ACCESS = env.bool('ALLOW_CROSS_TENANT_ACCESS', default=False)

# 租户会话隔离 / Tenant session isolation
# 如果为True，用户只能在其租户的会话中操作
# If True, users can only operate within their tenant's session
TENANT_SESSION_ISOLATION = env.bool('TENANT_SESSION_ISOLATION', default=True)

# =============================================================================
# 租户配额 / Tenant Quotas
# =============================================================================

# 每个租户最大角色数 / Maximum roles per tenant
MAX_ROLES_PER_TENANT = env.int('MAX_ROLES_PER_TENANT', default=50)

# 每个租户最大菜单数 / Maximum menus per tenant
MAX_MENUS_PER_TENANT = env.int('MAX_MENUS_PER_TENANT', default=200)

# 每个租户最大权限数 / Maximum permissions per tenant
MAX_PERMISSIONS_PER_TENANT = env.int('MAX_PERMISSIONS_PER_TENANT', default=500)

# 每个用户最大角色数 / Maximum roles per user
MAX_ROLES_PER_USER = env.int('MAX_ROLES_PER_USER', default=10)

# =============================================================================
# 日志和审计 / Logging and Auditing
# =============================================================================

# 是否记录租户操作日志 / Log tenant operations
LOG_TENANT_OPERATIONS = env.bool('LOG_TENANT_OPERATIONS', default=True)

# 是否记录权限检查失败 / Log permission check failures
LOG_PERMISSION_FAILURES = env.bool('LOG_PERMISSION_FAILURES', default=True)

# =============================================================================
# 性能优化 / Performance Optimization
# =============================================================================

# 是否启用租户缓存 / Enable tenant caching
TENANT_CACHE_ENABLED = env.bool('TENANT_CACHE_ENABLED', default=True)

# 租户缓存时间 / Tenant cache time (seconds)
TENANT_CACHE_TIMEOUT = env.int('TENANT_CACHE_TIMEOUT', default=3600)

# 是否启用权限缓存 / Enable permission caching
PERMISSION_CACHE_ENABLED = env.bool('PERMISSION_CACHE_ENABLED', default=True)

# =============================================================================
# 租户创建限制 / Tenant Creation Restrictions
# =============================================================================

# 是否允许自动创建租户 / Allow automatic tenant creation
ALLOW_AUTO_TENANT_CREATION = env.bool('ALLOW_AUTO_TENANT_CREATION', default=False)

# 租户代码保留字 / Reserved tenant codes
# 这些代码不能用于创建租户
RESERVED_TENANT_CODES = [
    'www',
    'api',
    'admin',
    'system',
    'root',
    'superuser',
    'test',
]

# =============================================================================
# 示例配置 / Example Configuration
# =============================================================================

# .env.example 文件中应该包含：
# The .env.example file should include:
#
# # Multi-Tenancy
# MULTI_TENANT_ENABLED=True
# MULTI_TENANT_REQUIRED=False
# DEFAULT_MAX_USERS=100
#
# # RBAC
# RBAC_ENABLED=True
# DATA_SCOPE_ENABLED=True
# DEFAULT_DATA_SCOPE=self
# PERMISSION_CACHE_TIMEOUT=3600
