# 创建项目目录
mkdir -p project/python/web/django/aether/

# 进入项目目录
cd project/python/web/django/aether/ &&

# 创建Python3虚拟环境
python3 -m venv pyvenv

# 激活Python3虚拟环境
source pyvenv/bin/activate

# 安装所需的Python3 packages
pip install -r requirements/local.txt

# 创建配置文件, 如.env
touch .env

# 运行项目
python3.11 manage.py runserver 0.0.0.0:5080 --settings=config.settings.local

# 后台运行
nohup python3.11 manage.py runserver 0.0.0.0:5080 --settings=config.settings.local &



# Docker部署
cd project/docker/ &&


# todo front
mkdir frontend && cd frontend &&
docker stop frontend && docker rm frontend
docker build -t frontend:1.0.0 .

docker run -dit \
-h frontend \
--name frontend \
-p 7001:7001 \
frontend:1.0


# todo backend
mkdir backend && cd backend && mkdir log static media
docker stop backend && docker rm backend
docker build -t backend:1.0.0 .

docker run -dit \
-h backend \
--name backend \
-p 5044:8000 \
-v $PWD/log:/affect/back/log \
-v $PWD/static:/affect/back/static \
-v $PWD/media:/affect/back/media \
backend:1.0.0


# todo nginx
mkdir nginx && cd nginx && mkdir static && touch nginx.conf
docker stop nginx_end && docker rm nginx_end
docker build -t nginx:base .

docker run -dit \
-h nginx \
--name nginx \
-p 7000:7000 \
-v $PWD/nginx.conf:/etc/nginx/nginx.conf \
nginx:latest \
nginx -g "daemon off;"


# todo mysql
mkdir mysql && cd mysql && mkdir data conf logs files
docker stop mysql && docker rm mysql

docker run -dit \
-h mysql \
--name mysql \
-p 13306:3306 \
-e MYSQL_ROOT_PASSWORD=Root1234 \
-v $PWD/conf:/etc/mysql/conf.d \
-v $PWD/data:/var/lib/mysql \
-v $PWD/logs:/var/log \
-v $PWD/files:/files \
--restart=on-failure \
mysql:8.0


# todo redis
mkdir redis && cd redis && mkdir data && touch redis.conf
docker run -dit \
--name redis \
-h redis \
-p 16379:6379 \
-v $PWD/redis.conf:/etc/redis/redis.conf \
-v $PWD/data:/data \
--restart=on-failure \
redis:6.2.0 \
redis-server /etc/redis/redis.conf \
--appendonly yes


# todo celery-beat
docker run -dit \
--name celery-beat \
-h celery-beat \
-e CELERY_BROKER_URL="redis://:$(python -c 'from urllib.parse import quote; print(quote("alita@202307251045"))')@47.116.3.206:16379/0" \
-e CELERY_RESULT_BACKEND="redis://:$(python -c 'from urllib.parse import quote; print(quote("alita@202307251045"))')@47.116.3.206:16379/0" \
-e C_FORCE_ROOT=true \
--user $(id -u):$(id -g) \
-v $PWD/alita:/home/celery/alita \
-v $PWD/celery_log:/celery_log \
-w /home/celery/alita \
--restart=on-failure \
celery:v2 \
celery beat --workdir=/home/celery/alita -A alita -l info -S django -f /celery_log/celery_beat.out

# todo celery-worker
docker run -dit \
--name celery-worker \
-h celery-worker \
-e CELERY_BROKER_URL="redis://:$(python -c 'from urllib.parse import quote; print(quote("alita@202307251045"))')@47.116.3.206:16379/0" \
-e CELERY_RESULT_BACKEND="redis://:$(python -c 'from urllib.parse import quote; print(quote("alita@202307251045"))')@47.116.3.206:16379/0" \
-e C_FORCE_ROOT=true \
--user $(id -u):$(id -g) \
-v $PWD/alita:/home/celery/alita \
-v $PWD/celery_log:/celery_log \
-w /home/celery/alita \
--restart=on-failure \
celery:v2 \
celery worker --workdir=/home/celery/alita -A alita -l debug -P threads -c 10 -f /celery_log/celery_worker.log

# kafka for celery
docker run -d \
--name my_kafka \
-p 9092:9092 \
-e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
-e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT \
-e KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:9092,PLAINTEXT_HOST://0.0.0.0:9093 \
-e KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT \
-e KAFKA_ZOOKEEPER_CONNECT=your_zookeeper_host:2181 \
wurstmeister/kafka:latest
