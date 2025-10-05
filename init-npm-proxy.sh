#!/bin/bash

# NPM代理配置初始化脚本
# 用于在NPM中预置域名和SSL配置

echo "🔧 初始化NPM代理配置..."

# 等待NPM服务启动
echo "⏳ 等待NPM服务启动..."
sleep 30

# 检查NPM是否可用
NPM_URL="http://localhost:81"
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s "$NPM_URL" > /dev/null 2>&1; then
        echo "✅ NPM服务已启动"
        break
    else
        echo "⏳ 等待NPM服务启动... ($((RETRY_COUNT + 1))/$MAX_RETRIES)"
        sleep 10
        RETRY_COUNT=$((RETRY_COUNT + 1))
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ NPM服务启动超时"
    exit 1
fi

# 创建代理主机配置
echo "🌐 配置代理主机..."

# 主站代理 (237890.xyz)
curl -X POST "$NPM_URL/api/nginx/proxy-hosts" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NPM_API_KEY" \
  -d '{
    "domain_names": ["237890.xyz", "www.237890.xyz"],
    "forward_host": "frontend",
    "forward_port": 5000,
    "forward_scheme": "http",
    "certificate_id": 1,
    "ssl_forced": true,
    "http2_support": true,
    "block_exploits": true,
    "caching_enabled": false,
    "allow_websocket_upgrade": true,
    "access_list_id": 0,
    "advanced_config": "",
    "enabled": true
  }' || echo "⚠️ 主站代理配置可能已存在"

# 图片服务代理 (img.237890.xyz)
curl -X POST "$NPM_URL/api/nginx/proxy-hosts" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NPM_API_KEY" \
  -d '{
    "domain_names": ["img.237890.xyz"],
    "forward_host": "tgstate",
    "forward_port": 8088,
    "forward_scheme": "http",
    "certificate_id": 1,
    "ssl_forced": true,
    "http2_support": true,
    "block_exploits": true,
    "caching_enabled": false,
    "allow_websocket_upgrade": true,
    "access_list_id": 0,
    "advanced_config": "",
    "enabled": true
  }' || echo "⚠️ 图片服务代理配置可能已存在"

# 创建重定向规则 (www.237890.xyz -> 237890.xyz)
echo "🔄 配置重定向规则..."
curl -X POST "$NPM_URL/api/nginx/redirection-hosts" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NPM_API_KEY" \
  -d '{
    "domain_names": ["www.237890.xyz"],
    "forward_scheme": "https",
    "forward_host": "237890.xyz",
    "forward_port": 443,
    "enabled": true
  }' || echo "⚠️ 重定向规则可能已存在"

# 申请SSL证书
echo "🔒 申请SSL证书..."
curl -X POST "$NPM_URL/api/nginx/certificates" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NPM_API_KEY" \
  -d '{
    "nice_name": "237890.xyz",
    "domain_names": ["237890.xyz", "www.237890.xyz", "img.237890.xyz"],
    "meta": {
      "letsencrypt_email": "admin@237890.xyz",
      "letsencrypt_agree": true
    }
  }' || echo "⚠️ SSL证书可能已存在"

echo "✅ NPM代理配置完成！"
echo ""
echo "🌐 访问地址："
echo "   主站: https://237890.xyz"
echo "   管理后台: https://237890.xyz/dm"
echo "   图片服务: https://img.237890.xyz"
echo "   图片管理: https://img.237890.xyz/dm"
echo ""
echo "📝 注意事项："
echo "   1. 确保域名DNS已正确解析到服务器IP"
echo "   2. SSL证书申请可能需要几分钟时间"
echo "   3. 如果证书申请失败，请检查域名解析和防火墙设置"
