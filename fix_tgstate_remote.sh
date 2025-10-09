#!/bin/bash
# 远程服务器 tgState 服务修复脚本 (Debian 12)

set -e

echo "========================================"
echo "  tgState 服务修复工具 (远程服务器)"
echo "========================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检查是否在项目目录
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}错误: 未找到 docker-compose.yml 文件${NC}"
    echo "请在项目根目录运行此脚本"
    exit 1
fi

echo -e "${BLUE}[1/7] 检查环境...${NC}"
# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: 未安装 Docker${NC}"
    exit 1
fi

# 检查 Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}错误: 未安装 Docker Compose${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 环境检查通过${NC}"
echo ""

echo -e "${BLUE}[2/7] 检查 .env 文件...${NC}"
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ 未找到 .env 文件，从 env.example 创建...${NC}"
    cp env.example .env
    echo -e "${GREEN}✓ .env 文件创建成功${NC}"
    echo -e "${YELLOW}! 请编辑 .env 文件配置 Telegram Bot Token 等信息${NC}"
    echo ""
    read -p "是否现在编辑 .env 文件? (y/n): " edit_env
    if [ "$edit_env" = "y" ] || [ "$edit_env" = "Y" ]; then
        ${EDITOR:-nano} .env
    fi
else
    echo -e "${GREEN}✓ .env 文件已存在${NC}"
fi
echo ""

echo -e "${BLUE}[3/7] 备份当前配置...${NC}"
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
if docker ps -a | grep -q tg2em-tgstate; then
    echo "备份容器日志..."
    docker logs tg2em-tgstate > "$BACKUP_DIR/tgstate.log" 2>&1 || true
fi
echo -e "${GREEN}✓ 备份完成: $BACKUP_DIR${NC}"
echo ""

echo -e "${BLUE}[4/7] 停止现有的 tgstate 容器...${NC}"
docker-compose stop tgstate 2>/dev/null || true
docker-compose rm -f tgstate 2>/dev/null || true
echo -e "${GREEN}✓ 已停止现有容器${NC}"
echo ""

echo -e "${BLUE}[5/7] 重新构建 tgstate 镜像...${NC}"
echo "这可能需要几分钟，请耐心等待..."
if docker-compose build --no-cache tgstate; then
    echo -e "${GREEN}✓ 镜像构建成功${NC}"
else
    echo -e "${RED}✗ 镜像构建失败${NC}"
    echo "请检查构建日志并修复错误"
    exit 1
fi
echo ""

echo -e "${BLUE}[6/7] 启动 tgstate 服务...${NC}"
if docker-compose up -d tgstate; then
    echo -e "${GREEN}✓ 服务启动成功${NC}"
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo "请检查日志: docker-compose logs tgstate"
    exit 1
fi
echo ""

echo -e "${BLUE}[7/7] 等待服务启动并验证...${NC}"
echo "等待 10 秒让服务完全启动..."
sleep 10

# 检查容器状态
if docker ps | grep -q tg2em-tgstate; then
    echo -e "${GREEN}✓ 容器运行正常${NC}"
else
    echo -e "${RED}✗ 容器未运行${NC}"
    echo "查看日志:"
    docker-compose logs --tail=20 tgstate
    exit 1
fi

# 测试管理 API
echo ""
echo "测试管理 API..."
if curl -s -f http://localhost:8001/api/management/status > /dev/null 2>&1; then
    response=$(curl -s http://localhost:8001/api/management/status)
    echo -e "${GREEN}✓ 管理 API 响应正常${NC}"
    echo "响应: $response"
else
    echo -e "${YELLOW}⚠ 管理 API 暂时无响应（可能还在初始化）${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}  修复完成！${NC}"
echo "========================================"
echo ""
echo "服务信息:"
echo "  - 管理服务: http://localhost:8001"
echo "  - 管理API: http://localhost:8001/api/management/status"
echo "  - 上传服务: http://localhost:8002"
echo ""
echo "常用命令:"
echo "  - 查看日志: docker-compose logs -f tgstate"
echo "  - 查看状态: docker-compose ps tgstate"
echo "  - 重启服务: docker-compose restart tgstate"
echo "  - 停止服务: docker-compose stop tgstate"
echo ""
echo "测试 API:"
echo "  curl http://localhost:8001/api/management/status"
echo ""

