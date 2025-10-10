#!/bin/bash

# tg2emall 数据库迁移脚本
# 用于添加缺失的表：search_logs 和 visit_logs

echo "🔄 开始数据库迁移..."

# 检查是否在Docker环境中
if [ -f /.dockerenv ]; then
    echo "📦 检测到Docker环境"
    MYSQL_HOST="mysql"
    MYSQL_PORT="3306"
else
    echo "🖥️ 检测到本地环境"
    # 检查Docker容器是否运行
    if docker ps | grep -q "tg2em-mysql"; then
        echo "🐳 检测到Docker容器运行中，使用容器连接"
        MYSQL_HOST="localhost"
        MYSQL_PORT="3306"
    else
        echo "❌ 未检测到Docker容器，请先启动服务："
        echo "   docker-compose up -d"
        exit 1
    fi
fi

# 数据库连接参数（与docker-compose.yml中的配置保持一致）
MYSQL_USER="tg2emall"
MYSQL_PASSWORD="tg2emall"
MYSQL_DATABASE="tg2em"

echo "🔗 连接到数据库: $MYSQL_HOST:$MYSQL_PORT"

# 测试数据库连接
echo "🔍 测试数据库连接..."
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" "$MYSQL_DATABASE" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ 数据库连接失败！"
    echo "💡 请检查："
    echo "   1. Docker容器是否运行：docker ps | grep tg2em-mysql"
    echo "   2. 数据库是否已启动：docker-compose logs mysql"
    echo "   3. 网络连接是否正常"
    exit 1
fi

echo "✅ 数据库连接成功！"

# 执行迁移脚本
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < migrate.sql

if [ $? -eq 0 ]; then
    echo "✅ 数据库迁移完成！"
    echo "📊 已添加以下表："
    echo "   - search_logs (搜索日志表)"
    echo "   - visit_logs (访问日志表)"
    echo "📈 已添加示例数据用于测试"
    
    # 修改 referrer 字段长度
    echo "🔧 修改 referrer 字段长度..."
    mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "ALTER TABLE visit_logs MODIFY COLUMN referrer TEXT;"
    
    if [ $? -eq 0 ]; then
        echo "✅ referrer 字段长度修改成功！"
    else
        echo "⚠️ referrer 字段长度修改失败，但不影响主要功能"
    fi
else
    echo "❌ 数据库迁移失败！"
    echo "💡 请检查数据库连接和权限"
    exit 1
fi

echo "🎉 迁移完成，现在可以正常使用热门搜索和访问统计功能了！"
echo ""
echo "📋 后续步骤："
echo "   1. 重启相关服务：docker-compose restart"
echo "   2. 检查服务状态：docker-compose ps"
echo "   3. 查看日志：docker-compose logs -f"
