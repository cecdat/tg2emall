# 使用多阶段构建
# 第一阶段：编译 Go 程序
FROM golang:1.20-alpine AS builder

# 设置工作目录
WORKDIR /app

# 复制 Go 模块文件
COPY go.mod ./

# 下载依赖并生成go.sum
RUN go mod download

# 复制源代码
COPY . .

# 确保所有依赖都被正确下载
RUN go mod download github.com/gorilla/mux

# 整理模块依赖并更新go.sum
RUN go mod tidy

# 编译管理服务和上传服务
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o management-service management-service.go
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o upload-service upload-service.go
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o management main.go management.go

# 第二阶段：运行环境
FROM alpine:latest

# 安装 ca-certificates 包，用于 HTTPS 连接
RUN apk --no-cache add ca-certificates

# 创建非 root 用户
RUN adduser -D -s /bin/sh tgstate

# 设置工作目录
WORKDIR /app

# 从构建阶段复制二进制文件
COPY --from=builder /app/management-service .
COPY --from=builder /app/upload-service .
COPY --from=builder /app/management .

# 复制模板文件
COPY --from=builder /app/assets/templates ./assets/templates

# 创建web目录用于管理页面
RUN mkdir -p ./web

# 设置文件权限  
RUN chown -R tgstate:tgstate /app && chmod +x ./management-service && chmod +x ./upload-service && chmod +x ./management

# 切换到非 root 用户
USER tgstate

# 设置暴露的端口
EXPOSE 8001 8002 8088

# 创建启动脚本
RUN echo '#!/bin/sh' > /app/start.sh && \
    echo './management-service &' >> /app/start.sh && \
    echo './management management &' >> /app/start.sh && \
    echo 'wait' >> /app/start.sh && \
    chmod +x /app/start.sh

# 设置容器启动时要执行的命令（同时启动管理服务和8088端口管理页面）
CMD ["/app/start.sh"]