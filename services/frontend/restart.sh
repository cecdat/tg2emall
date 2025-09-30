#!/bin/bash

echo "停止前端服务..."
docker-compose stop tg2em-frontend

echo "复制修复后的文件..."
cp app.py /path/to/docker/container/app.py

echo "重启前端服务..."
docker-compose up -d tg2em-frontend

echo "查看日志..."
docker-compose logs -f tg2em-frontend
