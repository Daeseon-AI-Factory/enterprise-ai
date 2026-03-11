# Offline Installation Guide (Linux / Windows)

## Overview

이 가이드는 **Enterprise LLM Platform**을 **완전한 폐쇄망(air-gapped network)**에 배포하는 방법을 다룹니다.
대상 서버/PC에 Python, Node.js, Docker 등 아무것도 설치되어 있지 않아도 됩니다.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Air-gapped Network                │
│                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐  │
│  │ Platform  │───>│ Backend  │───>│ GPU Server   │  │
│  │ (React)   │    │ (FastAPI)│    │ GPT-OSS/vLLM │  │
│  │ :3000     │    │ :8080    │    │ :8000        │  │
│  └──────────┘    └────┬─────┘    └──────────────┘  │
│                       │                             │
│              ┌────────┴────────┐                    │
│              │                 │                    │
│         ┌────┴─────┐   ┌──────┴───┐                │
│         │ ChromaDB  │   │ Embedding│                │
│         │ :8100     │   │ Model    │                │
│         └──────────┘   └──────────┘                │
└─────────────────────────────────────────────────────┘
```

---

## Step 1: 패키지 준비 (인터넷 PC)

인터넷이 되는 PC에서 오프라인 패키지를 생성합니다.

### 필요 환경 (인터넷 PC)

| 항목 | 요구사항 |
|------|---------|
| Python | 3.11+ |
| Node.js | 20.x LTS |
| Docker | Docker Desktop (이미지 저장용) |
| pip packages | `pip install huggingface_hub` |
| 디스크 | 최소 15 GB 여유 공간 |

### Linux/macOS/WSL에서 실행

```bash
git clone <this-repo>
cd Product006_ClosedEnterpriseLLM

# huggingface-cli 설치 (embedding model 다운로드용)
pip install huggingface_hub

# 패키지 생성 (Linux + Windows 둘 다)
bash scripts/prepare_offline_package.sh

# 옵션: Linux만
bash scripts/prepare_offline_package.sh --linux-only

# 옵션: Windows만
bash scripts/prepare_offline_package.sh --windows-only

# 옵션: Docker 이미지 제외 (용량 절약)
bash scripts/prepare_offline_package.sh --no-docker
```

### Windows (PowerShell)에서 실행

```powershell
git clone <this-repo>
cd Product006_ClosedEnterpriseLLM

pip install huggingface_hub

# 패키지 생성
powershell -ExecutionPolicy Bypass -File scripts\prepare_offline_package.ps1

# 옵션
powershell -ExecutionPolicy Bypass -File scripts\prepare_offline_package.ps1 -LinuxOnly
powershell -ExecutionPolicy Bypass -File scripts\prepare_offline_package.ps1 -WindowsOnly
powershell -ExecutionPolicy Bypass -File scripts\prepare_offline_package.ps1 -NoDocker
```

### 생성되는 파일

```
enterprise-llm-offline-linux.zip    (~5 GB)
enterprise-llm-offline-windows.zip  (~4 GB)
```

---

## Step 2: 전송

생성된 zip 파일을 폐쇄망으로 전송합니다.

- USB 드라이브
- 내부 승인된 파일 전송 시스템
- 보안 FTP
- 망간 자료전송 시스템 (CDMS 등)

---

## Step 3: 설치 (폐쇄망)

### Linux 서버

```bash
# 압축 해제
unzip enterprise-llm-offline-linux.zip
cd enterprise-llm-offline-linux

# 설치 (root 권한 필요)
sudo bash install.sh

# 또는 설치 디렉토리 지정
sudo bash install.sh /custom/path
```

설치 스크립트가 자동으로 수행하는 작업:

| 단계 | 설명 |
|------|------|
| 1 | Python 설치 (Miniconda, 기존 Python 없을 경우) |
| 2 | Node.js 설치 (없을 경우) |
| 3 | Docker + Docker Compose 설치 (없을 경우) |
| 4 | 소스 코드 추출 |
| 5 | Python 가상환경 생성 + 패키지 설치 |
| 6 | Embedding 모델 복사 (bge-m3) |
| 7 | 프론트엔드 빌드 (React + Vue widget) |
| 8 | Docker 이미지 로드 |
| 9 | 환경 설정 (.env, 데이터 디렉토리) |

### Windows PC

```powershell
# 압축 해제
Expand-Archive enterprise-llm-offline-windows.zip -DestinationPath .
cd enterprise-llm-offline-windows

# PowerShell을 관리자 권한으로 실행 후:
powershell -ExecutionPolicy Bypass -File install.ps1

# 또는 설치 디렉토리 지정
powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir "D:\enterprise-llm"
```

---

## Step 4: 설정

### .env 파일 편집

```bash
# Linux
vi /opt/enterprise-llm/app/.env

# Windows
notepad C:\enterprise-llm\app\.env
```

필수 수정 항목:

```env
MODE=airgap
LLM_API_BASE=http://<gpu-server-ip>:8000/v1
LLM_API_KEY=not-needed
LLM_MODEL=<your-model-name>
EMBEDDING_MODEL_PATH=./models/embedding
CHROMA_HOST=localhost
CHROMA_PORT=8100
```

---

## Step 5: 서비스 시작

### Option A: Docker Compose (권장)

```bash
cd /opt/enterprise-llm/app    # Linux
cd C:\enterprise-llm\app      # Windows

docker compose -f docker-compose.airgap.yml up -d
```

이 명령으로 시작되는 서비스:
- **Backend** (FastAPI) — `:8080`
- **Platform** (React UI) — `:3000`
- **ChromaDB** (Vector DB) — `:8100`
- **n8n** (Workflow) — `:5678`

### Option B: 수동 실행 (Docker 없이)

```bash
# Linux
source /opt/enterprise-llm/activate.sh
cd /opt/enterprise-llm/app

# ChromaDB만 Docker로 (필요시)
docker run -d -p 8100:8000 -v chroma_data:/chroma/chroma chromadb/chroma:latest

# Backend 시작
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Frontend (별도 터미널)
cd platform && npx serve dist -l 3000
```

```powershell
# Windows
C:\enterprise-llm\activate.bat
cd C:\enterprise-llm\app

uvicorn app.main:app --host 0.0.0.0 --port 8080
```

---

## Step 6: 검증

```bash
# Linux
source /opt/enterprise-llm/activate.sh
cd /opt/enterprise-llm/app
python scripts/verify_installation.py

# Windows
C:\enterprise-llm\activate.bat
cd C:\enterprise-llm\app
python scripts\verify_installation.py
```

정상 출력:
```
============================================================
Enterprise LLM — Installation Verification
============================================================

  ✓ FastAPI
  ✓ Uvicorn
  ✓ Pydantic Settings
  ✓ LangChain
  ✓ ChromaDB
  ✓ OpenAI Client
  ✓ Sentence Transformers
  ✓ PyPDF
  ✓ python-docx
  ✓ openpyxl
  ✓ BeautifulSoup4
  ✓ SQLAlchemy
  ✓ Loguru
  ✓ HTTPX
  ✓ App Config loads
  ✓ Embedding model directory exists
  ✓ Data directories writable
  ✓ Backend modules import

Results: 18 passed, 0 failed, 18 total
All checks passed! System is ready.
```

---

## Step 7: 접속

| 서비스 | URL |
|--------|-----|
| Platform UI | `http://<server-ip>:3000` |
| Backend API | `http://<server-ip>:8080` |
| API Docs (Swagger) | `http://<server-ip>:8080/docs` |
| ChromaDB | `http://<server-ip>:8100` |
| n8n Workflow | `http://<server-ip>:5678` |

---

## 폐쇄망 Docker FAQ

### Q: 폐쇄망에서 Docker가 가능한가요?

**가능합니다.** Docker는 인터넷 없이도 완벽하게 동작합니다.

작동 원리:
1. 인터넷 PC에서 `docker save`로 이미지를 `.tar` 파일로 저장
2. 폐쇄망으로 `.tar` 파일 전송
3. `docker load`로 이미지 로드
4. `docker compose up`으로 서비스 시작

본 패키지에 이미 다음 이미지가 포함되어 있습니다:
- `chromadb/chroma:latest` — Vector DB
- `n8nio/n8n:latest` — Workflow 자동화
- `python:3.11-slim` — Backend 빌드용
- `node:20-alpine` — Frontend 빌드용
- `nginx:alpine` — Frontend 서빙용

### Q: 폐쇄망에서 Docker 개발/디버깅이 가능한가요?

**가능합니다.** 다음과 같이 활용할 수 있습니다:

```bash
# 소스 코드를 volume mount하여 실시간 개발
docker compose -f docker-compose.airgap.yml up -d

# 컨테이너 로그 확인
docker compose logs -f backend

# 컨테이너 안으로 접속하여 디버깅
docker exec -it <container-name> bash

# 이미지 재빌드 (소스 변경 후)
docker compose build backend
docker compose up -d backend
```

`docker build`도 **base 이미지가 로컬에 있으면** 인터넷 없이 동작합니다.
본 패키지의 이미지가 이미 로드되어 있으므로 Dockerfile 기반 빌드도 가능합니다.

### Q: Windows에서 Docker를 사용하려면?

1. **Docker Desktop 설치** (인터넷 PC에서 다운로드하여 전송)
   - [docker.com](https://www.docker.com/products/docker-desktop/) 에서 다운로드
   - 설치 후 재부팅 필요
2. **Hyper-V 또는 WSL2 활성화** (Windows 기능)
   ```powershell
   # WSL2 활성화 (관리자 PowerShell)
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   # 재부팅 후
   wsl --set-default-version 2
   ```
3. **Docker 이미지 로드**
   ```powershell
   Get-ChildItem docker-images\*.tar | ForEach-Object { docker load -i $_.FullName }
   ```

---

## 패키지 내용물

### Linux 패키지

```
enterprise-llm-offline-linux/
├── installers/
│   ├── Miniconda3-latest-Linux-x86_64.sh   Python 설치 (~100 MB)
│   ├── node-v20.18.1-linux-x64.tar.xz     Node.js (~40 MB)
│   ├── docker-27.4.1.tgz                  Docker binary (~70 MB)
│   └── docker-compose                     Docker Compose (~60 MB)
├── python-packages/                        Python .whl (~500 MB)
├── npm-packages/
│   ├── widget_node_modules.tar.gz          Vue widget deps (~30 MB)
│   └── platform_node_modules.tar.gz        React platform deps (~350 MB)
├── docker-images/
│   ├── chromadb.tar                        ChromaDB (~500 MB)
│   ├── n8n.tar                            n8n (~800 MB)
│   ├── python311.tar                       Python 3.11 (~150 MB)
│   ├── node20.tar                          Node 20 (~200 MB)
│   └── nginx.tar                          Nginx (~50 MB)
├── models/
│   └── embedding/                          bge-m3 (~2.2 GB)
├── source.tar.gz                           Source code (~50 MB)
├── install.sh                              Installer script
├── scripts/
│   ├── verify_installation.py              Verification script
│   └── requirements.txt                    Python dependencies
└── README.txt                              Quick start
```

### Windows 패키지

```
enterprise-llm-offline-windows/
├── installers/
│   ├── python-3.11.9-amd64.exe            Python installer (~25 MB)
│   ├── node-v20.18.1-x64.msi              Node.js installer (~30 MB)
│   └── Git-2.47.1-64-bit.exe              Git installer (~55 MB)
├── python-packages/                        Python .whl (Windows) (~500 MB)
├── npm-packages/                           (same as Linux)
├── docker-images/                          (same as Linux)
├── models/                                 (same as Linux)
├── source.tar.gz
├── install.ps1                             PowerShell installer
├── scripts/
│   ├── verify_installation.py
│   └── requirements.txt
└── README.txt
```

### 패키지 크기

| 구성 요소 | 크기 |
|-----------|------|
| Python 설치 프로그램 | ~25–100 MB |
| Python 패키지 (.whl) | ~500 MB |
| Embedding 모델 | ~2.2 GB |
| Node.js 설치 프로그램 | ~30–40 MB |
| npm 패키지 | ~380 MB |
| Docker 바이너리 | ~70 MB |
| Docker 이미지 | ~1.7 GB |
| 소스 코드 | ~50 MB |
| **합계 (Docker 포함)** | **~4.2 GB** |
| **합계 (Docker 제외)** | **~2.3 GB** |

---

## 설치 후 디렉토리 구조

### Linux

```
/opt/enterprise-llm/
├── activate.sh                    환경 활성화 스크립트
├── enterprise-llm.service         systemd 서비스 파일
├── miniconda3/                    Python (Miniconda로 설치 시)
├── venv/                          Python 가상환경
└── app/                           프로젝트 소스
    ├── app/                       Backend (FastAPI)
    ├── platform/dist/             React UI (빌드 결과)
    ├── widget/dist/               Vue widget (빌드 결과)
    ├── models/embedding/          bge-m3
    ├── data/
    │   ├── conversations/
    │   ├── builds/
    │   ├── settings/
    │   └── confluence/
    ├── uploads/
    └── .env
```

### Windows

```
C:\enterprise-llm\
├── activate.bat                   CMD 환경 활성화
├── activate.ps1                   PowerShell 환경 활성화
├── venv\                          Python 가상환경
└── app\                           프로젝트 소스
    ├── app\                       Backend (FastAPI)
    ├── platform\dist\             React UI
    ├── widget\dist\               Vue widget
    ├── models\embedding\          bge-m3
    ├── data\
    ├── uploads\
    └── .env
```

---

## Troubleshooting

| 증상 | 해결 방법 |
|------|----------|
| `ModuleNotFoundError` | `pip install --no-index --find-links=<python-packages-path> -r requirements.txt` |
| `command not found: python3` | Miniconda 설치 확인: `source /opt/enterprise-llm/activate.sh` |
| `command not found: node` | Node.js 설치 확인: `node --version` |
| ChromaDB 연결 오류 | `docker compose -f docker-compose.airgap.yml up -d chromadb` |
| LLM 엔드포인트 연결 불가 | `.env`의 `LLM_API_BASE` 확인, GPU 서버 가동 상태 확인 |
| Embedding 모델 미발견 | `models/embedding/` 디렉토리 존재 확인 |
| Frontend 빌드 실패 | `node --version` 확인 (20.x 필요), npm-packages 압축해제 확인 |
| Docker 이미지 없음 | `docker load -i <image>.tar` 수동 실행 |
| Settings 저장 안됨 | `data/settings/` 디렉토리 쓰기 권한 확인 |
| Windows에서 tar 명령 없음 | Windows 10 1803+ 필요. 또는 7-Zip 사용 |
| PowerShell 실행 정책 오류 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Docker Desktop WSL2 오류 | Windows 기능에서 WSL2/Hyper-V 활성화 후 재부팅 |
| pip install 시 wheel 누락 | `--only-binary :all:` 없이 재다운로드, 또는 C compiler 설치 |

---

## Widget 통합 (기존 페이지 임베딩)

빌드된 위젯을 기존 Spring+Vue2 페이지에 삽입:

```html
<script src="http://<server-ip>:8080/widget/ai-chat.umd.js"></script>
```

또는 API 엔드포인트 지정:

```html
<script data-api="http://<server-ip>:8080" src="/path/to/ai-chat.umd.js"></script>
```

---

## systemd 서비스 등록 (Linux)

설치 스크립트가 자동으로 서비스 파일을 생성합니다:

```bash
# 서비스 등록
sudo cp /opt/enterprise-llm/enterprise-llm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now enterprise-llm

# 상태 확인
sudo systemctl status enterprise-llm

# 로그 확인
sudo journalctl -u enterprise-llm -f
```

---

## Post-Install Setup (Settings 페이지)

`http://<server-ip>:3000/settings` 에서 설정:

1. **Confluence tab**: 내부 Confluence Server URL + 인증 정보
2. **Build/Deploy tab**: 빌드 프리셋 등록
3. **Data tab**: Vector DB 컬렉션 확인
