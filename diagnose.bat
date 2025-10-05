@echo off
REM tg2emall 服务器诊断脚本 (Windows版本)
REM 用于检查端口配置和服务状态

echo 🔍 tg2emall 服务器诊断脚本
echo ==================================

REM 1. 检查Docker服务状态
echo.
echo 1. 检查Docker服务状态
echo --------------------------------
docker-compose ps

REM 2. 检查端口监听状态
echo.
echo 2. 检查端口监听状态
echo --------------------------------
echo 检查6000端口 (前端服务):
netstat -an | findstr :6000
if %errorlevel% neq 0 echo ❌ 6000端口未监听

echo 检查6001端口 (图片管理服务):
netstat -an | findstr :6001
if %errorlevel% neq 0 echo ❌ 6001端口未监听

echo 检查6002端口 (图片上传服务):
netstat -an | findstr :6002
if %errorlevel% neq 0 echo ❌ 6002端口未监听

echo 检查2003端口 (采集管理服务):
netstat -an | findstr :2003
if %errorlevel% neq 0 echo ❌ 2003端口未监听

REM 3. 检查服务日志
echo.
echo 3. 检查服务日志 (最近10行)
echo --------------------------------
echo 前端服务日志:
docker-compose logs --tail=10 frontend

echo.
echo 图片服务日志:
docker-compose logs --tail=10 tgstate

echo.
echo 采集服务日志:
docker-compose logs --tail=10 tg2em-scrape

REM 4. 检查网络连接
echo.
echo 4. 检查网络连接
echo --------------------------------
echo 检查本地连接:
curl -s -o nul -w "本地6000端口: %%{http_code}\n" http://localhost:6000
curl -s -o nul -w "本地6001端口: %%{http_code}\n" http://localhost:6001
curl -s -o nul -w "本地6002端口: %%{http_code}\n" http://localhost:6002

echo.
echo 建议的解决方案:
echo 1. 如果端口未监听，请重启服务: docker-compose restart
echo 2. 如果防火墙阻止，请开放端口:
echo    - Windows防火墙: 允许6000,6001,6002,2003端口
echo    - 云服务器安全组: 开放相应端口
echo 3. 如果服务异常，请检查日志: docker-compose logs [service_name]
echo 4. 确保云服务器安全组已开放相应端口

echo.
echo ✅ 诊断完成！
pause
