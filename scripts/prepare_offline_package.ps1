# ============================================================
# prepare_offline_package.ps1
#
# 인터넷 연결된 Windows PC에서 실행 — 폐쇄망 배포용 zip 패키지 생성
#
# Output:
#   enterprise-llm-offline-linux.zip    (~5 GB)
#   enterprise-llm-offline-windows.zip  (~4 GB)
#
# Prerequisites:
#   - Python 3.11+, pip
#   - Node.js 20+, npm
#   - Docker Desktop (for saving container images)
#   - pip install huggingface_hub
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\prepare_offline_package.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\prepare_offline_package.ps1 -NoDocker
#   powershell -ExecutionPolicy Bypass -File scripts\prepare_offline_package.ps1 -LinuxOnly
#   powershell -ExecutionPolicy Bypass -File scripts\prepare_offline_package.ps1 -WindowsOnly
# ============================================================
param(
    [switch]$NoDocker,
    [switch]$LinuxOnly,
    [switch]$WindowsOnly
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$BuildDir = Join-Path $ProjectDir "_offline_build"

# Versions
$PythonVersion = "3.11.9"
$NodeVersion = "v20.18.1"
$DockerVersion = "27.4.1"
$ComposeVersion = "v2.32.4"
$GitVersion = "2.47.1"

$BuildLinux = -not $WindowsOnly
$BuildWindows = -not $LinuxOnly
$IncludeDocker = -not $NoDocker

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Enterprise LLM — Offline Package Builder (Windows)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Linux package:   $BuildLinux"
Write-Host "  Windows package: $BuildWindows"
Write-Host "  Docker images:   $IncludeDocker"
Write-Host ""

# Clean previous build
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
New-Item -ItemType Directory -Force -Path (Join-Path $BuildDir "common") | Out-Null

function Download-File {
    param([string]$Url, [string]$OutFile, [string]$Label)
    Write-Host "  Downloading $Label..."
    if (Test-Path $OutFile) {
        Write-Host "    Already exists, skipping."
        return
    }
    try {
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
        Write-Host "    Done."
    } catch {
        Write-Host "    WARNING: Failed to download $Label" -ForegroundColor DarkYellow
        Write-Host "    URL: $Url"
    }
}

# ============================================================
# PHASE 1: Common downloads
# ============================================================
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Yellow
Write-Host " PHASE 1: Common Downloads" -ForegroundColor Yellow
Write-Host ("=" * 60) -ForegroundColor Yellow

# --- 1. Embedding Model ---
Write-Host ""
Write-Host "[1/4] Downloading embedding model (BAAI/bge-m3)..." -ForegroundColor Yellow
$modelDir = Join-Path $BuildDir "common\models\embedding"
New-Item -ItemType Directory -Force -Path $modelDir | Out-Null

if (Get-Command huggingface-cli -ErrorAction SilentlyContinue) {
    & huggingface-cli download BAAI/bge-m3 --local-dir $modelDir
    Write-Host "  Done: embedding model" -ForegroundColor Green
} else {
    Write-Host "  ERROR: huggingface-cli not found." -ForegroundColor Red
    Write-Host "  Run: pip install huggingface_hub"
    exit 1
}

# --- 2. npm packages ---
Write-Host ""
Write-Host "[2/4] Downloading npm packages..." -ForegroundColor Yellow
$npmDir = Join-Path $BuildDir "common\npm"
New-Item -ItemType Directory -Force -Path $npmDir | Out-Null

# Widget
Push-Location (Join-Path $ProjectDir "widget")
npm install 2>$null
tar -czf (Join-Path $npmDir "widget_node_modules.tar.gz") node_modules package-lock.json
Pop-Location
Write-Host "  Done: widget node_modules"

# Platform
Push-Location (Join-Path $ProjectDir "platform")
npm install 2>$null
tar -czf (Join-Path $npmDir "platform_node_modules.tar.gz") node_modules package-lock.json
Pop-Location
Write-Host "  Done: platform node_modules"

# --- 3. Docker images ---
if ($IncludeDocker) {
    Write-Host ""
    Write-Host "[3/4] Saving Docker images..." -ForegroundColor Yellow
    $dockerDir = Join-Path $BuildDir "common\docker-images"
    New-Item -ItemType Directory -Force -Path $dockerDir | Out-Null

    if (Get-Command docker -ErrorAction SilentlyContinue) {
        $images = @(
            @{ Image = "chromadb/chroma:latest"; Name = "chromadb" },
            @{ Image = "n8nio/n8n:latest"; Name = "n8n" },
            @{ Image = "python:3.11-slim"; Name = "python311" },
            @{ Image = "node:20-alpine"; Name = "node20" },
            @{ Image = "nginx:alpine"; Name = "nginx" }
        )
        foreach ($img in $images) {
            Write-Host "  Pulling $($img.Image)..."
            docker pull $img.Image
            Write-Host "  Saving $($img.Name).tar..."
            docker save $img.Image -o (Join-Path $dockerDir "$($img.Name).tar")
        }
        Write-Host "  Done: Docker images" -ForegroundColor Green
    } else {
        Write-Host "  WARNING: Docker not found. Images will not be included." -ForegroundColor DarkYellow
    }
} else {
    Write-Host ""
    Write-Host "[3/4] Skipping Docker images (-NoDocker)" -ForegroundColor DarkYellow
}

# --- 4. Source code archive ---
Write-Host ""
Write-Host "[4/4] Creating source code archive..." -ForegroundColor Yellow
Push-Location $ProjectDir
tar --exclude='_offline_build' --exclude='offline_packages' `
    --exclude='node_modules' --exclude='__pycache__' `
    --exclude='.git' --exclude='dist' --exclude='.next' `
    --exclude='*.pyc' --exclude='.venv' --exclude='venv' `
    --exclude='enterprise-llm-offline-*.zip' `
    -czf (Join-Path $BuildDir "common\source.tar.gz") .
Pop-Location
Write-Host "  Done: source archive"

# ============================================================
# PHASE 2: Linux package
# ============================================================
if ($BuildLinux) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Yellow
    Write-Host " PHASE 2: Building Linux Package" -ForegroundColor Yellow
    Write-Host ("=" * 60) -ForegroundColor Yellow

    $lpkg = Join-Path $BuildDir "enterprise-llm-offline-linux"
    foreach ($sub in @("installers", "python-packages", "npm-packages", "docker-images", "models", "scripts")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $lpkg $sub) | Out-Null
    }

    # Miniconda
    Download-File `
        -Url "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh" `
        -OutFile (Join-Path $lpkg "installers\Miniconda3-latest-Linux-x86_64.sh") `
        -Label "Miniconda (Python for Linux)"

    # Node.js Linux
    Download-File `
        -Url "https://nodejs.org/dist/$NodeVersion/node-$NodeVersion-linux-x64.tar.xz" `
        -OutFile (Join-Path $lpkg "installers\node-$NodeVersion-linux-x64.tar.xz") `
        -Label "Node.js for Linux"

    # Docker binary
    Download-File `
        -Url "https://download.docker.com/linux/static/stable/x86_64/docker-$DockerVersion.tgz" `
        -OutFile (Join-Path $lpkg "installers\docker-$DockerVersion.tgz") `
        -Label "Docker binary for Linux"

    # Docker Compose
    Download-File `
        -Url "https://github.com/docker/compose/releases/download/$ComposeVersion/docker-compose-linux-x86_64" `
        -OutFile (Join-Path $lpkg "installers\docker-compose") `
        -Label "Docker Compose for Linux"

    # Python wheels (Linux)
    Write-Host ""
    Write-Host "  Downloading Python packages for Linux..." -ForegroundColor Yellow
    $pyDirLinux = Join-Path $lpkg "python-packages"
    try {
        & pip download -r (Join-Path $ProjectDir "requirements.txt") `
            -d $pyDirLinux `
            --platform manylinux2014_x86_64 `
            --python-version 311 `
            --only-binary=":all:"
    } catch {
        Write-Host "  Retrying with source builds allowed..." -ForegroundColor DarkYellow
        & pip download -r (Join-Path $ProjectDir "requirements.txt") -d $pyDirLinux
    }
    Write-Host "  Done: Python packages for Linux"

    # Copy common files
    Write-Host "  Copying shared files..."
    Copy-Item -Recurse -Force (Join-Path $BuildDir "common\models\*") (Join-Path $lpkg "models\")
    Copy-Item -Force (Join-Path $BuildDir "common\npm\*") (Join-Path $lpkg "npm-packages\")
    if (Test-Path (Join-Path $BuildDir "common\docker-images")) {
        Copy-Item -Force (Join-Path $BuildDir "common\docker-images\*.tar") (Join-Path $lpkg "docker-images\") -ErrorAction SilentlyContinue
    }
    Copy-Item -Force (Join-Path $BuildDir "common\source.tar.gz") $lpkg

    # Install scripts
    Copy-Item -Force (Join-Path $ProjectDir "scripts\install_offline_linux.sh") (Join-Path $lpkg "install.sh")
    Copy-Item -Force (Join-Path $ProjectDir "scripts\verify_installation.py") (Join-Path $lpkg "scripts\")
    Copy-Item -Force (Join-Path $ProjectDir "requirements.txt") (Join-Path $lpkg "scripts\")

    # README
    @"
================================================================
  Enterprise LLM — Offline Linux Installation Package
================================================================

QUICK START:
  1. Copy this entire directory to the target server
  2. Run:  sudo bash install.sh
  3. Edit: /opt/enterprise-llm/app/.env
  4. Start: docker compose -f docker-compose.airgap.yml up -d

CONTENTS:
  installers/         Python (Miniconda), Node.js, Docker
  python-packages/    Python .whl files
  npm-packages/       Node.js dependencies
  docker-images/      Pre-saved Docker container images
  models/embedding/   BAAI/bge-m3 embedding model
  source.tar.gz       Application source code
  install.sh          Automated installer

For details: docs/OFFLINE_INSTALL_GUIDE.md (in source archive)
================================================================
"@ | Set-Content (Join-Path $lpkg "README.txt")

    # Create zip
    Write-Host ""
    Write-Host "  Creating enterprise-llm-offline-linux.zip..." -ForegroundColor Yellow
    $linuxZip = Join-Path $ProjectDir "enterprise-llm-offline-linux.zip"
    if (Test-Path $linuxZip) { Remove-Item $linuxZip }
    Compress-Archive -Path $lpkg -DestinationPath $linuxZip
    $linuxSize = [math]::Round((Get-Item $linuxZip).Length / 1GB, 2)
    Write-Host "  Done: enterprise-llm-offline-linux.zip ($linuxSize GB)" -ForegroundColor Green
}

# ============================================================
# PHASE 3: Windows package
# ============================================================
if ($BuildWindows) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor Yellow
    Write-Host " PHASE 3: Building Windows Package" -ForegroundColor Yellow
    Write-Host ("=" * 60) -ForegroundColor Yellow

    $wpkg = Join-Path $BuildDir "enterprise-llm-offline-windows"
    foreach ($sub in @("installers", "python-packages", "npm-packages", "docker-images", "models", "scripts")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $wpkg $sub) | Out-Null
    }

    # Python installer
    Download-File `
        -Url "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe" `
        -OutFile (Join-Path $wpkg "installers\python-$PythonVersion-amd64.exe") `
        -Label "Python $PythonVersion for Windows"

    # Node.js MSI
    Download-File `
        -Url "https://nodejs.org/dist/$NodeVersion/node-$NodeVersion-x64.msi" `
        -OutFile (Join-Path $wpkg "installers\node-$NodeVersion-x64.msi") `
        -Label "Node.js for Windows"

    # Git for Windows
    Download-File `
        -Url "https://github.com/git-for-windows/git/releases/download/v$GitVersion.windows.1/Git-$GitVersion-64-bit.exe" `
        -OutFile (Join-Path $wpkg "installers\Git-$GitVersion-64-bit.exe") `
        -Label "Git for Windows"

    # Python wheels (Windows)
    Write-Host ""
    Write-Host "  Downloading Python packages for Windows..." -ForegroundColor Yellow
    $pyDirWin = Join-Path $wpkg "python-packages"
    try {
        & pip download -r (Join-Path $ProjectDir "requirements.txt") `
            -d $pyDirWin `
            --platform win_amd64 `
            --python-version 311 `
            --only-binary=":all:"
    } catch {
        Write-Host "  Retrying with source builds allowed..." -ForegroundColor DarkYellow
        & pip download -r (Join-Path $ProjectDir "requirements.txt") -d $pyDirWin
    }
    Write-Host "  Done: Python packages for Windows"

    # Copy common files
    Write-Host "  Copying shared files..."
    Copy-Item -Recurse -Force (Join-Path $BuildDir "common\models\*") (Join-Path $wpkg "models\")
    Copy-Item -Force (Join-Path $BuildDir "common\npm\*") (Join-Path $wpkg "npm-packages\")
    if (Test-Path (Join-Path $BuildDir "common\docker-images")) {
        Copy-Item -Force (Join-Path $BuildDir "common\docker-images\*.tar") (Join-Path $wpkg "docker-images\") -ErrorAction SilentlyContinue
    }
    Copy-Item -Force (Join-Path $BuildDir "common\source.tar.gz") $wpkg

    # Install scripts
    Copy-Item -Force (Join-Path $ProjectDir "scripts\install_offline_windows.ps1") (Join-Path $wpkg "install.ps1")
    Copy-Item -Force (Join-Path $ProjectDir "scripts\verify_installation.py") (Join-Path $wpkg "scripts\")
    Copy-Item -Force (Join-Path $ProjectDir "requirements.txt") (Join-Path $wpkg "scripts\")

    # README
    @"
================================================================
  Enterprise LLM — Offline Windows Installation Package
================================================================

QUICK START:
  1. Copy this entire directory to the target PC
  2. Open PowerShell as Administrator
  3. Run:  powershell -ExecutionPolicy Bypass -File install.ps1
  4. Edit: C:\enterprise-llm\app\.env
  5. Run:  C:\enterprise-llm\activate.bat

CONTENTS:
  installers\          Python, Node.js, Git
  python-packages\     Python .whl files
  npm-packages\        Node.js dependencies
  docker-images\       Pre-saved Docker container images
  models\embedding\    BAAI/bge-m3 embedding model
  source.tar.gz        Application source code
  install.ps1          Automated installer

DOCKER (optional):
  Docker Desktop requires Hyper-V or WSL2.
  Pre-saved images are in docker-images\ folder.

For details: docs\OFFLINE_INSTALL_GUIDE.md (in source archive)
================================================================
"@ | Set-Content (Join-Path $wpkg "README.txt")

    # Create zip
    Write-Host ""
    Write-Host "  Creating enterprise-llm-offline-windows.zip..." -ForegroundColor Yellow
    $winZip = Join-Path $ProjectDir "enterprise-llm-offline-windows.zip"
    if (Test-Path $winZip) { Remove-Item $winZip }
    Compress-Archive -Path $wpkg -DestinationPath $winZip
    $winSize = [math]::Round((Get-Item $winZip).Length / 1GB, 2)
    Write-Host "  Done: enterprise-llm-offline-windows.zip ($winSize GB)" -ForegroundColor Green
}

# ============================================================
# Summary
# ============================================================
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host "  BUILD COMPLETE" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host ""
if ($BuildLinux) {
    Write-Host "  Linux:   enterprise-llm-offline-linux.zip ($linuxSize GB)" -ForegroundColor Cyan
}
if ($BuildWindows) {
    Write-Host "  Windows: enterprise-llm-offline-windows.zip ($winSize GB)" -ForegroundColor Cyan
}
Write-Host ""
Write-Host "  Transfer zip file(s) to the air-gapped network." -ForegroundColor White
Write-Host "  Extract and run the install script inside." -ForegroundColor White
Write-Host ""

# Cleanup
Remove-Item -Recurse -Force $BuildDir
Write-Host "Build directory cleaned up."
