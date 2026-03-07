#!/bin/bash
# ============================================================
# download_dependencies.sh
# Run this on an INTERNET-CONNECTED PC to download everything
# needed for offline/air-gapped deployment.
# Output: ./offline_packages/ directory (~4 GB)
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUT="$PROJECT_DIR/offline_packages"

echo "=== Enterprise LLM Offline Package Builder ==="
echo "Output directory: $OUT"

mkdir -p "$OUT"/{python,node,docker,models}

# ----------------------------------------------------------
# Step 1: Python wheels
# ----------------------------------------------------------
echo ""
echo "[1/6] Downloading Python wheels..."
pip download \
  -r "$PROJECT_DIR/requirements.txt" \
  -d "$OUT/python/" \
  --platform manylinux2014_x86_64 \
  --python-version 311 \
  --only-binary=:all: || {
    echo "WARNING: Some packages may need source build. Trying without --only-binary..."
    pip download -r "$PROJECT_DIR/requirements.txt" -d "$OUT/python/"
  }
echo "Python wheels: $(du -sh "$OUT/python/" | cut -f1)"

# ----------------------------------------------------------
# Step 2: Embedding model
# ----------------------------------------------------------
echo ""
echo "[2/6] Downloading embedding model (bge-large-en-v1.5)..."
if command -v huggingface-cli &>/dev/null; then
  huggingface-cli download BAAI/bge-large-en-v1.5 \
    --local-dir "$OUT/models/embedding"
else
  echo "huggingface-cli not found. Install: pip install huggingface_hub"
  echo "Then run: huggingface-cli download BAAI/bge-large-en-v1.5 --local-dir $OUT/models/embedding"
fi

# ----------------------------------------------------------
# Step 3: Node.js 20.x LTS installers
# ----------------------------------------------------------
echo ""
echo "[3/6] Downloading Node.js 20.x LTS installers..."
NODE_VERSION="v20.18.1"
wget -q --show-progress -P "$OUT/node/" \
  "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-x64.tar.xz" || true
wget -q --show-progress -P "$OUT/node/" \
  "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-x64.msi" || true

# ----------------------------------------------------------
# Step 4: npm packages (widget + platform)
# ----------------------------------------------------------
echo ""
echo "[4/6] Downloading npm packages..."

# Widget
cd "$PROJECT_DIR/widget"
npm install --prefer-offline 2>/dev/null || npm install
tar -czf "$OUT/node/widget_node_modules.tar.gz" node_modules/ package-lock.json
echo "Widget packages: $(du -sh "$OUT/node/widget_node_modules.tar.gz" | cut -f1)"

# Platform
cd "$PROJECT_DIR/platform"
npm install --prefer-offline 2>/dev/null || npm install
tar -czf "$OUT/node/platform_node_modules.tar.gz" node_modules/ package-lock.json
echo "Platform packages: $(du -sh "$OUT/node/platform_node_modules.tar.gz" | cut -f1)"

cd "$PROJECT_DIR"

# ----------------------------------------------------------
# Step 5: Docker offline packages
# ----------------------------------------------------------
echo ""
echo "[5/6] Downloading Docker packages..."

# Docker static binary (Linux)
DOCKER_VERSION="27.4.1"
wget -q --show-progress -P "$OUT/docker/" \
  "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz" || true

# Docker images
if command -v docker &>/dev/null; then
  echo "Pulling and saving Docker images..."
  docker pull chromadb/chroma:latest
  docker pull n8nio/n8n:latest
  docker save chromadb/chroma:latest -o "$OUT/docker/chromadb.tar"
  docker save n8nio/n8n:latest -o "$OUT/docker/n8n.tar"
else
  echo "Docker not found. Skip image download."
fi

# ----------------------------------------------------------
# Step 6: Summary
# ----------------------------------------------------------
echo ""
echo "=== Download Complete ==="
echo "Total size: $(du -sh "$OUT" | cut -f1)"
echo ""
echo "Transfer the entire offline_packages/ directory to the air-gapped network."
echo "Then run: scripts/install_offline_linux.sh"
