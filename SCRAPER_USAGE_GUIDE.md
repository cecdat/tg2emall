# 采集服务使用指南

## 🎯 重要说明

### 采集服务的双层架构

采集服务采用**双服务架构**，分为两个独立的部分：

1. **管理服务**（端口2003）- 始终运行
   - 负责控制采集服务的启停
   - 提供管理API接口
   - 自动随容器启动

2. **采集服务**（端口5002）- 需要手动启动
   - 负责实际的Telegram采集任务
   - 由管理服务控制启停
   - 执行登录和采集逻辑

### 采集任务的两步操作

⚠️ **关键理解**：启动采集服务 ≠ 启动采集任务

```
第1步: 启动采集服务（Flask API服务器）
   ↓
第2步: 启动采集任务（实际执行Telegram登录和采集）⭐ 这一步才会登录！
```

---

## 🚀 完整操作流程

### 步骤1：配置Telegram参数

1. 访问管理后台：`http://公网IP:8000/dm`
2. 登录（用户名：admin，密码：admin，验证码：2025）
3. 进入"配置管理"
4. 配置以下参数：
   ```
   telegram_api_id: 你的API ID
   telegram_api_hash: 你的API Hash  
   telegram_phone: +8613800138000（必须带国家代码）
   scrape_channels: 要采集的频道列表
   ```
5. 点击"保存配置"

### 步骤2：启动采集服务

1. 在管理后台点击"服务管理"
2. 选择"采集服务"
3. 点击"启动服务"按钮
4. 等待提示"启动成功"

**日志输出**（在容器中）：
```bash
✅ 从数据库获取Telegram配置: API_ID=1908***, Phone=+12282078999
📋 准备启动采集服务，配置信息:
   - API_ID: 1908***
   - API_Hash: ****
   - Phone: +12282078999
✅ 采集服务启动成功，PID: 10

# 采集服务（Flask服务器）启动
🚀 tg2em采集服务启动中...
📊 采集服务PID: 10
 * Running on http://0.0.0.0:5002
```

**此时**：采集服务（Flask API）已启动，但**还没有执行采集任务**！

### 步骤3：启动采集任务 ⭐ 关键步骤！

1. 在"采集服务管理"页面
2. 点击"**启动采集任务**"按钮（新增的蓝色按钮）
3. 确认启动
4. 等待响应

**日志输出**（现在才会看到登录过程）：
```bash
# 收到启动采集任务的API调用
172.20.0.4 - - [09/Oct/2025 11:20:00] "POST /api/scraper/start HTTP/1.1" 200 -

# 开始执行采集任务
🚀 开始采集任务...
🔐 初始化 Telegram 客户端...

# 首次运行：
📄 会话文件不存在，需要首次登录
🔐 开始Telegram登录流程...
📱 需要验证码，等待Web界面输入...

🔔 Telegram 需要验证码验证
📱 请前往管理后台输入验证码
🌐 访问地址: http://localhost:5000/dm
```

### 步骤4：输入Telegram验证码（首次运行）

1. 查看手机收到的Telegram验证码（5位数字）
2. 回到管理后台
3. 点击"Telegram验证"
4. 输入验证码
5. 点击"提交验证"

**日志输出**：
```bash
⏳ 等待验证码输入... (2s/300s)
⏳ 等待验证码输入... (4s/300s)
✅ 收到Web界面验证码: 12345
✅ Telegram验证成功！当前用户: @your_username
📁 会话已保存至: /app/sessions/tg2em_scraper.session

# 开始采集
✅ Telegram客户端启动成功
🚀 开始采集任务...
Telegram 客户端启动成功
开始采集频道消息...
```

### 步骤5：后续运行（自动使用已保存的会话）

后续再次启动采集任务时：

1. 点击"启动采集任务"
2. 无需验证码，直接开始采集

**日志输出**：
```bash
🚀 开始采集任务...
🔐 初始化 Telegram 客户端...
📄 发现会话文件: /app/sessions/tg2em_scraper.session
🔍 检查会话有效性...
✅ 会话有效！当前用户: @your_username (ID: 123456789)
🔄 使用已保存的有效会话，直接连接...
✅ Telegram客户端启动成功
🚀 开始采集任务...
```

---

## 📊 界面说明

### 管理后台 - 采集服务管理页面

访问：`http://公网IP:8000/dm` → 服务管理 → 采集服务

**服务控制区域**：

```
┌─────────────────────────────────┐
│        服务控制                  │
├─────────────────────────────────┤
│  [停止服务]                      │  ← 停止采集服务（Flask API）
│  [重启服务]                      │  ← 重启采集服务
│  ────────────────────────        │
│  [启动采集任务] ⭐ 新增！        │  ← 启动实际的采集任务（登录+采集）
│  ℹ️ 启动Telegram采集任务         │
│     （首次需要验证）              │
│  [刷新状态]                      │
└─────────────────────────────────┘
```

---

## 🔍 常见问题

### Q1: 为什么点击"启动服务"后没有看到登录？

**A**: "启动服务"只是启动Flask API服务器，不会执行采集任务。需要再点击"**启动采集任务**"按钮才会真正登录Telegram。

### Q2: 启动采集任务后没有反应？

**A**: 查看容器日志：
```bash
docker logs -f tg2em-scrape
```

检查是否有错误信息。

### Q3: 验证页面显示"验证已完成"但实际没有登录？

**A**: 这是因为数据库中缓存了旧的验证状态。清除状态：

```bash
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
DELETE FROM system_config WHERE config_key LIKE '%verification%';
"
```

然后重新启动采集任务。

### Q4: 如何知道采集任务是否在运行？

**A**: 查看日志中是否有以下信息：

```bash
# 任务运行中的标志：
🚀 开始采集任务...
Telegram 客户端启动成功
开始采集频道消息...
采集到 X 条新消息
```

---

## 📝 完整的日志示例

### 首次运行（需要验证码）

```bash
# 1. 启动采集服务
209.141.50.239 - - [09/Oct/2025 11:15:57] "POST /api/management/start HTTP/1.1" 200 -
✅ 采集模块导入成功
🚀 tg2em采集服务启动中...
📊 采集服务PID: 10
 * Running on http://0.0.0.0:5002

# 2. 启动采集任务 ⭐
172.20.0.4 - - [09/Oct/2025 11:20:00] "POST /api/scraper/start HTTP/1.1" 200 -
🚀 开始采集任务...
🔐 初始化 Telegram 客户端...
📄 会话文件不存在，需要首次登录
🔐 开始Telegram登录流程...
📱 需要验证码，等待Web界面输入...

🔔 Telegram 需要验证码验证
📱 请前往管理后台输入验证码

# 3. 在Web界面输入验证码后
⏳ 等待验证码输入... (6s/300s)
✅ 收到Web界面验证码: 12345
✅ Telegram验证成功！当前用户: @your_username
📁 会话已保存至: /app/sessions/tg2em_scraper.session

# 4. 开始采集
✅ Telegram客户端启动成功
🚀 开始采集任务...
Telegram 客户端启动成功
开始采集频道消息...
采集到 5 条新消息
✅ 采集任务完成
```

### 后续运行（使用已保存会话）

```bash
# 点击"启动采集任务"
172.20.0.4 - - [09/Oct/2025 11:25:00] "POST /api/scraper/start HTTP/1.1" 200 -
🚀 开始采集任务...
🔐 初始化 Telegram 客户端...
📄 发现会话文件: /app/sessions/tg2em_scraper.session
🔍 检查会话有效性...
✅ 会话有效！当前用户: @your_username (ID: 123456789)
✅ Telegram客户端已连接，无需重新登录 (用户: @your_username)
✅ Telegram 客户端初始化成功
🚀 开始采集任务...
开始采集频道消息...
采集到 3 条新消息
✅ 采集任务完成
```

---

## 🎯 操作要点

### ✅ 正确的操作顺序

1. **配置管理** → 填写Telegram参数
2. **服务管理** → 点击"启动服务"（启动Flask API）
3. **服务管理** → 点击"**启动采集任务**"（⭐ 这一步才登录和采集！）
4. **Telegram验证** → 输入验证码（仅首次需要）

### ❌ 常见误区

- ❌ 只点击"启动服务"就期望开始采集
  - ✅ 需要再点击"启动采集任务"

- ❌ 在Telegram验证页面等待
  - ✅ 应该先启动采集任务，然后才需要验证

- ❌ 使用localhost地址
  - ✅ 使用公网IP地址访问

---

## 📞 查看采集进度

```bash
# 实时查看采集日志
docker logs -f tg2em-scrape

# 查看最近100行日志
docker logs --tail=100 tg2em-scrape

# 查看采集到的消息
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
SELECT id, title, created_at FROM messages ORDER BY created_at DESC LIMIT 10;
"
```

---

## 🔄 自动化采集（定时任务）

如果需要定时自动采集，可以配置cron任务：

```bash
# 创建采集任务脚本
cat > /root/tg2emall/trigger_scrape.sh << 'EOF'
#!/bin/bash
# 触发采集任务

# 获取认证token（假设已登录）
COOKIE=$(curl -s -c - http://localhost:8000/dm/login -X POST \
  -d "username=admin&password=admin&captcha=2025" | grep session | awk '{print $7}')

# 调用采集任务API
curl -X POST http://localhost:8000/admin/services/scraper/scrape/start \
  -H "Cookie: session=$COOKIE" \
  -H "Content-Type: application/json"

echo "采集任务已触发"
EOF

chmod +x /root/tg2emall/trigger_scrape.sh

# 添加cron任务（每小时执行一次）
crontab -e

# 添加以下行：
0 * * * * /root/tg2emall/trigger_scrape.sh >> /root/tg2emall/cron.log 2>&1
```

---

## 📊 提交总结

### 最新提交：d143f65

**标题**：`feat:add-start-scraping-task-button-in-admin`

**修改内容**：
1. 在管理后台添加"启动采集任务"按钮
2. 添加 `/admin/services/<service_name>/scrape/start` API路由
3. 实现启动采集任务的前后端逻辑

**影响**：
- 用户现在可以通过Web界面启动采集任务
- 清晰区分"启动服务"和"启动任务"
- 首次运行会提示需要验证码

---

## 🎯 快速开始

### 一键启动采集（完整流程）

```bash
# 在远程服务器执行：
cd ~/tg2emall

# 1. 拉取最新代码
git checkout -- deploy.sh  # 如果有冲突
git pull origin main

# 2. 重新构建
docker-compose build --no-cache

# 3. 重启服务
docker-compose down
docker-compose up -d

# 4. 查看日志
docker logs -f tg2em-scrape
```

然后：
1. 访问 `http://公网IP:8000/dm`
2. 进入"服务管理" → "采集服务"
3. 如果服务已停止，点击"启动服务"
4. **点击"启动采集任务"** ⭐
5. 如果需要验证码，前往"Telegram验证"页面输入

---

## ✅ 成功标志

采集任务成功运行的标志：

1. **日志中出现**：
   ```
   🔐 初始化 Telegram 客户端...
   ✅ Telegram客户端启动成功
   🚀 开始采集任务...
   开始采集频道消息...
   ```

2. **数据库中有新消息**：
   ```bash
   docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e \
     "SELECT COUNT(*) as total FROM messages;"
   ```

3. **前端页面能看到文章**：
   访问 `http://公网IP:8000`

---

**更新时间**: 2025-10-09  
**提交**: d143f65  
**重要**: 记得点击"启动采集任务"按钮！

