#!/bin/bash

# tg2emall 服务器诊断脚本
# 用于检查端口配置和服务状态

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 tg2emall 服务器诊断脚本${NC}"
echo "=================================="

# 1. 检查Docker服务状态
echo -e "\n${YELLOW}1. 检查Docker服务状态${NC}"
echo "--------------------------------"
docker-compose ps

# 2. 检查端口监听状态
echo -e "\n${YELLOW}2. 检查端口监听状态${NC}"
echo "--------------------------------"
echo "检查6000端口 (前端服务):"
netstat -tlnp | grep :6000 || echo "❌ 6000端口未监听"

echo "检查6001端口 (图片管理服务):"
netstat -tlnp | grep :6001 || echo "❌ 6001端口未监听"

echo "检查6002端口 (图片上传服务):"
netstat -tlnp | grep :6002 || echo "❌ 6002端口未监听"

echo "检查2003端口 (采集管理服务):"
netstat -tlnp | grep :2003 || echo "❌ 2003端口未监听"

# 3. 检查防火墙状态
echo -e "\n${YELLOW}3. 检查防火墙状态${NC}"
echo "--------------------------------"
if command -v ufw &> /dev/null; then
    echo "UFW防火墙状态:"
    ufw status
elif command -v firewall-cmd &> /dev/null; then
    echo "Firewalld防火墙状态:"
    firewall-cmd --list-all
elif command -v iptables &> /dev/null; then
    echo "iptables防火墙状态:"
    iptables -L -n | head -20
else
    echo "未检测到防火墙服务"
fi

# 4. 检查服务日志
echo -e "\n${YELLOW}4. 检查服务日志 (最近10行)${NC}"
echo "--------------------------------"
echo "前端服务日志:"
docker-compose logs --tail=10 frontend

echo -e "\n图片服务日志:"
docker-compose logs --tail=10 tgstate

echo -e "\n采集服务日志:"
docker-compose logs --tail=10 tg2em-scrape

# 5. 检查网络连接
echo -e "\n${YELLOW}5. 检查网络连接${NC}"
echo "--------------------------------"
echo "检查本地连接:"
curl -s -o /dev/null -w "本地6000端口: %{http_code}\n" http://localhost:6000 || echo "❌ 本地6000端口连接失败"
curl -s -o /dev/null -w "本地6001端口: %{http_code}\n" http://localhost:6001 || echo "❌ 本地6001端口连接失败"
curl -s -o /dev/null -w "本地6002端口: %{http_code}\n" http://localhost:6002 || echo "❌ 本地6002端口连接失败"

# 6. 检查公网IP
echo -e "\n${YELLOW}6. 检查公网IP配置${NC}"
echo "--------------------------------"
echo "当前公网IP:"
curl -s ifconfig.me || curl -s ipinfo.io/ip || echo "无法获取公网IP"

echo -e "\n建议的解决方案:"
echo "1. 如果端口未监听，请重启服务: docker-compose restart"
echo "2. 如果防火墙阻止，请开放端口:"
echo "   - UFW: sudo ufw allow 6000,6001,6002,2003"
echo "   - Firewalld: sudo firewall-cmd --permanent --add-port=6000-6002/tcp --add-port=2003/tcp"
echo "3. 如果服务异常，请检查日志: docker-compose logs [service_name]"
echo "4. 确保云服务器安全组已开放相应端口"

echo -e "\n${GREEN}诊断完成！${NC}"
