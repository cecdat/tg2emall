# Telegram 采集系统部署指南

## 🚀 Docker 整体部署

### 1. 快速启动
```bash
# 克隆项目
git clone <repository-url>
cd tg2emall

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 2. 验证码配置 (首次使用)
首次启动采集服务需要输入 Telegram 验证码：

```bash
# 连接到采集服务容器进行交互式验证
docker attach tg2em-scrape
```

**验证码输入流程：**
```
==================================================
Telegram 需要验证码验证
==================================================
请输入验证码 (5位数字): 
```

1. 输入手机接收的5位验证码
2. 如有两步验证，会提示输入密码
3. 验证成功后会显示 "✅ Telegram 验证成功！"
4. 退出 attach 模式按 `Ctrl+P` 然后 `Ctrl+Q`（不会停止容器）

### 3. 服务管理

**查看日志：**
```bash
docker-compose logs frontend     # 前端服务
docker-compose logs tg2em-scrape # 采集服务
docker-compose logs mysql        # 数据库服务
docker-compose logs tgstate      # 图片上传服务
```

**重启服务：**
```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart frontend
docker-compose restart tg2em-scrape
```

**重新构建：**
```bash
# 停止并重新构建所有服务
docker-compose down
docker-compose up --build -d
```

## 🌐 服务访问

启动成功后，各服务可通过以下地址访问：

- **前端展示**: http://localhost:5000
- **后台管理**: http://localhost:5000/admin
- **图片上传**: http://localhost:8088
- **反向代理管理**: http://localhost:81

## 📊 系统监控

### 服务健康检查
```bash
# 检查前端服务
curl http://localhost:5000/api/stats

# 检查数据库连接
docker-compose exec mysql mysql -u tg2em -p1989hewei -e "SHOW DATABASES;"

# 检查采集服务状态
docker-compose logs tg2em-scrape --tail 50
```

### 存储查看
```bash
# 查看数据存储
ls -la ./data/

# 查看日志文件
tail -f ./data/logs/scrape.log
```

## ⚠️ 部署注意事项

### 1. 首次部署
- ✅ 确保网络能够访问 Telegram 服务
- ✅ 准备好 Telegram 账号和验证码
- ✅ 检查防火墙设置，确保端口可用

### 2. 数据持久化
- 📁 `./data/mysql/` - 数据库文件
- 📁 `./data/telegram-dessions/` - Telegram 会话文件
- 📁 `./data/logs/` - 应用日志
- 📁 `./data/upload/` - 上传的图片文件

### 3. 环境变量
可通过 `.env` 文件自定义配置：
```bash
# Telegram 相关
TGSTATE_TOKEN=your_token
TGSTATE_TARGET=your_target
TGSTATE_PASS=your_pass
```

## 🛠 故障排除

### 常见问题

**1. 采集服务启动失败**
```bash
# 查看详细日志
docker-compose logs tg2em-scrape

# 检查配置文件
docker-compose exec tg2em-scrape cat config.yaml

# 如需手动输入验证码，使用attach模式
docker attach tg2em-scrape
# 验证完成后按 Ctrl+P, Ctrl+Q 退出attach模式
```

**2. 前端页面显示错误**
```bash
# 检查前端服务日志
docker-compose logs frontend

# 检查数据库连接
docker-compose exec mysql mysql -u tg2em -p1989hewei -e "USE tg2em; SHOW TABLES;"
```

**3. 数据库连接问题**
```bash
# 重启数据库服务
docker-compose restart mysql

# 检查数据库健康状态
docker-compose ps mysql
```

## 🔧 配置更新

### 修改配置文件
```bash
# 编辑采集配置
vim ./services/tg2em/config.yaml

# 重新构建采集服务
docker-compose up --build tg2em-scrape -d
```

### 更新依赖
```bash
# 更新 Python 依赖
vim ./services/tg2em/requirements.txt
docker-compose up --build tg2em-scrape -d

vim ./services/frontend/requirements.txt
docker-compose up --build frontend -d
```

## 📈 性能优化

### 系统资源
- 建议至少 2GB 内存
- 建议至少 20GB 硬盘空间
- 确保网络带宽充足

### 监控建议
- 定期检查日志文件大小
- 监控数据库空间使用
- 定期备份重要数据
