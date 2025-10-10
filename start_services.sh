#!/bin/bash

# tg2emall 服务启动脚本
# 用于在远程服务器上启动所有服务

echo "🚀 启动 tg2emall 服务..."
echo "=================================="

# 检查是否存在 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 未找到 .env 文件，请先创建配置文件"
    echo "💡 可以复制 env.example 文件："
    echo "   cp env.example .env"
    echo "   然后编辑 .env 文件，填入正确的配置"
    exit 1
fi

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker 服务"
    echo "💡 启动命令："
    echo "   sudo systemctl start docker"
    exit 1
fi

echo "📦 启动 Docker 服务..."

# 停止现有服务（如果有）
echo "🛑 停止现有服务..."
docker-compose down

# 启动服务
echo "🚀 启动所有服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

echo ""
echo "🌐 测试服务接口..."

# 等待更长时间让服务完全启动
sleep 20

# 测试关键服务
test_services() {
    local service_name=$1
    local url=$2
    local max_attempts=10
    local attempt=1
    
    echo -n "测试 $service_name: "
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s --connect-timeout 5 "$url" > /dev/null 2>&1; then
            echo "✅ 成功"
            return 0
        else
            echo -n "."
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    echo "❌ 失败"
    return 1
}

# 测试各个服务
test_services "前端服务" "http://localhost:8000"
test_services "采集管理" "http://localhost:2003/api/management/status"
test_services "tgState管理" "http://localhost:8001/api/management/status"
test_services "tgState页面" "http://localhost:8088"

echo ""
echo "📋 服务访问地址:"
echo "--------------------------------"
echo "🌐 前端页面: http://your-server-ip:8000"
echo "🔧 管理后台: http://your-server-ip:8000/admin"
echo "📊 tgState管理: http://your-server-ip:8088"
echo ""
echo "🔑 默认管理员账号:"
echo "   用户名: admin"
echo "   密码: admin123"
echo ""
echo "📝 查看日志:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 停止服务:"
echo "   docker-compose down"
