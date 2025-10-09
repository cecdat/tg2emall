#!/bin/bash

# tg2emall 端口和地址修复脚本
# 用于修复 ERR_UNSAFE_PORT 错误和地址配置问题

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  tg2emall 端口和地址修复脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. 获取公网IP
echo -e "${BLUE}[1/5]${NC} 获取公网IP地址..."
PUBLIC_IP=""

# 尝试多个服务
for service in "ifconfig.me" "api.ipify.org" "ipinfo.io/ip" "api.ip.sb/ip"; do
    ip=$(curl -s --connect-timeout 3 $service || echo "")
    if [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        PUBLIC_IP=$ip
        echo -e "${GREEN}✅ 公网IP: $PUBLIC_IP${NC}"
        break
    fi
done

if [ -z "$PUBLIC_IP" ]; then
    echo -e "${RED}❌ 无法获取公网IP，请手动输入${NC}"
    read -p "请输入服务器公网IP或域名: " PUBLIC_IP
fi

# 2. 更新 .env 文件
echo ""
echo -e "${BLUE}[2/5]${NC} 更新环境变量配置..."

if [ ! -f ".env" ]; then
    cp env.example .env
    echo -e "${GREEN}✅ 创建 .env 文件${NC}"
fi

# 更新或添加配置
grep -q "^FRONTEND_PORT=" .env && sed -i "s/^FRONTEND_PORT=.*/FRONTEND_PORT=8000/" .env || echo "FRONTEND_PORT=8000" >> .env
grep -q "^PUBLIC_IP=" .env && sed -i "s/^PUBLIC_IP=.*/PUBLIC_IP=$PUBLIC_IP/" .env || echo "PUBLIC_IP=$PUBLIC_IP" >> .env
grep -q "^TGSTATE_URL=" .env && sed -i "s|^TGSTATE_URL=.*|TGSTATE_URL=http://$PUBLIC_IP:8001|" .env || echo "TGSTATE_URL=http://$PUBLIC_IP:8001" >> .env

echo -e "${GREEN}✅ 环境变量已更新${NC}"

# 3. 停止服务
echo ""
echo -e "${BLUE}[3/5]${NC} 停止现有服务..."
docker-compose down
echo -e "${GREEN}✅ 服务已停止${NC}"

# 4. 重新构建前端
echo ""
echo -e "${BLUE}[4/5]${NC} 重新构建前端服务..."
docker-compose build frontend
echo -e "${GREEN}✅ 前端服务已重新构建${NC}"

# 5. 启动服务
echo ""
echo -e "${BLUE}[5/5]${NC} 启动所有服务..."
docker-compose up -d

# 等待服务启动
echo ""
echo -e "${YELLOW}⏳ 等待服务启动（30秒）...${NC}"
sleep 30

# 6. 更新数据库配置
echo ""
echo -e "${BLUE}[额外]${NC} 更新数据库配置..."

# 等待MySQL完全启动
echo -e "${YELLOW}⏳ 等待MySQL完全启动（10秒）...${NC}"
sleep 10

# 更新数据库中的URL配置
docker exec tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
UPDATE system_config 
SET config_value = 'http://$PUBLIC_IP:8001' 
WHERE config_key = 'tgstate_url';
" 2>/dev/null && echo -e "${GREEN}✅ 数据库配置已更新${NC}" || echo -e "${YELLOW}⚠️  数据库配置更新失败，请手动更新${NC}"

# 7. 显示访问信息
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  修复完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}📍 访问地址：${NC}"
echo -e "  • 主站: ${YELLOW}http://$PUBLIC_IP:8000${NC}"
echo -e "  • 管理后台: ${YELLOW}http://$PUBLIC_IP:8000/dm${NC}"
echo -e "  • 图片服务: ${YELLOW}http://$PUBLIC_IP:8001${NC}"
echo -e "  • 采集管理: ${YELLOW}http://$PUBLIC_IP:2003${NC}"
echo -e "  • NPM管理: ${YELLOW}http://$PUBLIC_IP:81${NC}"
echo ""
echo -e "${BLUE}🔐 默认登录信息：${NC}"
echo -e "  • 用户名: ${YELLOW}admin${NC}"
echo -e "  • 密码: ${YELLOW}admin${NC}"
echo -e "  • 验证码: ${YELLOW}2025${NC}"
echo ""
echo -e "${BLUE}📊 查看服务状态：${NC}"
echo -e "  ${YELLOW}docker-compose ps${NC}"
echo ""
echo -e "${BLUE}📝 查看日志：${NC}"
echo -e "  ${YELLOW}docker-compose logs -f${NC}"
echo ""
echo -e "${GREEN}✅ 不会再出现 ERR_UNSAFE_PORT 错误！${NC}"
echo ""

