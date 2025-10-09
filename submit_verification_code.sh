#!/bin/bash

# Telegram 验证码提交脚本
# 用于在Web界面未更新时快速提交验证码

echo "=========================================="
echo "  Telegram 验证码提交工具"
echo "=========================================="
echo ""

# 检查参数
if [ -z "$1" ]; then
    echo "请输入您收到的5位验证码："
    read -r CODE
else
    CODE=$1
fi

# 验证码格式检查
if [[ ! $CODE =~ ^[0-9]{5}$ ]]; then
    echo "❌ 错误：验证码必须是5位数字"
    echo "示例：12345"
    exit 1
fi

echo ""
echo "📱 验证码：$CODE"
echo "📤 正在提交到数据库..."

# 提交验证码到数据库
docker exec tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "
-- 插入或更新验证码
INSERT INTO system_config (config_key, config_value, config_type, description, category)
VALUES ('telegram_verification_code', '$CODE', 'string', 'Telegram验证码', 'telegram')
ON DUPLICATE KEY UPDATE config_value = '$CODE', updated_at = NOW();

-- 标记验证码已提交
INSERT INTO system_config (config_key, config_value, config_type, description, category)
VALUES ('telegram_verification_submitted', 'true', 'boolean', '验证码已提交', 'telegram')
ON DUPLICATE KEY UPDATE config_value = 'true', updated_at = NOW();

-- 标记需要验证（确保采集脚本能检测到）
INSERT INTO system_config (config_key, config_value, config_type, description, category)
VALUES ('telegram_verification_required', 'true', 'boolean', '需要验证码', 'telegram')
ON DUPLICATE KEY UPDATE config_value = 'true', updated_at = NOW();

SELECT '验证码已提交' as status;
" 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ 验证码提交成功！"
    echo ""
    echo "📝 请查看采集服务日志，等待验证完成："
    echo "   docker logs -f tg2em-scrape"
    echo ""
    echo "⏳ 脚本会等待验证码被读取..."
    
    # 查看日志（实时显示验证过程）
    docker logs -f --tail=20 tg2em-scrape
else
    echo "❌ 验证码提交失败，请检查数据库连接"
    exit 1
fi

