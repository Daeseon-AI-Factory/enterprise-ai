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
- Python packages (FastAPI, LangChain, ChromaDB, etc.)
- Embedding model (bge-large-en-v1.5)
- Frontend builds (widget + platform)

## Step 1: Download (Internet PC)

On a PC with internet access:

```bash
git clone <this-repo>
cd Product006_ClosedEnterpriseLLM

# Install Python deps on the internet PC first
pip install -r requirements.txt

# Download everything for offline transfer
bash scripts/download_dependencies.sh
```

This creates `./offline_packages/` (~4 GB).

## Step 2: Transfer

Copy the **entire project directory** (including `offline_packages/`) to the air-gapped server via USB or approved transfer method.

```
Product006_ClosedEnterpriseLLM/     (~4.5 GB total)
├── offline_packages/               (~4 GB - all dependencies)
├── app/                            (backend source)
├── platform/                       (frontend source)
├── widget/                         (chat widget source)
├── scripts/                        (installation scripts)
└── ...
```

## Step 3: Install (Air-gapped Server)

```bash
cd Product006_ClosedEnterpriseLLM
sudo bash scripts/install_offline_linux.sh
```

This script will:
1. Install Node.js (if not present)
2. Install Docker (if not present)
3. Create isolated Python venv
4. Install Python packages offline
5. Copy embedding model
6. Build frontends
7. Load Docker images
8. Create `.env` from template

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

```bash
# Start ChromaDB + n8n
docker compose -f docker-compose.airgap.yml up -d

# Activate venv
source /opt/enterprise-llm/venv/bin/activate

# Set offline flags
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

## Step 6: Verify

```bash
python scripts/verify_installation.py
```

## Step 7: Access

- **Platform UI**: http://<server-ip>:3000
- **Backend API**: http://<server-ip>:8080
- **API Docs**: http://<server-ip>:8080/docs
- **n8n**: http://<server-ip>:5678

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
| ChromaDB connection error | `docker compose -f docker-compose.airgap.yml up -d chromadb` |
| LLM endpoint unreachable | Check `LLM_API_BASE` in `.env` matches your GPT-OSS serving URL |
| Embedding model not found | Copy `offline_packages/models/embedding` to `./models/embedding` |
| Frontend build fails | Ensure Node.js is installed: `node --version` |

## Transfer Size Estimate

| Component | Size |
|-----------|------|
| Python wheels | ~500 MB |
| Embedding model | ~1.3 GB |
| Node.js installer | ~80 MB |
| npm packages (widget + platform) | ~400 MB |
| Docker binary | ~70 MB |
| Docker images (ChromaDB + n8n) | ~1.3 GB |
| **Total** | **~3.7 GB** |
