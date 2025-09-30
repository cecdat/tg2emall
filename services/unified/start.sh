#!/bin/bash

echo "🚀 启动统一服务容器..."

# 设置环境变量
export PYTHONPATH="/app:/app/frontend:/app/tg2em"
export FLASK_ENV=production

# 确保日志目录存在
mkdir -p /app/logs

# 启动服务管理程序
echo "📋 启动服务管理程序..."
python3 /app/service_manager.py &

# 等待服务管理程序启动
sleep 2

# 启动后端Go服务 (tgstate)
echo "🖼️ 启动图片上传服务..."
cd /app/tgstate
nohup ./tgstate > /app/logs/tgstate.log 2>&1 &
TGSTATE_PID=$!
echo "图片上传服务PID: $TGSTATE_PID"

# 等待tgstate服务启动
sleep 3

# 启动Telegram采集服务
echo "📱 启动Telegram采集服务..."
cd /app/tg2em
nohup python3 scrape.py > /app/logs/scraper.log 2>&1 &
SCRAPER_PID=$!
echo "采集服务PID: $SCRAPER_PID"

# 等待采集服务启动
sleep 2

# 启动前端Flask应用
echo "🌐 启动前端服务..."
cd /app/frontend
nohup python3 app.py > /app/logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "前端服务PID: $FRONTEND_PID"

# 保存所有PID到文件中供服务控制使用
echo "FRONTEND_PID=$FRONTEND_PID" > /app/data/pids.env
echo "SCRAPER_PID=$SCRAPER_PID" >> /app/data/pids.env
echo "TGSTATE_PID=$TGSTATE_PID" >> /app/data/pids.env

echo "✅ 所有服务已启动完成!"
echo "📊 前端服务: http://localhost:5000"
echo "🖼️ 图片服务: http://localhost:8088"
echo ""
echo "📋 服务状态监控中..."

# 监控进程，如果任何进程退出则重启
while true; do
    # 检查前端服务
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "⚠️ 前端服务进程死亡，正在重启..."
        cd /app/frontend
        nohup python3 app.py > /app/logs/frontend.log 2>&1 &
        FRONTEND_PID=$!
        echo "FRONTEND_PID=$FRONTEND_PID" > /app/data/pids.env
        echo "✅ 前端服务已重启 (PID: $FRONTEND_PID)"
    fi
    
    # 检查采集服务
    if ! kill -0 $SCRAPER_PID 2>/dev/null; then
        echo "⚠️ 采集服务进程死亡，正在重启..."
        cd /app/tg2em || echo "❌ 采集服务重启失败：找不到工作目录"
        nohup python3 scrape.py > /app/logs/scraper.log 2>&1 &
        SCRAPER_PID=$!
        echo "SCRAPER_PID=$SCRAPER_PID" >> /app/data/pids.env
        echo "✅ 采集服务已重启 (PID: $SCRAPER_PID)"
    fi
    
    # 检查图片服务
    if ! kill -0 $TGSTATE_PID 2>/dev/null; then
        echo "⚠️ 图片服务进程死亡，正在重启..."
        cd /app/tgstate
        nohup ./tgstate > /app/logs/tgstate.log 2>&1 &
        TGSTATE_PID=$!
        echo "TGSTATE_PID=$TGSTATE_PID" >> /app/data/pids.env
        echo "✅ 图片服务已重启 (PID: $TGSTATE_PID)"
    fi
    
    # 等待10秒再次检查
    sleep 10
done
