# Django Project Template

> A production-ready Django template with REST Framework, featuring best practices for security, testing, and deployment.
>
> 集成RBAC的Django脚手架，封装了CRUD、Response、Exception、Handler等工具，集成了JWT、Celery、Redis等常用组件。

## Features / 功能特性

- **Django 4.2** with REST Framework
- **JWT Authentication** with SimpleJWT / JWT身份验证
- **Security Hardened** with configurable policies / 安全加固配置
- **Celery** for async task processing / 异步任务处理
- **Redis** caching and sessions / 缓存和会话
- **Docker** support for containerization / Docker容器化支持
- **Comprehensive Testing** setup with pytest / 完整的测试配置
- **Code Quality** tools (black, isort, ruff, mypy) / 代码质量工具
- **API Documentation** with drf-spectacular (OpenAPI 3.0) / API文档

## Quick Start / 快速开始

### Prerequisites / 前置要求

- Python 3.11+
- MySQL 8.0+
- Redis 6.0+

### Installation / 安装

1. **Clone the repository / 克隆仓库**
   ```bash
   git clone <repository-url>
   cd Django-Template
   ```

2. **Create virtual environment / 创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies / 安装依赖**
   ```bash
   pip install -r requirements/local.txt
   ```

4. **Configure environment variables / 配置环境变量**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration / 编辑配置文件
   ```

5. **Generate RSA keys / 生成RSA密钥** (for password encryption / 用于密码加密)
   ```bash
   mkdir -p secrets
   openssl genrsa -out secrets/pri.key 2048
   openssl rsa -in secrets/pri.key -pubout -out secrets/pub.key
   chmod 600 secrets/pri.key
   chmod 644 secrets/pub.key
   ```

6. **Run migrations / 运行迁移**
   ```bash
   python manage.py migrate
   ```

7. **Create superuser / 创建超级用户**
   ```bash
   python manage.py createsuperuser
   ```

8. **Run development server / 启动开发服务器**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000`
API docs: `http://localhost:8000/api/schema/`

## Project Structure / 项目结构

```
Django-Template/
├── apps/                    # Django applications / Django应用
│   ├── core/               # Core utilities and base classes / 核心工具类
│   └── users/              # User management app / 用户管理应用
├── config/                 # Configuration files / 配置文件
│   ├── settings/           # Django settings modules / Django设置模块
│   │   ├── base.py         # Base settings / 基础设置
│   │   ├── local.py        # Local development / 本地开发
│   │   ├── production.py   # Production / 生产环境
│   │   ├── security.py     # Security config / 安全配置
│   │   ├── database.py     # Database config / 数据库配置
│   │   ├── auth.py         # Authentication / 认证设置
│   │   ├── api.py          # API/DRF settings / API配置
│   │   ├── cache.py        # Cache and Celery / 缓存配置
│   │   ├── storage.py      # Static/media / 文件存储
│   │   └── email.py        # Email config / 邮件配置
│   ├── urls.py             # Root URL config / URL配置
│   └── wsgi.py             # WSGI configuration / WSGI配置
├── docs/                   # Documentation / 文档
├── secrets/                # Sensitive files (not in git) / 敏感文件
├── static/                 # Static files / 静态文件
├── templates/              # Django templates / 模板文件
├── utils/                  # Utility modules / 工具模块
├── manage.py               # Django management script / 管理脚本
├── pyproject.toml          # Modern Python config / Python配置
└── README.md
```

## Environment Variables / 环境变量

See `.env.example` for all available configuration options.

**Required variables for production / 生产环境必需变量:**

```bash
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DJANGO_SECURE_SSL_REDIRECT=True
```

**Database / 数据库:**
```bash
MYSQL_DATABASE=your_database
MYSQL_USER=your_user
MYSQL_PASSWORD=your_secure_password
MYSQL_HOST=your_host
MYSQL_PORT=3306
```

**Security / 安全:**
```bash
DJANGO_RSA_PASSWORD=your-rsa-password
START_PASSWORD=ChangeMe123!
```

## Development / 开发

### Code Quality / 代码质量

Run code quality checks:
```bash
# Format code / 格式化代码
black .
isort .

# Lint / 代码检查
ruff check .
flake8 .

# Type checking / 类型检查
mypy .

# Security check / 安全检查
bandit -r .
```

### Testing / 测试

Run tests:
```bash
# Run all tests / 运行所有测试
pytest

# Run with coverage / 运行测试并生成覆盖率报告
pytest --cov=apps --cov=utils --cov-report=html

# Run specific test file / 运行特定测试文件
pytest apps/users/tests/test_views.py

# Run with pytest-xdist (parallel) / 并行运行测试
pytest -n auto
```

### Database Management / 数据库管理

```bash
# Create migrations / 创建迁移文件
python manage.py makemigrations

# Apply migrations / 应用迁移
python manage.py migrate

# Show migrations / 查看迁移状态
python manage.py showmigrations

# Create migration for specific app / 为特定应用创建迁移
python manage.py makemigrations users
```

## Production Deployment / 生产部署

### Using Docker / 使用Docker

1. **Build image / 构建镜像**
   ```bash
   docker build -f docker/local/django/Dockerfile -t myapp:latest .
   ```

2. **Run with docker-compose / 使用docker-compose运行**
   ```bash
   docker-compose up -d
   ```

### Manual Deployment / 手动部署

1. **Set environment variables / 设置环境变量**
   ```bash
   export DJANGO_SETTINGS_MODULE=config.settings.production
   ```

2. **Collect static files / 收集静态文件**
   ```bash
   python manage.py collectstatic --noinput
   ```

3. **Run with gunicorn / 使用gunicorn运行**
   ```bash
   gunicorn config.wsgi:application --bind 0.0.0.0:8000
   ```

### Security Checklist / 安全检查清单

Before deploying to production / 部署到生产环境前:

- [ ] Change `DJANGO_SECRET_KEY` to a random string / 修改密钥
- [ ] Set `DJANGO_DEBUG=False` / 关闭调试模式
- [ ] Configure `DJANGO_ALLOWED_HOSTS` to your domain / 配置允许的主机
- [ ] Set `DJANGO_SECURE_SSL_REDIRECT=True` / 启用SSL重定向
- [ ] Set strong database passwords / 设置强密码
- [ ] Configure `DJANGO_RSA_PASSWORD` / 配置RSA密码
- [ ] Change `START_PASSWORD` from default / 修改默认密码
- [ ] Set up proper CORS origins / 配置CORS
- [ ] Configure email backend / 配置邮件服务
- [ ] Set up monitoring and logging / 配置监控和日志
- [ ] Enable HTTPS with valid certificates / 启用HTTPS
- [ ] Configure firewall rules / 配置防火墙
- [ ] Set up database backups / 配置数据库备份
- [ ] Review security headers / 检查安全头

## API Documentation / API文档

Interactive API documentation is available when running the development server:

- Swagger UI: `http://localhost:8000/api/schema/swagger-ui/`
- ReDoc: `http://localhost:8000/api/schema/redoc/`
- OpenAPI Schema: `http://localhost:8000/api/schema/`

## Tech Stack / 技术栈

### 1. Django Framework / Django框架
- Django: Main web framework / 主要Web框架
- Django REST Framework (DRF): RESTful API / RESTful API构建

### 2. Authentication & Authorization / 身份验证和授权
- django-allauth: User registration, login, social auth / 用户注册、登录、社交认证
- rest_framework_simplejwt: JWT authentication / JWT身份验证

### 3. Database / 数据库
- MySQL: Primary database / 主数据库
- Django ORM: Database interaction / 数据库交互
- Redis: Caching and sessions / 缓存和会话

### 4. Message Queue & Async Tasks / 消息队列和异步任务
- Celery: Async task processing / 异步任务处理
- Redis: Message broker / 消息代理

### 5. Logging / 日志管理
- Python logging: Structured logging / 结构化日志
- TimedRotatingFileHandler: Log rotation / 日志轮换

### 6. Internationalization / 国际化
- Django i18n: Built-in internationalization / 内置国际化

### 7. Static & Media Files / 静态和媒体文件
- Django staticfiles: Static file management / 静态文件管理
- MEDIA_ROOT: Media file handling / 媒体文件处理

### 8. Middleware / 中间件
- CORS Headers: Cross-origin requests / 跨域请求
- Custom middleware: Request ID, security / 自定义中间件

### 9. Security / 安全
- CSRF protection: CSRF保护
- X-Frame-Options: Clickjacking prevention / 防止点击劫持
- Security headers: HSTS, SSL / 安全头配置

### 10. API Documentation / API文档
- drf-spectacular: OpenAPI 3.0 documentation / OpenAPI文档

## Troubleshooting / 故障排除

### Migration Issues / 迁移问题
```bash
python manage.py migrate --fake-initial
python manage.py migrate --run-syncdb
```

### Redis Connection / Redis连接
```bash
redis-cli ping  # Should return PONG / 应返回PONG
```

### Celery Tasks / Celery任务
```bash
celery -A config worker -l info
```

## Contributing / 贡献

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License / 许可证

This project is licensed under the MIT License.

## Support / 支持

For issues and questions, please use the GitHub issue tracker.
