#!/bin/bash

echo "🔧 修复 tgState 图片上传服务..."
echo ""

# 设置颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 .env 文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  未找到 .env 文件，从 env.example 创建...${NC}"
    cp env.example .env
    echo -e "${GREEN}✅ .env 文件创建成功${NC}"
else
    echo -e "${GREEN}✅ .env 文件已存在${NC}"
fi

# 停止现有的 tgstate 容器
echo ""
echo "🛑 停止现有的 tgstate 容器..."
docker-compose stop tgstate 2>/dev/null || true
docker-compose rm -f tgstate 2>/dev/null || true

# 重新构建 tgstate 镜像
echo ""
echo "🔨 重新构建 tgstate 镜像..."
docker-compose build --no-cache tgstate

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ tgstate 镜像构建成功${NC}"
else
    echo -e "${RED}❌ tgstate 镜像构建失败${NC}"
    exit 1
fi

# 启动 tgstate 服务
echo ""
echo "🚀 启动 tgstate 服务..."
docker-compose up -d tgstate

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ tgstate 服务启动成功${NC}"
else
    echo -e "${RED}❌ tgstate 服务启动失败${NC}"
    exit 1
fi

# 等待服务启动
echo ""
echo "⏳ 等待服务完全启动..."
sleep 5

# 检查服务状态
echo ""
echo "📊 检查服务状态..."
docker-compose ps tgstate

# 查看服务日志
echo ""
echo "📋 服务日志（最近10行）："
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker-compose logs --tail=10 tgstate
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 测试管理接口
echo ""
echo "🧪 测试管理接口..."
sleep 2

# 测试状态接口
STATUS_RESPONSE=$(curl -s http://localhost:8001/api/management/status 2>/dev/null || echo "连接失败")
if [[ "$STATUS_RESPONSE" == *"success"* ]]; then
    echo -e "${GREEN}✅ 管理接口响应正常${NC}"
    echo "   响应: $STATUS_RESPONSE"
else
    echo -e "${RED}❌ 管理接口无响应${NC}"
    echo "   响应: $STATUS_RESPONSE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}🎉 修复流程完成！${NC}"
echo ""
echo "📌 服务信息："
echo "   - 管理服务: http://localhost:8001"
echo "   - 管理API: http://localhost:8001/api/management/status"
echo "   - 上传服务: http://localhost:8002"
echo ""
echo "📌 常用命令："
echo "   - 查看日志: docker-compose logs -f tgstate"
echo "   - 重启服务: docker-compose restart tgstate"
echo "   - 停止服务: docker-compose stop tgstate"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

