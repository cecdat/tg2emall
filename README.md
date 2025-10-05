# 📱 tg2emall - Telegram 到自定义前端一体化解决方案

[![Docker](https://img.shields.io/badge/Docker-兼容-2496ED?logo=docker)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python)](https://www.python.org/)
[![Go](https://img.shields.io/badge/Go-1.19+-00ADD8?logo=go)](https://golang.org/)
[![Flask](https://img.shields.io/badge/Flask-Latest-000000?logo=flask)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**tg2emall** 是一个基于 Docker 的双服务架构一体化解决方案，可以自动抓取 Telegram 频道消息，通过 Web 界面进行管理展示，支持图片上传和服务配置。

## ✨ 核心功能

### 🎯 **主要特性**
- 🤖 **自动化采集**: 定时抓取 Telegram 频道消息
- 🌐 **Web 管理界面**: 完整的后台管理系统
- 📷 **图片上传**: 支持 Telegram 图床服务
- 🔧 **配置管理**: Web 界面管理所有配置参数
- 🖥️ **服务控制**: 一键启动/停止采集和图片服务
- 📱 **Telegram 验证**: Web 界面输入验证码
- 🔄 **会话持久化**: Telegram 会话文件自动保存
- 🛡️ **安全保护**: 完善的身份验证和权限控制
- 🏗️ **双服务架构**: 管理服务和业务服务分离设计

### 🏗️ **技术架构**

#### **双服务架构设计**
```
📦 tg2emall 容器集群
├── 🌐 前端服务 (Flask + Bootstrap 5)
├── 🗄️ MySQL 数据库
├── 🔄 采集服务容器
│   ├── 📊 管理服务 (端口5001) - 控制采集服务启停
│   └── 🤖 采集服务 (端口5002) - 专门负责Telegram采集
└── 📷 图片服务容器
    ├── 📊 管理服务 (端口8088) - 控制上传服务启停
    └── 🖼️ 上传服务 (端口8089) - 专门负责图片上传
```

#### **技术栈**
- **前端**: Flask + Bootstrap 5 + Jinja2 + SweetAlert2
- **采集服务**: Python + Telethon + AsyncIO + Flask
- **图片服务**: Go + Telegram Bot API + HTTP API
- **数据库**: MySQL 8.0
- **部署**: Docker Compose + 双服务架构
- **反向代理**: Nginx Proxy Manager

## 🚀 快速开始

### 📋 **系统要求**
- Docker & Docker Compose
- 2GB+ 内存
- 10GB+ 磁盘空间

### ⚡ **一键部署**
```bash
# 克隆项目
git clone https://github.com/your-repo/tg2emall.git
cd tg2emall

# 配置环境变量
cp env.example .env
# 编辑 .env 文件配置参数

# 运行部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 🔧 **手动部署**
```bash
# 1. 启动基础服务（MySQL、前端、代理）
docker-compose up -d

# 2. 等待 30 秒让基础服务启动
sleep 30

# 3. 访问管理后台配置参数
# http://your-server:5000/dm
# 用户名: admin, 密码: admin, 验证码: 2025

# 4. 启动业务服务（可选）
docker-compose --profile services up -d tgstate tg2em-scrape
```

## ⚙️ 配置指南

### 🔐 **管理后台访问**
- **访问地址**: `https://237890.xyz/dm`
- **默认账号**: admin 
- **默认密码**: admin
- **验证码**: 2025 (固定验证码)

### 🌐 **域名配置**
- **主站**: `https://237890.xyz`
- **管理后台**: `https://237890.xyz/dm`
- **图片服务**: `https://img.237890.xyz`
- **图片管理**: `https://img.237890.xyz/dm`
- **强制HTTPS**: 所有域名强制使用HTTPS访问
- **www重定向**: `www.237890.xyz` 自动重定向到 `237890.xyz`

### 📱 **Telegram 配置**
在管理后台"配置管理"页面配置：

```
telegram_api_id:      # 从 https://my.telegram.org 获取
telegram_api_hash:    # 从 https://my.telegram.org 获取
telegram_phone:       # Telegram绑定手机号码（带国家代码，如：+8613800138000）
telegram_session_name: tg2em_scraper (默认)
scrape_channels:      [{"url": "https://t.me/channel", "limit": 10}, {"id": -1001234567890, "limit": 15}]
scrape_limit:         10 (每次采集数量)
scrape_interval:      300 (采集间隔秒数)
```

### 📷 **图片服务配置（可选）**
如果要使用 Telegram 图床：

```
tgstate_token:        # Telegram Bot Token
tgstate_target:       # 目标频道 @channel_name
tgstate_pass:         none (访问密码)
tgstate_mode:         p (API模式)
tgstate_url:          https://img.237890.xyz (基础URL)
tgstate_port:         8088 (管理服务端口)
```

#### **图片服务双架构说明**
- **管理服务 (8088端口)**: 自动启动，控制上传服务
- **上传服务 (8089端口)**: 由管理服务控制，专门处理图片上传
- **访问方式**: 
  - 管理界面: `http://your-domain:8088`
  - 上传测试: `https://img.your-domain.com` (需要密码)

### 🗄️ **数据库配置**
```bash
MYSQL_ROOT_PASSWORD=tg2emall
MYSQL_DATABASE=tg2em
MYSQL_USER=tg2emall
MYSQL_PASSWORD=tg2emall
```

## 📱 Telegram 验证流程

### 🌐 **Web 验证流程**
首次部署或重新配置时，Telegram 会要求手机验证码：

1. **自动检测**: 系统检测到需要验证码时自动提醒
2. **进入验证页面**: 管理后台 → "Telegram验证"
3. **输入验证码**: 检查手机短信，输入5位数字验证码
4. **自动验证**: 系统自动处理验证过程
5. **验证完成**: 显示绿色成功状态

### ⏰ **验证特性**
- 🌐 **完全 Web 化**: 无需 SSH 或命令行操作
- ⚡ **快速验证**: 5位数字自动提交
- 📱 **移动友好**: 支持手机和平板操作
- 🔔 **智能提醒**: 自动检测并提示验证需求
- 🛡️ **安全处理**: 验证码临时存储，完成后立即清除

## 🖥️ 管理功能

### 📊 **控制台**
- **统计数据**: 总文章数、今日/昨日新增、访问IP统计
- **服务状态**: 实时显示各个服务的运行状态
- **访问来源**: 搜索引擎、直接访问、社交媒体等统计

### 📝 **内容管理**
- **文章列表**: 分页显示所有采集的文章
- **编辑文章**: 修改标题和内容
- **删除文章**: 安全删除不需要的文章
- **搜索功能**: 按标题或标签搜索文章

### ⚙️ **配置管理**
- **Telegram 配置**: API参数、会话设置、采集参数
- **图片服务配置**: tgState 图床相关参数
- **服务控制配置**: 各服务的启用状态

### 🔧 **服务管理**

#### **双服务架构控制**
- **采集服务**: 管理服务(5001) + 采集服务(5002)
- **图片服务**: 管理服务(8088) + 上传服务(8089)
- **服务状态**: 实时监控所有服务运行状态
- **一键控制**: 启动/停止采集和图片服务
- **批量操作**: 同时启动或停止所有业务服务
- **状态刷新**: 自动和手动刷新服务状态

#### **服务管理页面**
- **采集服务管理**: `http://your-domain:5001`
- **图片服务管理**: `http://your-domain:8088`
- **统一管理后台**: `http://your-domain:5000/dm` → 服务管理

## 🛠️ 故障排除

### ❌ **常见问题**

#### **1. 数据库初始化失败**
**错误**: `ERROR 1054 (42S22): Unknown column 'description'`

**解决方案**:
```bash
# 方案一：清理重新部署（推荐）
docker-compose down
docker volume rm tg2emall_mysql-data
docker-compose up -d

# 方案二：手动修复现有数据库
docker exec -it tg2em-mysql mysql -u root -ptg2emall tg2em
# 在 MySQL 中执行：
ALTER TABLE messages ADD COLUMN source_channel varchar(100) DEFAULT NULL COMMENT '来源频道';
```

#### **2. 模板语法错误**
**错误**: `Unknown tag 'cycle'`

**解决方案**: 已在新版本中修复，重新部署即可。

#### **3. Telegram 验证码输入**
**现象**: 需要在容器中输入验证码

**解决方案**: 使用管理后台的"Telegram验证"功能：
1. 访问管理后台验证页面
2. 输入收到的5位数字验证码
3. 系统自动处理验证

#### **4. 图片上传失败**
**错误**: `Cannot connect to host tgstate:8088`

**解决方案**:
1. 检查 tgState 服务是否启动：`docker-compose ps`
2. 如果未启动，在管理后台"服务管理"页面启动
3. 或配置 tgState 参数后重启服务

#### **5. 服务默认不启动**
**现象**: 部署后只有基础服务运行

**说明**: 这是正常的！业务服务（图片、采集）需要配置后再启动：
```bash
# 方法一：管理后台启动
# 进入"服务管理" → 点击"启动"按钮

# 方法二：命令行启动
docker-compose --profile services up -d tgstate tg2em-scrape
```

### 🔍 **检查和调试**

#### **查看服务状态**
```bash
# 查看所有服务
docker-compose ps

# 查看日志
docker-compose logs frontend
docker-compose logs tg2em-scrape
docker-compose logs tgstate
```

#### **数据库检查**
```bash
# 连接数据库
docker exec -it tg2em-mysql mysql -u tg2emall -ptg2emall tg2em

# 检查表结构
DESCRIBE messages;
DESCRIBE system_config;
DESCRIBE services_status;

# 查看配置
SELECT * FROM system_config WHERE category = 'telegram';
```

#### **网络连接检查**
```bash
# 检查容器网络
docker network ls | grep tg2em

# 测试内部服务连接
docker exec tg2em-scrape ping tgstate
docker exec tg2em-frontend ping mysql
```

## 📂 **项目结构**

```
tg2emall/
├── 📄 README.md                    # 项目说明（本文件）
├── 🐳 docker-compose.yml          # Docker 编排配置
├── 📜 deploy.sh                    # 部署脚本
├── ⚙️ env.example                  # 环境变量示例
├── 🗄️ init.sql                    # 数据库初始化脚本
├── 📁 services/                    # 服务代码
│   ├── 📁 frontend/               # Flask 前端服务
│   │   ├── 📜 app.py             # 主应用
│   │   ├── 📁 templates/         # Jinja2 模板
│   │   └── 📄 service_controller.py # 服务控制器
│   ├── 📁 tg2em/                 # Telegram 采集服务
│   │   ├── 📜 management-service.py # 采集管理服务
│   │   ├── 📜 scraper-service.py    # 采集业务服务
│   │   ├── 📜 scrape.py          # 采集脚本
│   │   └── 📜 management_api.py  # 管理API (兼容)
│   └── 📁 tgstate/               # Go 图片服务
│       ├── 📜 management-service.go # 图片管理服务
│       ├── 📜 upload-service.go     # 图片上传服务
│       ├── 📁 web/                # 管理界面
│       └── 📁 assets/             # 静态资源
├── 📁 data/                       # 数据目录（自动创建）
│   ├── 📁 mysql/                 # MySQL 数据
│   ├── 📁 telegram-sessions/      # Telegram 会话
│   ├── 📁 logs/                  # 日志文件
│   └── 📁 upload/               # 图片文件
└── 📁 init-npm.sql               # NPM 初始化脚本
```

## 🔄 **更新和维护**

### 📅 **定期维护任务**
- 🔍 **日志清理**: 定期清理日志文件
- 💾 **数据备份**: 备份 MySQL 数据库
- 🔄 **服务重启**: 定期重启服务以确保稳定运行

### 🔧 **手动清理**
```bash
# 清理日志
docker system prune -f

# 清理旧镜像
docker image prune -f

# 备份数据库
docker exec tg2em-mysql mysqldump -u root -ptg2emall tg2em > backup.sql
```

## 🤝 **贡献指南**

欢迎提交 Issue 和 Pull Request！

### 🐛 **报告问题**
请提供：
- 操作系统和 Docker 版本
- 完整的错误日志
- 复现步骤

### 💻 **开发环境**
```bash
# 克隆项目
git clone https://github.com/your-repo/tg2emall.git

# 开发模式运行
docker-compose -f docker-compose.dev.yml up
```

## 📋 **更新日志**

### 🆕 v3.0 - 双服务架构重构
- ✅ **双服务架构设计**: 管理服务和业务服务分离
- ✅ **采集服务重构**: 管理服务(5001) + 采集服务(5002)
- ✅ **图片服务重构**: 管理服务(8088) + 上传服务(8089)
- ✅ **统一管理界面**: 每个服务都有独立的管理页面
- ✅ **配置热更新**: 支持配置变更后自动重启服务
- ✅ **服务状态监控**: 实时监控双服务架构状态
- ✅ **API接口统一**: 所有服务提供统一的REST API

### 🆕 v2.1 - 配置管理和服务控制
- ✅ Web 界面配置管理
- ✅ 服务启动/停止控制
- ✅ Telegram 验证码 Web 输入
- ✅ Docker Profiles 部署优化
- ✅ 数据库字段和模板错误修复

### 🆕 v2.0 - 管理后台整合
- ✅ 集成管理后台到前端服务
- ✅ 管理员登录验证
- ✅ 文章管理和编辑功能
- ✅ 统计数据展示

### 🆕 v1.0 - 基础功能
- ✅ Telegram 消息采集
- ✅ Flask 前端展示
- ✅ Docker 一键部署
- ✅ 图片上传支持

## 📞 **支持**

- 📖 **文档**: 本项目说明
- 🐛 **问题**: [GitHub Issues](https://github.com/your-repo/tg2emall/issues)
- 💬 **讨论**: [GitHub Discussions](https://github.com/your-repo/tg2emall/discussions)

## 📄 **许可证**

本项目基于 [MIT License](LICENSE) 开源。

---

**🎯 tg2emall - 让 Telegram 采集和 Web 管理变得更简单！**

<div align="center">

**[🏠 首页](http://your-server)** | **[🔧 管理后台](http://your-server/dm)** | **[📚 文档](#-配置指南)** | **[🐛 报告问题](https://github.com/your-repo/tg2emall/issues)**

</div>