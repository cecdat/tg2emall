# Telegram 采集脚本改进说明

## 🆕 主要改进

### 1. 删除了已废弃的 publish.py
- **原因**: `publish.py` 用于发布内容到 emlog 博客系统，但项目已不再使用 emlog
- **替代**: 现在数据直接保存到 `messages` 表，前端直接从数据库读取显示
- **好处**: 简化架构，减少不必要的发布步骤

### 2. 改进 Telegram 验证码处理

#### 原问题：
- 使用 `phone=lambda: phone` 会卡住等待验证码输入
- 没有友好的用户交互界面
- 无法处理两步验证

#### 解决方案：
```python
def get_code_input():
    """获取验证码输入的交互函数"""
    print("\n" + "="*50)
    print("Telegram 需要验证码验证")
    print("="*50)
    
    code = input("请输入验证码 (5位数字): ").strip()
    if not code.isdigit() or len(code) != 5:
        print("❌ 验证码格式错误，请输入5位数字")
        return get_code_input()
    
    print(f"✅ 验证码已输入: {code}")
    return code
```

#### 特性：
- ✅ 友好的命令行交互界面
- ✅ 验证码格式验证
- ✅ 支持两步验证密码
- ✅ 自动检测已保存的会话文件

### 3. 优雅退出机制

#### 新增功能：
- 信号处理器处理 `SIGINT` 和 `SIGTERM`
- 可中断的等待循环
- 优雅的资源清理

```python
def signal_handler(signum, frame):
    """处理退出信号"""
    global shutdown_requested
    logging.info(f"收到退出信号 {signum}，准备优雅退出...")
    shutdown_requested = True
```

### 4. 配置文件优化

#### 移除的内容：
- `emlog` 配置段
- `baidu_push` 配置段
- `publish` 任务配置

#### 新增的内容：
- `two_factor_password` 可选配置

## 🚀 使用方法

### Docker 整体部署：
```bash
# 克隆项目
git clone <repository-url>
cd lg2emall

# 启动所有服务
docker-compose up -d

# 查看日志，特别是采集服务
docker-compose logs -f tg2em-scrape
```

### 验证码输入流程：
1. Docker 启动后，采集服务会等待用户交互
2. 使用以下命令进入采集服务容器：
```bash
docker-compose exec tg2em-scrape python scrape.py
```

3. 首次连接会显示：
```
==================================================
Telegram 需要验证码验证
==================================================
请输入验证码 (5位数字): 
```

4. 输入手机接收的5位验证码
5. 如有两步验证，会提示输入密码
6. 验证成功后会显示 "✅ Telegram 验证成功！"

### 会话文件持久化：
- Docker volume `telegram-sessions` 保存会话文件
- 验证成功后下次启动会自动使用会话，无需再次验证

## 📋 配置文件更新

### 新增或修改的配置：
```yaml
telegram:
  api_id: 19089950
  api_hash: "10d7322d62ce3aa8dec17c69ac0ec847"
  phone_number: "+12282078999"
  # two_factor_password: "your_2fa_password"  # 可选的两步验证密码
```

### 移除的配置：
- `emlog` 段（不再需要）
- `prelish` 任务配置（publish.py 已删除）
- `baidu_push` 段（不再使用）

## 🛠 启动优化

### Docker 环境：
```bash
cd tg2emall/services/tg2em
docker-compose up tg2em-tg2em
```

### 本地环境：
```bash
cd tg2emall/services/tg2em
python scrape.py
# 或使用启动脚本
./start_scraper.sh
```

## ⚠️ 注意事项

1. **第一次运行**需要手机接收验证码
2. **两步验证**开启的用户需要输入密码
3. **网络连接**需要能够访问 Telegram 服务
4. **权限要求**需要创建 `logs` 和 `upload` 目录

## 🔧 故障排除

### 常见问题：

1. **验证码输入错误**：重新运行脚本，重新验证
2. **网络问题**：检查网络连接，确保能访问 Telegram
3. **会话文件损坏**：删除 `session_name.session` 文件重新验证
4. **权限问题**：确保对当前目录有写入权限

### 查看日志：
```bash
tail -f logs/scrape.log
```
