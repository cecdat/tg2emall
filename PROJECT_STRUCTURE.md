# 📁 tg2emall 项目结构

## 📂 **根目录文件**

| 文件名 | 说明 | 用途 |
|-------|------|------|
| 📄 **README.md** | 项目完整说明文档 | 包含部署、配置、故障排除等所有信息 |
| 🐳 **docker-compose.yml** | Docker 编排配置 | 定义所有服务和依赖关系 |
| 📜 **deploy.sh** | 自动化部署脚本 | 一键部署整个项目 |
| ⚙️ **env.example** | 环境变量模板 | 复制为 .env 并配置参数 |
| 🗄️ **init.sql** | 数据库初始化脚本 | MySQL 表结构和初始数据 |
| 🔧 **init-npm.sql** | NPM 数据库初始化 | Nginx Proxy Manager 数据表 |

## 📁 **services/ 目录**

```
services/
├── 📁 frontend/               # Flask 前端服务
│   ├── 📄 app.py            # 主Flask应用（前台+后台）
│   ├── 📄 service_controller.py # Docker服务控制器
│   ├── 📁 templates/        # Jinja2模板文件
│   │   ├── 📄 base.html     # 基础模板
│   │   ├── 📄 index.html    # 首页模板
│   │   ├── 📄 article.html  # 文章详情页
│   │   ├── 📄 search.html   # 搜索结果页
│   │   ├── 📄 admin.html    # 管理后台首页
│   │   ├── 📄 admin_login.html # 管理员登录页
│   │   ├── 📄 admin_articles.html # 文章管理页
│   │   ├── 📄 admin_config.html # 配置管理页
│   │   ├── 📄 admin_services.html # 服务管理页
│   │   └── 📄 admin_telegram_verification.html # Telegram验证页
│   ├── 📁 static/          # 静态资源
│   └── 📄 Dockerfile       # 前端服务Docker配置
├── 📁 tg2em/              # Telegram采集服务
│   ├── 📄 scrape.py       # 主要采集脚本
│   └── 📄 Dockerfile       # 采集服务Docker配置
└── 📁 tgstate/           # Go图片上传服务
    ├── 📄 main.go         # Go服务主程序
    ├── 📁 conf/           # 配置模块
    ├── 📁 control/         # API控制器
    └── 📄 Dockerfile      # 图片服务Docker配置
```

## 📁 **data/ 目录（部署后自动创建）**

```
data/
├── 📁 mysql/                  # MySQL数据存储
├── 📁 npm/                   # NPM数据存储
├── 📁 letsencrypt/           # SSL证书存储
├── 📁 telegram-sessions/     # Telegram会话文件
├── 📁 logs/                  # 服务日志文件
└── 📁 upload/                # 图片上传存储
```

## 🗑️ **已移除的文档文件**

为了简化项目结构，已将以下重复的文档文件整合到 `README.md` 中：

- ❌ ~~ADMIN_LOGIN_EXAMPLE.md~~ → 📄 登录信息已整合到README
- ❌ ~~ADMIN_LOGIN_GUIDE.md~~ → 🌐 Web验证说明已整合到README  
- ❌ ~~CONFIG_AND_SERVICE_MANAGEMENT.md~~ → ⚙️ 配置管理已整合到README
- ❌ ~~DATABASE_INIT_FIX.md~~ → 🔧 故障排除已整合到README
- ❌ ~~DEPLOYMENT_FIX.md~~ → 🛠️ 部署和故障排除已整合到README
- ❌ ~~DOCKER_COMMANDS.md~~ → 🚀 部署指南已整合到README
- ❌ ~~FIX_TGSTATE_API.md~~ → 🛠️ tgState问题已整合到README
- ❌ ~~FIX_TGSTATE_ENV_VARS.md~~ → ⚙️ 环境配置已整合到README
- ❌ ~~QUICK_DEPLOY_GUIDE.md~~ → 🚀 快速开始已整合到README
- ❌ ~~REBUILD_WITH_TOKEN.md~~ → 🔧 重建指南已整合到README
- ❌ ~~SESSION_MANAGEMENT.md~~ → 📱 会话管理已整合到README
- ❌ ~~TELEGRAM_VERIFICATION_GUIDE.md~~ → 📱 验证指南已整合到README
- ❌ ~~TGSTATE_TROUBLESHOOTING.md~~ → 🛠️ 故障排除已整合到README

## 📋 **项目优势**

### 🎯 **简洁性**
- 📄 **单一文档**: 所有信息集中在一个 `README.md` 中
- 🗂️ **清晰结构**: 按功能分组的目录结构
- 🧹 **无冗余**: 删除了重复的文档文件

### 📖 **可读性**
- 🏷️ **徽章标签**: 清晰的功能和版本标识
- 📑 **目录导航**: 完整的功能索引
- 🎨 **视觉友好**: 丰富的图标和格式化

### 🔧 **维护性**
- 📚 **信息完整**: 从部署到故障排除一应俱全
- 🔄 **版本控制**: 清晰的更新日志记录
- 🤝 **贡献友好**: 明确的贡献指南

---

**现在项目结构更加简洁明了，所有信息都集中在 `README.md` 中！** ✨
