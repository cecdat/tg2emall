# 🐳 统一容器部署方案

## 🎯 **架构变更**

### **修改前（多容器）**:
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  tg2em-frontend │  │  tg2em-tgstate  │  │ tg2em-scrape    │
│                 │  │                 │  │                 │
│  Flask应用      │  │  Go图片服务     │  │ Python采集器    │
│  端口: 5000     │  │  端口: 8088     │  │ 无端口          │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌─────────────────┐
                    │  tg2em-mysql    │
                    │  MySQL数据库    │
                    │  端口: 3306     │
                    └─────────────────┘
```

### **修改后（统一容器）**:
```
┌─────────────────────────────────────────────────────────────┐
│                    tg2em-unified                            │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Flask前端  │  │  Go图片服务 │  │ Python采集  │        │
│  │  端口: 5000 │  │  端口: 8088 │  │ 进程管理    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              进程监控和重启脚本                      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                               │
                    ┌─────────────────┐
                    │  tg2em-mysql    │
                    │  MySQL数据库    │
                    │  端口: 3306     │
                    └─────────────────┘
```

## 🔧 **核心优势**

### **1. 真实服务控制**
- ✅ **进程级管理**: 使用 `psutil` 和 `signal` 进行真实的进程控制
- ✅ **PID跟踪**: 实时跟踪每个服务的进程ID
- ✅ **状态监控**: 真实的进程状态检查，非模拟

### **2. 简化部署**
- ✅ **单一容器**: 只需管理一个业务容器
- ✅ **统一日志**: 所有服务日志集中管理
- ✅ **简化网络**: 减少容器间通信复杂度

### **3. 自动恢复**
- ✅ **进程监控**: 自动检测进程死亡
- ✅ **自动重启**: 进程异常退出时自动重启
- ✅ **健康检查**: 持续监控服务健康状态

## 📁 **文件结构**

```
tg2emall/
├── services/
│   └── unified/
│       ├── Dockerfile              # 统一容器构建文件
│       ├── start.sh               # 服务启动脚本
│       ├── service_manager.py     # 进程管理程序
│       └── requirements.txt       # Python依赖
├── docker-compose.yml             # 更新的编排文件
└── deploy.sh                      # 更新的部署脚本
```

## 🚀 **部署步骤**

### **1. 构建统一容器**
```bash
cd ~/tg2emall
docker-compose build unified
```

### **2. 启动服务**
```bash
# 启动核心服务
docker-compose up -d mysql unified nginx-proxy-manager

# 查看状态
docker-compose ps
```

### **3. 查看日志**
```bash
# 查看统一容器日志
docker-compose logs -f unified

# 查看特定服务日志
docker exec tg2em-unified tail -f /app/logs/frontend.log
docker exec tg2em-unified tail -f /app/logs/scraper.log
docker exec tg2em-unified tail -f /app/logs/tgstate.log
```

## 🎮 **服务控制**

### **管理界面控制**
访问 http://localhost:5000/dm 进行服务管理：

- **服务状态**: 显示真实的进程状态和PID
- **启动服务**: 发送启动信号给监控脚本
- **停止服务**: 发送SIGTERM信号终止进程
- **重启服务**: 先停止再启动

### **命令行控制**
```bash
# 进入统一容器
docker exec -it tg2em-unified /bin/bash

# 查看进程状态
ps aux | grep -E "(python|tgstate)"

# 手动停止服务
kill -TERM <PID>

# 查看PID文件
cat /app/data/pids.env
```

## 🔍 **进程管理机制**

### **启动流程**
1. **启动脚本**: `start.sh` 启动所有服务
2. **PID记录**: 将进程ID保存到 `/app/data/pids.env`
3. **监控循环**: 每10秒检查进程状态
4. **自动重启**: 检测到进程死亡时自动重启

### **服务控制器**
```python
# 真实进程状态检查
def get_service_status(self, service_name):
    pid = self.services[service_name]['pid']
    if psutil.pid_exists(pid):
        process = psutil.Process(pid)
        return 'running' if process.is_running() else 'stopped'
    return 'stopped'

# 真实进程控制
def stop_service(self, service_name):
    pid = self.services[service_name]['pid']
    os.kill(pid, signal.SIGTERM)  # 发送终止信号
```

## 📊 **监控和日志**

### **日志文件**
- `/app/logs/frontend.log` - Flask前端服务日志
- `/app/logs/scraper.log` - Telegram采集服务日志  
- `/app/logs/tgstate.log` - 图片上传服务日志

### **状态文件**
- `/app/data/pids.env` - 进程ID记录文件
- 格式: `FRONTEND_PID=1234\nSCRAPER_PID=5678\nTGSTATE_PID=9012`

### **健康检查**
```bash
# 检查服务状态
docker exec tg2em-unified python3 -c "
from service_manager import service_manager
print(service_manager.get_service_status('frontend'))
print(service_manager.get_service_status('scraper'))
print(service_manager.get_service_status('tgstate'))
"
```

## 🛠️ **故障排除**

### **服务无法启动**
```bash
# 检查容器日志
docker-compose logs unified

# 检查进程状态
docker exec tg2em-unified ps aux

# 手动启动服务
docker exec tg2em-unified /app/start.sh
```

### **进程管理问题**
```bash
# 重新加载PID文件
docker exec tg2em-unified python3 -c "
from service_manager import service_manager
service_manager.load_pids()
print('PID文件已重新加载')
"

# 重启监控脚本
docker exec tg2em-unified pkill -f service_manager.py
docker exec tg2em-unified python3 /app/service_manager.py &
```

### **端口冲突**
```bash
# 检查端口占用
docker exec tg2em-unified netstat -tlnp

# 检查服务监听
docker exec tg2em-unified lsof -i :5000
docker exec tg2em-unified lsof -i :8088
```

## 🎉 **优势总结**

### **✅ 解决的问题**
1. **Docker API连接问题**: 不再需要Docker socket挂载
2. **容器间通信**: 所有服务在同一容器内，直接进程通信
3. **服务控制真实性**: 真实的进程管理，非模拟控制
4. **部署简化**: 单一容器部署，减少复杂度

### **✅ 新增功能**
1. **自动进程监控**: 持续监控服务健康状态
2. **自动重启机制**: 进程异常时自动恢复
3. **统一日志管理**: 集中化的日志收集
4. **真实状态反馈**: 管理界面显示真实进程状态

### **✅ 用户体验**
1. **管理界面**: 真实的服务控制按钮
2. **状态显示**: 准确的进程状态和PID信息
3. **操作反馈**: 即时的启动/停止操作结果
4. **错误处理**: 友好的错误信息显示

**现在您拥有了真正的服务控制能力！** 🚀
