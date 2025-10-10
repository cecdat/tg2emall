# tg2emall 部署指南

## 🚀 快速部署

### 1. **克隆代码到远程服务器**
```bash
# 克隆项目
git clone https://github.com/cecdat/tg2emall.git
cd tg2emall

# 或者如果已有代码，拉取最新更新
git pull origin main
```

### 2. **配置环境变量**
```bash
# 复制环境变量文件
cp env.example .env

# 编辑配置文件
nano .env
```

**必需配置项**：
```bash
# Telegram API 配置
API_ID=your_api_id_here
API_HASH=your_api_hash_here
PHONE_NUMBER=+1234567890

# Telegram 验证配置
TELEGRAM_VERIFICATION_TIMEOUT=600

# tgState 图片上传服务配置 (可选)
TGSTATE_TOKEN=your_bot_token_here
TGSTATE_TARGET=@your_channel_name
TGSTATE_PASS=your_password_here
TGSTATE_MODE=p
TGSTATE_URL=http://your-domain.com:8088

# 公网访问地址
PUBLIC_URL=http://your-domain.com:8088

# MySQL 数据库配置
MYSQL_ROOT_PASSWORD=tg2emall
MYSQL_DATABASE=tg2em
MYSQL_USER=tg2emall
MYSQL_PASSWORD=tg2emall

# 时区配置
TZ=Asia/Shanghai
```

### 3. **启动服务**
```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. **配置Telegram参数**
1. 访问管理后台：`http://your-server:8000/dm`
2. 用户名：`admin`，密码：`admin`，验证码：`2025`
3. 进入"配置管理"页面
4. 配置Telegram API参数：
   - API ID
   - API Hash  
   - 手机号码
5. 保存配置

### 5. **启动采集服务**
1. 在管理后台进入"服务管理"页面
2. 启动"采集服务"
3. 如果首次运行，会提示需要验证码
4. 进入"Telegram验证"页面输入验证码

## 🔧 服务端口说明

| 服务 | 端口 | 描述 |
|------|------|------|
| 前端服务 | 8000 | Web展示和管理界面 |
| MySQL | 3306 | 数据库服务 |
| 采集管理服务 | 2003 | 采集服务管理接口 |
| 采集服务 | 5002 | 实际采集业务服务 |
| tgState管理服务 | 8001 | 图片服务管理接口 |
| tgState上传服务 | 8002 | 图片上传业务服务 |
| tgState管理页面 | 8088 | 图片服务Web界面 |

## 📋 配置管理

### 1. **数据库配置支持**
所有配置都可以通过Web界面管理：
- Telegram API配置
- 采集参数配置
- 图片处理配置
- 频道配置
- 屏蔽标签配置

### 2. **配置热更新**
- 配置修改后自动生效
- 无需重启服务
- 支持配置缓存机制

### 3. **配置优先级**
1. 数据库配置（最高优先级）
2. 环境变量
3. config.yaml（默认值）

## 🛠️ 故障排除

### 1. **服务启动失败**
```bash
# 查看详细日志
docker-compose logs [service_name]

# 重启特定服务
docker-compose restart [service_name]

# 重新构建并启动
docker-compose up --build -d
```

### 2. **数据库连接问题**
```bash
# 检查数据库状态
docker-compose exec mysql mysql -u root -ptg2emall -e "SHOW DATABASES;"

# 重启数据库
docker-compose restart mysql
```

### 3. **Telegram验证问题**
1. 检查API ID和API Hash是否正确
2. 确认手机号码格式（包含国家代码）
3. 在"Telegram验证"页面输入验证码
4. 检查网络连接是否正常

### 4. **图片上传问题**
1. 检查tgState服务是否启动
2. 验证tgState配置参数
3. 检查网络连接和端口访问

## 📊 监控和维护

### 1. **查看服务状态**
```bash
# 查看所有服务状态
docker-compose ps

# 查看资源使用情况
docker stats

# 查看日志
docker-compose logs -f [service_name]
```

### 2. **数据备份**
```bash
# 备份数据库
docker-compose exec mysql mysqldump -u root -ptg2emall tg2em > backup_$(date +%Y%m%d).sql

# 备份会话文件
tar -czf telegram_sessions_$(date +%Y%m%d).tar.gz data/telegram-sessions/
```

### 3. **清理和维护**
```bash
# 清理未使用的Docker资源
docker system prune -f

# 清理日志文件
docker-compose logs --tail=0 -f | head -n 0
```

## 🔄 更新部署

### 1. **代码更新**
```bash
# 拉取最新代码
git pull origin main

# 重新构建并启动
docker-compose up --build -d
```

### 2. **配置迁移**
- 新版本会自动处理配置迁移
- 现有配置保持不变
- 新增配置项使用默认值

## 🎯 性能优化

### 1. **资源配置**
- 建议至少2GB内存
- 10GB以上磁盘空间
- 稳定的网络连接

### 2. **配置调优**
- 调整采集间隔避免频繁请求
- 配置合适的图片压缩参数
- 设置合理的日志保留策略

## 📞 技术支持

如果遇到问题，请检查：
1. 系统日志：`docker-compose logs`
2. 配置文档：`DATABASE_CONFIG_SUPPORT.md`
3. 优化说明：`TELEGRAM_OPTIMIZATION_SUMMARY.md`

## 🎉 部署完成

部署完成后，你可以：
1. 访问前端：`http://your-server:8000`
2. 管理后台：`http://your-server:8000/dm`
3. 图片服务：`http://your-server:8088`
4. 通过Web界面管理所有配置和监控服务状态
