#!/bin/bash

# tg2emall 服务状态检查脚本
# 用于检查远程服务器上的服务运行状态

echo "🔍 检查 tg2emall 服务状态..."
echo "=================================="

# 检查Docker容器状态
echo "📦 Docker容器状态:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(tg2em|mysql|nginx)"

echo ""
echo "🌐 服务端口检查:"
echo "--------------------------------"

# 检查各服务端口
services=(
    "前端服务:8000"
    "MySQL:3306" 
    "采集管理:2003"
    "采集服务:5002"
    "tgState管理:8001"
    "tgState上传:8002"
    "tgState页面:8088"
)

for service in "${services[@]}"; do
    name=$(echo $service | cut -d: -f1)
    port=$(echo $service | cut -d: -f2)
    
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        echo "✅ $name (端口 $port): 运行中"
    else
        echo "❌ $name (端口 $port): 未运行"
    fi
done

echo ""
echo "🔗 服务接口测试:"
echo "--------------------------------"

# 测试服务接口
test_urls=(
    "http://localhost:8000"
    "http://localhost:2003/api/management/status"
    "http://localhost:8001/api/management/status"
    "http://localhost:8088"
)

for url in "${test_urls[@]}"; do
    if curl -s --connect-timeout 3 "$url" > /dev/null 2>&1; then
        echo "✅ $url: 可访问"
    else
        echo "❌ $url: 不可访问"
    fi
done

echo ""
echo "📊 系统资源使用:"
echo "--------------------------------"
echo "内存使用:"
free -h
echo ""
echo "磁盘使用:"
df -h | grep -E "(/$|/var|/opt)"

echo ""
echo "🐳 Docker资源使用:"
echo "--------------------------------"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}" 2>/dev/null | head -10
