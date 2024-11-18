#!/bin/bash

set -e  # 如果任何命令失败，立即退出脚本

# 定义常量
BACKEND_DIR="/home/xingtao/data/back"
FRONTEND_DIR="/home/xingtao/data/front"

# 获取当前版本号并自增
get_new_version() {
    local current_version=$1
    local version_number="${current_version##*:}"  # 提取冒号后面的版本号
    local new_version=$((version_number + 1))       # 版本号自增
    echo "${current_version%%:*}:$new_version"       # 返回新的版本标签
}

# 定义初始版本
BACKEND_IMAGE="end:1.0.1"
FRONTEND_IMAGE="front:1.0.1"

# 从 .env 文件中读取现有配置
if [[ -f .env ]]; then
    # 读取现有的版本号
    while IFS='=' read -r key value; do
        case "$key" in
            END_IMAGE_VERSION) BACKEND_IMAGE="end:$value" ;;
            FRONT_IMAGE_VERSION) FRONTEND_IMAGE="front:$value" ;;
        esac
    done < .env
fi

# 获取新的版本号
BACKEND_IMAGE=$(get_new_version "$BACKEND_IMAGE")
FRONTEND_IMAGE=$(get_new_version "$FRONTEND_IMAGE")

# 更新 .env 文件，保留其他配置并更新版本号
{
    # 遍历现有的配置，输出到新的 .env 文件
    while IFS='=' read -r key value; do
        if [[ "$key" == "END_IMAGE_VERSION" ]]; then
            echo "END_IMAGE_VERSION=${BACKEND_IMAGE##*:}"
        elif [[ "$key" == "FRONT_IMAGE_VERSION" ]]; then
            echo "FRONT_IMAGE_VERSION=${FRONTEND_IMAGE##*:}"
        else
            echo "$key=$value"  # 保留其他配置
        fi
    done < .env
} > .env.tmp

# 替换原来的 .env 文件
mv .env.tmp .env

# 更新代码的函数
update_code() {
    local dir=$1
    cd "$dir" || { echo "目录 $dir 不存在"; exit 1; }
    git pull
}

# 更新后端和前端代码
update_code "$BACKEND_DIR" &
update_code "$FRONTEND_DIR" &
wait  # 等待所有后台进程完成

# 构建镜像的函数
build_image() {
    local dir=$1
    local image_name=$2
    cd "$dir" || { echo "目录 $dir 不存在"; exit 1; }
    docker build -t "$image_name" .
}

# 构建后端和前端镜像
build_image "$BACKEND_DIR" "$BACKEND_IMAGE" &
build_image "$FRONTEND_DIR" "$FRONTEND_IMAGE" &
wait  # 等待所有后台进程完成

# 运行容器
docker-compose stop
# docker-compose rm -f  # 使用 -f 强制删除
docker-compose up -d  # 在后台运行

echo "部署完成！"
echo "新后端镜像版本: $BACKEND_IMAGE"
echo "新前端镜像版本: $FRONTEND_IMAGE"
