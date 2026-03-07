#!/bin/bash
# ============================================================
# install_offline_linux.sh
# Run this on the AIR-GAPPED server to install everything.
# Requires: offline_packages/ directory from download step.
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PKG="$PROJECT_DIR/offline_packages"
INSTALL_DIR="/opt/enterprise-llm"

echo "=== Enterprise LLM Offline Installer ==="

# Validate offline_packages exists
if [ ! -d "$PKG" ]; then
  echo "ERROR: offline_packages/ directory not found at $PKG"
  echo "Run download_dependencies.sh on an internet-connected PC first."
  exit 1
fi

# ----------------------------------------------------------
# Step 1: Node.js (if not installed)
# ----------------------------------------------------------
if ! command -v node &>/dev/null; then
  echo "[1/8] Installing Node.js..."
  if [ -f "$PKG/node/node-"*"-linux-x64.tar.xz" ]; then
    tar -xf "$PKG"/node/node-*-linux-x64.tar.xz -C /usr/local --strip-components=1
    echo "Node.js $(node --version) installed"
  else
    echo "WARNING: Node.js installer not found in offline_packages/node/"
  fi
else
  echo "[1/8] Node.js already installed: $(node --version)"
fi

# ----------------------------------------------------------
# Step 2: Docker (if not installed)
# ----------------------------------------------------------
if ! command -v docker &>/dev/null; then
  echo "[2/8] Installing Docker..."
  if [ -f "$PKG/docker/docker-"*".tgz" ]; then
    tar -xzf "$PKG"/docker/docker-*.tgz
    cp docker/* /usr/bin/
    rm -rf docker/
    echo "Docker installed"
  else
    echo "WARNING: Docker installer not found in offline_packages/docker/"
  fi
else
  echo "[2/8] Docker already installed: $(docker --version)"
fi

# ----------------------------------------------------------
# Step 3: Python venv (isolate from model serving env)
# ----------------------------------------------------------
echo "[3/8] Creating Python virtual environment..."
mkdir -p "$INSTALL_DIR"
python3 -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# ----------------------------------------------------------
# Step 4: Python packages
# ----------------------------------------------------------
echo "[4/8] Installing Python packages (offline)..."
pip install --no-index --find-links="$PKG/python/" -r "$PROJECT_DIR/requirements.txt"

# ----------------------------------------------------------
# Step 5: Embedding model
# ----------------------------------------------------------
echo "[5/8] Copying embedding model..."
if [ -d "$PKG/models/embedding" ]; then
  mkdir -p "$PROJECT_DIR/models"
  cp -r "$PKG/models/embedding" "$PROJECT_DIR/models/"
  echo "Embedding model copied to $PROJECT_DIR/models/embedding"
else
  echo "WARNING: Embedding model not found in offline_packages/models/"
fi

# ----------------------------------------------------------
# Step 6: Frontend builds
# ----------------------------------------------------------
echo "[6/8] Building frontends..."

# Widget
cd "$PROJECT_DIR/widget"
if [ -f "$PKG/node/widget_node_modules.tar.gz" ]; then
  tar -xzf "$PKG/node/widget_node_modules.tar.gz"
  npm run build
  echo "Widget built successfully"
fi

# Platform
cd "$PROJECT_DIR/platform"
if [ -f "$PKG/node/platform_node_modules.tar.gz" ]; then
  tar -xzf "$PKG/node/platform_node_modules.tar.gz"
  npm run build
  echo "Platform built successfully"
fi

cd "$PROJECT_DIR"

# ----------------------------------------------------------
# Step 7: Docker images
# ----------------------------------------------------------
echo "[7/8] Loading Docker images..."
if command -v docker &>/dev/null; then
  [ -f "$PKG/docker/chromadb.tar" ] && docker load -i "$PKG/docker/chromadb.tar"
  [ -f "$PKG/docker/n8n.tar" ] && docker load -i "$PKG/docker/n8n.tar"
else
  echo "Docker not available. Skipping image load."
fi

# ----------------------------------------------------------
# Step 8: Environment setup
# ----------------------------------------------------------
echo "[8/8] Setting up environment..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
  cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
  echo "Created .env from .env.example — EDIT THIS FILE:"
  echo "  - Set MODE=airgap"
  echo "  - Set LLM_API_BASE to your GPT-OSS endpoint"
fi

# Set offline flags
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env (set MODE=airgap, LLM_API_BASE, etc.)"
echo "  2. Start services: docker compose -f docker-compose.airgap.yml up -d"
echo "  3. Activate venv: source $INSTALL_DIR/venv/bin/activate"
echo "  4. Start backend: uvicorn app.main:app --host 0.0.0.0 --port 8080"
echo "  5. Verify: python scripts/verify_installation.py"
