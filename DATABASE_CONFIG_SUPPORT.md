# 数据库配置支持完整指南

## 🎯 概述

tg2emall项目现在支持**所有配置项都可以从数据库读取**，实现了完全的配置动态化管理。通过Web管理界面修改配置后，系统会自动使用新的配置，无需重启服务。

## 🏗️ 配置管理架构

### 1. **DatabaseConfigManager** - 核心配置管理器
```python
class DatabaseConfigManager:
    """数据库配置管理器 - 统一管理所有配置项"""
    
    def __init__(self):
        self.config_cache = {}  # 配置缓存
        self.cache_time = None
        self.cache_duration = 60  # 缓存60秒
    
    async def get_config(self, config_key, default_value=None, config_type="string"):
        """从数据库获取单个配置项"""
    
    async def get_all_configs(self):
        """获取所有配置项"""
```

**特性**：
- ✅ 配置缓存机制（60秒缓存）
- ✅ 自动类型转换（string, int, bool, list）
- ✅ 降级到默认值
- ✅ 错误处理和日志记录

### 2. **专用配置类** - 分类管理

#### **TelegramConfig** - Telegram相关配置
```python
class TelegramConfig:
    def __init__(self, db_config_manager=None):
        self.api_id = None
        self.api_hash = None
        self.phone_number = None
        self.session_name = None
        self.two_factor_password = None
```

**支持的配置项**：
- `telegram_api_id` - Telegram API ID
- `telegram_api_hash` - Telegram API Hash
- `telegram_phone` - 手机号码
- `telegram_session_name` - 会话文件名
- `telegram_two_factor_password` - 两步验证密码

#### **ScrapeConfig** - 采集相关配置
```python
class ScrapeConfig:
    def __init__(self, db_config_manager=None):
        self.blocked_tags = []
        self.retention_days = 7
        self.default_limit = 25
        self.interval_minutes = 5
        self.scrape_channels = []
        self.scrape_limit = 25
```

**支持的配置项**：
- `blocked_tags` - 屏蔽标签（逗号分隔）
- `retention_days` - 记录保留天数
- `default_limit` - 默认采集数量
- `interval_minutes` - 采集间隔（分钟）
- `scrape_channels` - 采集频道配置
- `scrape_limit` - 采集数量限制

#### **ImageConfig** - 图片相关配置
```python
class ImageConfig:
    def __init__(self, db_config_manager=None):
        self.upload_dir = "./upload"
        self.compression_quality = 50
        self.compression_format = "webp"
        self.tgstate_url = "http://tgstate:8001"
        self.tgstate_port = "8088"
        self.tgstate_pass = "none"
```

**支持的配置项**：
- `image_upload_dir` - 图片上传目录
- `image_compression_quality` - 压缩质量
- `image_compression_format` - 压缩格式
- `tgstate_url` - tgState服务URL
- `tgstate_port` - tgState服务端口
- `tgstate_pass` - tgState访问密码

## 📋 支持的配置项列表

### **Telegram配置**
| 配置键 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `telegram_api_id` | string | 从config.yaml | Telegram API ID |
| `telegram_api_hash` | string | 从config.yaml | Telegram API Hash |
| `telegram_phone` | string | 从config.yaml | 手机号码 |
| `telegram_session_name` | string | "tg2em_scraper" | 会话文件名 |
| `telegram_two_factor_password` | string | "" | 两步验证密码 |

### **采集配置**
| 配置键 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `blocked_tags` | string | 从config.yaml | 屏蔽标签（逗号分隔） |
| `retention_days` | int | 7 | 记录保留天数 |
| `default_limit` | int | 25 | 默认采集数量 |
| `interval_minutes` | int | 5 | 采集间隔（分钟） |
| `scrape_channels` | string | 从config.yaml | 采集频道配置 |
| `scrape_limit` | int | 25 | 采集数量限制 |

### **图片配置**
| 配置键 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `image_upload_dir` | string | "./upload" | 图片上传目录 |
| `image_compression_quality` | int | 50 | 压缩质量 |
| `image_compression_format` | string | "webp" | 压缩格式 |
| `tgstate_url` | string | "http://tgstate:8001" | tgState服务URL |
| `tgstate_port` | string | "8088" | tgState服务端口 |
| `tgstate_pass` | string | "none" | tgState访问密码 |

### **验证配置**
| 配置键 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `telegram_verification_timeout` | int | 600 | 验证码超时时间（秒） |

## 🔄 配置优先级

1. **数据库配置** - 最高优先级
2. **环境变量** - 中等优先级
3. **config.yaml** - 最低优先级（默认值）

## 💡 使用示例

### 1. **在代码中使用配置**
```python
# 创建配置管理器
db_config_manager = DatabaseConfigManager()

# 加载Telegram配置
telegram_config = TelegramConfig(db_config_manager)
await telegram_config.load_from_db()

# 使用配置
api_id = telegram_config.api_id
phone_number = telegram_config.phone_number
```

### 2. **获取单个配置项**
```python
# 获取单个配置
value = await db_config_manager.get_config("telegram_api_id", "default_value", "string")
int_value = await db_config_manager.get_config("scrape_limit", 25, "int")
bool_value = await db_config_manager.get_config("enable_feature", False, "bool")
```

### 3. **获取所有配置**
```python
# 获取所有配置
all_configs = await db_config_manager.get_all_configs()
```

## 🛠️ 配置更新流程

### 1. **通过Web界面更新**
1. 访问管理后台：`http://your-domain:8000/dm`
2. 进入"配置管理"页面
3. 修改相关配置项
4. 点击"保存配置"
5. 系统自动应用新配置

### 2. **通过数据库直接更新**
```sql
-- 更新Telegram API配置
UPDATE system_config 
SET config_value = 'your_new_api_id' 
WHERE config_key = 'telegram_api_id';

-- 更新采集间隔
UPDATE system_config 
SET config_value = '10' 
WHERE config_key = 'interval_minutes';
```

## 🚀 配置热更新特性

### 1. **自动配置刷新**
- 配置缓存60秒自动过期
- 下次访问时自动从数据库重新加载
- 无需重启服务即可生效

### 2. **配置验证**
- 自动验证配置完整性
- 类型检查和转换
- 错误配置自动降级到默认值

### 3. **日志记录**
- 配置加载过程详细日志
- 配置错误自动记录
- 便于问题排查

## 📊 性能优化

### 1. **配置缓存**
- 60秒缓存机制
- 减少数据库查询
- 提高响应速度

### 2. **批量加载**
- 支持批量获取配置
- 减少数据库连接次数
- 提高效率

### 3. **错误处理**
- 配置获取失败时使用默认值
- 不影响系统正常运行
- 自动重试机制

## 🔧 配置管理最佳实践

### 1. **配置分类**
- 按功能模块分类管理
- 使用有意义的配置键名
- 添加配置描述和类型

### 2. **默认值设置**
- 为所有配置项设置合理的默认值
- 确保系统在配置缺失时仍能运行
- 提供配置示例和说明

### 3. **配置验证**
- 在配置加载时进行验证
- 检查配置值的有效性
- 提供清晰的错误信息

## 🎉 总结

通过实现完整的数据库配置支持，tg2emall项目现在具备了：

1. **完全的配置动态化** - 所有配置都可以从数据库读取
2. **配置热更新** - 无需重启服务即可应用新配置
3. **配置缓存机制** - 提高性能，减少数据库压力
4. **类型安全** - 自动类型转换和验证
5. **错误处理** - 配置错误时自动降级到默认值
6. **易于维护** - 统一的配置管理接口

这使得系统更加灵活、可维护，用户可以通过Web界面轻松管理所有配置，无需修改代码或重启服务。
