# 采集服务故障排查指南

## 🔍 问题：采集服务显示启动但没有实际执行

### 症状描述
1. 管理后台显示"采集服务启动成功"
2. 但容器日志中看不到采集服务的实际日志
3. Telegram验证页面显示"验证已完成"但实际没有登录
4. 日志显示：`Phone=`（电话号码为空）

---

## 🛠️ 修复内容（提交 426daa6）

### 1. 修复日志输出问题

**问题**：采集服务的 stdout/stderr 被 PIPE 捕获，导致看不到日志

**修复**：
```python
# 之前：
self.scraper_process = subprocess.Popen(
    cmd, env=env,
    stdout=subprocess.PIPE,  # ❌ 日志被捕获
    stderr=subprocess.PIPE,  # ❌ 日志被捕获
)

# 修复后：
self.scraper_process = subprocess.Popen(
    cmd, env=env,
    stdout=None,  # ✅ 直接输出到容器日志
    stderr=None,  # ✅ 直接输出到容器日志
)
```

### 2. 添加配置验证

**新增**：启动前检查配置完整性
```python
if not self.config['api_id'] or not self.config['api_hash']:
    print("❌ Telegram配置不完整")
    return {'success': False, 'message': '请配置API ID和API Hash'}

if not self.config['phone_number']:
    print("⚠️  警告: 未配置手机号码")
```

### 3. 添加详细日志

**新增**：启动时显示配置信息
```python
print("📋 准备启动采集服务，配置信息:")
print(f"   - API_ID: {api_id[:4]}***")
print(f"   - API_Hash: {api_hash[:4]}***")
print(f"   - Phone: {phone_number or '未配置'}")
```

---

## 🚀 部署修复

### 步骤1：拉取最新代码

```bash
cd ~/tg2emall
git pull origin main
```

### 步骤2：重新构建采集服务

```bash
docker-compose build tg2em-scrape
```

### 步骤3：停止并重启服务

```bash
# 停止采集服务
docker-compose stop tg2em-scrape

# 启动采集服务
docker-compose up -d tg2em-scrape
```

### 步骤4：查看日志（现在可以看到详细日志了）

```bash
# 实时查看采集服务日志
docker logs -f tg2em-scrape

# 应该看到类似输出：
# ✅ 从数据库获取Telegram配置: API_ID=1234***, Phone=+8613800138000
# 📋 准备启动采集服务，配置信息:
#    - API_ID: 1234***
#    - API_Hash: abcd***
#    - Phone: +8613800138000
#    - MySQL: mysql:tg2em
# ✅ 采集服务启动成功，PID: 123
# 
# 🔐 初始化 Telegram 客户端...
# 📄 发现会话文件: /app/sessions/tg2em_scraper.session
# 🔍 检查会话有效性...
# ✅ 会话有效！当前用户: @username (ID: 123456789)
```

---

## 📋 配置Telegram参数

### 方式1：通过管理后台配置（推荐）

1. 访问管理后台：`http://公网IP:8000/dm`
2. 登录（用户名：admin，密码：admin，验证码：2025）
3. 进入"配置管理"
4. 找到Telegram配置部分，填写：
   ```
   telegram_api_id: 你的API ID
   telegram_api_hash: 你的API Hash
   telegram_phone: +8613800138000（带国家代码）
   ```
5. 点击"保存配置"

### 方式2：直接修改数据库

```bash
# 连接数据库
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em

# 更新配置
UPDATE system_config SET config_value = '你的API_ID' WHERE config_key = 'telegram_api_id';
UPDATE system_config SET config_value = '你的API_HASH' WHERE config_key = 'telegram_api_hash';
UPDATE system_config SET config_value = '+8613800138000' WHERE config_key = 'telegram_phone';

# 查看配置
SELECT config_key, config_value FROM system_config WHERE config_key LIKE 'telegram_%';

# 退出
exit
```

### 方式3：通过环境变量（不推荐，会被数据库配置覆盖）

编辑 `docker-compose.yml`:
```yaml
tg2em-scrape:
  environment:
    API_ID: "你的API_ID"
    API_HASH: "你的API_HASH"
    PHONE_NUMBER: "+8613800138000"
```

---

## 🔐 Telegram首次验证流程

### 正常流程

1. **启动采集服务**
   ```bash
   # 在管理后台点击"启动采集服务"
   # 或命令行执行
   docker-compose restart tg2em-scrape
   ```

2. **查看日志，等待验证码请求**
   ```bash
   docker logs -f tg2em-scrape
   
   # 应该看到：
   # 📄 会话文件不存在，需要首次登录
   # 🔐 开始Telegram登录流程...
   # 📱 需要验证码，等待Web界面输入...
   # 
   # 🔔 Telegram 需要验证码验证
   # 📱 请前往管理后台输入验证码
   ```

3. **在管理后台输入验证码**
   - 访问：`http://公网IP:8000/dm`
   - 进入："Telegram验证"页面
   - 检查手机收到的5位验证码
   - 在页面输入并提交

4. **验证成功**
   ```bash
   # 日志显示：
   # ✅ 收到Web界面验证码: 12345
   # ✅ Telegram验证成功！当前用户: @username
   # 📁 会话已保存至: /app/sessions/tg2em_scraper.session
   # 🚀 开始采集任务...
   ```

### 常见问题

#### Q1: 日志显示 `Phone=`（电话号码为空）

**原因**：数据库中没有配置 `telegram_phone`

**解决**：
```bash
# 检查配置
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e \
  "SELECT config_value FROM system_config WHERE config_key = 'telegram_phone';"

# 如果为空，设置电话号码
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e \
  "UPDATE system_config SET config_value = '+8613800138000' WHERE config_key = 'telegram_phone';"

# 重启采集服务
docker-compose restart tg2em-scrape
```

#### Q2: 看不到采集服务的实际日志

**原因**：使用了旧版本代码，日志被PIPE捕获

**解决**：
```bash
# 拉取最新代码（已修复）
git pull origin main

# 重新构建
docker-compose build tg2em-scrape

# 重启
docker-compose restart tg2em-scrape
```

#### Q3: 验证页面显示"验证已完成"但实际没有登录

**原因**：数据库缓存了旧的验证状态

**解决**：
```bash
# 清除验证状态
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
DELETE FROM system_config WHERE config_key IN (
  'telegram_verification_required',
  'telegram_verification_code',
  'telegram_verification_submitted'
);
"

# 重启采集服务
docker-compose restart tg2em-scrape
```

#### Q4: 采集服务启动后立即退出

**检查配置**：
```bash
# 查看完整日志
docker logs tg2em-scrape

# 查看配置是否完整
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
SELECT config_key, config_value FROM system_config 
WHERE config_key IN ('telegram_api_id', 'telegram_api_hash', 'telegram_phone');
"
```

---

## 🧪 完整测试流程

### 1. 验证配置

```bash
# 检查数据库配置
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
SELECT config_key, 
       CASE 
         WHEN config_key LIKE '%hash%' OR config_key LIKE '%id%' 
         THEN CONCAT(LEFT(config_value, 4), '***')
         ELSE config_value 
       END as value
FROM system_config 
WHERE config_key LIKE 'telegram_%';
"

# 应该看到：
# telegram_api_id     | 1234***
# telegram_api_hash   | abcd***
# telegram_phone      | +8613800138000
```

### 2. 清理旧状态

```bash
# 删除旧的会话文件（如果需要重新验证）
docker exec tg2em-scrape rm -f /app/sessions/tg2em_scraper.session

# 清除验证状态
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
DELETE FROM system_config WHERE config_key LIKE '%verification%';
"
```

### 3. 启动服务

```bash
# 重启采集服务
docker-compose restart tg2em-scrape

# 实时查看日志
docker logs -f tg2em-scrape
```

### 4. 预期日志输出

```
✅ 从数据库获取Telegram配置: API_ID=1234***, Phone=+8613800138000
🚀 tg2em采集服务管理服务启动中...
📊 管理服务PID: 1
🔧 管理端口: 2003
📡 采集服务端口: 5002
 * Running on all addresses (0.0.0.0)
 * Running on http://0.0.0.0:2003

# 点击"启动采集服务"后：
📋 准备启动采集服务，配置信息:
   - API_ID: 1234***
   - API_Hash: abcd***
   - Phone: +8613800138000
   - MySQL: mysql:tg2em
✅ 采集服务启动成功，PID: 45

# 采集服务日志：
🚀 tg2em采集服务启动中...
📊 采集服务PID: 45
📡 服务端口: 5002
🔐 初始化 Telegram 客户端...
📄 发现会话文件: /app/sessions/tg2em_scraper.session
🔍 检查会话有效性...
✅ 会话有效！当前用户: @username (ID: 123456789)
🔄 使用已保存的有效会话，直接连接...
✅ Telegram客户端启动成功 (用户: @username)
🚀 开始采集任务...
```

---

## 📞 获取支持

如果问题仍未解决：

1. **收集日志**：
   ```bash
   docker logs tg2em-scrape > scraper.log
   docker logs tg2em-frontend > frontend.log
   ```

2. **检查配置**：
   ```bash
   docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e \
     "SELECT * FROM system_config WHERE category = 'telegram';" > config.txt
   ```

3. **提供信息**：
   - 错误日志
   - 配置信息（隐藏敏感信息）
   - 操作步骤

---

**更新时间**: 2025-10-09  
**提交**: 426daa6  
**修复**: 采集服务日志输出和配置验证

