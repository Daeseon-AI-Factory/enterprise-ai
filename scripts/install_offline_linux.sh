#!/bin/bash
# ============================================================
# Enterprise LLM — Offline Installer (Linux)
#
# 폐쇄망 Linux 서버에서 실행하는 설치 스크립트
# Python, Node.js, Docker 가 없어도 자동 설치됩니다.
#
# Usage:
#   sudo bash install.sh
#   sudo bash install.sh /custom/install/dir
#
# Works from:
#   - Standalone package (enterprise-llm-offline-linux/)
#   - Repository with offline_packages/ directory
# ============================================================
set -euo pipefail

INSTALL_DIR="${1:-/opt/enterprise-llm}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Detect package layout ──────────────────────────────────
if [ -f "$SCRIPT_DIR/source.tar.gz" ]; then
  # Standalone package (from zip)
  PKG="$SCRIPT_DIR"
  INSTALLERS="$PKG/installers"
  PY_PKGS="$PKG/python-packages"
  NPM_PKGS="$PKG/npm-packages"
  DOCKER_IMGS="$PKG/docker-images"
  MODEL_SRC="$PKG/models/embedding"
  SOURCE_TAR="$PKG/source.tar.gz"
  REQ_FILE="$PKG/scripts/requirements.txt"
  MODE="standalone"
elif [ -d "$(dirname "$SCRIPT_DIR")/offline_packages" ]; then
  # Repository mode
  REPO_DIR="$(dirname "$SCRIPT_DIR")"
  PKG="$REPO_DIR/offline_packages"
  INSTALLERS="$PKG"
  PY_PKGS="$PKG/python"
  NPM_PKGS="$PKG/node"
  DOCKER_IMGS="$PKG/docker"
  MODEL_SRC="$PKG/models/embedding"
  SOURCE_TAR="$PKG/source.tar.gz"
  REQ_FILE="$REPO_DIR/requirements.txt"
  MODE="repo"
else
  echo "ERROR: Cannot find offline packages."
  echo ""
  echo "Expected either:"
  echo "  - Standalone package directory with source.tar.gz"
  echo "  - Repository with offline_packages/ subdirectory"
  exit 1
fi

echo "================================================================"
echo "  Enterprise LLM — Offline Installer (Linux)"
echo "================================================================"
echo ""
echo "  Package mode : $MODE"
echo "  Package dir  : $PKG"
echo "  Install dir  : $INSTALL_DIR"
echo ""

mkdir -p "$INSTALL_DIR"

# ── Step 1: Python ─────────────────────────────────────────
echo "[1/9] Setting up Python..."

PYTHON_CMD=""
# Check for existing Python 3.10+
for cmd in python3.11 python3.12 python3.10 python3; do
  if command -v $cmd &>/dev/null; then
    ver=$($cmd --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
      PYTHON_CMD=$cmd
      break
    fi
  fi
done

if [ -z "$PYTHON_CMD" ]; then
  MINICONDA_SH=$(find "$INSTALLERS" -name "Miniconda3-*.sh" 2>/dev/null | head -1)
  if [ -n "$MINICONDA_SH" ]; then
    echo "  Installing Miniconda..."
    bash "$MINICONDA_SH" -b -p "$INSTALL_DIR/miniconda3"
    export PATH="$INSTALL_DIR/miniconda3/bin:$PATH"
    PYTHON_CMD="$INSTALL_DIR/miniconda3/bin/python3"
    echo "  Python $($PYTHON_CMD --version 2>&1) installed via Miniconda"
  else
    echo "  ERROR: Python 3.10+ not found and no Miniconda installer available."
    exit 1
  fi
else
  echo "  Python already installed: $($PYTHON_CMD --version 2>&1)"
fi

# ── Step 2: Node.js ────────────────────────────────────────
echo "[2/9] Setting up Node.js..."

if ! command -v node &>/dev/null; then
  NODE_TAR=$(find "$INSTALLERS" -name "node-*-linux-x64.tar.xz" 2>/dev/null | head -1)
  if [ -n "$NODE_TAR" ]; then
    tar -xf "$NODE_TAR" -C /usr/local --strip-components=1
    echo "  Node.js $(node --version) installed"
  else
    echo "  WARNING: Node.js installer not found. Frontend builds will be skipped."
  fi
else
  echo "  Node.js already installed: $(node --version)"
fi

# ── Step 3: Docker ─────────────────────────────────────────
echo "[3/9] Setting up Docker..."

if ! command -v docker &>/dev/null; then
  DOCKER_TGZ=$(find "$INSTALLERS" -name "docker-*.tgz" 2>/dev/null | head -1)
  if [ -n "$DOCKER_TGZ" ]; then
    tar -xzf "$DOCKER_TGZ" -C /tmp/
    cp /tmp/docker/* /usr/bin/
    rm -rf /tmp/docker
    echo "  Docker binaries installed"
  fi

  # Docker Compose
  if [ -f "$INSTALLERS/docker-compose" ]; then
    cp "$INSTALLERS/docker-compose" /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    # Also symlink for 'docker compose' (V2 plugin)
    mkdir -p /usr/local/lib/docker/cli-plugins/
    ln -sf /usr/local/bin/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
    echo "  Docker Compose installed"
  fi
else
  echo "  Docker already installed: $(docker --version)"
fi

# Start dockerd if not running
if command -v docker &>/dev/null; then
  if ! docker info &>/dev/null 2>&1; then
    echo "  Starting Docker daemon..."
    nohup dockerd &>/dev/null &
    sleep 3
  fi
fi

# ── Step 4: Extract source code ────────────────────────────
echo "[4/9] Setting up source code..."

if [ "$MODE" = "standalone" ] && [ -f "$SOURCE_TAR" ]; then
  PROJECT_DIR="$INSTALL_DIR/app"
  mkdir -p "$PROJECT_DIR"
  tar -xzf "$SOURCE_TAR" -C "$PROJECT_DIR"
  REQ_FILE="$PROJECT_DIR/requirements.txt"
  echo "  Source extracted to $PROJECT_DIR"
else
  PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
  echo "  Using existing source: $PROJECT_DIR"
fi

# ── Step 5: Python venv + packages ─────────────────────────
echo "[5/9] Setting up Python virtual environment..."

VENV_DIR="$INSTALL_DIR/venv"
$PYTHON_CMD -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Upgrade pip first (offline)
PIP_WHL=$(find "$PY_PKGS" -name "pip-*.whl" 2>/dev/null | head -1)
if [ -n "$PIP_WHL" ]; then
  pip install --no-index "$PIP_WHL" 2>/dev/null || true
fi

echo "  Installing Python packages (offline)..."
pip install --no-index --find-links="$PY_PKGS" -r "$REQ_FILE"
echo "  Python packages installed"

# ── Step 6: Embedding model ────────────────────────────────
echo "[6/9] Setting up embedding model..."

if [ -d "$MODEL_SRC" ]; then
  mkdir -p "$PROJECT_DIR/models"
  cp -r "$MODEL_SRC" "$PROJECT_DIR/models/embedding"
  echo "  Embedding model copied to $PROJECT_DIR/models/embedding"
else
  echo "  WARNING: Embedding model not found at $MODEL_SRC"
  echo "  The system will not be able to do vector search without it."
fi

# ── Step 7: Frontend builds ────────────────────────────────
echo "[7/9] Building frontends..."

if command -v node &>/dev/null; then
  # Widget
  WIDGET_TAR=""
  for f in "$NPM_PKGS/widget_node_modules.tar.gz" "$NPM_PKGS"/widget_node_modules.tar.gz; do
    [ -f "$f" ] && WIDGET_TAR="$f" && break
  done
  if [ -n "$WIDGET_TAR" ]; then
    cd "$PROJECT_DIR/widget"
    tar -xzf "$WIDGET_TAR"
    npm run build 2>/dev/null
    echo "  Widget built"
  fi

  # Platform
  PLATFORM_TAR=""
  for f in "$NPM_PKGS/platform_node_modules.tar.gz" "$NPM_PKGS"/platform_node_modules.tar.gz; do
    [ -f "$f" ] && PLATFORM_TAR="$f" && break
  done
  if [ -n "$PLATFORM_TAR" ]; then
    cd "$PROJECT_DIR/platform"
    tar -xzf "$PLATFORM_TAR"
    npm run build 2>/dev/null
    echo "  Platform built"
  fi

  cd "$PROJECT_DIR"
else
  echo "  Node.js not available. Skipping frontend builds."
fi

# ── Step 8: Docker images ──────────────────────────────────
echo "[8/9] Loading Docker images..."

if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
  for img_tar in "$DOCKER_IMGS"/*.tar; do
    if [ -f "$img_tar" ]; then
      name=$(basename "$img_tar" .tar)
      echo "  Loading $name..."
      docker load -i "$img_tar"
    fi
  done
  echo "  Docker images loaded"
else
  echo "  Docker not available. Skipping image loading."
  echo "  You can load images later: docker load -i <image>.tar"
fi

# ── Step 9: Environment setup ──────────────────────────────
echo "[9/9] Setting up environment..."

# Data directories
mkdir -p "$PROJECT_DIR"/{data/conversations,data/builds,data/settings,data/confluence,uploads}

# .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
  if [ -f "$PROJECT_DIR/.env.example" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    sed -i 's/^MODE=local/MODE=airgap/' "$PROJECT_DIR/.env"
    echo "  Created .env from template (MODE=airgap)"
  fi
fi

# Activation script
cat > "$INSTALL_DIR/activate.sh" << 'ACTIVATE_EOF'
#!/bin/bash
# Enterprise LLM environment activation script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
echo "Enterprise LLM environment activated (offline mode)"
echo "  Python: $(python --version)"
echo "  To start: cd <project-dir> && uvicorn app.main:app --host 0.0.0.0 --port 8080"
ACTIVATE_EOF
chmod +x "$INSTALL_DIR/activate.sh"

# systemd service file (optional)
cat > "$INSTALL_DIR/enterprise-llm.service" << SERVICE_EOF
[Unit]
Description=Enterprise LLM Backend
After=network.target docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment=HF_HUB_OFFLINE=1
Environment=TRANSFORMERS_OFFLINE=1
ExecStart=$VENV_DIR/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo ""
echo "================================================================"
echo "  Installation Complete!"
echo "================================================================"
echo ""
echo "  Project: $PROJECT_DIR"
echo "  Venv:    $VENV_DIR"
echo "  Activate: source $INSTALL_DIR/activate.sh"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Configure .env:"
echo "     vi $PROJECT_DIR/.env"
echo "     -> LLM_API_BASE=http://<gpu-server>:8000/v1"
echo "     -> LLM_MODEL=<your-model-name>"
echo ""
echo "  2a. Start with Docker Compose:"
echo "      cd $PROJECT_DIR"
echo "      docker compose -f docker-compose.airgap.yml up -d"
echo ""
echo "  2b. Or start manually:"
echo "      source $INSTALL_DIR/activate.sh"
echo "      cd $PROJECT_DIR"
echo "      uvicorn app.main:app --host 0.0.0.0 --port 8080"
echo ""
echo "  3. (Optional) Install as systemd service:"
echo "     cp $INSTALL_DIR/enterprise-llm.service /etc/systemd/system/"
echo "     systemctl daemon-reload"
echo "     systemctl enable --now enterprise-llm"
echo ""
echo "  4. Verify installation:"
echo "     source $INSTALL_DIR/activate.sh"
echo "     cd $PROJECT_DIR"
echo "     python scripts/verify_installation.py"
echo ""
echo "  Access:"
echo "    Platform UI : http://localhost:3000"
echo "    Backend API : http://localhost:8080"
echo "    API Docs    : http://localhost:8080/docs"
echo "    ChromaDB    : http://localhost:8100"
echo ""
