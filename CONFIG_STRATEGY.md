# 配置管理策略说明

## 🎯 配置分类

### 1. **系统级配置** (必须通过环境变量)
这些配置在容器启动时就需要，无法从数据库读取：

#### 数据库连接配置
```bash
MYSQL_HOST=mysql
MYSQL_DATABASE=tg2em
MYSQL_USER=tg2emall
MYSQL_PASSWORD=tg2emall
```

#### 服务端口配置
```bash
FRONTEND_PORT=8000
SCRAPER_PORT=5002
MANAGEMENT_PORT=2003
```

#### 安全配置
```bash
SECRET_KEY=tg2emall-secret-key-2024
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin
```

#### 系统级参数
```bash
TELEGRAM_VERIFICATION_TIMEOUT=600
TZ=Asia/Shanghai
```

### 2. **业务配置** (支持数据库管理)
这些配置可以在应用运行时动态读取：

#### Telegram配置
- `telegram_api_id` - API ID
- `telegram_api_hash` - API Hash
- `telegram_phone` - 手机号码
- `telegram_session_name` - 会话文件名
- `telegram_two_factor_password` - 两步验证密码

#### 采集配置
- `scrape_channels` - 采集频道
- `scrape_limit` - 采集数量
- `interval_minutes` - 采集间隔
- `blocked_tags` - 屏蔽标签
- `retention_days` - 记录保留天数

#### 图片配置
- `image_upload_dir` - 上传目录
- `image_compression_quality` - 压缩质量
- `image_compression_format` - 压缩格式
- `tgstate_url` - tgState服务URL
- `tgstate_token` - tgState Token
- `tgstate_target` - tgState目标频道
- `tgstate_pass` - tgState访问密码

## 🔄 配置优先级

```
1. 数据库配置 (最高优先级)
   ↓
2. 环境变量 (.env文件)
   ↓
3. config.yaml (默认值)
```

## 💡 为什么需要 .env 文件？

### 1. **容器化限制**
- Docker容器启动时需要知道数据库连接信息
- 服务端口必须在容器启动时确定
- 安全密钥必须在应用启动时加载

### 2. **安全性考虑**
- 敏感配置通过环境变量管理
- 避免在代码中硬编码敏感信息
- 支持不同环境的配置隔离

### 3. **系统稳定性**
- 系统级配置相对稳定，不需要频繁修改
- 业务配置可以动态调整，提高灵活性

## 🚀 使用建议

### 1. **首次部署**
```bash
# 1. 配置系统级参数
cp env.example .env
nano .env

# 2. 启动服务
docker-compose up -d

# 3. 通过Web界面配置业务参数
# 访问管理后台配置Telegram、采集等参数
```

### 2. **日常管理**
```bash
# 系统级配置修改（需要重启）
nano .env
docker-compose restart

# 业务配置修改（无需重启）
# 通过Web界面直接修改
```

### 3. **配置备份**
```bash
# 备份系统配置
cp .env .env.backup

# 备份数据库配置
# 通过Web界面导出配置
```

## 🔧 未来优化方向

### 1. **减少环境变量依赖**
- 可以考虑将更多配置移到数据库
- 使用配置服务统一管理所有配置

### 2. **配置模板化**
- 提供不同环境的配置模板
- 支持配置一键切换

### 3. **配置验证**
- 添加配置完整性检查
- 提供配置建议和优化提示
