# Offline Installation Guide

## Overview

This guide covers deploying the Enterprise LLM Platform to an **air-gapped (closed) network**.

## Prerequisites

### Already installed on the air-gapped server:
- GPT-OSS 120B model + model serving (vLLM/TGI)
- GPU + NVIDIA Driver + CUDA Toolkit
- Python 3.11+
- Linux OS

### Will be installed by this package:
- Node.js 20.x LTS
- Docker (optional, for ChromaDB + n8n)
- Python packages (FastAPI, LangChain, ChromaDB, BeautifulSoup4, etc.)
- Embedding model (bge-large-en-v1.5)
- Frontend builds (widget + platform)

## Step 1: Download (Internet PC)

### Linux / macOS

```bash
git clone <this-repo>
cd Product006_ClosedEnterpriseLLM

pip install -r requirements.txt
bash scripts/download_dependencies.sh
```

### Windows 10 (PowerShell)

```powershell
git clone <this-repo>
cd Product006_ClosedEnterpriseLLM

pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File scripts\download_dependencies.ps1
```

**Windows 10 Requirements:**
- Python 3.11+ (python.org installer or winget)
- Node.js 20.x LTS (nodejs.org installer)
- Docker Desktop (for Docker image saving — optional but recommended)
- Git for Windows
- `pip install huggingface_hub` (for embedding model download)

**Windows 10 Notes:**
- Windows `tar` command is available since Windows 10 1803
- If `tar` fails, install 7-Zip and use `7z` instead
- Docker Desktop must be running before executing the script
- PowerShell execution policy may need: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

This creates `./offline_packages/` (~5 GB).

## Step 2: Transfer

Copy `offline_packages/` to the air-gapped server via USB or approved transfer method.

```
offline_packages/                  (~5 GB)
├── python/                        Python .whl files
├── models/embedding/              bge-large-en-v1.5 model files
├── node/
│   ├── node-v20.18.1-linux-x64.tar.xz
│   ├── node-v20.18.1-x64.msi     (Windows, for reference)
│   ├── widget_node_modules.tar.gz
│   └── platform_node_modules.tar.gz
├── docker/
│   ├── docker-27.4.1.tgz          Docker binary (Linux)
│   ├── chromadb.tar                ChromaDB image
│   ├── n8n.tar                     n8n image
│   ├── python311.tar               Python 3.11 image (for backend Docker build)
│   ├── node20.tar                  Node 20 image (for frontend Docker build)
│   └── nginx.tar                   Nginx image (for frontend Docker build)
└── source.tar.gz                   Source code archive
```

## Step 3: Install (Air-gapped Server)

```bash
cd Product006_ClosedEnterpriseLLM
sudo bash scripts/install_offline_linux.sh
```

This script will:
1. Install Node.js (if not present)
2. Install Docker (if not present)
3. Create isolated Python venv at `/opt/enterprise-llm/venv`
4. Install Python packages offline
5. Copy embedding model
6. Build frontends
7. Load Docker images (ChromaDB, n8n, Python, Node, Nginx)
8. Create data directories
9. Create `.env` from template

## Step 4: Configure

Edit `.env`:

```env
MODE=airgap
LLM_API_BASE=http://<gpu-server-ip>:8000/v1
LLM_API_KEY=not-needed
LLM_MODEL=gpt-oss-120b
EMBEDDING_MODEL_PATH=./models/embedding
CHROMA_HOST=localhost
CHROMA_PORT=8100
```

## Step 5: Start Services

### Option A: Docker Compose (recommended)

```bash
docker compose -f docker-compose.airgap.yml up -d
```

This starts backend (:8080), platform (:3000), ChromaDB (:8100), n8n (:5678).

### Option B: Manual (without Docker)

```bash
# Start ChromaDB
docker run -d -p 8100:8000 -v chroma_data:/chroma/chroma chromadb/chroma:latest

# Activate venv
source /opt/enterprise-llm/venv/bin/activate

# Set offline flags
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Serve frontend (separate terminal)
cd platform && npm run preview -- --port 3000 --host
```

## Step 6: Verify

```bash
python scripts/verify_installation.py
```

Expected output:
```
  [OK] FastAPI
  [OK] BeautifulSoup4
  [OK] Backend modules import
  [OK] Data directories writable
  [OK] ChromaDB reachable
  ...
  Results: 20 passed, 0 failed, 20 total
  All checks passed! System is ready.
```

## Step 7: Access

- **Platform UI**: http://<server-ip>:3000
- **Backend API**: http://<server-ip>:8080
- **API Docs (Swagger)**: http://<server-ip>:8080/docs
- **n8n Workflow**: http://<server-ip>:5678

## Step 8: Post-Install Setup (via Settings page)

Open http://<server-ip>:3000/settings and configure:

1. **Confluence tab**: Enter internal Confluence Server URL + credentials
2. **Build/Deploy tab**: Register build presets for your projects
3. **Data tab**: Verify vector DB collections

## Integrating the Widget

Add to any existing Spring+Vue2 page:

```html
<script src="http://<server-ip>:8080/widget/ai-chat.umd.js"></script>
```

Or with a custom API endpoint:

```html
<script data-api="http://<server-ip>:8080" src="/path/to/ai-chat.umd.js"></script>
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Re-run `pip install --no-index --find-links=./offline_packages/python/ -r requirements.txt` |
| `No module named 'bs4'` | `pip install --no-index --find-links=./offline_packages/python/ beautifulsoup4` |
| ChromaDB connection error | `docker compose -f docker-compose.airgap.yml up -d chromadb` |
| LLM endpoint unreachable | Check `LLM_API_BASE` in `.env` matches your GPT-OSS serving URL |
| Embedding model not found | Copy `offline_packages/models/embedding` to `./models/embedding` |
| Frontend build fails | Ensure Node.js is installed: `node --version` |
| Docker build fails (no base image) | `docker load -i offline_packages/docker/python311.tar` etc. |
| Settings not persisting | Check `data/settings/` directory is writable |
| Confluence sync fails | Verify internal Confluence URL is reachable from this server |

## Transfer Size Estimate

| Component | Size |
|-----------|------|
| Python wheels | ~500 MB |
| Embedding model | ~1.3 GB |
| Node.js installer | ~80 MB |
| npm packages (widget + platform) | ~400 MB |
| Docker binary | ~70 MB |
| Docker images (ChromaDB + n8n + build images) | ~2.0 GB |
| Source archive | ~50 MB |
| **Total** | **~4.4 GB** |

## Directory Structure on Server

```
/opt/enterprise-llm/
└── venv/                          Python virtual environment

Product006_ClosedEnterpriseLLM/
├── app/                           Backend source
├── platform/                      Frontend source + dist/
├── widget/                        Widget source + dist/
├── models/embedding/              bge-large-en-v1.5
├── data/
│   ├── conversations/             Chat history (JSON)
│   ├── builds/                    Build/deploy logs (JSON)
│   ├── settings/                  User settings (JSON)
│   └── confluence/                Sync state (JSON)
├── uploads/                       RAG uploaded documents
└── .env                           Environment configuration
```
