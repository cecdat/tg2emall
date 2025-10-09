# 快速开始指南

## ⚡ 您的采集任务正在等待验证码！

### 立即操作（30秒完成）

```bash
# 将下面的 12345 替换为您手机收到的5位验证码
CODE="12345"

docker exec tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
INSERT INTO system_config (config_key, config_value, config_type) 
VALUES ('telegram_verification_code', '$CODE', 'string')
ON DUPLICATE KEY UPDATE config_value = '$CODE', updated_at = NOW();

INSERT INTO system_config (config_key, config_value, config_type) 
VALUES ('telegram_verification_submitted', 'true', 'boolean')
ON DUPLICATE KEY UPDATE config_value = 'true', updated_at = NOW();
"

echo "✅ 验证码已提交: $CODE"
docker logs -f tg2em-scrape
```

**预期结果**（几秒内）：
```
✅ 收到Web界面验证码: xxxxx
✅ Telegram验证成功！当前用户: @your_username
📁 会话已保存至: /app/sessions/tg2em_scraper.session
🚀 开始采集任务...
```

---

## 🔄 更新前端（使用Web界面）

验证成功后，更新前端以便下次使用Web界面：

```bash
# 在远程服务器执行
cd ~/tg2emall

# 使用新的update命令（自动拉取代码）
./deploy.sh update

# 或者手动执行
git pull origin main
docker-compose build --no-cache frontend
docker-compose restart frontend
```

---

## 📋 部署脚本新功能

### 自动拉取代码

现在 `deploy.sh` 会自动拉取最新代码：

```bash
# 完整部署（自动拉取代码）
./deploy.sh

# 仅更新代码和服务
./deploy.sh update

# 仅拉取代码
./deploy.sh pull
```

### 智能处理本地修改

如果有本地修改：
1. 脚本会提示暂存本地修改
2. 拉取最新代码
3. 询问是否恢复本地修改

### 新增命令

```bash
./deploy.sh update   # 更新代码并重新构建服务
./deploy.sh pull     # 仅拉取最新代码（不重新构建）
./deploy.sh status   # 查看服务状态和访问地址
./deploy.sh logs     # 查看所有服务日志
```

---

## 🎯 完整的Web界面功能

更新前端后，您可以：

### 1. Telegram验证页面

**位置**：左侧菜单 → "Telegram验证"

**功能**：
- ✅ 实时状态显示
- ✅ 验证码输入框
- ✅ 真实Docker日志显示
- ✅ 自动刷新（每10秒）
- ✅ 重置验证功能

### 2. 服务管理页面

**位置**：左侧菜单 → "服务管理" → "采集服务"

**功能**：
- ✅ 启动/停止/重启服务
- ✅ **启动采集任务**按钮 ⭐
- ✅ 服务状态监控
- ✅ 双服务架构信息

### 3. 配置管理页面

**功能**：
- ✅ Telegram参数配置
- ✅ 图片服务配置
- ✅ 采集频道配置
- ✅ 验证状态提醒

---

## 📊 操作流程对比

### 之前（❌ 复杂）

```
1. SSH到服务器
2. 手动拉取代码
3. 手动重新构建
4. 手动重启服务
5. 查看日志找验证码提示
6. 手动执行SQL提交验证码
7. 继续查看日志等待验证
```

### 现在（✅ 简单）

```
1. 运行 ./deploy.sh update（自动拉取+构建）
2. 访问 http://公网IP:8000/dm
3. 点击"Telegram验证"
4. 输入验证码
5. 完成！✅
```

---

## 🧪 快速测试

### 测试更新功能

```bash
cd ~/tg2emall

# 测试仅拉取代码
./deploy.sh pull

# 测试完整更新
./deploy.sh update
```

### 测试Web验证界面

```bash
# 获取访问地址
PUBLIC_IP=$(curl -s ifconfig.me)
echo "管理后台: http://$PUBLIC_IP:8000/dm"
echo "左侧菜单 → Telegram验证"
```

---

## 📝 所有可用命令

```bash
# 部署相关
./deploy.sh              # 完整部署（自动拉取代码）
./deploy.sh update       # 更新代码并重新构建
./deploy.sh pull         # 仅拉取代码

# 服务控制
./deploy.sh start        # 启动服务
./deploy.sh stop         # 停止服务
./deploy.sh restart      # 重启服务
./deploy.sh status       # 查看状态

# 镜像和日志
./deploy.sh build        # 构建镜像
./deploy.sh logs         # 查看日志

# 数据库
./deploy.sh backup       # 备份数据库
./deploy.sh restore      # 恢复数据库
./deploy.sh init-db      # 初始化数据库
./deploy.sh check-db     # 检查数据库

# 清理
./deploy.sh clean        # 清理所有数据
```

---

## ✅ 立即验证码提交（快速）

由于您的采集任务正在等待，现在立即提交验证码：

```bash
# 执行这一个命令（替换验证码）
CODE="您的5位验证码" && docker exec tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "INSERT INTO system_config (config_key, config_value, config_type) VALUES ('telegram_verification_code', '$CODE', 'string') ON DUPLICATE KEY UPDATE config_value = '$CODE', updated_at = NOW(); INSERT INTO system_config (config_key, config_value, config_type) VALUES ('telegram_verification_submitted', 'true', 'boolean') ON DUPLICATE KEY UPDATE config_value = 'true', updated_at = NOW();" && echo "✅ 验证码已提交" && docker logs -f tg2em-scrape
```

---

## 🎯 下次使用

```bash
# 1. 更新代码和服务
./deploy.sh update

# 2. 访问Web界面操作
http://公网IP:8000/dm
  → 服务管理 → 采集服务 → 启动采集任务
  → Telegram验证 → 输入验证码（如需要）

# 3. 查看采集结果
http://公网IP:8000
```

简单！✅

---

**提交**: 36e1e4b  
**功能**: 自动拉取最新代码

