# ============================================================
# Enterprise LLM — Offline Installer (Windows)
#
# 폐쇄망 Windows PC에서 실행하는 설치 스크립트
# Python, Node.js 가 없어도 자동 설치됩니다.
#
# Usage (PowerShell as Administrator):
#   powershell -ExecutionPolicy Bypass -File install.ps1
#   powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir "D:\enterprise-llm"
#
# Works from:
#   - Standalone package (enterprise-llm-offline-windows\)
#   - Repository with offline_packages\ directory
# ============================================================
param(
    [string]$InstallDir = "C:\enterprise-llm"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ── Detect package layout ──────────────────────────────────
if (Test-Path (Join-Path $ScriptDir "source.tar.gz")) {
    $PkgDir = $ScriptDir
    $Installers = Join-Path $PkgDir "installers"
    $PyPkgs = Join-Path $PkgDir "python-packages"
    $NpmPkgs = Join-Path $PkgDir "npm-packages"
    $DockerImgs = Join-Path $PkgDir "docker-images"
    $ModelSrc = Join-Path $PkgDir "models\embedding"
    $SourceTar = Join-Path $PkgDir "source.tar.gz"
    $ReqFile = Join-Path $PkgDir "scripts\requirements.txt"
    $Mode = "standalone"
} elseif (Test-Path (Join-Path (Split-Path -Parent $ScriptDir) "offline_packages")) {
    $RepoDir = Split-Path -Parent $ScriptDir
    $PkgDir = Join-Path $RepoDir "offline_packages"
    $Installers = $PkgDir
    $PyPkgs = Join-Path $PkgDir "python"
    $NpmPkgs = Join-Path $PkgDir "node"
    $DockerImgs = Join-Path $PkgDir "docker"
    $ModelSrc = Join-Path $PkgDir "models\embedding"
    $SourceTar = Join-Path $PkgDir "source.tar.gz"
    $ReqFile = Join-Path $RepoDir "requirements.txt"
    $Mode = "repo"
} else {
    Write-Host "ERROR: Cannot find offline packages." -ForegroundColor Red
    Write-Host ""
    Write-Host "Expected either:"
    Write-Host "  - Standalone package directory with source.tar.gz"
    Write-Host "  - Repository with offline_packages\ subdirectory"
    exit 1
}

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Enterprise LLM — Offline Installer (Windows)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Package mode : $Mode"
Write-Host "  Package dir  : $PkgDir"
Write-Host "  Install dir  : $InstallDir"
Write-Host ""

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + `
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# ── Step 1: Python ─────────────────────────────────────────
Write-Host "[1/8] Setting up Python..." -ForegroundColor Yellow

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$needPython = $true

if ($pythonCmd) {
    $ver = & python --version 2>&1
    if ($ver -match "3\.(1[0-9]|[2-9][0-9])") {
        $needPython = $false
        Write-Host "  Python already installed: $ver"
    }
}

if ($needPython) {
    $pyInstaller = Get-ChildItem $Installers -Filter "python-*-amd64.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($pyInstaller) {
        Write-Host "  Installing Python (silent install)..."
        $pyArgs = @(
            "/quiet",
            "InstallAllUsers=1",
            "PrependPath=1",
            "Include_pip=1",
            "Include_test=0",
            "Include_launcher=1",
            "InstallLauncherAllUsers=1"
        )
        Start-Process -FilePath $pyInstaller.FullName -ArgumentList $pyArgs -Wait -NoNewWindow
        Refresh-Path
        Write-Host "  Python installed: $(python --version 2>&1)"
    } else {
        Write-Host "  ERROR: Python not found and no installer available." -ForegroundColor Red
        Write-Host "  Place python-X.Y.Z-amd64.exe in installers\ folder."
        exit 1
    }
}

# ── Step 2: Node.js ────────────────────────────────────────
Write-Host "[2/8] Setting up Node.js..." -ForegroundColor Yellow

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    $nodeMsi = Get-ChildItem $Installers -Filter "node-*-x64.msi" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($nodeMsi) {
        Write-Host "  Installing Node.js (silent install)..."
        Start-Process msiexec.exe -ArgumentList "/i", $nodeMsi.FullName, "/qn", "/norestart" -Wait -NoNewWindow
        Refresh-Path
        Write-Host "  Node.js installed: $(node --version 2>&1)"
    } else {
        Write-Host "  WARNING: Node.js installer not found. Frontend builds will be skipped." -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  Node.js already installed: $(node --version)"
}

# ── Step 3: Git (optional) ─────────────────────────────────
Write-Host "[3/8] Checking Git..." -ForegroundColor Yellow

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    $gitExe = Get-ChildItem $Installers -Filter "Git-*-64-bit.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($gitExe) {
        Write-Host "  Installing Git (silent install)..."
        Start-Process -FilePath $gitExe.FullName -ArgumentList "/VERYSILENT", "/NORESTART" -Wait -NoNewWindow
        Refresh-Path
        Write-Host "  Git installed"
    } else {
        Write-Host "  Git not found (optional, skipping)" -ForegroundColor DarkYellow
    }
} else {
    Write-Host "  Git already installed: $(git --version)"
}

# ── Step 4: Extract source code ────────────────────────────
Write-Host "[4/8] Setting up source code..." -ForegroundColor Yellow

if ($Mode -eq "standalone" -and (Test-Path $SourceTar)) {
    $ProjectDir = Join-Path $InstallDir "app"
    New-Item -ItemType Directory -Force -Path $ProjectDir | Out-Null
    tar -xzf $SourceTar -C $ProjectDir
    $ReqFile = Join-Path $ProjectDir "requirements.txt"
    Write-Host "  Source extracted to $ProjectDir"
} else {
    $ProjectDir = Split-Path -Parent $ScriptDir
    Write-Host "  Using existing source: $ProjectDir"
}

# ── Step 5: Python venv + packages ─────────────────────────
Write-Host "[5/8] Setting up Python virtual environment..." -ForegroundColor Yellow

$VenvDir = Join-Path $InstallDir "venv"
python -m venv $VenvDir

# Activate venv
$activateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
& $activateScript

# Upgrade pip if wheel exists
$pipWhl = Get-ChildItem $PyPkgs -Filter "pip-*.whl" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($pipWhl) {
    pip install --no-index $pipWhl.FullName 2>$null
}

Write-Host "  Installing Python packages (offline)..."
pip install --no-index --find-links=$PyPkgs -r $ReqFile
Write-Host "  Python packages installed"

# ── Step 6: Embedding model ────────────────────────────────
Write-Host "[6/8] Setting up embedding model..." -ForegroundColor Yellow

if (Test-Path $ModelSrc) {
    $targetModelDir = Join-Path $ProjectDir "models"
    New-Item -ItemType Directory -Force -Path $targetModelDir | Out-Null
    Copy-Item -Recurse -Force $ModelSrc (Join-Path $targetModelDir "embedding")
    Write-Host "  Embedding model copied"
} else {
    Write-Host "  WARNING: Embedding model not found at $ModelSrc" -ForegroundColor DarkYellow
}

# ── Step 7: Frontend builds ───────────────────────────────
Write-Host "[7/8] Building frontends..." -ForegroundColor Yellow

if (Get-Command node -ErrorAction SilentlyContinue) {
    # Widget
    $widgetTar = Join-Path $NpmPkgs "widget_node_modules.tar.gz"
    if (Test-Path $widgetTar) {
        Push-Location (Join-Path $ProjectDir "widget")
        tar -xzf $widgetTar
        npm run build 2>$null
        Pop-Location
        Write-Host "  Widget built"
    }

    # Platform
    $platformTar = Join-Path $NpmPkgs "platform_node_modules.tar.gz"
    if (Test-Path $platformTar) {
        Push-Location (Join-Path $ProjectDir "platform")
        tar -xzf $platformTar
        npm run build 2>$null
        Pop-Location
        Write-Host "  Platform built"
    }
} else {
    Write-Host "  Node.js not available. Skipping frontend builds." -ForegroundColor DarkYellow
}

# ── Step 8: Environment setup ──────────────────────────────
Write-Host "[8/8] Setting up environment..." -ForegroundColor Yellow

# Data directories
foreach ($sub in @("data\conversations", "data\builds", "data\settings", "data\confluence", "uploads")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $ProjectDir $sub) | Out-Null
}

# .env
$envFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $envFile)) {
    $envExample = Join-Path $ProjectDir ".env.example"
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        (Get-Content $envFile) -replace '^MODE=local', 'MODE=airgap' | Set-Content $envFile
        Write-Host "  Created .env from template (MODE=airgap)"
    }
}

# Activation batch script
$activateBat = Join-Path $InstallDir "activate.bat"
@"
@echo off
call "$VenvDir\Scripts\activate.bat"
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1
echo.
echo Enterprise LLM environment activated (offline mode)
echo   Python: %VIRTUAL_ENV%
echo   To start: cd "$ProjectDir" ^&^& uvicorn app.main:app --host 0.0.0.0 --port 8080
echo.
"@ | Set-Content $activateBat -Encoding ASCII

# Activation PowerShell script
$activatePs1 = Join-Path $InstallDir "activate.ps1"
@"
# Enterprise LLM environment activation
& "$VenvDir\Scripts\Activate.ps1"
`$env:HF_HUB_OFFLINE = "1"
`$env:TRANSFORMERS_OFFLINE = "1"
Write-Host ""
Write-Host "Enterprise LLM environment activated (offline mode)" -ForegroundColor Green
Write-Host "  Python: `$(python --version)"
Write-Host "  To start: cd '$ProjectDir'; uvicorn app.main:app --host 0.0.0.0 --port 8080"
Write-Host ""
"@ | Set-Content $activatePs1

# Docker images (if Docker Desktop is available)
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host ""
    Write-Host "  Loading Docker images..." -ForegroundColor Yellow
    Get-ChildItem $DockerImgs -Filter "*.tar" -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Host "    Loading $($_.BaseName)..."
        docker load -i $_.FullName
    }
    Write-Host "  Docker images loaded"
} else {
    Write-Host ""
    Write-Host "  Docker not installed. Skipping image loading." -ForegroundColor DarkYellow
    Write-Host "  Install Docker Desktop to use containerized deployment."
}

# ── Done ───────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Project : $ProjectDir" -ForegroundColor White
Write-Host "  Venv    : $VenvDir" -ForegroundColor White
Write-Host "  Activate: $activateBat" -ForegroundColor White
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Configure .env:" -ForegroundColor White
Write-Host "     notepad $envFile"
Write-Host "     -> LLM_API_BASE=http://<gpu-server>:8000/v1"
Write-Host "     -> LLM_MODEL=<your-model-name>"
Write-Host ""
Write-Host "  2a. Start with Docker Compose:" -ForegroundColor White
Write-Host "      cd $ProjectDir"
Write-Host "      docker compose -f docker-compose.airgap.yml up -d"
Write-Host ""
Write-Host "  2b. Or start manually:" -ForegroundColor White
Write-Host "      $activateBat"
Write-Host "      cd $ProjectDir"
Write-Host "      uvicorn app.main:app --host 0.0.0.0 --port 8080"
Write-Host ""
Write-Host "  3. Verify installation:" -ForegroundColor White
Write-Host "      $activateBat"
Write-Host "      cd $ProjectDir"
Write-Host "      python scripts\verify_installation.py"
Write-Host ""
Write-Host "  Access:" -ForegroundColor Cyan
Write-Host "    Platform UI : http://localhost:3000"
Write-Host "    Backend API : http://localhost:8080"
Write-Host "    API Docs    : http://localhost:8080/docs"
Write-Host ""
