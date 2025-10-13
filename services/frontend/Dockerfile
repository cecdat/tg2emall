FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY . .

# 创建日志目录并设置权限
RUN mkdir -p /app/logs && chmod 755 /app/logs

# 创建非 root 用户
RUN useradd -m -u 1000 frontend && chown -R frontend:frontend /app
USER frontend

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "app.py"]
