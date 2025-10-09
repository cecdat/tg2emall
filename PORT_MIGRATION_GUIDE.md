# 端口迁移指南 - 6xxx → 8xxx

## 📋 端口变更总结

为避免浏览器的 `ERR_UNSAFE_PORT` 错误，所有 6 开头的端口已统一替换为 8 开头的端口。

### 端口对照表

| 服务 | 旧端口 | 新端口 | 变更理由 |
|------|--------|--------|----------|
| 前端展示 | 6000 | **8000** | 避免 ERR_UNSAFE_PORT |
| 图片管理服务 | 6001 | **8001** | 统一端口规范 |
| 图片上传服务 | 6002 | **8002** | 统一端口规范 |

**未变更的端口**:
- NPM管理: `81`
- 采集管理: `2003`
- 采集服务: `5002`
- MySQL: `3306`

---

## 🔧 修改的文件清单

### 1. Docker配置文件
- ✅ `docker-compose.yml`
  - 前端: `6000:6000` → `8000:8000`
  - tgState管理: `6001:6001` → `8001:8001`
  - tgState上传: `6002:6002` → `8002:8002`
  - 环境变量URL更新

### 2. Go服务文件
- ✅ `services/tgstate/management-service.go`
  - 服务监听端口: `6001` → `8001`
- ✅ `services/tgstate/upload-service.go`
  - 默认端口: `6002` → `8002`
  - 默认URL: `http://localhost:6001` → `http://localhost:8001`
- ✅ `services/tgstate/Dockerfile`
  - EXPOSE端口: `6001 6002` → `8001 8002`

### 3. 前端服务文件
- ✅ `services/frontend/Dockerfile`
  - EXPOSE端口: `6000` → `8000`
- ✅ `services/frontend/service_controller.py`
  - tgState连接地址: `:6001` → `:8001`
- ✅ `services/frontend/templates/admin_config.html`
  - 示例端口更新: `6001/6002` → `8001/8002`

### 4. 数据库配置
- ✅ `init.sql`
  - `tgstate_management_port`: `6001` → `8001`
  - `tgstate_upload_port`: `6002` → `8002`

### 5. 部署和文档
- ✅ `deploy.sh`
  - 显示地址更新
- ✅ `fix_port.sh`
  - 端口配置更新
- ✅ `fix_port_and_address.md`
  - 文档端口更新

---

## 🚀 部署步骤

### 步骤1: 拉取最新代码

```bash
cd ~/tg2emall
git pull origin main
```

### 步骤2: 停止现有服务

```bash
docker-compose down
```

### 步骤3: 更新数据库配置

```bash
# 启动MySQL容器
docker-compose up -d mysql

# 等待MySQL启动
sleep 30

# 更新端口配置
docker exec tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
UPDATE system_config SET config_value = '8001' WHERE config_key = 'tgstate_management_port';
UPDATE system_config SET config_value = '8002' WHERE config_key = 'tgstate_upload_port';

-- 如果配置了tgstate_url，也需要更新
UPDATE system_config SET config_value = REPLACE(config_value, ':6001', ':8001') WHERE config_key = 'tgstate_url';
"

# 验证更新
docker exec tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
SELECT config_key, config_value FROM system_config WHERE config_key LIKE '%port%' OR config_key = 'tgstate_url';
"
```

### 步骤4: 重新构建服务

```bash
# 重新构建前端和tgState服务
docker-compose build frontend tgstate

# 或者重新构建所有服务
docker-compose build
```

### 步骤5: 启动所有服务

```bash
docker-compose up -d
```

### 步骤6: 验证服务

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f frontend
docker-compose logs -f tgstate
```

### 步骤7: 更新防火墙规则

```bash
# UFW
sudo ufw delete allow 6000/tcp
sudo ufw delete allow 6001/tcp
sudo ufw delete allow 6002/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 8001/tcp
sudo ufw allow 8002/tcp

# Firewalld
sudo firewall-cmd --permanent --remove-port=6000-6002/tcp
sudo firewall-cmd --permanent --add-port=8000-8002/tcp
sudo firewall-cmd --reload
```

### 步骤8: 更新云服务器安全组

如果使用云服务器（阿里云/腾讯云/AWS等），需要在控制台更新安全组规则：

1. 移除旧规则：
   - 删除 6000、6001、6002 端口
   
2. 添加新规则：
   - 允许 8000（前端）
   - 允许 8001（图片管理）
   - 允许 8002（图片上传）

---

## 🧪 测试验证

### 1. 端口监听检查

```bash
# 检查新端口是否在监听
netstat -tlnp | grep -E "8000|8001|8002"

# 应该看到类似输出：
# tcp6       0      0 :::8000              :::*                    LISTEN      12345/docker-proxy
# tcp6       0      0 :::8001              :::*                    LISTEN      12346/docker-proxy
# tcp6       0      0 :::8002              :::*                    LISTEN      12347/docker-proxy
```

### 2. 服务访问测试

```bash
# 获取公网IP
PUBLIC_IP=$(curl -s ifconfig.me)

# 测试前端服务
curl -I http://$PUBLIC_IP:8000

# 测试图片管理服务
curl -I http://$PUBLIC_IP:8001

# 测试图片上传服务
curl -I http://$PUBLIC_IP:8002
```

### 3. 浏览器访问测试

- 前端: `http://你的公网IP:8000`
- 管理后台: `http://你的公网IP:8000/dm`
- 图片管理: `http://你的公网IP:8001`

**预期结果**: 不再出现 `ERR_UNSAFE_PORT` 错误！ ✅

---

## 📝 配置更新

### .env 文件

更新或添加以下配置：

```bash
# 前端端口
FRONTEND_PORT=8000

# tgState配置
TGSTATE_URL=http://你的公网IP:8001
TGSTATE_MANAGEMENT_PORT=8001
TGSTATE_UPLOAD_PORT=8002
```

### 数据库配置

确保以下配置值正确：

```sql
-- 检查配置
SELECT config_key, config_value FROM system_config 
WHERE config_key IN (
    'tgstate_management_port', 
    'tgstate_upload_port', 
    'tgstate_url'
);

-- 应该看到：
-- tgstate_management_port | 8001
-- tgstate_upload_port     | 8002
-- tgstate_url             | http://你的公网IP:8001
```

---

## ⚠️ 常见问题

### Q1: 拉取代码时提示冲突

```bash
error: Your local changes to the following files would be overwritten by merge:
        deploy.sh
```

**解决方案**:
```bash
# 方案1: 暂存本地修改
git stash
git pull
git stash pop

# 方案2: 放弃本地修改
git checkout -- deploy.sh
git pull
```

### Q2: 更新后无法访问服务

**检查步骤**:
1. 确认容器正在运行: `docker-compose ps`
2. 检查端口监听: `netstat -tlnp | grep 800`
3. 查看服务日志: `docker-compose logs frontend`
4. 检查防火墙规则: `sudo ufw status`
5. 检查云服务器安全组

### Q3: 图片上传失败

**问题**: 容器间通信地址未更新

**解决方案**:
```bash
# 检查环境变量
docker exec tg2em-scrape env | grep TGSTATE_URL

# 应该显示: TGSTATE_URL=http://tgstate:8001

# 如果不对，重新构建并启动
docker-compose down
docker-compose build tg2em-scrape
docker-compose up -d
```

### Q4: Nginx Proxy Manager 反向代理配置

如果使用NPM配置了反向代理，需要更新：

1. 登录 NPM: `http://你的公网IP:81`
2. 找到对应的代理主机
3. 更新转发端口:
   - 前端: `6000` → `8000`
   - 图片服务: `6001` → `8001`

---

## 📊 回滚方案

如果需要回滚到旧端口：

```bash
# 1. 回退Git提交
git revert HEAD

# 2. 停止服务
docker-compose down

# 3. 重新构建
docker-compose build

# 4. 启动服务
docker-compose up -d

# 5. 恢复防火墙规则
sudo ufw allow 6000-6002/tcp
sudo ufw delete allow 8000-8002/tcp
```

---

## ✅ 验证清单

部署完成后，请确认：

- [ ] 所有容器正常运行 (`docker-compose ps`)
- [ ] 可以通过 8000 端口访问前端
- [ ] 可以通过 8000/dm 访问管理后台
- [ ] 不再出现 ERR_UNSAFE_PORT 错误
- [ ] 图片上传功能正常
- [ ] 采集服务可以连接到图片服务
- [ ] 防火墙/安全组规则已更新

---

## 📞 支持

如有问题：
1. 查看日志: `docker-compose logs -f [service_name]`
2. 检查配置: 访问管理后台 → 配置管理
3. 参考文档: `fix_port_and_address.md`

---

**提交哈希**: 134dee7  
**更新日期**: 2025-10-09  
**影响范围**: 所有使用 6xxx 端口的服务

