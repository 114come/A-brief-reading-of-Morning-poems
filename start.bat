@echo off
setlocal enabledelayedexpansion
title ChaoCiQianYue - One-Click Start
cd /d "%~dp0"

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%english-learning"
set "PY=%ROOT%venv\Scripts\python.exe"

if not exist "%PY%" (
  echo [ERROR] Python venv not found: %PY%
  pause
  exit /b 1
)

echo.
echo  ==============================================
echo   ChaoCiQianYue - One-Click Start
echo  ==============================================
echo.

REM ---------- 1. MySQL ----------
echo [1/4] Checking MySQL (3306) ...
netstat -ano 2>nul | findstr /C:":3306 " | findstr "LISTENING" >nul
if errorlevel 1 (
  echo   ..  Not running. Starting service MySQL80 ...
  net start MySQL80 >nul 2>&1
  if errorlevel 1 (
    echo   WARN  Could not auto-start MySQL. Start it manually and re-run.
  ) else (
    echo   OK   MySQL started
  )
) else (
  echo   OK   MySQL already running
)

REM ---------- 2. Backend ----------
echo [2/4] Checking backend API (8001) ...
netstat -ano 2>nul | findstr /C:":8001 " | findstr "LISTENING" >nul
if errorlevel 1 (
  echo   ..  Starting FastAPI backend ...
  start "backend-8001" /min cmd /c "cd /d %BACKEND% && %PY% -m uvicorn app.main:app --host 127.0.0.1 --port 8001"
  call :wait_http 8001 /health 60
) else (
  echo   OK   Backend already running
)

REM ---------- 3. Frontend ----------
echo [3/4] Checking frontend (5174) ...
netstat -ano 2>nul | findstr /C:":5174 " | findstr "LISTENING" >nul
if errorlevel 1 (
  echo   ..  Starting Vite frontend ...
  start "frontend-5174" /min cmd /c "cd /d %FRONTEND% && npm run dev"
  call :wait_http 5174 "" 40
) else (
  echo   OK   Frontend already running
)

REM ---------- 4. Browser ----------
if /i not "%~1"=="nobrowser" (
  echo [4/4] Opening browser ...
  start "" http://localhost:5174
) else (
  echo [4/4] nobrowser given - skip opening browser
)

echo.
echo  ==============================================
echo   All done.
echo     Frontend : http://localhost:5174
echo     API docs : http://localhost:8001/docs
echo     Account  : english_admin / 123456
echo  ==============================================
echo.
echo   ^> Services run in separate background windows.
pause
exit /b

REM ---------- Subroutine: poll until HTTP ready ----------
REM   call :wait_http <port> <path> <max-tries>
:wait_http
set "port=%~1"
set "wpath=%~2"
set "max=%~3"
set /a tries=0
:wait_loop
set /a tries+=1
set "code="
for /f %%c in ('curl -s -o nul -w "%%{http_code}" http://localhost:%port%%wpath% 2^>nul') do set "code=%%c"
if "!code!"=="200" (
  echo   OK   http://localhost:%port%%wpath% is ready
  goto :eof
)
if !tries! geq !max! (
  echo   WARN  Timeout waiting for port %port%. Check the service window log.
  goto :eof
)
>nul ping -n 2 127.0.0.1
goto wait_loop
