# 远程服务器 tgState 服务修复指南 (Debian 12)

## 问题描述

您在远程 Debian 12 服务器上遇到了 tgState 图片上传服务启动报错：
```
POST /admin/services/tgstate-service/start HTTP/1.1" 500 -
GET /admin/services/tgstate/status HTTP/1.1" 500 -
```

## 已修复的问题

1. ✅ 修正 `management-service.go` 日志输出的端口号错误
2. ✅ 修复密码验证中间件，允许管理 API 无需密码访问
3. ✅ 修正环境变量配置中的 URL 端口
4. ✅ 修正 docker-compose.yml 中的容器内部 URL

## 远程服务器修复步骤

### 方案一：使用自动修复脚本（推荐）

1. **SSH 连接到服务器**
   ```bash
   ssh your-user@your-server-ip
   ```

2. **进入项目目录**
   ```bash
   cd /path/to/tg2emall
   ```

3. **拉取最新代码（包含修复）**
   ```bash
   git pull origin main
   # 或者如果有冲突，先备份本地修改
   git stash
   git pull origin main
   git stash pop
   ```

4. **添加执行权限并运行修复脚本**
   ```bash
   chmod +x fix_tgstate_remote.sh
   ./fix_tgstate_remote.sh
   ```

   脚本会自动完成：
   - ✓ 检查 Docker 环境
   - ✓ 创建/检查 .env 文件
   - ✓ 备份当前配置
   - ✓ 停止现有容器
   - ✓ 重新构建镜像
   - ✓ 启动服务
   - ✓ 验证服务状态

### 方案二：手动修复

如果自动脚本失败，可以手动执行以下步骤：

#### 1. 检查并配置环境变量

```bash
# 如果没有 .env 文件，从示例创建
if [ ! -f .env ]; then
    cp env.example .env
fi

# 编辑 .env 文件
nano .env
```

确保配置正确：
```bash
TGSTATE_TOKEN=你的Telegram_Bot_Token
TGSTATE_TARGET=@你的频道名
TGSTATE_PASS=google
TGSTATE_MODE=p
TGSTATE_URL=http://localhost:8001

# API 配置（可选）
API_ID=
API_HASH=

# MySQL 配置
MYSQL_ROOT_PASSWORD=tg2emall
MYSQL_DATABASE=tg2em
MYSQL_USER=tg2emall
MYSQL_PASSWORD=tg2emall

TZ=Asia/Shanghai
```

#### 2. 停止现有容器

```bash
docker-compose stop tgstate
docker-compose rm -f tgstate
```

#### 3. 重新构建镜像

```bash
# 不使用缓存重新构建
docker-compose build --no-cache tgstate
```

#### 4. 启动服务

```bash
docker-compose up -d tgstate
```

#### 5. 查看日志

```bash
# 实时查看日志
docker-compose logs -f tgstate

# 或查看最近 50 行
docker-compose logs --tail=50 tgstate
```

#### 6. 验证服务

```bash
# 检查容器状态
docker-compose ps tgstate

# 测试管理 API
curl http://localhost:8001/api/management/status

# 预期返回 JSON 响应
# {"success":true,"data":{"status":"stopped",...}}
```

## 验证修复是否成功

### 1. 容器状态检查

```bash
docker-compose ps
```

期望输出：
```
NAME              IMAGE     COMMAND       SERVICE   STATUS
tg2em-tgstate     ...       ...          tgstate   Up 30 seconds
```

### 2. API 接口测试

```bash
# 测试状态接口
curl -X GET http://localhost:8001/api/management/status

# 测试信息接口
curl -X GET http://localhost:8001/api/management/info
```

成功响应示例：
```json
{
  "success": true,
  "data": {
    "status": "stopped",
    "pid": 0,
    "uptime": "0s",
    "start_time": "2025-10-09 13:40:00"
  }
}
```

### 3. 从前端服务测试

```bash
# 进入前端容器测试内部网络连接
docker exec -it tg2em-frontend curl http://tgstate:8001/api/management/status
```

## 常见问题排查

### 问题 1: 容器启动后立即退出

**排查步骤**:
```bash
# 查看详细日志
docker-compose logs tgstate

# 检查容器退出码
docker inspect tg2em-tgstate --format='{{.State.ExitCode}}'
```

**可能原因**:
- Go 程序编译错误
- 依赖缺失
- 端口被占用

**解决方案**:
```bash
# 检查端口占用
netstat -tlnp | grep 8001
# 或
ss -tlnp | grep 8001

# 如果端口被占用，停止占用进程或修改端口映射
```

### 问题 2: 管理 API 返回 500 错误

**排查步骤**:
```bash
# 查看前端服务日志
docker-compose logs frontend | grep tgstate

# 测试从前端容器内部访问
docker exec -it tg2em-frontend curl -v http://tgstate:8001/api/management/status
```

**可能原因**:
- tgstate 服务未启动
- 网络连接问题
- 代码未正确更新

**解决方案**:
```bash
# 确保使用最新代码
git pull

# 重新构建并启动
docker-compose build --no-cache tgstate
docker-compose up -d tgstate
```

### 问题 3: Docker 网络问题

**排查步骤**:
```bash
# 检查网络
docker network ls
docker network inspect tg2em-network

# 检查容器网络连接
docker exec -it tg2em-frontend ping tgstate
```

**解决方案**:
```bash
# 重建网络
docker-compose down
docker-compose up -d
```

### 问题 4: 镜像构建失败

**排查步骤**:
```bash
# 查看详细构建过程
docker-compose build --no-cache --progress=plain tgstate
```

**可能原因**:
- 网络问题（无法下载依赖）
- 磁盘空间不足
- Go 模块下载失败

**解决方案**:
```bash
# 检查磁盘空间
df -h

# 清理 Docker 缓存
docker system prune -a

# 配置 Go 代理（如果在中国）
# 编辑 services/tgstate/Dockerfile，在 RUN go mod download 前添加：
# ENV GOPROXY=https://goproxy.cn,direct
```

## 完整重新部署

如果修复仍然失败，可以尝试完全重新部署：

```bash
# 1. 停止所有服务
docker-compose down

# 2. 备份数据（如果需要）
docker run --rm -v tg2emall_mysql:/data -v $(pwd):/backup \
  alpine tar czf /backup/mysql_backup_$(date +%Y%m%d).tar.gz /data

# 3. 删除所有容器、网络和镜像
docker-compose down -v --rmi all

# 4. 拉取最新代码
git pull origin main

# 5. 重新构建和启动
docker-compose build --no-cache
docker-compose up -d

# 6. 查看启动日志
docker-compose logs -f
```

## 服务架构说明

### 端口说明

| 服务 | 容器内端口 | 主机映射端口 | 说明 |
|------|-----------|-------------|------|
| 管理服务 | 8001 | 8001 | HTTP 管理 API |
| 上传服务 | 8002 | 8002 | 图片上传服务 |

### 服务依赖

```
tgstate 容器启动
  └── management-service (8001)
      └── 管理 API 接口
      └── 可以启动/停止 upload-service (8002)
```

### 网络通信

- **外部访问**: `http://服务器IP:8001/api/management/status`
- **容器间通信**: `http://tgstate:8001/api/management/status`
- **前端服务访问**: 使用容器名 `tgstate` 而非 `localhost`

## 监控和日志

### 实时监控

```bash
# 查看所有服务状态
docker-compose ps

# 实时查看 CPU/内存使用
docker stats tg2em-tgstate

# 实时日志
docker-compose logs -f tgstate
```

### 日志管理

```bash
# 查看最近日志
docker-compose logs --tail=100 tgstate

# 导出日志到文件
docker-compose logs tgstate > tgstate_$(date +%Y%m%d).log

# 查看日志文件大小
du -sh /var/lib/docker/containers/*/
```

### 设置日志轮转

创建或编辑 `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

重启 Docker:
```bash
sudo systemctl restart docker
```

## 生产环境建议

### 1. 使用反向代理

配置 Nginx 反向代理：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/tgstate/ {
        proxy_pass http://localhost:8001/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 2. 配置防火墙

```bash
# 仅允许必要的端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp

# 不要直接暴露 Docker 端口到公网
```

### 3. 设置自动重启

确保 docker-compose.yml 中配置了：
```yaml
restart: always
```

### 4. 监控和告警

安装监控工具：
```bash
# 安装 ctop（容器监控）
sudo wget https://github.com/bcicen/ctop/releases/download/v0.7.7/ctop-0.7.7-linux-amd64 \
  -O /usr/local/bin/ctop
sudo chmod +x /usr/local/bin/ctop

# 使用
ctop
```

## 获取帮助

如果问题仍未解决，请提供以下信息：

```bash
# 1. 系统信息
uname -a
cat /etc/os-release

# 2. Docker 版本
docker --version
docker-compose --version

# 3. 容器状态
docker-compose ps

# 4. 完整日志
docker-compose logs tgstate > logs.txt

# 5. 网络信息
docker network inspect tg2em-network > network.txt
```

## 相关文件

- `services/tgstate/management-service.go` - 管理服务主程序（已修复）
- `services/tgstate/upload-service.go` - 上传服务程序
- `services/tgstate/Dockerfile` - Docker 构建文件
- `docker-compose.yml` - 服务编排配置（已修复）
- `env.example` - 环境变量示例（已修复）
- `fix_tgstate_remote.sh` - 自动修复脚本

## 更新日期

2025-10-09 - 修复 tgState 服务启动问题

