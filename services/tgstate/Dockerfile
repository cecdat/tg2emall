# 使用多阶段构建
# 第一阶段：编译 Go 程序
FROM golang:1.20-alpine AS builder

# 设置工作目录
WORKDIR /app

# 复制 Go 模块文件
COPY go.mod go.sum ./

# 下载依赖
RUN go mod download

# 复制源代码
COPY . .

# 编译程序
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o tgstate .

# 第二阶段：运行环境
FROM alpine:latest

# 安装 ca-certificates 包，用于 HTTPS 连接
RUN apk --no-cache add ca-certificates

# 创建非 root 用户
RUN adduser -D -s /bin/sh tgstate

# 设置工作目录
WORKDIR /app

# 从构建阶段复制二进制文件
COPY --from=builder /app/tgstate .

# 复制模板文件
COPY --from=builder /app/assets/templates ./assets/templates

# 设置文件权限
RUN chown -R tgstate:tgstate /app

# 切换到非 root 用户
USER tgstate

# 设置暴露的端口
EXPOSE 8088

# 设置容器启动时要执行的命令（默认启动管理接口）
CMD ["./tgState", "management"]