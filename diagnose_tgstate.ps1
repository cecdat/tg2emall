# PowerShell 脚本：诊断 tgState 服务问题

Write-Host "🔍 诊断 tgState 图片上传服务..." -ForegroundColor Cyan
Write-Host ""

# 切换到脚本所在目录
Set-Location $PSScriptRoot

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "1️⃣  检查 Docker 容器状态" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
docker ps -a | Select-String "tg2em"

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "2️⃣  检查 .env 文件" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
if (Test-Path .env) {
    Write-Host "✅ .env 文件存在" -ForegroundColor Green
    Write-Host ""
    Write-Host "环境变量配置：" -ForegroundColor Cyan
    Get-Content .env | Select-String "TGSTATE"
} else {
    Write-Host "❌ .env 文件不存在" -ForegroundColor Red
    Write-Host "   请运行: Copy-Item env.example .env" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "3️⃣  检查 tgstate 容器日志" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
$containerExists = docker ps -a --format "{{.Names}}" | Select-String "tg2em-tgstate"
if ($containerExists) {
    Write-Host "容器日志（最近 20 行）：" -ForegroundColor Cyan
    docker logs tg2em-tgstate --tail 20
} else {
    Write-Host "❌ tg2em-tgstate 容器不存在或未启动" -ForegroundColor Red
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "4️⃣  测试管理 API 端口" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "测试端口 8001..." -ForegroundColor Cyan
try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect("localhost", 8001)
    $tcpClient.Close()
    Write-Host "✅ 端口 8001 可访问" -ForegroundColor Green
} catch {
    Write-Host "❌ 端口 8001 无法访问" -ForegroundColor Red
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "5️⃣  测试管理 API 接口" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

Write-Host "测试 /api/management/status ..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/management/status" -Method Get -TimeoutSec 5
    Write-Host "✅ API 响应正常" -ForegroundColor Green
    Write-Host "   响应内容: $($response | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "❌ API 无响应" -ForegroundColor Red
    Write-Host "   错误: $($_.Exception.Message)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "6️⃣  测试前端服务连接" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$frontendExists = docker ps --format "{{.Names}}" | Select-String "tg2em-frontend"
if ($frontendExists) {
    Write-Host "✅ 前端服务正在运行" -ForegroundColor Green
    Write-Host ""
    Write-Host "前端服务日志（最近 10 行）：" -ForegroundColor Cyan
    docker logs tg2em-frontend --tail 10
} else {
    Write-Host "❌ 前端服务未运行" -ForegroundColor Red
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host "📊 诊断总结" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

$issues = @()
$solutions = @()

# 检查容器状态
$tgstateRunning = docker ps --format "{{.Names}}" | Select-String "tg2em-tgstate"
if (-not $tgstateRunning) {
    $issues += "❌ tgstate 容器未运行"
    $solutions += "运行: docker-compose up -d tgstate"
}

# 检查 .env 文件
if (-not (Test-Path .env)) {
    $issues += "❌ .env 文件缺失"
    $solutions += "运行: Copy-Item env.example .env"
}

if ($issues.Count -eq 0) {
    Write-Host "✅ 未发现明显问题" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "发现的问题：" -ForegroundColor Yellow
    foreach ($issue in $issues) {
        Write-Host "  $issue" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "建议的解决方案：" -ForegroundColor Yellow
    foreach ($solution in $solutions) {
        Write-Host "  • $solution" -ForegroundColor Cyan
    }
    Write-Host ""
    Write-Host "或者运行修复脚本:" -ForegroundColor Yellow
    Write-Host "  .\fix_tgstate.ps1" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray

