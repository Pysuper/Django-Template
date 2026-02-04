# Security Guide / 安全指南

This document outlines security best practices and configurations for the Django application.

## Table of Contents / 目录

1. [Environment Variables / 环境变量](#environment-variables)
2. [Password Security / 密码安全](#password-security)
3. [API Security / API安全](#api-security)
4. [Database Security / 数据库安全](#database-security)
5. [Session Security / 会话安全](#session-security)
6. [File Upload Security / 文件上传安全](#file-upload-security)
8. [Dependencies / 依赖项](#dependencies)
9. [Deployment Security / 部署安全](#deployment-security)

## Environment Variables / 环境变量

### Required Security Variables / 必需的安全变量

```bash
# Generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
DJANGO_SECRET_KEY=<unique-random-string>

# Set to False in production / 生产环境设置为False
DJANGO_DEBUG=False

# Comma-separated list of allowed domains / 逗号分隔的允许域名列表
DJANGO_ALLOWED_HOSTS=example.com,www.example.com

# RSA password for encryption / RSA加密密码
DJANGO_RSA_PASSWORD=<strong-random-password>

# Default password for initial users / 初始用户默认密码
START_PASSWORD=<strong-default-password>
```

### Generating Secure Keys / 生成安全密钥

```bash
# Django Secret Key / Django密钥
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Or use secrets module / 或使用secrets模块
python -c 'import secrets; print(secrets.token_urlsafe(50))'
```

## Password Security / 密码安全

### Password Policy Configuration / 密码策略配置

The application enforces a strong password policy configured in `config/settings/security.py`:

```python
PASSWORD_POLICY = {
    "min_length": 8,                    # Minimum length / 最小长度
    "require_uppercase": True,          # Require uppercase / 需要大写字母
    "require_lowercase": True,          # Require lowercase / 需要小写字母
    "require_digits": True,             # Require digits / 需要数字
    "require_special": True,            # Require special chars / 需要特殊字符
    "password_history": 5,              # Remember last 5 passwords / 记住最近5次密码
    "password_expire_days": 90,         # Password expiration / 密码过期时间
}
```

### Password Hashers / 密码哈希

The application uses Argon2 as the primary password hasher:

```python
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",  # Best choice / 最佳选择
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
```

## API Security / API安全

### JWT Configuration / JWT配置

```python
# Access token lifetime: 150 minutes / 访问令牌生命周期
ACCESS_TOKEN_LIFETIME = 150

# Refresh token lifetime: 1 day / 刷新令牌生命周期
REFRESH_TOKEN_LIFETIME = 1

# Token blacklist enabled / 令牌黑名单已启用
BLACKLIST_AFTER_ROTATION = True
```

### Rate Limiting / 速率限制

```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",      # Anonymous users / 匿名用户
        "user": "1000/day",     # Authenticated users / 已认证用户
    }
}
```

### API Authentication / API认证

The application supports multiple authentication methods:

1. **JWT Authentication** (Recommended / 推荐)
   - Stateless
   - Scalable
   - Mobile-friendly

2. **Session Authentication**
   - For traditional web apps
   - CSRF protection enabled

## Database Security / 数据库安全

### Connection Security / 连接安全

```python
DATABASES = {
    "default": {
        # Use strong passwords / 使用强密码
        "PASSWORD": env.str("MYSQL_PASSWORD"),

        # Enable SSL in production / 生产环境启用SSL
        "OPTIONS": {
            "ssl": {
                "ca": "/path/to/ca-cert.pem",
                "cert": "/path/to/client-cert.pem",
                "key": "/path/to/client-key.pem",
            }
        }
    }
}
```

### SQL Injection Prevention / SQL注入防护

The application uses Django ORM which automatically prevents SQL injection:

```python
# ✅ SAFE - Django ORM handles escaping / 安全
User.objects.filter(username=user_input)

# ❌ UNSAFE - Never use raw SQL with user input / 不安全
cursor.execute(f"SELECT * FROM users WHERE username = '{user_input}'")
```

## Session Security / 会话安全

### Session Configuration / 会话配置

```python
SESSION_POLICY = {
    "session_timeout": 1800,        # 30 minutes / 30分钟
    "max_sessions": 5,              # Max concurrent sessions / 最大并发会话
    "allow_concurrent": True,       # Allow multiple sessions / 允许多个会话
}
```

### Cookie Security / Cookie安全

```python
# Production settings / 生产环境设置
SESSION_COOKIE_SECURE = True       # HTTPS only / 仅HTTPS
SESSION_COOKIE_HTTPONLY = True     # No JavaScript access / 禁止JS访问
SESSION_COOKIE_SAMESITE = "Lax"    # CSRF protection / CSRF保护

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
```

## File Upload Security / 文件上传安全

### File Size Limits / 文件大小限制

```python
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440  # 2.5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
```

### File Validation / 文件验证

Always validate uploaded files:

```python
def validate_file(file):
    # Check file extension / 检查文件扩展名
    allowed_extensions = ['.jpg', '.png', '.pdf']
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError("Invalid file type")

    # Check file size / 检查文件大小
    if file.size > MAX_FILE_SIZE:
        raise ValidationError("File too large")

    # Check MIME type / 检查MIME类型
    allowed_mime_types = ['image/jpeg', 'image/png', 'application/pdf']
    if file.content_type not in allowed_mime_types:
        raise ValidationError("Invalid MIME type")
```

## CORS Configuration / CORS配置

```python
# Development / 开发环境
CORS_ALLOW_ALL_ORIGINS = True

# Production / 生产环境
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://example.com",
    "https://www.example.com",
]
```

## Security Headers / 安全头

The application sets the following security headers:

```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 2592000  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
```

## Dependency Management / 依赖管理

### Regular Updates / 定期更新

```bash
# Check for outdated packages / 检查过时的包
pip list --outdated

# Update requirements / 更新依赖
pip-compile requirements.in --upgrade
```

### Security Scanning / 安全扫描

```bash
# Run Bandit security linter / 运行Bandit安全检查
bandit -r .

# Scan for vulnerabilities / 扫描漏洞
safety check
```

## Deployment Security / 部署安全

### Production Checklist / 生产环境检查清单

- [ ] Use environment variables for all sensitive data / 所有敏感数据使用环境变量
- [ ] Enable HTTPS with valid certificates / 使用有效证书启用HTTPS
- [ ] Set `DEBUG = False` / 设置调试模式为False
- [ ] Configure `ALLOWED_HOSTS` properly / 正确配置允许的主机
- [ ] Enable database SSL / 启用数据库SSL
- [ ] Set up firewall rules / 设置防火墙规则
- [ ] Configure log monitoring / 配置日志监控
- [ ] Enable rate limiting / 启用速率限制
- [ ] Set up automatic backups / 设置自动备份
- [ ] Review user permissions / 审查用户权限
- [ ] Implement Content Security Policy / 实施内容安全策略
- [ ] Enable security monitoring / 启用安全监控

### SSL/TLS Configuration / SSL/TLS配置

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Modern configuration / 现代配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

## Monitoring and Logging / 监控和日志

### Security Events Logging / 安全事件日志

The application logs the following security events:

- Failed login attempts / 登录失败
- Password changes / 密码更改
- Permission changes / 权限更改
- API access / API访问
- Suspicious activity / 可疑活动

### Log Monitoring / 日志监控

```bash
# Monitor failed login attempts / 监控登录失败
tail -f logs/info.log | grep "Failed login"

# Monitor error logs / 监控错误日志
tail -f logs/err.log
```

## Security Best Practices / 安全最佳实践

1. **Never commit sensitive data** / 永不提交敏感数据
   - Use `.gitignore` to exclude secrets
   - Use environment variables
   - Rotate credentials regularly

2. **Principle of Least Privilege** / 最小权限原则
   - Grant minimal required permissions
   - Review permissions regularly
   - Use role-based access control

3. **Defense in Depth** / 纵深防御
   - Multiple layers of security
   - Don't rely on single control
   - Assume controls can fail

4. **Security by Design** / 安全设计
   - Implement security from start
   - Not an afterthought
   - Review code for vulnerabilities

## Reporting Security Issues / 报告安全问题

If you discover a security vulnerability, please:

1. Do NOT disclose it publicly / 不要公开披露
2. Email security@example.com / 发送邮件
3. Include details and reproduction steps / 包含详细信息
4. Allow time to fix before disclosure / 披露前留出修复时间

## Resources / 资源

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Django Security](https://owasp.org/www-project-django-security/)
- [Django REST Framework Security](https://www.django-rest-framework.org/topics/security/)
