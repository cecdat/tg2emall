@echo off
chcp 65001 >nul
echo ================================================================
echo   tgState 服务快速修复工具
echo ================================================================
echo.

cd /d %~dp0

echo [1/6] 检查 .env 文件...
if not exist .env (
    echo    未找到 .env 文件，从 env.example 创建...
    copy env.example .env >nul
    echo    .env 文件创建成功！
) else (
    echo    .env 文件已存在
)
echo.

echo [2/6] 停止现有的 tgstate 容器...
docker-compose stop tgstate 2>nul
docker-compose rm -f tgstate 2>nul
echo    已停止现有容器
echo.

echo [3/6] 重新构建 tgstate 镜像（这可能需要几分钟）...
docker-compose build --no-cache tgstate
if %errorlevel% neq 0 (
    echo    镜像构建失败！
    pause
    exit /b 1
)
echo    镜像构建成功！
echo.

echo [4/6] 启动 tgstate 服务...
docker-compose up -d tgstate
if %errorlevel% neq 0 (
    echo    服务启动失败！
    pause
    exit /b 1
)
echo    服务启动成功！
echo.

echo [5/6] 等待服务完全启动...
timeout /t 5 /nobreak >nul
echo.

echo [6/6] 检查服务状态...
docker-compose ps tgstate
echo.

echo ================================================================
echo   修复完成！
echo ================================================================
echo.
echo 服务信息：
echo   - 管理服务: http://localhost:8001
echo   - 管理API: http://localhost:8001/api/management/status
echo   - 上传服务: http://localhost:8002
echo.
echo 查看日志: docker-compose logs -f tgstate
echo.
pause

