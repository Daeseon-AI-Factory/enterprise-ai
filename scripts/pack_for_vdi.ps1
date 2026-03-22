# VDI 전송용 ZIP 패키지 생성
# Usage: powershell -ExecutionPolicy Bypass -File scripts\pack_for_vdi.ps1

$ErrorActionPreference = "Continue"
$ROOT = Resolve-Path (Join-Path $PSScriptRoot "..")
$STAGING = Join-Path $ROOT "vdi_staging"
$ZIP = Join-Path $ROOT "EnterpriseLLM_VDI.zip"

Write-Host "===== VDI 패키지 생성 시작 ====="

if (Test-Path $STAGING) { Remove-Item -Recurse -Force $STAGING }
if (Test-Path $ZIP) { Remove-Item -Force $ZIP }
New-Item -ItemType Directory -Force $STAGING | Out-Null

# --- 1. 소스코드 ---
Write-Host "[1/4] 소스코드..."
$src = Join-Path $STAGING "source"
New-Item -ItemType Directory -Force $src | Out-Null

$include = @("app", "platform\src", "platform\public", "platform\index.html",
             "platform\package.json", "platform\tsconfig.json", "platform\vite.config.ts",
             "platform\tailwind.config.js", "platform\postcss.config.js",
             "platform\components.json",
             "scripts", "docs", "tests",
             "requirements.txt", "CLAUDE.md", ".env.example", ".env.airgap",
             "docker-compose.vllm.yml", "docker-compose.vllm-cpu.yml",
             "docker-compose.airgap.yml")

foreach ($item in $include) {
    $full = Join-Path $ROOT $item
    if (Test-Path $full) {
        $dest = Join-Path $src $item
        $parent = Split-Path $dest -Parent
        if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force $parent | Out-Null }
        if ((Get-Item $full).PSIsContainer) {
            Copy-Item -Recurse -Force $full $dest
        } else {
            Copy-Item -Force $full $dest
        }
    }
}

# --- 2. 임베딩 모델 ---
Write-Host "[2/4] 임베딩 모델..."
$embSrc = Join-Path $ROOT "models\embedding"
$embDst = Join-Path $STAGING "models\embedding"
if (Test-Path $embSrc) {
    Copy-Item -Recurse -Force $embSrc $embDst
    Write-Host "  OK"
} else {
    Write-Host "  WARNING: models/embedding not found"
}

# --- 3. Python 패키지 (오프라인) ---
Write-Host "[3/4] Python 패키지 다운로드..."
$pkgDir = Join-Path $STAGING "packages"
New-Item -ItemType Directory -Force $pkgDir | Out-Null
$reqFile = Join-Path $ROOT "requirements.txt"
& pip download -r $reqFile -d $pkgDir --quiet 2>$null
Write-Host "  OK"

# --- 4. 설치 가이드 ---
Write-Host "[4/4] 설치 가이드..."
$guide = @'
============================================
 Enterprise LLM Platform - VDI Install Guide
============================================

1. 이 ZIP을 VDI에 압축 해제

2. 환경 설정
   cd source
   copy ..\.env.airgap .env
   메모장으로 .env 열어서 GPU 서버 주소 수정:
     LLM_API_BASE=http://GPU서버IP:포트/v1
     LLM_MODEL=gpt-oss-120b

3. 임베딩 모델 배치
   xcopy /E /I ..\models\embedding models\embedding

4. Python 패키지 설치
   pip install --no-index --find-links=..\packages -r requirements.txt

5. 프론트엔드 빌드
   cd platform
   npm install
   npm run build
   cd ..

6. 백엔드 실행
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8080

7. 브라우저 접속
   http://localhost:8080
   로그인: admin / changeme123!
'@
$guide | Out-File -Encoding utf8 (Join-Path $STAGING "INSTALL_GUIDE.txt")

# --- ZIP 생성 ---
Write-Host ""
Write-Host "ZIP 압축 중..."
Compress-Archive -Path (Join-Path $STAGING "*") -DestinationPath $ZIP -CompressionLevel Optimal

# 정리
Remove-Item -Recurse -Force $STAGING

$sizeMB = [math]::Round((Get-Item $ZIP).Length / 1MB, 1)
Write-Host ""
Write-Host "===== 완료 ====="
Write-Host "파일: $ZIP"
Write-Host "크기: ${sizeMB}MB"
