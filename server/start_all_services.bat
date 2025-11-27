@echo off
setlocal enabledelayedexpansion

:: 设置中文编码
chcp 65001

:: 系统启动服务批处理脚本
:: 此脚本用于在系统启动后自动运行所有必要的服务
:: 建议添加到Windows任务计划程序，设置为系统启动时自动运行

:: 调试模式：打印当前目录和环境信息
echo 当前目录: %CD%
echo 操作系统版本: %OS%
echo 计算机名称: %COMPUTERNAME%

:: 暂时注释管理员权限检查，用于调试
:: 检查管理员权限
NET SESSION >nul 2>&1
if %ERRORLEVEL% neq 0 (
   echo ERROR: 此脚本需要以管理员身份运行。
   echo 请右键点击并选择"以管理员身份运行"。
   pause
   exit /b 1
)

echo 开始启动所有服务...

:: 创建日志目录
if not exist "C:\www\logs" (
    mkdir "C:\www\logs"
)

:: 记录启动时间
echo %date% %time% - 开始启动所有服务 >> "C:\www\logs\service_start.log"

:: 1. 启动 Python 应用 (app.py)
echo 启动 Python 应用程序...
cd /d "C:\www\server"
start "EarthOnline App" /min python app.py
if %ERRORLEVEL% equ 0 (
    echo Python 应用程序已启动 >> "C:\www\logs\service_start.log"
) else (
    echo Python 应用程序启动失败 >> "C:\www\logs\service_start.log"
)

:: 等待几秒确保前一个服务启动
ping 127.0.0.1 -n 3 > nul

:: 2. 启动 Nginx
echo 启动 Nginx...
cd /d "C:\nginx"
if exist "nginx.exe" (
    start "Nginx Server" /min nginx.exe
    echo Nginx 已启动 >> "C:\www\logs\service_start.log"
) else (
    echo Nginx 未找到 >> "C:\www\logs\service_start.log"
)

:: 等待几秒确保前一个服务启动
ping 127.0.0.1 -n 3 > nul

:: 3. 启动 FRP 服务器
echo 启动 FRP 服务器...
cd /d "C:\frp"
if exist "frps.exe" (
    start "FRP Server" /min frps.exe -c frps.ini
    echo FRP 服务器已启动 >> "C:\www\logs\service_start.log"
) else (
    echo FRP 服务器未找到 >> "C:\www\logs\service_start.log"
)

:: 等待几秒确保前一个服务启动
ping 127.0.0.1 -n 3 > nul

:: 4. 启动证书续期服务
echo 启动证书续期服务...
:: 使用用户提供的路径
if exist "d:\code\EarthOnline\server\utils\SSL_TOOL\start_certificate_service.bat" (
    start "Certificate Service" /min "d:\code\EarthOnline\server\utils\SSL_TOOL\start_certificate_service.bat"
    echo 证书续期服务已启动 >> "C:\www\logs\service_start.log"
) else (
    echo 证书续期服务脚本未找到 >> "C:\www\logs\service_start.log"
)

echo 所有服务启动命令已执行完毕
:: 记录完成时间
echo %date% %time% - 所有服务启动命令执行完毕 >> "C:\www\logs\service_start.log"

:: 可选：保持窗口打开用于调试
pause

:: 可选：自动关闭窗口
:: exit