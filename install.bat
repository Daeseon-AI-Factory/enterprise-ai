@echo off
chcp 65001 >nul
echo ============================================
echo  Enterprise LLM Platform - 자동 설치
echo ============================================
echo.

REM 1. pip 오프라인 설치
echo [1/3] Python 패키지 설치 중...
pip install --no-index --find-links=offline_packages -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] 일부 패키지 설치 실패. 수동 확인 필요.
)
echo.

REM 2. 환경 설정
echo [2/3] 환경 설정...
if not exist .env (
    copy .env.airgap .env
    echo .env 파일 생성됨. GPU 서버 주소를 수정해주세요:
    echo   LLM_API_BASE=http://GPU서버IP:포트/v1
) else (
    echo .env 이미 존재. 스킵.
)
echo.

REM 3. 임베딩 모델 확인
echo [3/3] 임베딩 모델 확인...
if exist models\embedding\config.json (
    echo 임베딩 모델 OK
) else (
    echo [WARNING] models\embedding\ 폴더에 임베딩 모델을 복사해주세요.
)
echo.

echo ============================================
echo  설치 완료!
echo ============================================
echo.
echo 실행 방법:
echo   python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
echo.
echo 접속: http://localhost:8080
echo 로그인: admin / changeme123!
echo.
pause
