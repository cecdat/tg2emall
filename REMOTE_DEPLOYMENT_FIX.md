# tg2emall 远程服务器部署修复指南

## 🚨 当前问题

1. **tgState服务管理接口连接失败**
   - 错误：无法连接到 tgstate-service 管理接口
   - 原因：tgState服务未运行或端口配置错误

2. **采集服务管理问题**
   - 采集服务可能自动启动，无法通过管理后台控制
   - 服务状态获取失败

## 🔧 快速修复步骤

### 1. 检查当前状态

```bash
# 在远程服务器上执行
cd /path/to/tg2emall
chmod +x check_services.sh
./check_services.sh
```

### 2. 修复服务问题

```bash
# 修复服务管理问题
chmod +x fix_services.sh
./fix_services.sh
```

### 3. 重新启动服务

```bash
# 完全重新部署
chmod +x start_services.sh
./start_services.sh
```

## 📋 详细修复步骤

### 步骤1：检查环境配置

```bash
# 1. 检查 .env 文件是否存在
ls -la .env

# 2. 如果不存在，创建配置文件
cp env.example .env
nano .env  # 编辑配置文件
```

**必需的 .env 配置：**
```ini
# Telegram API 配置（必需）
API_ID=your_api_id_here
API_HASH=your_api_hash_here
PHONE_NUMBER=+1234567890

# tgState 配置（可选，如果不配置会使用本地存储）
TGSTATE_TOKEN=your_bot_token_here
TGSTATE_TARGET=@your_channel_name
TGSTATE_PASS=your_password_here
TGSTATE_MODE=p
TGSTATE_URL=http://your-domain.com:8088

# 公网访问地址（重要）
PUBLIC_URL=http://your-domain.com:8088
```

### 步骤2：停止并清理现有服务

```bash
# 停止所有服务
docker-compose down

# 清理Docker资源
docker system prune -f

# 删除可能有问题的镜像
docker rmi $(docker images -q tg2emall_*) 2>/dev/null || true
```

### 步骤3：重新构建和启动

```bash
# 重新构建服务
docker-compose build --no-cache

# 启动服务
docker-compose up -d

# 查看启动日志
docker-compose logs -f
```

### 步骤4：验证服务状态

```bash
# 检查容器状态
docker-compose ps

# 检查端口监听
netstat -tlnp | grep -E "(8000|2003|5002|8001|8002|8088|3306)"

# 测试服务接口
curl http://localhost:8000
curl http://localhost:2003/api/management/status
curl http://localhost:8001/api/management/status
curl http://localhost:8088
```

## 🔍 故障排除

### 问题1：tgState服务无法启动

**症状：** 无法连接到 tgstate-service 管理接口

**解决方案：**
```bash
# 检查tgState容器日志
docker-compose logs tgstate

# 检查端口是否被占用
netstat -tlnp | grep 8001

# 重启tgState服务
docker-compose restart tgstate
```

### 问题2：采集服务自动启动

**症状：** 采集服务在管理后台显示为运行中，但无法控制

**解决方案：**
```bash
# 停止采集服务
docker-compose stop tg2em-scrape

# 检查是否有其他进程占用端口
lsof -i :2003
lsof -i :5002

# 重新启动
docker-compose up -d tg2em-scrape
```

### 问题3：端口冲突

**症状：** 服务启动失败，端口被占用

**解决方案：**
```bash
# 查找占用端口的进程
sudo netstat -tlnp | grep -E "(8000|2003|5002|8001|8002|8088|3306)"

# 杀死占用端口的进程
sudo kill -9 <PID>

# 或者修改 docker-compose.yml 中的端口映射
```

### 问题4：数据库连接失败

**症状：** 服务启动后无法连接数据库

**解决方案：**
```bash
# 检查MySQL容器状态
docker-compose logs mysql

# 重启MySQL服务
docker-compose restart mysql

# 等待MySQL完全启动
sleep 30

# 测试数据库连接
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall -e "SELECT 1;"
```

## 📊 服务端口说明

| 服务 | 容器名 | 端口 | 功能 |
|------|--------|------|------|
| 前端服务 | tg2em-frontend | 8000 | Web界面 |
| MySQL | tg2em-mysql | 3306 | 数据库 |
| 采集管理 | tg2em-scrape | 2003 | 采集服务管理API |
| 采集服务 | tg2em-scrape | 5002 | 采集业务服务API |
| tgState管理 | tg2em-tgstate | 8001 | 图片服务管理API |
| tgState上传 | tg2em-tgstate | 8002 | 图片上传API |
| tgState页面 | tg2em-tgstate | 8088 | 图片管理页面 |

## 🌐 访问地址

- **前端页面**: http://your-server-ip:8000
- **管理后台**: http://your-server-ip:8000/admin
- **tgState管理**: http://your-server-ip:8088

## 🔑 默认账号

- **管理员用户名**: admin
- **管理员密码**: admin123

## 📝 常用命令

```bash
# 查看所有服务状态
docker-compose ps

# 查看服务日志
docker-compose logs -f

# 重启特定服务
docker-compose restart <service_name>

# 停止所有服务
docker-compose down

# 启动所有服务
docker-compose up -d

# 查看资源使用情况
docker stats
```

## ⚠️ 注意事项

1. **防火墙设置**: 确保服务器防火墙允许相关端口访问
2. **资源要求**: 建议至少2GB内存，2核CPU
3. **磁盘空间**: 确保有足够的磁盘空间存储图片和日志
4. **网络配置**: 确保服务器可以访问Telegram API和外部网络

## 🆘 获取帮助

如果问题仍然存在，请提供以下信息：

1. 服务器操作系统版本
2. Docker版本 (`docker --version`)
3. 服务启动日志 (`docker-compose logs`)
4. 系统资源使用情况 (`free -h`, `df -h`)
5. 网络连接测试结果
