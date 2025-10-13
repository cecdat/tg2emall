#!/bin/bash

# tg2emall 日志监控脚本
# 用于监控日志文件大小和状态

# 设置日志目录
LOG_DIR="/data/tg2emall/logs"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== tg2emall 日志监控报告 ===${NC}"
echo "时间: $(date)"
echo ""

# 检查日志目录是否存在
if [ ! -d "$LOG_DIR" ]; then
    echo -e "${RED}错误: 日志目录 $LOG_DIR 不存在${NC}"
    exit 1
fi

# 监控各服务的日志文件
services=("frontend" "scraper" "tgstate" "admin" "unified" "system")

for service in "${services[@]}"; do
    service_log_dir="$LOG_DIR/$service"
    
    echo -e "${YELLOW}=== $service 服务日志 ===${NC}"
    
    if [ -d "$service_log_dir" ]; then
        # 统计日志文件数量和大小
        log_count=$(find "$service_log_dir" -name "*.log*" -type f | wc -l)
        total_size=$(du -sh "$service_log_dir" 2>/dev/null | cut -f1)
        
        echo -e "日志文件数量: ${GREEN}$log_count${NC}"
        echo -e "总大小: ${GREEN}$total_size${NC}"
        
        # 显示最大的几个日志文件
        echo -e "${BLUE}最大的日志文件:${NC}"
        find "$service_log_dir" -name "*.log*" -type f -exec ls -lh {} \; | sort -k5 -hr | head -5 | while read line; do
            echo "  $line"
        done
        
        # 检查是否有错误日志
        error_logs=$(find "$service_log_dir" -name "*error*.log*" -type f | wc -l)
        if [ $error_logs -gt 0 ]; then
            echo -e "${RED}发现 $error_logs 个错误日志文件${NC}"
        fi
        
    else
        echo -e "${YELLOW}日志目录不存在${NC}"
    fi
    echo ""
done

# 检查Docker容器日志
echo -e "${YELLOW}=== Docker容器日志状态 ===${NC}"
docker ps --filter "name=tg2em" --format "table {{.Names}}\t{{.Status}}\t{{.Size}}" | while read line; do
    echo -e "${BLUE}$line${NC}"
done

# 检查磁盘空间
echo -e "${YELLOW}=== 磁盘空间使用情况 ===${NC}"
df -h "$LOG_DIR" 2>/dev/null | tail -1 | awk '{print "可用空间: " $4 " / " $2 " (" $5 " 已使用)"}'

# 检查最近的错误
echo -e "${YELLOW}=== 最近的错误日志 (最近10条) ===${NC}"
find "$LOG_DIR" -name "*error*.log" -type f -exec tail -10 {} \; 2>/dev/null | head -20

echo -e "${GREEN}日志监控完成！${NC}"
