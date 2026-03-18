@echo off
chcp 65001 >nul 2>&1
title 启动API和WebUI服务

:: 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未检测到Python环境，请先安装Python并添加到系统环境变量！
    pause
    exit /b 1
)

echo ==============================================
echo 正在启动 ServerRESTapi.py...
start "ServerRESTapi" cmd /k "python ServerRESTapi.py"

echo 正在启动 WebUi.py...
start "WebUi" cmd /k "python WebUi.py"

echo ==============================================
echo ✅ 两个服务已分别在新窗口启动！
echo 📌 关闭本窗口不会影响服务运行，如需停止服务请关闭对应的Python窗口
