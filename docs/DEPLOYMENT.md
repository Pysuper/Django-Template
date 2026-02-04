# Deployment Guide / 部署指南

This guide covers deploying the Django application to production.

## Table of Contents / 目录

1. [Pre-deployment Checklist / 部署前检查](#pre-deployment-checklist)
2. [Environment Setup / 环境设置](#environment-setup)
3. [Docker Deployment / Docker部署](#docker-deployment)
4. [Manual Deployment / 手动部署](#manual-deployment)
5. [Post-deployment / 部署后](#post-deployment)
6. [Monitoring / 监控](#monitoring)

## Pre-deployment Checklist / 部署前检查

### Security / 安全

- [ ] Change `DJANGO_SECRET_KEY` to random string
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure `DJANGO_ALLOWED_HOSTS`
- [ ] Set strong database passwords
- [ ] Configure `DJANGO_RSA_PASSWORD`
- [ ] Change `START_PASSWORD` from default
- [ ] Enable SSL/HTTPS
- [ ] Review CORS settings

### Performance / 性能

- [ ] Configure static files serving
- [ ] Set up caching (Redis)
- [ ] Configure database connection pooling
- [ ] Enable gzip compression
- [ ] Set up CDN for static assets (optional)

### Backup / 备份

- [ ] Set up database backups
- [ ] Set up media file backups
- [ ] Test restore procedures
- [ ] Document recovery process

## Environment Setup / 环境设置

### System Requirements / 系统要求

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip mysql-server redis-server nginx

# CentOS/RHEL
sudo yum install -y python311 python311-venv python3-pip mysql-server redis nginx
```

### Application User / 应用用户

```bash
# Create dedicated user / 创建专用用户
sudo useradd -m -s /bin/bash django
sudo su - django
```

### Directory Structure / 目录结构

```bash
/opt/myapp/
├── application/          # Application code / 应用代码
├── venv/                # Virtual environment / 虚拟环境
├── logs/                # Log files / 日志文件
├── media/               # User uploaded files / 用户上传文件
└── static/              # Collected static files / 收集的静态文件
```

## Docker Deployment / Docker部署

### Build Docker Image / 构建Docker镜像

```bash
docker build -f docker/production/django/Dockerfile -t myapp:latest .
```

### Docker Compose / Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: myapp
      MYSQL_USER: myapp
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
    restart: always

  redis:
    image: redis:7-alpine
    restart: always

  django:
    image: myapp:latest
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - ./static:/app/staticfiles
      - ./media:/app/media
      - ./logs:/app/logs
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./static:/static
      - ./media:/media
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - django
    restart: always

  celery:
    image: myapp:latest
    command: celery -A config worker -l info
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.production
    env_file:
      - .env.production
    depends_on:
      - redis
      - db
    restart: always

volumes:
  mysql_data:
```

### Run with Docker Compose / 使用Docker Compose运行

```bash
# Start services / 启动服务
docker-compose -f docker-compose.production.yml up -d

# Check status / 检查状态
docker-compose ps

# View logs / 查看日志
docker-compose logs -f django

# Stop services / 停止服务
docker-compose down
```

## Manual Deployment / 手动部署

### 1. Clone Repository / 克隆仓库

```bash
cd /opt
sudo git clone <repository-url> myapp
sudo chown -R django:django myapp
cd myapp
```

### 2. Create Virtual Environment / 创建虚拟环境

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements/production.txt
```

### 3. Configure Environment / 配置环境

```bash
cp .env.example .env
nano .env  # Edit configuration / 编辑配置
```

Production `.env` example:

```bash
DJANGO_SECRET_KEY=<generate-random-key>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=example.com,www.example.com
DJANGO_SECURE_SSL_REDIRECT=True

DATABASE_URL=mysql://user:password@localhost:3306/myapp

MYSQL_DATABASE=myapp
MYSQL_USER=myapp
MYSQL_PASSWORD=<strong-password>
MYSQL_HOST=localhost
MYSQL_PORT=3306

REDIS_URL=redis://localhost:6379/0

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@example.com
EMAIL_HOST_PASSWORD=<email-password>
```

### 4. Collect Static Files / 收集静态文件

```bash
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py collectstatic --noinput
```

### 5. Run Migrations / 运行迁移

```bash
python manage.py migrate --noinput
```

### 6. Create Superuser / 创建超级用户

```bash
python manage.py createsuperuser
```

### 7. Configure Gunicorn / 配置Gunicorn

Create `/etc/systemd/system/gunicorn.service`:

```ini
[Unit]
Description=Gunicorn instance to serve Django
After=network.target

[Service]
User=django
Group=django
WorkingDirectory=/opt/myapp
Environment="PATH=/opt/myapp/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
ExecStart=/opt/myapp/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/opt/myapp/gunicorn.sock \
    --access-logfile /opt/myapp/logs/gunicorn-access.log \
    --error-logfile /opt/myapp/logs/gunicorn-error.log \
    --log-level info \
    --timeout 120 \
    config.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start Gunicorn:

```bash
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl status gunicorn
```

### 8. Configure Nginx / 配置Nginx

Create `/etc/nginx/sites-available/myapp`:

```nginx
upstream django {
    server unix:/opt/myapp/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name example.com www.example.com;

    # Redirect to HTTPS / 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name example.com www.example.com;

    # SSL Configuration / SSL配置
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers / 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Max upload size / 最大上传大小
    client_max_body_size 10M;

    # Static files / 静态文件
    location /static/ {
        alias /opt/myapp/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files / 媒体文件
    location /media/ {
        alias /opt/myapp/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    # Django application / Django应用
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 9. Configure Celery / 配置Celery

Create `/etc/systemd/system/celery.service`:

```ini
[Unit]
Description=Celery Worker
After=network.target redis.service mysql.service

[Service]
Type=forking
User=django
Group=django
WorkingDirectory=/opt/myapp
Environment="PATH=/opt/myapp/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings.production"
ExecStart=/opt/myapp/venv/bin/celery -A config worker \
    --loglevel=info \
    --logfile=/opt/myapp/logs/celery.log \
    --pidfile=/opt/myapp/celery.pid

[Install]
WantedBy=multi-user.target
```

Enable and start Celery:

```bash
sudo systemctl start celery
sudo systemctl enable celery
sudo systemctl status celery
```

### 10. Configure SSL with Let's Encrypt / 使用Let's Encrypt配置SSL

```bash
# Install Certbot / 安装Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate / 获取证书
sudo certbot --nginx -d example.com -d www.example.com

# Auto-renewal / 自动续期
sudo certbot renew --dry-run
```

## Post-deployment / 部署后

### Verify Deployment / 验证部署

```bash
# Check Gunicorn / 检查Gunicorn
curl -I http://localhost:8000

# Check Nginx / 检查Nginx
curl -I https://example.com

# Check logs / 检查日志
tail -f /opt/myapp/logs/gunicorn-error.log
tail -f /opt/myapp/logs/info.log
```

### Database Backup / 数据库备份

Create backup script `/opt/myapp/scripts/backup.sh`:

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
MYSQL_USER="myapp"
MYSQL_PASSWORD="password"
DATABASE="myapp"

# Create backup / 创建备份
mysqldump -u$MYSQL_USER -p$MYSQL_PASSWORD $DATABASE | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Keep last 7 days / 保留最近7天
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
```

Add to crontab:

```bash
# Daily backup at 2 AM / 每天凌晨2点备份
0 2 * * * /opt/myapp/scripts/backup.sh
```

### Log Rotation / 日志轮换

Create `/etc/logrotate.d/django`:

```
/opt/myapp/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 django django
    sharedscripts
    postrotate
        systemctl reload gunicorn > /dev/null 2>&1 || true
    endscript
}
```

## Monitoring / 监控

### Application Monitoring / 应用监控

Install monitoring tools:

```bash
pip install django-prometheus
```

Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    'django_prometheus',
    ...
]
```

Add to URLs:

```python
urlpatterns = [
    ...
    path('', include('django_prometheus.urls')),
]
```

### System Monitoring / 系统监控

Install tools:

```bash
# System monitoring / 系统监控
sudo apt install htop iotop nethogs

# Docker monitoring (if using Docker) / Docker监控
docker stats
```

### Health Checks / 健康检查

Create health check endpoint and set up monitoring:

```bash
# Using curl / 使用curl
curl https://example.com/health/

# Using Uptime Robot / 使用Uptime Robot
# https://uptimerobot.com
```

## Updating / 更新

### Update Procedure / 更新流程

```bash
# 1. Backup current version / 备份当前版本
cd /opt/myapp
tar -czf ../myapp-backup-$(date +%Y%m%d).tar.gz .

# 2. Pull latest code / 拉取最新代码
git pull origin main

# 3. Activate virtual environment / 激活虚拟环境
source venv/bin/activate

# 4. Update dependencies / 更新依赖
pip install -r requirements/production.txt

# 5. Run migrations / 运行迁移
python manage.py migrate

# 6. Collect static files / 收集静态文件
python manage.py collectstatic --noinput

# 7. Restart services / 重启服务
sudo systemctl restart gunicorn
sudo systemctl restart celery
```

### Rollback / 回滚

```bash
# Restore from backup / 从备份恢复
cd /opt
tar -xzf myapp-backup-YYYYMMDD.tar.gz

# Restart services / 重启服务
sudo systemctl restart gunicorn
sudo systemctl restart celery
```

## Troubleshooting / 故障排除

### Common Issues / 常见问题

1. **Permission Denied / 权限被拒绝**
   ```bash
   sudo chown -R django:django /opt/myapp
   ```

2. **Database Connection Error / 数据库连接错误**
   ```bash
   # Check MySQL status / 检查MySQL状态
   sudo systemctl status mysql

   # Check credentials / 检查凭据
   # Verify .env configuration / 验证.env配置
   ```

3. **Static Files Not Loading / 静态文件未加载**
   ```bash
   # Check permissions / 检查权限
   ls -la /opt/myapp/static/

   # Recollect static files / 重新收集静态文件
   python manage.py collectstatic --noinput --clear
   ```

4. **502 Bad Gateway / 502网关错误**
   ```bash
   # Check Gunicorn status / 检查Gunicorn状态
   sudo systemctl status gunicorn

   # Check Gunicorn logs / 检查Gunicorn日志
   tail -f /opt/myapp/logs/gunicorn-error.log
   ```

## Resources / 资源

- [Django Deployment Documentation](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [Gunicorn Documentation](https://docs.gunicorn.org/)
- [Nginx Django Setup](https://www.nginx.com/resources/wiki/start/topics/examples/django/)
