@echo off
REM 朝词浅阅 - 后端生产启动脚本（Windows）
REM 前置：MySQL 已运行（3306），backend/.env 配置正确
REM 用法：双击运行，或命令行执行

echo [1/3] 运行数据库迁移...
cd /d E:\20260718\backend
E:\20260718\venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 (
    echo 迁移失败，请检查 MySQL 连接
    pause
    exit /b 1
)

echo [2/3] 启动 FastAPI 后端 (127.0.0.1:8001)...
REM 首次启动会自动播种词书 + 词库 + 管理员账号
E:\20260718\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
