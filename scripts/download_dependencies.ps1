# ============================================================
# download_dependencies.ps1
# Run this on a WINDOWS 10 PC with internet to download
# everything needed for air-gapped Linux deployment.
# Output: .\offline_packages\ directory (~4 GB)
#
# Usage: Right-click → Run with PowerShell
#   or:  powershell -ExecutionPolicy Bypass -File scripts\download_dependencies.ps1
# ============================================================
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$Out = Join-Path $ProjectDir "offline_packages"

Write-Host "=== Enterprise LLM Offline Package Builder (Windows) ===" -ForegroundColor Cyan
Write-Host "Output directory: $Out"

# Create directories
foreach ($sub in @("python", "node", "docker", "models")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Out $sub) | Out-Null
}

# ----------------------------------------------------------
# Step 1: Python wheels (for Linux target)
# ----------------------------------------------------------
Write-Host ""
Write-Host "[1/7] Downloading Python wheels (Linux target)..." -ForegroundColor Yellow

$reqFile = Join-Path $ProjectDir "requirements.txt"
$pyDir = Join-Path $Out "python"

# Try binary-only first (faster), fall back to source
try {
    & pip download -r $reqFile -d $pyDir `
        --platform manylinux2014_x86_64 `
        --python-version 311 `
        --only-binary=:all:
} catch {
    Write-Host "WARNING: Some packages need source build. Retrying without --only-binary..." -ForegroundColor DarkYellow
    & pip download -r $reqFile -d $pyDir
}

$pySize = (Get-ChildItem $pyDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "Python wheels: $([math]::Round($pySize)) MB"

# ----------------------------------------------------------
# Step 2: Embedding model
# ----------------------------------------------------------
Write-Host ""
Write-Host "[2/7] Downloading embedding model (bge-large-en-v1.5)..." -ForegroundColor Yellow

$modelDir = Join-Path $Out "models\embedding"

if (Get-Command huggingface-cli -ErrorAction SilentlyContinue) {
    & huggingface-cli download BAAI/bge-large-en-v1.5 --local-dir $modelDir
} else {
    Write-Host "huggingface-cli not found." -ForegroundColor DarkYellow
    Write-Host "Install: pip install huggingface_hub"
    Write-Host "Then run: huggingface-cli download BAAI/bge-large-en-v1.5 --local-dir $modelDir"
}

# ----------------------------------------------------------
# Step 3: Node.js installers (both Linux + Windows)
# ----------------------------------------------------------
Write-Host ""
Write-Host "[3/7] Downloading Node.js 20.x LTS..." -ForegroundColor Yellow

$nodeVersion = "v20.18.1"
$nodeDir = Join-Path $Out "node"

# Linux tar (for target server)
$linuxUrl = "https://nodejs.org/dist/$nodeVersion/node-$nodeVersion-linux-x64.tar.xz"
$linuxFile = Join-Path $nodeDir "node-$nodeVersion-linux-x64.tar.xz"
if (-not (Test-Path $linuxFile)) {
    Write-Host "  Downloading Linux Node.js..."
    Invoke-WebRequest -Uri $linuxUrl -OutFile $linuxFile -UseBasicParsing
}

# Windows MSI (for this PC if needed)
$winUrl = "https://nodejs.org/dist/$nodeVersion/node-$nodeVersion-x64.msi"
$winFile = Join-Path $nodeDir "node-$nodeVersion-x64.msi"
if (-not (Test-Path $winFile)) {
    Write-Host "  Downloading Windows Node.js..."
    Invoke-WebRequest -Uri $winUrl -OutFile $winFile -UseBasicParsing
}

# ----------------------------------------------------------
# Step 4: npm packages (widget + platform)
# ----------------------------------------------------------
Write-Host ""
Write-Host "[4/7] Downloading npm packages..." -ForegroundColor Yellow

# Widget
$widgetDir = Join-Path $ProjectDir "widget"
Push-Location $widgetDir
npm install 2>$null
$widgetTar = Join-Path $nodeDir "widget_node_modules.tar.gz"
tar -czf $widgetTar node_modules package-lock.json
Pop-Location
Write-Host "  Widget packages archived"

# Platform
$platformDir = Join-Path $ProjectDir "platform"
Push-Location $platformDir
npm install 2>$null
$platformTar = Join-Path $nodeDir "platform_node_modules.tar.gz"
tar -czf $platformTar node_modules package-lock.json
Pop-Location
Write-Host "  Platform packages archived"

# ----------------------------------------------------------
# Step 5: Docker images (if Docker Desktop is installed)
# ----------------------------------------------------------
Write-Host ""
Write-Host "[5/7] Downloading Docker images..." -ForegroundColor Yellow

$dockerDir = Join-Path $Out "docker"

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "  Pulling images..."
    docker pull chromadb/chroma:latest
    docker pull n8nio/n8n:latest
    docker pull python:3.11-slim
    docker pull node:20-alpine
    docker pull nginx:alpine

    Write-Host "  Saving images (this takes a while)..."
    docker save chromadb/chroma:latest -o (Join-Path $dockerDir "chromadb.tar")
    docker save n8nio/n8n:latest -o (Join-Path $dockerDir "n8n.tar")
    docker save python:3.11-slim -o (Join-Path $dockerDir "python311.tar")
    docker save node:20-alpine -o (Join-Path $dockerDir "node20.tar")
    docker save nginx:alpine -o (Join-Path $dockerDir "nginx.tar")
    Write-Host "  Docker images saved"

    # Also download Docker static binary for Linux (in case target has no Docker)
    $dockerVer = "27.4.1"
    $dockerBin = Join-Path $dockerDir "docker-$dockerVer.tgz"
    if (-not (Test-Path $dockerBin)) {
        Write-Host "  Downloading Docker binary for Linux..."
        Invoke-WebRequest -Uri "https://download.docker.com/linux/static/stable/x86_64/docker-$dockerVer.tgz" `
            -OutFile $dockerBin -UseBasicParsing
    }
} else {
    Write-Host "  Docker not found. Install Docker Desktop to save images." -ForegroundColor DarkYellow
    Write-Host "  Or download images on another machine with Docker."
}

# ----------------------------------------------------------
# Step 6: Source code archive
# ----------------------------------------------------------
Write-Host ""
Write-Host "[6/7] Creating source code archive..." -ForegroundColor Yellow

Push-Location $ProjectDir
$sourceFile = Join-Path $Out "source.tar.gz"
tar --exclude='offline_packages' --exclude='node_modules' --exclude='__pycache__' `
    --exclude='.git' --exclude='dist' --exclude='.next' `
    -czf $sourceFile .
Pop-Location
Write-Host "  Source archive created"

# ----------------------------------------------------------
# Step 7: Summary
# ----------------------------------------------------------
Write-Host ""
Write-Host "=== Download Complete ===" -ForegroundColor Green
Write-Host ""

$totalSize = (Get-ChildItem $Out -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
Write-Host "Total size: $([math]::Round($totalSize, 2)) GB"
Write-Host ""
Write-Host "Directory contents:" -ForegroundColor Cyan
Get-ChildItem $Out -Recurse | Group-Object DirectoryName |
    ForEach-Object {
        $size = ($_.Group | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host "  $($_.Name): $([math]::Round($size)) MB"
    }

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Copy the entire 'offline_packages' folder to a USB drive"
Write-Host "2. Transfer to the air-gapped Linux server"
Write-Host "3. Run: sudo bash scripts/install_offline_linux.sh"
Write-Host ""
Write-Host "Transfer checklist:" -ForegroundColor Yellow
Write-Host "  [  ] offline_packages/python/       (Python wheels)"
Write-Host "  [  ] offline_packages/models/        (Embedding model)"
Write-Host "  [  ] offline_packages/node/           (Node.js + npm packages)"
Write-Host "  [  ] offline_packages/docker/         (Docker images)"
Write-Host "  [  ] offline_packages/source.tar.gz   (Source code)"
