# 端口和地址问题修复指南

## 🔍 问题说明

### 1. ERR_UNSAFE_PORT 错误
- **原因**: Chrome/Edge 浏览器将 6000 端口列为"不安全端口"，会阻止访问
- **解决**: 将前端端口改为 8000（安全端口）

### 2. 地址使用问题
- ❌ **错误**: 使用 `localhost` 或 `127.0.0.1`
- ✅ **正确**: 
  - 前端访问：使用公网IP或域名
  - 容器间通信：使用容器名（如 `mysql`, `tgstate`, `tg2em-scrape`）

---

## 🛠️ 修复步骤

### 步骤1：更新配置文件

已修改的文件：
- ✅ `docker-compose.yml` - 前端端口改为 8000
- ✅ `services/frontend/app.py` - 自动获取公网IP
- ✅ `services/tg2em/scrape.py` - 容器间使用容器名

### 步骤2：更新数据库配置

连接到数据库并更新配置：

```sql
-- 连接数据库
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em

-- 更新 tgState URL（使用实际的公网IP或域名）
UPDATE system_config 
SET config_value = 'http://YOUR_PUBLIC_IP:6001' 
WHERE config_key = 'tgstate_url';

-- 或者使用域名
UPDATE system_config 
SET config_value = 'https://img.yourdomain.com' 
WHERE config_key = 'tgstate_url';

-- 查看更新结果
SELECT config_key, config_value FROM system_config WHERE config_key LIKE '%url%';
```

### 步骤3：重启服务

```bash
# 停止所有服务
docker-compose down

# 重新构建并启动
docker-compose build frontend
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看前端日志
docker-compose logs -f frontend
```

---

## 📋 端口对照表

### 对外访问端口（需要公网IP/域名）

| 服务 | 旧端口 | 新端口 | 访问地址示例 | 说明 |
|------|--------|--------|--------------|------|
| 前端展示 | 6000 | **8000** | `http://公网IP:8000` | 主站 |
| 管理后台 | 6000 | **8000** | `http://公网IP:8000/dm` | 管理界面 |
| NPM管理 | 81 | 81 | `http://公网IP:81` | Nginx代理管理 |
| 图片管理 | 6001 | 6001 | `http://公网IP:6001` | tgState管理 |
| 采集管理 | 2003 | 2003 | `http://公网IP:2003` | 采集服务管理 |

### 容器间通信（使用容器名）

| 通信方向 | 容器名 | 端口 | 地址示例 |
|----------|--------|------|----------|
| Frontend → MySQL | `mysql` | 3306 | `mysql:3306` |
| Frontend → tgState | `tg2em-tgstate` | 6001 | `tg2em-tgstate:6001` |
| Frontend → Scraper | `tg2em-scrape` | 2003 | `tg2em-scrape:2003` |
| Scraper → MySQL | `mysql` | 3306 | `mysql:3306` |
| Scraper → tgState | `tg2em-tgstate` | 6001 | `tg2em-tgstate:6001` |

---

## 🌐 获取公网IP方法

### 方法1：自动获取（推荐）
应用启动时会自动获取并显示公网IP

### 方法2：手动查询
```bash
# Linux服务器
curl ifconfig.me

# 或
curl api.ipify.org

# Windows PowerShell
(Invoke-WebRequest -Uri "https://api.ipify.org").Content
```

---

## 🔧 配置示例

### 完整的环境变量配置（.env）

```env
# ========== 前端配置 ==========
FRONTEND_PORT=8000

# ========== tgState 图床配置 ==========
TGSTATE_TOKEN=your_bot_token
TGSTATE_TARGET=@your_channel
TGSTATE_PASS=your_password
TGSTATE_MODE=p
TGSTATE_URL=http://YOUR_PUBLIC_IP:6001

# ========== Telegram 采集配置 ==========
API_ID=your_api_id
API_HASH=your_api_hash
PHONE_NUMBER=+8613800138000

# ========== MySQL 配置 ==========
MYSQL_ROOT_PASSWORD=tg2emall
MYSQL_DATABASE=tg2em
MYSQL_USER=tg2emall
MYSQL_PASSWORD=tg2emall
```

### 管理后台配置路径

1. 访问：`http://YOUR_PUBLIC_IP:8000/dm`
2. 登录：用户名 `admin`，密码 `admin`，验证码 `2025`
3. 进入"配置管理"
4. 修改以下配置：
   - `tgstate_url`: `http://YOUR_PUBLIC_IP:6001`
   - 其他相关URL配置

---

## ✅ 验证清单

- [ ] 前端可以通过 `http://公网IP:8000` 访问
- [ ] 管理后台可以通过 `http://公网IP:8000/dm` 访问
- [ ] 不再出现 ERR_UNSAFE_PORT 错误
- [ ] 容器间可以正常通信（查看日志无连接错误）
- [ ] 图片上传服务正常工作
- [ ] 采集服务可以连接到 MySQL

---

## 🚨 常见问题

### Q1: 修改后仍然无法访问
**A**: 检查防火墙规则
```bash
# 开放 8000 端口
sudo ufw allow 8000/tcp

# 或者在云服务商控制台添加安全组规则
```

### Q2: 容器间无法通信
**A**: 确保所有容器在同一网络
```bash
# 检查网络
docker network inspect tg2em-network

# 重新创建网络
docker network rm tg2em-network
docker network create tg2em-network
docker-compose up -d
```

### Q3: 公网IP获取失败
**A**: 手动设置环境变量
```bash
export PUBLIC_IP=$(curl -s ifconfig.me)
echo "PUBLIC_IP=$PUBLIC_IP" >> .env
```

---

## 📞 支持

如有问题，请查看日志：
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f frontend
docker-compose logs -f tg2em-scrape
```

