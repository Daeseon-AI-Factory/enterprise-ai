# 🏭 Enterprise LLM Platform

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Oracle](https://img.shields.io/badge/Oracle-XE_21c-F80000?logo=oracle&logoColor=white)](https://oracle.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> [🇺🇸 English README](README.md)

**폐쇄망 대응 AI 통합 플랫폼 — 자연어로 DB 조회, 문서 검색, 코드 분석**

기업 내부 DB·문서·소스코드를 LLM과 연결하여, 자연어 질문만으로 데이터 조회·문서 검색·통합 분석이 가능한 AI 플랫폼입니다. 인터넷이 차단된 폐쇄망 환경에서도 자체 모델로 완전한 오프라인 동작을 지원합니다.

---

## 📋 목차

- [주요 기능](#-주요-기능)
- [아키텍처](#-아키텍처)
- [기술 스택](#-기술-스택)
- [빠른 시작](#-빠른-시작)
- [폐쇄망 배포 가이드](#-폐쇄망-배포-가이드)
- [API 엔드포인트](#-api-엔드포인트)
- [프로젝트 구조](#-프로젝트-구조)
- [스크린샷](#-스크린샷)
- [라이선스](#-라이선스)

---

## ✨ 주요 기능

| # | 기능 | 설명 |
|---|------|------|
| 🗣️ | **Text-to-SQL** | 자연어 질문 → SQL 자동 생성 → Oracle/PostgreSQL/MySQL 실시간 조회 |
| 📚 | **RAG 문서 검색** | 사내 문서를 벡터 DB에 색인, BM25 + Dense + Reranker 하이브리드 검색 |
| 💻 | **Git Code RAG** | Git 저장소를 색인하여 소스코드 기반 AI 질의응답 |
| 🔬 | **통합 진단 (Analyze)** | RAG + Text-to-SQL 동시 실행, DB 수치와 문서를 종합한 분석 답변 |
| 🔒 | **폐쇄망 모드 (Airgap)** | 외부 인터넷 없이 자체 LLM + 로컬 임베딩으로 완전 오프라인 동작 |
| 📖 | **Confluence 연동** | Confluence REST API로 사내 Wiki 자동 동기화 및 검색 |
| 🤖 | **AI 코딩 에이전트** | 코드 생성·리뷰·분석을 수행하는 에이전트 기능 |
| 🎙️ | **음성 인식 (STT)** | Whisper 모델 기반 음성-텍스트 변환 |
| 👁️ | **Vision / OCR** | 이미지 분석 및 문서 OCR (PaddleOCR / Tesseract) |
| ⚡ | **Function Calling** | LLM 네이티브 함수 호출로 도구 자동 선택 및 실행 |

---

## 🏗️ 아키텍처

```
사용자 (자연어 질문)
    │
    ▼
┌──────────────────────────────────────────────────────┐
│              Enterprise LLM Platform                  │
│                                                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │
│  │ Text-to-SQL │ │ RAG 문서검색 │ │  Git Code RAG   │ │
│  └──────┬──────┘ └──────┬──────┘ └────────┬────────┘ │
│         │               │                  │          │
│         └───────┬───────┘                  │          │
│                 ▼                          │          │
│        ┌────────────────┐                  │          │
│        │ 통합 진단       │◄────────────────┘          │
│        │ (Analyze)      │                             │
│        └───────┬────────┘                             │
│                ▼                                      │
│  ┌──────────────────────────────────────┐             │
│  │  LLM Engine                          │             │
│  │  ┌──────────┐    ┌────────────────┐  │             │
│  │  │ OpenAI   │ OR │ vLLM (자체모델) │  │             │
│  │  │ GPT-4o   │    │ Mistral-7B     │  │             │
│  │  └──────────┘    └────────────────┘  │             │
│  └──────────────────────────────────────┘             │
│                                                       │
│  ┌────────┐ ┌──────────┐ ┌──────┐ ┌────────────────┐ │
│  │ 인증   │ │ STT/OCR  │ │Agent │ │ Function Call   │ │
│  │ (JWT)  │ │ (Whisper) │ │      │ │                 │ │
│  └────────┘ └──────────┘ └──────┘ └────────────────┘ │
└──────────────────────────────────────────────────────┘
       │            │            │
  Oracle DB     ChromaDB      Git Repo
 (업무 DB)     (벡터 DB)     (소스코드)
```

### 핵심 설계 원칙

1. **Deterministic Backbone** — AI는 판단·생성에만 사용, 검증·실행은 코드로 처리
2. **이중 모드** — `MODE=local` (OpenAI API) / `MODE=airgap` (자체 모델) `.env` 한 줄로 전환
3. **모듈 독립성** — Text-to-SQL, RAG, Git RAG가 독립적으로 동작, 통합 진단에서 조합

---

## 🛠️ 기술 스택

| 영역 | 기술 | 비고 |
|------|------|------|
| **Backend** | Python 3.12, FastAPI | 비동기 처리, 19개 라우터 |
| **Frontend** | React 18, TypeScript 5, Tailwind CSS | Vite 빌드, 다국어(KO/EN) |
| **DB 연동** | Oracle XE 21c, PostgreSQL, MySQL | Text-to-SQL 대상 DB |
| **벡터 DB** | ChromaDB | 임베딩 기반 유사도 검색 |
| **LLM** | OpenAI API (gpt-4o-mini) / vLLM (Mistral-7B) | 자체 모델 전환 가능 |
| **검색 엔진** | BM25 + Dense + Reranker | 하이브리드 검색 파이프라인 |
| **인증** | JWT + bcrypt | 토큰 기반 인증 (24시간 만료) |
| **인프라** | Docker Compose | 개발/운영 환경 일관성 |
| **문서 연동** | Confluence REST API | 사내 Wiki 자동 동기화 |
| **음성/비전** | Whisper, PaddleOCR | STT + OCR 멀티모달 |

---

## 🚀 빠른 시작

### 사전 요구사항

- **Python** 3.12+
- **Node.js** 18+ (프론트엔드 빌드)
- **Oracle XE 21c** 또는 PostgreSQL (Text-to-SQL용, 선택)
- **Docker** (선택 — ChromaDB, vLLM 등 컨테이너 실행 시)

### 설치

```bash
# 1. 저장소 클론
git clone https://github.com/JasonAIFactory/Product006_ClosedEnterpriseLLM.git
cd Product006_ClosedEnterpriseLLM

# 2. 백엔드 의존성 설치
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. 프론트엔드 빌드
cd platform && npm install && npm run build && cd ..
```

### 환경 설정

```bash
# .env.example을 복사하여 .env 생성
cp .env.example .env
```

`.env` 주요 설정:

```env
# 모드 선택: "local" (OpenAI) 또는 "airgap" (폐쇄망)
MODE=local

# LLM 설정
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-your-key-here
LLM_MODEL=gpt-4o-mini

# 임베딩 모델 경로
EMBEDDING_MODEL_PATH=./models/embedding

# ChromaDB (0 = 로컬 in-process 모드, Docker 불필요)
CHROMA_PORT=0

# DB 연결 (Text-to-SQL)
DB_TYPE=oracle
DB_HOST=localhost
DB_PORT=1521
DB_NAME=ORCL
DB_USER=readonly_user
DB_PASSWORD=your-password
```

### 실행

```bash
# 백엔드 서버 시작 (포트 8080)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# 프론트엔드 개발 서버 (포트 3000)
cd platform && npm run dev
```

브라우저에서 `http://localhost:3000` 접속

---

## 🔐 폐쇄망 배포 가이드

인터넷이 차단된 환경(VDI, 보안망 등)에 배포하는 방법입니다.

### 1. 온라인 환경에서 패키지 준비

```bash
# Python 오프라인 패키지 다운로드
pip download -r requirements.txt -d offline_packages/ \
    --platform win_amd64 --python-version 3.12 --only-binary=:all:

# 임베딩 모델 다운로드 (models/embedding 디렉토리에 저장)
# node_modules 포함 여부 확인
```

### 2. 폐쇄망 설치

```bash
# 오프라인 pip 설치
pip install --no-index --find-links=offline_packages/ -r requirements.txt

# 환경 변수 설정
MODE=airgap
CHROMA_PORT=0
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

### 3. 배포 체크리스트

- [ ] 대상 Python 버전, OS, 아키텍처 확인 (Python 3.12, Windows AMD64)
- [ ] 코드의 모든 import가 requirements.txt에 포함되어 있는지 확인
- [ ] 임베딩 모델 포함 (`models/embedding`)
- [ ] `.env` 설정 파일 포함
- [ ] `install.bat` 스크립트 포함
- [ ] 가상환경에서 실제 오프라인 설치 테스트 완료

> `install.bat` 스크립트가 프로젝트 루트에 포함되어 있습니다.

---

## 📡 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 상태 확인 (모드, 모델 정보) |
| `POST` | `/api/auth/login` | 로그인 (JWT 토큰 발급) |
| `POST` | `/api/chat/` | 일반 채팅 (LLM 대화) |
| `POST` | `/api/text2sql/generate` | 자연어 → SQL 생성 |
| `POST` | `/api/text2sql/execute` | 생성된 SQL 실행 |
| `POST` | `/api/text2sql/discover` | DB 스키마 자동 탐색 |
| `POST` | `/api/rag/query` | RAG 문서 검색 질의 |
| `POST` | `/api/rag/upload` | 문서 업로드 및 색인 |
| `GET` | `/api/rag/collections` | RAG 컬렉션 목록 |
| `POST` | `/api/analyze` | 통합 진단 (RAG + SQL) |
| `POST` | `/api/git/index` | Git 저장소 색인 |
| `POST` | `/api/git/query` | Git 코드 RAG 질의 |
| `POST` | `/api/confluence/sync` | Confluence 문서 동기화 |
| `POST` | `/api/function-chat/` | Function Calling 채팅 |
| `POST` | `/api/agent/run` | AI 에이전트 실행 |
| `POST` | `/api/stt/transcribe` | 음성 → 텍스트 변환 |
| `POST` | `/api/vision/analyze` | 이미지 분석 |
| `POST` | `/api/ocr/extract` | OCR 텍스트 추출 |
| `POST` | `/api/codegen/generate` | 코드 생성 |
| `POST` | `/api/review/analyze` | 코드 리뷰 |
| `POST` | `/api/webhook/` | 웹훅 수신 (n8n 연동) |

---

## 📁 프로젝트 구조

```
Product006_ClosedEnterpriseLLM/
├── app/                          # 🔧 백엔드 (FastAPI)
│   ├── main.py                   #   앱 진입점, 라우터 등록
│   ├── config.py                 #   환경 설정 (.env 로드)
│   ├── llm_client.py             #   LLM API 클라이언트
│   ├── routers/                  #   API 라우터 (19개)
│   │   ├── auth.py               #     인증 (로그인/JWT)
│   │   ├── chat.py               #     일반 채팅
│   │   ├── text2sql.py           #     Text-to-SQL
│   │   ├── rag.py                #     RAG 문서 검색
│   │   ├── analyze.py            #     통합 진단
│   │   ├── git_rag.py            #     Git Code RAG
│   │   ├── confluence.py         #     Confluence 연동
│   │   ├── function_chat.py      #     Function Calling
│   │   ├── agent.py              #     AI 에이전트
│   │   ├── stt.py                #     음성 인식
│   │   ├── vision.py             #     이미지 분석
│   │   ├── ocr.py                #     OCR
│   │   ├── codegen.py            #     코드 생성
│   │   ├── review.py             #     코드 리뷰
│   │   ├── webhook.py            #     웹훅
│   │   └── ...
│   ├── services/                 #   비즈니스 로직 (서비스 계층)
│   │   ├── text2sql_service.py
│   │   ├── rag_service.py
│   │   ├── chat_service.py
│   │   └── ...
│   ├── core/                     #   공통 모듈 (인증, 프롬프트)
│   └── connectors/               #   외부 시스템 커넥터
├── platform/                     # 🎨 프론트엔드 (React + TypeScript)
│   └── src/
│       ├── App.tsx
│       ├── pages/                #   페이지 컴포넌트
│       ├── components/           #   공통 UI 컴포넌트
│       ├── lib/                  #   API 클라이언트, 유틸리티
│       └── layouts/              #   레이아웃 컴포넌트
├── models/                       # 🧠 로컬 AI 모델 (임베딩, Whisper)
├── data/                         # 💾 스키마, RAG 데이터
├── chroma_data/                  # 🔍 ChromaDB 벡터 저장소
├── scripts/                      # 📜 유틸리티 스크립트
├── tests/                        # ✅ 테스트
├── docs/                         # 📖 문서
├── docker-compose.yml            # 🐳 Docker 구성
├── docker-compose.airgap.yml     # 🐳 폐쇄망용 Docker 구성
├── docker-compose.vllm.yml       # 🐳 vLLM GPU 구성
├── requirements.txt              # 📦 Python 의존성
├── install.bat                   # 💿 Windows 설치 스크립트
├── .env.example                  # ⚙️ 환경 변수 예시
└── CLAUDE.md                     # 📋 프로젝트 철학
```

---

## 📸 스크린샷

> 추후 추가 예정

| 기능 | 스크린샷 |
|------|----------|
| Text-to-SQL 대화 | ![Text-to-SQL](docs/screenshots/text2sql.png) |
| RAG 문서 검색 | ![RAG Search](docs/screenshots/rag-search.png) |
| 통합 진단 (Analyze) | ![Analyze](docs/screenshots/analyze.png) |
| Git Code RAG | ![Git RAG](docs/screenshots/git-rag.png) |
| 대시보드 | ![Dashboard](docs/screenshots/dashboard.png) |

---

## 📄 라이선스

이 프로젝트는 [MIT License](LICENSE) 하에 배포됩니다.

---

<p align="center">
  <b>Enterprise LLM Platform</b> — 1인 기획·설계·구현 by Jason (유대선)<br>
  제조 도메인 전문성 + 백엔드 개발 경력 + AI 플랫폼 기획·구현 역량
</p>
