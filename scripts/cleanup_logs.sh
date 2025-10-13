#!/bin/bash

# tg2emall 日志清理脚本
# 用于清理过期的日志文件

# 设置日志目录
LOG_DIR="/data/tg2emall/logs"
DAYS_TO_KEEP=30

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始清理 tg2emall 日志文件...${NC}"

# 检查日志目录是否存在
if [ ! -d "$LOG_DIR" ]; then
    echo -e "${RED}错误: 日志目录 $LOG_DIR 不存在${NC}"
    exit 1
fi

# 清理各服务的日志文件
services=("frontend" "scraper" "tgstate" "admin" "unified" "system")

for service in "${services[@]}"; do
    service_log_dir="$LOG_DIR/$service"
    
    if [ -d "$service_log_dir" ]; then
        echo -e "${YELLOW}清理 $service 服务日志...${NC}"
        
        # 查找并删除超过指定天数的日志文件
        find "$service_log_dir" -name "*.log*" -type f -mtime +$DAYS_TO_KEEP -exec rm -f {} \;
        
        # 统计剩余文件
        remaining_files=$(find "$service_log_dir" -name "*.log*" -type f | wc -l)
        echo -e "${GREEN}$service 服务: 保留 $remaining_files 个日志文件${NC}"
    else
        echo -e "${YELLOW}$service 服务日志目录不存在，跳过${NC}"
    fi
done

# 清理Docker容器日志
echo -e "${YELLOW}清理Docker容器日志...${NC}"

# 清理所有tg2em相关的容器日志
docker ps -a --filter "name=tg2em" --format "{{.Names}}" | while read container; do
    if [ ! -z "$container" ]; then
        echo -e "${YELLOW}清理容器 $container 的日志...${NC}"
        docker logs "$container" > /dev/null 2>&1
    fi
done

# 清理系统日志（如果存在）
if [ -d "/var/log/tg2emall" ]; then
    echo -e "${YELLOW}清理系统日志...${NC}"
    find /var/log/tg2emall -name "*.log*" -type f -mtime +$DAYS_TO_KEEP -exec rm -f {} \;
fi

# 显示磁盘使用情况
echo -e "${GREEN}日志清理完成！${NC}"
echo -e "${YELLOW}当前日志目录磁盘使用情况:${NC}"
du -sh "$LOG_DIR"/* 2>/dev/null | sort -hr

# 显示总磁盘使用情况
echo -e "${YELLOW}总日志目录大小:${NC}"
du -sh "$LOG_DIR"

echo -e "${GREEN}日志清理脚本执行完成！${NC}"
