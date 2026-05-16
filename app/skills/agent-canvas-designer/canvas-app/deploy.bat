@echo off
chcp 65001 >nul
echo ========================================
echo   智能体画布 v3.0 — 一键部署
echo ========================================
echo.

set CANVAS_DIR=D:\work\DriFoxx\app\skills\agent-canvas-designer\canvas-app
set DEPLOY_DIR=C:\tmp\canvas

echo [1/3] 构建前端...
cd /d "%CANVAS_DIR%"
call npm run build
if errorlevel 1 (
    echo ❌ 构建失败
    pause
    exit /b 1
)
echo ✅ 构建完成

echo.
echo [2/3] 部署到 %DEPLOY_DIR%...
if not exist "%DEPLOY_DIR%" mkdir "%DEPLOY_DIR%"
if exist "%DEPLOY_DIR%\dist" rmdir /s /q "%DEPLOY_DIR%\dist"
xcopy /e /y "%CANVAS_DIR%\dist" "%DEPLOY_DIR%\dist\"
copy /y "%CANVAS_DIR%\server.py" "%DEPLOY_DIR%\server.py"
echo ✅ 部署完成

echo.
echo [3/3] 文件清单:
dir /b "%DEPLOY_DIR%"
dir /b "%DEPLOY_DIR%\dist"

echo.
echo ========================================
echo   🚀 启动画布:
echo      cd /d C:\tmp\canvas
echo      python server.py
echo   🌐 访问: http://localhost:8081
echo ========================================
pause
