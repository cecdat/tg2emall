# tg2emall 服务启动指南

## 前提条件

1. 已安装 Docker 和 Docker Compose
2. 已配置 Telegram Bot Token 和频道

## 快速启动

### 1. 配置环境变量

```powershell
# Windows PowerShell
Copy-Item env.example .env

# Linux/Mac
cp env.example .env
```

然后编辑 `.env` 文件，填入您的配置：

```bash
# tgState 图片上传服务配置
TGSTATE_TOKEN=你的Telegram_Bot_Token
TGSTATE_TARGET=@你的频道名
TGSTATE_PASS=google
TGSTATE_MODE=p
TGSTATE_URL=http://localhost:8001

# Telegram API 配置（采集服务需要）
API_ID=你的API_ID
API_HASH=你的API_HASH

# MySQL 数据库配置（保持默认即可）
MYSQL_ROOT_PASSWORD=tg2emall
MYSQL_DATABASE=tg2em
MYSQL_USER=tg2emall
MYSQL_PASSWORD=tg2emall

# 时区配置
TZ=Asia/Shanghai
```

### 2. 启动所有服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 3. 只启动特定服务

```bash
# 只启动数据库和前端
docker-compose up -d mysql frontend

# 只启动 tgstate 图片服务
docker-compose up -d tgstate

# 只启动采集服务
docker-compose up -d tg2em-scrape
```

## 服务说明

### 服务列表

| 服务名 | 容器名 | 端口 | 说明 |
|--------|--------|------|------|
| nginx-proxy-manager | nginx-proxy-manager | 80, 81, 443 | 反向代理管理 |
| mysql | tg2em-mysql | 3306 | MySQL 数据库 |
| frontend | tg2em-frontend | 8000 | 前端展示系统 |
| tgstate | tg2em-tgstate | 8001, 8002 | 图片上传服务 |
| tg2em-scrape | tg2em-scrape | 2003, 5002 | Telegram 采集服务 |

### 访问地址

- **前端系统**: http://localhost:8000
- **Nginx 管理**: http://localhost:81
- **tgState 管理**: http://localhost:8001
- **采集管理**: http://localhost:2003

## 服务启动顺序

建议按以下顺序启动服务：

1. **MySQL 数据库**
   ```bash
   docker-compose up -d mysql
   # 等待数据库初始化完成（约 30 秒）
   ```

2. **Nginx Proxy Manager**
   ```bash
   docker-compose up -d nginx-proxy-manager
   ```

3. **tgState 图片服务**
   ```bash
   docker-compose up -d tgstate
   ```

4. **前端服务**
   ```bash
   docker-compose up -d frontend
   ```

5. **采集服务**（可选）
   ```bash
   docker-compose up -d tg2em-scrape
   ```

## 验证服务

### 1. 检查容器状态

```bash
docker-compose ps
```

所有服务应该显示为 "Up" 状态。

### 2. 检查 MySQL 连接

```bash
# 进入 MySQL 容器
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em

# 查看数据表
SHOW TABLES;

# 退出
EXIT;
```

### 3. 测试 tgState API

```powershell
# Windows PowerShell
Invoke-RestMethod -Uri "http://localhost:8001/api/management/status"

# 期望输出
# {
#   "success": true,
#   "data": {
#     "status": "stopped",
#     ...
#   }
# }
```

### 4. 访问前端页面

打开浏览器访问: http://localhost:8000

## 常用命令

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs

# 实时跟踪日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs frontend
docker-compose logs tgstate
docker-compose logs tg2em-scrape

# 查看最近 50 行日志
docker-compose logs --tail=50
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart tgstate
docker-compose restart frontend
```

### 停止服务

```bash
# 停止所有服务
docker-compose stop

# 停止特定服务
docker-compose stop tgstate
```

### 删除服务

```bash
# 停止并删除所有容器
docker-compose down

# 停止并删除所有容器和数据卷
docker-compose down -v

# 停止并删除所有容器、数据卷和镜像
docker-compose down -v --rmi all
```

### 重新构建

```bash
# 重新构建所有服务
docker-compose build

# 重新构建特定服务
docker-compose build tgstate

# 不使用缓存重新构建
docker-compose build --no-cache tgstate
```

## 故障排查

### 问题 1: 容器启动后立即退出

**检查日志**:
```bash
docker-compose logs tgstate
```

**可能原因**:
- 环境变量配置错误
- 依赖服务未启动
- 端口被占用

**解决方案**:
```bash
# 检查环境变量
cat .env

# 检查端口占用
netstat -ano | findstr :8001

# 重新构建
docker-compose build --no-cache tgstate
docker-compose up -d tgstate
```

### 问题 2: 数据库连接失败

**检查数据库状态**:
```bash
docker-compose ps mysql
docker-compose logs mysql
```

**解决方案**:
```bash
# 重启数据库
docker-compose restart mysql

# 如果仍有问题，删除数据卷重新初始化
docker-compose down -v
docker-compose up -d mysql
```

### 问题 3: tgState 服务 500 错误

这是本次修复的主要问题。请执行：

```bash
# 停止服务
docker-compose stop tgstate

# 重新构建（应用修复）
docker-compose build --no-cache tgstate

# 启动服务
docker-compose up -d tgstate

# 查看日志
docker-compose logs -f tgstate
```

### 问题 4: 前端无法连接到 tgstate

**检查网络**:
```bash
# 检查容器网络
docker network inspect tg2em-network

# 确保所有容器在同一网络
docker-compose ps
```

**测试连接**:
```bash
# 从前端容器测试连接
docker exec -it tg2em-frontend curl http://tgstate:8001/api/management/status
```

## 开发调试

### 进入容器

```bash
# 进入前端容器
docker exec -it tg2em-frontend /bin/bash

# 进入 tgstate 容器
docker exec -it tg2em-tgstate /bin/sh

# 进入数据库容器
docker exec -it tg2em-mysql /bin/bash
```

### 查看容器内部文件

```bash
# 列出 tgstate 容器文件
docker exec -it tg2em-tgstate ls -la /app

# 查看日志文件
docker exec -it tg2em-frontend cat /app/logs/frontend.log
```

### 实时监控

```bash
# 监控容器资源使用
docker stats

# 监控特定容器
docker stats tg2em-tgstate tg2em-frontend
```

## 生产环境部署

### 使用 Nginx 反向代理

1. 访问 Nginx Proxy Manager: http://localhost:81
2. 默认账号: admin@example.com / changeme
3. 添加代理主机指向各个服务

### 配置 SSL 证书

在 Nginx Proxy Manager 中可以自动申请 Let's Encrypt 证书。

### 数据备份

```bash
# 备份 MySQL 数据
docker exec tg2em-mysql mysqldump -u tg2emall -ptg2emall tg2em > backup.sql

# 恢复数据
docker exec -i tg2em-mysql mysql -u tg2emall -ptg2emall tg2em < backup.sql
```

## 更新服务

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build

# 重启服务（不中断）
docker-compose up -d
```

## 监控和维护

### 定期检查

```bash
# 检查磁盘使用
docker system df

# 清理未使用的镜像和容器
docker system prune -a

# 查看容器日志大小
docker ps -q | xargs -I {} docker inspect -f '{{.Name}} {{.LogPath}}' {}
```

### 日志轮转

建议配置 Docker 日志轮转：

编辑 `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

然后重启 Docker:
```bash
sudo systemctl restart docker
```

## 相关文档

- [TGSTATE_FIX_GUIDE.md](./TGSTATE_FIX_GUIDE.md) - tgState 服务修复指南
- [QUICK_START.md](./QUICK_START.md) - 快速开始指南
- [README.md](./README.md) - 项目说明

## 技术支持

遇到问题请查看：
1. 服务日志: `docker-compose logs -f`
2. 容器状态: `docker-compose ps`
3. 修复指南: [TGSTATE_FIX_GUIDE.md](./TGSTATE_FIX_GUIDE.md)

