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
:: 复制静态文件
copy /Y "%CANVAS_DIR%\dist\index.html" "%DEPLOY_DIR%\index.html" >nul
if exist "%CANVAS_DIR%\dist\assets" (
    for %%f in ("%CANVAS_DIR%\dist\assets\*") do (
        copy /Y "%%f" "%DEPLOY_DIR%\assets\" >nul 2>&1
    )
)
:: 复制服务器
copy /Y "%CANVAS_DIR%\server.py" "%DEPLOY_DIR%\server.py" >nul
echo ✅ 部署完成

echo.
echo [3/3] 启动服务器...
start cmd /k "cd /d %DEPLOY_DIR% && python server.py"

echo.
echo ========================================
echo   🚀 画布已启动: http://localhost:8081
echo ========================================
pause