# 后端技术文档
> 集成RBAC的Django脚手架
> 
> 封装了CRUD、Response、Exception、Handler等工具
> 
> 集成了JWT、Celery、Redis等常用组件
> 
> 详细的文档和注释，助力开发者快速上手
> 
> 适合中大型项目的后端开发
> 
> 后续将持续更新，欢迎关注

### 1. Django 框架
- Django: 作为主要的 Web 框架。
- Django REST Framework (DRF): 用于构建 RESTful API。

### 2. 身份验证和授权
- django-allauth: 用于处理用户注册、登录和社交账号登录。
- rest_framework_simplejwt: 用于 JWT 身份验证。

### 3. 数据库
- MySQL: 通过 `DATABASE_URL` 配置使用 MySQL 数据库。
- Django ORM: 用于数据库交互。

### 4. 消息队列和异步任务
- Celery: 用于处理异步任务。
- Redis: 作为 Celery 的消息代理。

### 5. 日志管理
- Python logging: 用于日志记录，配置了多种日志格式和处理器。
- TimedRotatingFileHandler: 用于日志文件的定期轮换。

### 6. 国际化和本地化
- Django 内置国际化功能: 使用 `USE_I18N` 和 `USE_L10N`。

### 7. 静态文件和媒体文件管理
- Django 静态文件管理: 使用 `STATICFILES_DIRS` 和 `MEDIA_ROOT`。

### 8. 中间件
- CORS Headers: 通过 `corsheaders` 处理跨域请求。
- 自定义中间件: 如 `JWTAuthenticationMiddleware`。

### 9. 安全
- CSRF 保护: 使用 `CsrfViewMiddleware`。
- X-Frame-Options: 设置为 `DENY` 以防止点击劫持。

### 10. API 文档
- drf-spectacular: 用于生成 OpenAPI 文档。

### 11. 其他
- environ: 用于从环境变量中读取配置。
- Pathlib: 用于路径管理。
- GZipMiddleware: 用于响应的 GZip 压缩。

