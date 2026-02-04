# Production Dockerfile for Django / Django生产环境Dockerfile
# Uses Python 3.11 slim image / 使用Python 3.11 slim镜像
# Multi-stage build for optimization / 多阶段构建优化

# Stage 1: Builder / 构建阶段
FROM python:3.11-slim-bullseye as builder

# Build dependencies / 构建依赖
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies / 安装构建依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libmariadb-dev \
        pkg-config \
        && rm -rf /var/lib/apt/lists/*

# Create virtual environment / 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies / 安装Python依赖
COPY requirements/ /app/requirements/
RUN pip install --no-cache-dir -r /app/requirements/production.txt


# Stage 2: Runtime / 运行阶段
FROM python:3.11-slim-bullseye as runtime

# Runtime dependencies / 运行时依赖
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

# Install runtime dependencies only / 仅安装运行时依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmariadb3 \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Create non-root user for security / 创建非root用户以提高安全性
RUN groupadd -r django && useradd -r -g django django

# Copy virtual environment from builder / 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# Set working directory / 设置工作目录
WORKDIR /app

# Copy application code / 复制应用代码
COPY --chown=django:django . /app

# Create necessary directories / 创建必要目录
RUN mkdir -p /app/logs /app/media /app/staticfiles && \
    chown -R django:django /app/logs /app/media /app/staticfiles

# Copy entrypoint scripts / 复制入口脚本
COPY --chown=django:django docker/production/django/entrypoint /entrypoint
RUN chmod +x /entrypoint

COPY --chown=django:django docker/production/django/start /start
RUN chmod +x /start

# Health check / 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Switch to non-root user / 切换到非root用户
USER django

# Expose port / 暴露端口
EXPOSE 8000

# Set resource limits (in compose file) / 设置资源限制（在compose文件中）

# Entry point / 入口点
ENTRYPOINT ["/entrypoint"]

# Default command / 默认命令
CMD ["/start"]
