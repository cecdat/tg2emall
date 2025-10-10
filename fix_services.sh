#!/bin/bash

# tg2emall 服务修复脚本
# 用于修复服务管理问题

echo "🔧 修复 tg2emall 服务管理问题..."
echo "=================================="

# 检查当前状态
echo "📊 当前服务状态:"
docker-compose ps

echo ""
echo "🛑 停止所有服务..."
docker-compose down

echo ""
echo "🧹 清理Docker资源..."
# 清理未使用的容器和镜像
docker system prune -f

echo ""
echo "🔧 重新构建服务..."
# 重新构建可能有问题的服务
docker-compose build --no-cache tgstate
docker-compose build --no-cache tg2em-scrape

echo ""
echo "🚀 启动服务..."
docker-compose up -d

echo ""
echo "⏳ 等待服务完全启动..."
sleep 30

echo ""
echo "🔍 检查服务状态..."

# 检查各个服务的健康状态
check_service() {
    local service_name=$1
    local container_name=$2
    local port=$3
    
    echo -n "检查 $service_name: "
    
    # 检查容器是否运行
    if docker ps | grep -q "$container_name"; then
        echo -n "容器运行中 "
        
        # 检查端口是否监听
        if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
            echo "✅ 端口 $port 监听中"
        else
            echo "⚠️ 端口 $port 未监听"
        fi
    else
        echo "❌ 容器未运行"
    fi
}

check_service "MySQL" "tg2em-mysql" "3306"
check_service "前端服务" "tg2em-frontend" "8000"
check_service "采集管理" "tg2em-scrape" "2003"
check_service "tgState管理" "tg2em-tgstate" "8001"
check_service "tgState上传" "tg2em-tgstate" "8002"
check_service "tgState页面" "tg2em-tgstate" "8088"

echo ""
echo "🌐 测试服务接口..."

# 测试服务接口
test_api() {
    local service_name=$1
    local url=$2
    
    echo -n "测试 $service_name API: "
    if curl -s --connect-timeout 5 "$url" > /dev/null 2>&1; then
        echo "✅ 可访问"
    else
        echo "❌ 不可访问"
        echo "   尝试访问: $url"
    fi
}

test_api "前端服务" "http://localhost:8000"
test_api "采集管理" "http://localhost:2003/api/management/status"
test_api "tgState管理" "http://localhost:8001/api/management/status"
test_api "tgState页面" "http://localhost:8088"

echo ""
echo "📋 修复完成！"
echo "=================================="
echo "如果仍有问题，请检查："
echo "1. 防火墙设置是否允许相关端口"
echo "2. .env 文件配置是否正确"
echo "3. 服务器资源是否充足"
echo "4. 查看详细日志: docker-compose logs"
