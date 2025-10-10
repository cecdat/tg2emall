FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖（Pillow 需要 libjpeg 和 zlib）
RUN apt-get update && apt-get install -y \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Flask 用于管理接口
RUN pip install --no-cache-dir Flask Flask-CORS

# 复制项目文件
COPY . .

# 创建日志目录
RUN mkdir -p /app/logs

# 暴露管理服务和采集服务端口
EXPOSE 2003 5002

# 默认启动管理服务
CMD ["python", "management-service.py"]
