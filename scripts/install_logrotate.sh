#!/bin/bash

# tg2emall 日志轮转安装脚本
# 用于在服务器上安装和配置日志轮转

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== tg2emall 日志轮转安装脚本 ===${NC}"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}错误: 请以root用户运行此脚本${NC}"
    echo "使用: sudo $0"
    exit 1
fi

# 创建日志目录
echo -e "${YELLOW}创建日志目录...${NC}"
mkdir -p /data/tg2emall/logs/{frontend,scraper,tgstate,admin,unified,system}

# 设置权限
chown -R 1000:1000 /data/tg2emall/logs
chmod -R 755 /data/tg2emall/logs

# 安装logrotate配置
echo -e "${YELLOW}安装logrotate配置...${NC}"
if [ -f "logrotate.conf" ]; then
    cp logrotate.conf /etc/logrotate.d/tg2emall
    chmod 644 /etc/logrotate.d/tg2emall
    echo -e "${GREEN}logrotate配置已安装${NC}"
else
    echo -e "${RED}错误: 找不到logrotate.conf文件${NC}"
    exit 1
fi

# 测试logrotate配置
echo -e "${YELLOW}测试logrotate配置...${NC}"
logrotate -d /etc/logrotate.d/tg2emall
if [ $? -eq 0 ]; then
    echo -e "${GREEN}logrotate配置测试通过${NC}"
else
    echo -e "${RED}logrotate配置测试失败${NC}"
    exit 1
fi

# 创建cron任务
echo -e "${YELLOW}创建cron任务...${NC}"

# 添加日志清理任务（每天凌晨2点执行）
(crontab -l 2>/dev/null; echo "0 2 * * * /data/tg2emall/scripts/cleanup_logs.sh >> /var/log/tg2emall-cleanup.log 2>&1") | crontab -

# 添加日志监控任务（每小时执行一次）
(crontab -l 2>/dev/null; echo "0 * * * * /data/tg2emall/scripts/monitor_logs.sh >> /var/log/tg2emall-monitor.log 2>&1") | crontab -

echo -e "${GREEN}cron任务已创建${NC}"

# 创建系统日志目录
mkdir -p /var/log/tg2emall
chown root:root /var/log/tg2emall
chmod 755 /var/log/tg2emall

# 设置脚本权限
chmod +x /data/tg2emall/scripts/*.sh

echo -e "${GREEN}=== 安装完成 ===${NC}"
echo -e "${BLUE}日志轮转配置已安装到: /etc/logrotate.d/tg2emall${NC}"
echo -e "${BLUE}日志目录已创建: /data/tg2emall/logs${NC}"
echo -e "${BLUE}cron任务已设置:${NC}"
echo -e "  - 日志清理: 每天凌晨2点"
echo -e "  - 日志监控: 每小时"
echo ""
echo -e "${YELLOW}手动测试命令:${NC}"
echo -e "  sudo logrotate -f /etc/logrotate.d/tg2emall  # 强制执行日志轮转"
echo -e "  /data/tg2emall/scripts/monitor_logs.sh      # 查看日志状态"
echo -e "  /data/tg2emall/scripts/cleanup_logs.sh      # 清理过期日志"
