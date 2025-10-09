# tgState 图片上传服务启动问题修复指南

## 问题描述

图片上传服务 (tgState) 启动时报错：
```
tg2em-frontend | POST /admin/services/tgstate-service/start HTTP/1.1" 500 -
tg2em-frontend | GET /admin/services/tgstate/status HTTP/1.1" 500 -
```

## 问题原因

1. **端口配置不一致**：日志输出显示端口 8088，但实际监听端口是 8001
2. **密码验证中间件阻止 API 访问**：管理 API 被密码验证中间件拦截
3. **环境变量配置错误**：TGSTATE_URL 配置为 localhost:8088 而非正确的端口
4. **容器未正常启动**：服务可能未正确编译或启动

## 修复内容

### 1. 修复日志输出错误

**文件**: `services/tgstate/management-service.go`

**修改内容**:
```go
// 第 112 行
-	log.Println("✅ tgState管理服务已启动，监听端口: 8088")
+	log.Println("✅ tgState管理服务已启动，监听端口: 8001")
```

### 2. 修复密码验证中间件

**文件**: `services/tgstate/management-service.go`

**修改内容**: 添加了管理 API 路由的白名单，使其无需密码即可访问：

```go
// passwordAuthMiddleware 密码验证中间件
func passwordAuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// 管理 API 路由不需要密码验证（用于内部服务调用）
		if r.URL.Path == "/api/management/status" ||
		   r.URL.Path == "/api/management/start" ||
		   r.URL.Path == "/api/management/stop" ||
		   r.URL.Path == "/api/management/restart" ||
		   r.URL.Path == "/api/management/config" ||
		   r.URL.Path == "/api/management/info" {
			// 允许跨域访问（CORS）
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			
			// 处理 OPTIONS 预检请求
			if r.Method == "OPTIONS" {
				w.WriteHeader(http.StatusOK)
				return
			}
			
			next.ServeHTTP(w, r)
			return
		}
		
		// ... 其他密码验证逻辑 ...
	})
}
```

### 3. 修复环境变量配置

**文件**: `env.example`

```bash
# 修改前
TGSTATE_URL=http://localhost:8088

# 修改后
TGSTATE_URL=http://localhost:8001
```

**文件**: `docker-compose.yml`

```yaml
# 修改前
URL: "${TGSTATE_URL:-http://localhost:8001}"

# 修改后（容器内部使用容器名）
URL: "${TGSTATE_URL:-http://tgstate:8001}"
```

## 快速修复步骤

### Windows 用户

1. **运行诊断脚本**（可选）：
   ```powershell
   .\diagnose_tgstate.ps1
   ```

2. **运行修复脚本**：
   ```powershell
   .\fix_tgstate.ps1
   ```

   该脚本会自动：
   - 创建 .env 文件（如果不存在）
   - 停止现有的 tgstate 容器
   - 重新构建镜像
   - 启动服务
   - 测试管理接口

### Linux/Mac 用户

1. **运行诊断脚本**（可选）：
   ```bash
   bash diagnose.sh
   ```

2. **运行修复脚本**：
   ```bash
   chmod +x fix_tgstate.sh
   ./fix_tgstate.sh
   ```

## 手动修复步骤

如果自动脚本失败，可以手动执行以下步骤：

### 1. 创建或更新 .env 文件

```bash
# 复制示例文件
cp env.example .env

# 确保包含以下配置
TGSTATE_TOKEN=你的Telegram Bot Token
TGSTATE_TARGET=@你的频道名
TGSTATE_PASS=访问密码
TGSTATE_MODE=p
TGSTATE_URL=http://localhost:8001
```

### 2. 停止并删除旧容器

```bash
docker-compose stop tgstate
docker-compose rm -f tgstate
```

### 3. 重新构建镜像

```bash
docker-compose build --no-cache tgstate
```

### 4. 启动服务

```bash
docker-compose up -d tgstate
```

### 5. 查看日志

```bash
docker-compose logs -f tgstate
```

## 验证修复

### 1. 检查容器状态

```bash
docker-compose ps tgstate
```

期望输出：容器状态为 "Up"

### 2. 测试管理 API

```bash
# Windows PowerShell
Invoke-RestMethod -Uri "http://localhost:8001/api/management/status" -Method Get

# Linux/Mac
curl http://localhost:8001/api/management/status
```

期望响应：
```json
{
  "success": true,
  "data": {
    "status": "stopped",
    "pid": 0,
    "uptime": "0s",
    "start_time": "2025-10-09 13:40:00"
  }
}
```

### 3. 测试服务信息

```bash
# Windows PowerShell
Invoke-RestMethod -Uri "http://localhost:8001/api/management/info" -Method Get

# Linux/Mac
curl http://localhost:8001/api/management/info
```

## 服务架构说明

tgState 服务采用双服务架构：

1. **管理服务** (management-service)
   - 端口: 8001
   - 功能: 提供服务管理 API，控制上传服务的启动/停止/重启
   - 路由:
     - `/api/management/status` - 查询服务状态
     - `/api/management/start` - 启动上传服务
     - `/api/management/stop` - 停止上传服务
     - `/api/management/restart` - 重启上传服务
     - `/api/management/config` - 配置管理
     - `/api/management/info` - 服务信息

2. **上传服务** (upload-service)
   - 端口: 8002
   - 功能: 实际处理图片上传到 Telegram 频道
   - 由管理服务动态启动和停止

## 常见问题

### Q1: 容器启动后立即退出

**原因**: 可能是环境变量配置错误或依赖缺失

**解决方案**:
```bash
# 查看详细日志
docker-compose logs tgstate

# 检查 .env 文件配置
cat .env
```

### Q2: 管理 API 返回 401 Unauthorized

**原因**: 密码验证中间件拦截了请求

**解决方案**: 
- 确保已应用本次修复（中间件白名单）
- 重新构建镜像

### Q3: 前端无法连接到 tgstate 服务

**原因**: 容器网络问题或服务未启动

**解决方案**:
```bash
# 检查容器网络
docker network inspect tg2em-network

# 确保所有容器在同一网络
docker-compose ps
```

### Q4: 端口 8001 被占用

**原因**: 其他程序占用了端口

**解决方案**:
```bash
# Windows
netstat -ano | findstr :8001

# Linux/Mac
lsof -i :8001

# 修改 docker-compose.yml 中的端口映射
ports:
  - "8003:8001"  # 将主机端口改为 8003
```

## 相关文件

- `services/tgstate/management-service.go` - 管理服务主程序
- `services/tgstate/upload-service.go` - 上传服务程序
- `services/tgstate/Dockerfile` - Docker 构建文件
- `docker-compose.yml` - Docker Compose 配置
- `env.example` - 环境变量示例
- `.env` - 实际环境变量（需创建）

## 技术支持

如果问题仍未解决，请提供以下信息：

1. 容器日志: `docker-compose logs tgstate`
2. 容器状态: `docker-compose ps`
3. 环境变量: `cat .env`（注意隐藏敏感信息）
4. 系统信息: `docker version`

## 更新日志

- **2025-10-09**: 修复管理服务日志输出错误
- **2025-10-09**: 修复密码验证中间件阻止 API 访问
- **2025-10-09**: 修正环境变量配置
- **2025-10-09**: 添加诊断和修复脚本

