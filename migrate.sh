#!/bin/bash

# tg2emall 数据库迁移脚本
# 用于添加缺失的表：search_logs 和 visit_logs

echo "🔄 开始数据库迁移..."

# 检查是否在Docker环境中
if [ -f /.dockerenv ]; then
    echo "📦 检测到Docker环境"
    MYSQL_HOST="mysql"
else
    echo "🖥️ 检测到本地环境"
    MYSQL_HOST="localhost"
fi

# 数据库连接参数
MYSQL_USER="tg2emall"
MYSQL_PASSWORD="tg2emall"
MYSQL_DATABASE="tg2em"

echo "🔗 连接到数据库: $MYSQL_HOST"

# 执行迁移脚本
mysql -h "$MYSQL_HOST" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < migrate.sql

if [ $? -eq 0 ]; then
    echo "✅ 数据库迁移完成！"
    echo "📊 已添加以下表："
    echo "   - search_logs (搜索日志表)"
    echo "   - visit_logs (访问日志表)"
    echo "📈 已添加示例数据用于测试"
else
    echo "❌ 数据库迁移失败！"
    echo "💡 请检查数据库连接和权限"
    exit 1
fi

echo "🎉 迁移完成，现在可以正常使用热门搜索和访问统计功能了！"
