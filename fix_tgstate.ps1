# PowerShell 脚本：修复 tgState 图片上传服务

Write-Host "🔧 修复 tgState 图片上传服务..." -ForegroundColor Cyan
Write-Host ""

# 切换到脚本所在目录
Set-Location $PSScriptRoot

# 检查 .env 文件
if (-not (Test-Path .env)) {
    Write-Host "⚠️  未找到 .env 文件，从 env.example 创建..." -ForegroundColor Yellow
    Copy-Item env.example .env
    Write-Host "✅ .env 文件创建成功" -ForegroundColor Green
} else {
    Write-Host "✅ .env 文件已存在" -ForegroundColor Green
}

# 停止现有的 tgstate 容器
Write-Host ""
Write-Host "🛑 停止现有的 tgstate 容器..." -ForegroundColor Cyan
docker-compose stop tgstate 2>$null
docker-compose rm -f tgstate 2>$null

# 重新构建 tgstate 镜像
Write-Host ""
Write-Host "🔨 重新构建 tgstate 镜像..." -ForegroundColor Cyan
docker-compose build --no-cache tgstate

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ tgstate 镜像构建成功" -ForegroundColor Green
} else {
    Write-Host "❌ tgstate 镜像构建失败" -ForegroundColor Red
    exit 1
}

# 启动 tgstate 服务
Write-Host ""
Write-Host "🚀 启动 tgstate 服务..." -ForegroundColor Cyan
docker-compose up -d tgstate

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ tgstate 服务启动成功" -ForegroundColor Green
} else {
    Write-Host "❌ tgstate 服务启动失败" -ForegroundColor Red
    exit 1
}

# 等待服务启动
Write-Host ""
Write-Host "⏳ 等待服务完全启动..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# 检查服务状态
Write-Host ""
Write-Host "📊 检查服务状态..." -ForegroundColor Cyan
docker-compose ps tgstate

# 查看服务日志
Write-Host ""
Write-Host "📋 服务日志（最近10行）：" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
docker-compose logs --tail=10 tgstate
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

# 测试管理接口
Write-Host ""
Write-Host "🧪 测试管理接口..." -ForegroundColor Cyan
Start-Sleep -Seconds 2

# 测试状态接口
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/management/status" -Method Get -TimeoutSec 5
    if ($response.success) {
        Write-Host "✅ 管理接口响应正常" -ForegroundColor Green
        Write-Host "   响应: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
    } else {
        Write-Host "❌ 管理接口返回错误" -ForegroundColor Red
        Write-Host "   响应: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ 管理接口无响应" -ForegroundColor Red
    Write-Host "   错误: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "🎉 修复流程完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📌 服务信息：" -ForegroundColor Cyan
Write-Host "   - 管理服务: http://localhost:8001"
Write-Host "   - 管理API: http://localhost:8001/api/management/status"
Write-Host "   - 上传服务: http://localhost:8002"
Write-Host ""
Write-Host "📌 常用命令：" -ForegroundColor Cyan
Write-Host "   - 查看日志: docker-compose logs -f tgstate"
Write-Host "   - 重启服务: docker-compose restart tgstate"
Write-Host "   - 停止服务: docker-compose stop tgstate"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

