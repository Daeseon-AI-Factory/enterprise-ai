@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  Enterprise LLM Platform - Starting...
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python이 설치되어 있지 않습니다.
    pause
    exit /b 1
)

echo http://localhost:8080 에서 실행됩니다...
echo 종료: 이 창을 닫으세요
echo.

timeout /t 3 /nobreak >nul
start http://localhost:8080

python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
pause
