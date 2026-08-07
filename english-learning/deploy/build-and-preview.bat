@echo off
REM 朝词浅阅 - 前端构建 + 本地预览脚本
REM 用法：双击运行，或命令行执行

echo [1/2] 构建前端生产包...
cd /d E:\20260718\english-learning
call npm run build
if errorlevel 1 (
    echo 构建失败
    pause
    exit /b 1
)

echo [2/2] 预览生产包 (http://localhost:4173)...
echo 注：预览模式的 /api 不会代理到后端，需配合 nginx 或后端起在 8001
call npm run preview
