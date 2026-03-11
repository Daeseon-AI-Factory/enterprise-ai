#!/bin/bash
# ============================================================
# prepare_offline_package.sh
#
# 인터넷 연결된 PC에서 실행 — 폐쇄망 배포용 zip 패키지 2개 생성
#
# Output:
#   enterprise-llm-offline-linux.zip    (~5 GB)
#   enterprise-llm-offline-windows.zip  (~4 GB)
#
# Prerequisites (on the internet-connected machine):
#   - Python 3.11+, pip
#   - Node.js 20+, npm
#   - Docker (for saving container images)
#   - pip install huggingface_hub  (for embedding model)
#   - wget, zip
#
# Usage:
#   bash scripts/prepare_offline_package.sh
#   bash scripts/prepare_offline_package.sh --no-docker
#   bash scripts/prepare_offline_package.sh --linux-only
#   bash scripts/prepare_offline_package.sh --windows-only
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/_offline_build"

# Versions
PYTHON_VERSION="3.11.9"
NODE_VERSION="v20.18.1"
DOCKER_VERSION="27.4.1"
COMPOSE_VERSION="v2.32.4"

# Flags
BUILD_LINUX=true
BUILD_WINDOWS=true
INCLUDE_DOCKER=true

for arg in "$@"; do
  case $arg in
    --no-docker) INCLUDE_DOCKER=false ;;
    --linux-only) BUILD_WINDOWS=false ;;
    --windows-only) BUILD_LINUX=false ;;
    *) echo "Unknown option: $arg"; exit 1 ;;
  esac
done

echo "================================================================"
echo "  Enterprise LLM — Offline Package Builder"
echo "================================================================"
echo ""
echo "  Linux package:   $BUILD_LINUX"
echo "  Windows package: $BUILD_WINDOWS"
echo "  Docker images:   $INCLUDE_DOCKER"
echo ""

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/common"

# ============================================================
# PHASE 1: Common downloads (shared between Linux & Windows)
# ============================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " PHASE 1: Downloading common files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- 1. Embedding Model (~1.3 GB) ---
echo ""
echo "[1/4] Downloading embedding model (BAAI/bge-m3)..."
mkdir -p "$BUILD_DIR/common/models/embedding"
if command -v huggingface-cli &>/dev/null; then
  huggingface-cli download BAAI/bge-m3 \
    --local-dir "$BUILD_DIR/common/models/embedding"
  echo "  Done: embedding model"
else
  echo "  ERROR: huggingface-cli not found."
  echo "  Run: pip install huggingface_hub"
  echo "  Then re-run this script."
  exit 1
fi

# --- 2. npm packages ---
echo ""
echo "[2/4] Downloading npm packages..."
mkdir -p "$BUILD_DIR/common/npm"

cd "$PROJECT_DIR/widget"
npm install --prefer-offline 2>/dev/null || npm install
tar -czf "$BUILD_DIR/common/npm/widget_node_modules.tar.gz" node_modules/ package-lock.json
echo "  Done: widget node_modules"

cd "$PROJECT_DIR/platform"
npm install --prefer-offline 2>/dev/null || npm install
tar -czf "$BUILD_DIR/common/npm/platform_node_modules.tar.gz" node_modules/ package-lock.json
echo "  Done: platform node_modules"

cd "$PROJECT_DIR"

# --- 3. Docker images ---
if [ "$INCLUDE_DOCKER" = true ]; then
  echo ""
  echo "[3/4] Saving Docker images..."
  mkdir -p "$BUILD_DIR/common/docker-images"

  if command -v docker &>/dev/null; then
    IMAGES=("chromadb/chroma:latest" "n8nio/n8n:latest" "python:3.11-slim" "node:20-alpine" "nginx:alpine")
    NAMES=("chromadb" "n8n" "python311" "node20" "nginx")
    for i in "${!IMAGES[@]}"; do
      echo "  Pulling ${IMAGES[$i]}..."
      docker pull "${IMAGES[$i]}"
      echo "  Saving ${NAMES[$i]}.tar..."
      docker save "${IMAGES[$i]}" -o "$BUILD_DIR/common/docker-images/${NAMES[$i]}.tar"
    done
    echo "  Done: Docker images"
  else
    echo "  WARNING: Docker not found. Docker images will not be included."
    echo "  Install Docker to include pre-built container images."
  fi
else
  echo ""
  echo "[3/4] Skipping Docker images (--no-docker)"
fi

# --- 4. Source code archive ---
echo ""
echo "[4/4] Creating source code archive..."
cd "$PROJECT_DIR"
tar --exclude='_offline_build' --exclude='offline_packages' \
    --exclude='node_modules' --exclude='__pycache__' \
    --exclude='.git' --exclude='dist' --exclude='.next' \
    --exclude='*.pyc' --exclude='.venv' --exclude='venv' \
    --exclude='enterprise-llm-offline-*.zip' \
    -czf "$BUILD_DIR/common/source.tar.gz" .
echo "  Done: source archive"

# ============================================================
# PHASE 2: Linux package
# ============================================================
if [ "$BUILD_LINUX" = true ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo " PHASE 2: Building Linux package"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  LPKG="$BUILD_DIR/enterprise-llm-offline-linux"
  mkdir -p "$LPKG"/{installers,python-packages,npm-packages,docker-images,models,scripts}

  # Miniconda (Python for Linux)
  echo ""
  echo "[L1/6] Downloading Miniconda (Python for Linux)..."
  wget -q --show-progress -O "$LPKG/installers/Miniconda3-latest-Linux-x86_64.sh" \
    "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"

  # Node.js
  echo "[L2/6] Downloading Node.js for Linux..."
  wget -q --show-progress -O "$LPKG/installers/node-${NODE_VERSION}-linux-x64.tar.xz" \
    "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-x64.tar.xz"

  # Docker binary + Compose
  echo "[L3/6] Downloading Docker binary for Linux..."
  wget -q --show-progress -O "$LPKG/installers/docker-${DOCKER_VERSION}.tgz" \
    "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz"
  wget -q --show-progress -O "$LPKG/installers/docker-compose" \
    "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-x86_64"
  chmod +x "$LPKG/installers/docker-compose"

  # Python wheels for Linux
  echo "[L4/6] Downloading Python packages for Linux..."
  pip download \
    -r "$PROJECT_DIR/requirements.txt" \
    -d "$LPKG/python-packages/" \
    --platform manylinux2014_x86_64 \
    --python-version 311 \
    --only-binary=:all: 2>/dev/null || {
      echo "  Retrying with source builds allowed..."
      pip download -r "$PROJECT_DIR/requirements.txt" -d "$LPKG/python-packages/"
    }

  # Copy common files
  echo "[L5/6] Copying shared files..."
  cp -r "$BUILD_DIR/common/models/"* "$LPKG/models/"
  cp "$BUILD_DIR/common/npm/"* "$LPKG/npm-packages/"
  if [ -d "$BUILD_DIR/common/docker-images" ]; then
    cp "$BUILD_DIR/common/docker-images/"*.tar "$LPKG/docker-images/" 2>/dev/null || true
  fi
  cp "$BUILD_DIR/common/source.tar.gz" "$LPKG/"

  # Copy install scripts
  cp "$PROJECT_DIR/scripts/install_offline_linux.sh" "$LPKG/install.sh"
  chmod +x "$LPKG/install.sh"
  cp "$PROJECT_DIR/scripts/verify_installation.py" "$LPKG/scripts/"
  cp "$PROJECT_DIR/requirements.txt" "$LPKG/scripts/"

  # README
  cat > "$LPKG/README.txt" << 'README_EOF'
================================================================
  Enterprise LLM — Offline Linux Installation Package
================================================================

This package contains everything needed to install the
Enterprise LLM Platform on an air-gapped Linux server.

QUICK START:
  1. Copy this entire directory to the target server
  2. Run:  sudo bash install.sh
  3. Edit: /opt/enterprise-llm/app/.env
  4. Start: docker compose -f docker-compose.airgap.yml up -d

CONTENTS:
  installers/         Python (Miniconda), Node.js, Docker
  python-packages/    Python .whl files (offline pip install)
  npm-packages/       Node.js dependencies (widget + platform)
  docker-images/      Pre-saved Docker container images
  models/embedding/   BAAI/bge-m3 embedding model
  source.tar.gz       Application source code
  install.sh          Automated installer
  scripts/            Verification & helper scripts

REQUIREMENTS:
  - Linux x86_64 (RHEL/CentOS/Ubuntu/Debian)
  - 8 GB RAM minimum
  - 20 GB disk space
  - GPU server with GPT-OSS model serving (vLLM/TGI)

For detailed instructions, see docs/OFFLINE_INSTALL_GUIDE.md
in the extracted source code.
================================================================
README_EOF

  # Create zip
  echo "[L6/6] Creating enterprise-llm-offline-linux.zip..."
  cd "$BUILD_DIR"
  zip -r "$PROJECT_DIR/enterprise-llm-offline-linux.zip" enterprise-llm-offline-linux/
  LINUX_SIZE=$(du -sh "$PROJECT_DIR/enterprise-llm-offline-linux.zip" | cut -f1)
  echo "  Done: enterprise-llm-offline-linux.zip ($LINUX_SIZE)"
fi

# ============================================================
# PHASE 3: Windows package
# ============================================================
if [ "$BUILD_WINDOWS" = true ]; then
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo " PHASE 3: Building Windows package"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  WPKG="$BUILD_DIR/enterprise-llm-offline-windows"
  mkdir -p "$WPKG"/{installers,python-packages,npm-packages,docker-images,models,scripts}

  # Python installer for Windows
  echo ""
  echo "[W1/6] Downloading Python ${PYTHON_VERSION} for Windows..."
  wget -q --show-progress -O "$WPKG/installers/python-${PYTHON_VERSION}-amd64.exe" \
    "https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-amd64.exe"

  # Node.js MSI
  echo "[W2/6] Downloading Node.js for Windows..."
  wget -q --show-progress -O "$WPKG/installers/node-${NODE_VERSION}-x64.msi" \
    "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-x64.msi"

  # Git for Windows
  echo "[W3/6] Downloading Git for Windows..."
  GIT_VERSION="2.47.1"
  wget -q --show-progress -O "$WPKG/installers/Git-${GIT_VERSION}-64-bit.exe" \
    "https://github.com/git-for-windows/git/releases/download/v${GIT_VERSION}.windows.1/Git-${GIT_VERSION}-64-bit.exe" 2>/dev/null || {
      echo "  WARNING: Could not download Git for Windows. Skipping."
    }

  # Python wheels for Windows
  echo "[W4/6] Downloading Python packages for Windows..."
  pip download \
    -r "$PROJECT_DIR/requirements.txt" \
    -d "$WPKG/python-packages/" \
    --platform win_amd64 \
    --python-version 311 \
    --only-binary=:all: 2>/dev/null || {
      echo "  Retrying with source builds allowed..."
      pip download -r "$PROJECT_DIR/requirements.txt" -d "$WPKG/python-packages/"
    }

  # Copy common files
  echo "[W5/6] Copying shared files..."
  cp -r "$BUILD_DIR/common/models/"* "$WPKG/models/"
  cp "$BUILD_DIR/common/npm/"* "$WPKG/npm-packages/"
  if [ -d "$BUILD_DIR/common/docker-images" ]; then
    cp "$BUILD_DIR/common/docker-images/"*.tar "$WPKG/docker-images/" 2>/dev/null || true
  fi
  cp "$BUILD_DIR/common/source.tar.gz" "$WPKG/"

  # Copy install scripts
  cp "$PROJECT_DIR/scripts/install_offline_windows.ps1" "$WPKG/install.ps1"
  cp "$PROJECT_DIR/scripts/verify_installation.py" "$WPKG/scripts/"
  cp "$PROJECT_DIR/requirements.txt" "$WPKG/scripts/"

  # README
  cat > "$WPKG/README.txt" << 'README_EOF'
================================================================
  Enterprise LLM — Offline Windows Installation Package
================================================================

This package contains everything needed to install the
Enterprise LLM Platform on an air-gapped Windows PC.

QUICK START:
  1. Copy this entire directory to the target PC
  2. Open PowerShell as Administrator
  3. Run:  powershell -ExecutionPolicy Bypass -File install.ps1
  4. Edit: C:\enterprise-llm\app\.env
  5. Start the backend (see instructions after install)

CONTENTS:
  installers\          Python, Node.js, Git
  python-packages\     Python .whl files (offline pip install)
  npm-packages\        Node.js dependencies (widget + platform)
  docker-images\       Pre-saved Docker container images
  models\embedding\    BAAI/bge-m3 embedding model
  source.tar.gz        Application source code
  install.ps1          Automated installer
  scripts\             Verification & helper scripts

REQUIREMENTS:
  - Windows 10/11 x64
  - 8 GB RAM minimum
  - 20 GB disk space
  - Access to a GPU server running GPT-OSS (vLLM/TGI)

DOCKER (optional):
  Docker Desktop can be installed for container-based deployment.
  Requires Hyper-V or WSL2 enabled in Windows Features.
  Docker images are pre-saved in docker-images\ folder.

For detailed instructions, see docs\OFFLINE_INSTALL_GUIDE.md
in the extracted source code.
================================================================
README_EOF

  # Create zip
  echo "[W6/6] Creating enterprise-llm-offline-windows.zip..."
  cd "$BUILD_DIR"
  zip -r "$PROJECT_DIR/enterprise-llm-offline-windows.zip" enterprise-llm-offline-windows/
  WIN_SIZE=$(du -sh "$PROJECT_DIR/enterprise-llm-offline-windows.zip" | cut -f1)
  echo "  Done: enterprise-llm-offline-windows.zip ($WIN_SIZE)"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "================================================================"
echo "  BUILD COMPLETE"
echo "================================================================"
echo ""
if [ "$BUILD_LINUX" = true ]; then
  echo "  Linux:   enterprise-llm-offline-linux.zip ($LINUX_SIZE)"
fi
if [ "$BUILD_WINDOWS" = true ]; then
  echo "  Windows: enterprise-llm-offline-windows.zip ($WIN_SIZE)"
fi
echo ""
echo "  Transfer the zip file(s) to the air-gapped network."
echo "  Extract and run the install script inside."
echo ""

# Cleanup
rm -rf "$BUILD_DIR"
echo "Build directory cleaned up."
