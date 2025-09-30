FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    wget \
    git \
    g++ \
    make \
    # Go环境依赖
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装Go
ENV GO_VERSION=1.21.0
RUN wget -O go.tar.gz "https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz" && \
    tar -C /usr/local -xzf go.tar.gz && \
    rm go.tar.gz
ENV PATH="/usr/local/go/bin:${PATH}"

# 复制所有服务源码
COPY frontend/ ./frontend/
COPY tg2em/ ./tg2em/
COPY tgstate/ ./tgstate/

# 构建tgstate Go服务
WORKDIR /app/tgstate
RUN go mod init tgstate && \
    go mod tidy && \
    go build -o tgstate main.go control/control.go conf/conf.go utils/utils.go

# 回到工作目录
WORKDIR /app

# 安装Python依赖
COPY unified/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制统一启动脚本
COPY unified/start.sh ./start.sh
RUN chmod +x ./start.sh

# 创建进程管理脚本
COPY unified/service_manager.py ./service_manager.py

# 创建非 root 用户
RUN useradd -m -u 1000 unified && chown -R unified:unified /app
USER unified

# 创建必要的目录
RUN mkdir -p /app/data/uploads /app/data/sessions /app/logs

# 暴露端口
EXPOSE 5000 8088

# 启动命令
CMD ["./start.sh"]
