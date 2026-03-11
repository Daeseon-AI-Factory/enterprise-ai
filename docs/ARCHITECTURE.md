# Enterprise LLM Platform — Architecture & Process Guide

> 최종 업데이트: 2026-03-11

---

## 1. 시스템 개요

폐쇄망(Air-gapped) 환경에서 동작하는 사내 AI 플랫폼.
외부 API(OpenAI) 또는 내부 LLM(GPT-OSS 120B) 양쪽 모두 지원.

```
┌─────────────────────────────────────────────────────────────┐
│                      사용자 브라우저                          │
│                                                             │
│  ┌─────────────────┐      ┌──────────────────────────────┐  │
│  │  Chat Widget    │      │  Admin Platform (React/Vite) │  │
│  │  (Vue.js)       │      │  - 대화, RAG, SQL, 코드생성   │  │
│  │  사내 웹 임베드  │      │  - 코드리뷰, Confluence 연동  │  │
│  └────────┬────────┘      └──────────────┬───────────────┘  │
│           │                              │                  │
└───────────┼──────────────────────────────┼──────────────────┘
            │          HTTP/REST           │
            ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (:8000)                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    API Routers                        │   │
│  │  /api/chat    /api/rag     /api/text2sql             │   │
│  │  /api/codegen /api/review  /api/confluence            │   │
│  │  /api/build   /api/settings                           │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │                   Services Layer                      │   │
│  │  ChatService  RagService  Text2SqlService             │   │
│  │  CodegenService  ReviewService  ConfluenceService     │   │
│  │  BuildService  SettingsService                        │   │
│  └──────────┬───────────┬───────────┬───────────────────┘   │
│             │           │           │                       │
│  ┌──────────▼──┐ ┌──────▼─────┐ ┌──▼──────────────────┐    │
│  │ LLM Client  │ │VectorStore │ │ Document Loader     │    │
│  │ (OpenAI SDK)│ │ (ChromaDB) │ │ PDF/DOCX/XLSX/Code  │    │
│  └──────┬──────┘ └──────┬─────┘ └─────────────────────┘    │
│         │               │                                   │
└─────────┼───────────────┼───────────────────────────────────┘
          │               │
          ▼               ▼
  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐
  │  LLM Engine   │  │   ChromaDB     │  │  Oracle / DB     │
  │               │  │  Vector Store  │  │  (Text-to-SQL)   │
  │ OpenAI API    │  │  + bge-m3      │  │                  │
  │ or GPT-OSS    │  │  Embedding     │  │                  │
  └───────────────┘  └────────────────┘  └──────────────────┘
```

---

## 2. 동작 모드

### local 모드 (인터넷 환경, 개발용)
```env
MODE=local
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=sk-xxxx
LLM_MODEL=gpt-4o-mini
```
- OpenAI API 직접 호출
- 로컬 ChromaDB (PersistentClient) 또는 Docker ChromaDB
- 임베딩 모델: 로컬 파일 (`./models/embedding/bge-m3`)

### airgap 모드 (폐쇄망, 운영용)
```env
MODE=airgap
LLM_API_BASE=http://localhost:8000/v1
LLM_API_KEY=not-needed
LLM_MODEL=gpt-oss-120b
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```
- 사내 GPT-OSS 서버를 OpenAI-compatible 엔드포인트로 호출
- 동일한 코드, `.env`만 변경

**핵심: LLM Client는 OpenAI SDK를 사용하되 `base_url`만 바꿔치기.**
코드 한 줄도 수정 없이 OpenAI ↔ GPT-OSS 전환 가능.

---

## 3. 핵심 모듈 상세

### 3.1 LLM Client (`app/llm_client.py`)

```python
client = OpenAI(base_url=settings.LLM_API_BASE, api_key=settings.LLM_API_KEY)

def chat_completion(messages, model=None, temperature=0.7, max_tokens=2048, stream=False):
    return client.chat.completions.create(...)
```

- 모든 서비스가 이 함수 하나로 LLM 호출
- stream=True면 SSE 스트리밍 응답

### 3.2 Vector Store (`app/core/vector_store.py`)

```
문서 업로드 → DocumentLoader → 텍스트 추출 → 청킹 → bge-m3 임베딩 → ChromaDB 저장
질문 입력 → bge-m3 임베딩 → ChromaDB 유사도 검색 → top-k 문서 반환
```

- **임베딩 모델**: BAAI/bge-m3 (로컬 파일, 인터넷 불필요)
- **벡터 DB**: ChromaDB (Docker HttpClient 또는 로컬 PersistentClient)
- **CHROMA_PORT=0** 이면 Docker 없이 로컬 파일 모드로 동작

### 3.3 Document Loader (`app/core/document_loader.py`)

| 파일 형식 | 처리 방법 |
|-----------|----------|
| PDF       | pypdf — 페이지별 텍스트 추출 |
| DOCX      | python-docx — 문단별 추출 |
| XLSX/XLS  | openpyxl — 시트별, 행별 탭 구분 텍스트 |
| 코드 (.py, .java, .js, .ts, .sql 등) | UTF-8 텍스트 읽기 |
| 텍스트 (.txt, .md, .csv) | UTF-8 텍스트 읽기 |

**청킹 설정:**
- 청크 크기: 1,000자
- 오버랩: 200자
- 1,000자씩 자르되 200자 겹쳐서 문맥 유지

### 3.4 Conversation Store (`app/core/conversation_store.py`)

- 파일 기반 JSON 저장 (`conversations/` 디렉토리)
- 대화 ID별 메시지 히스토리 관리
- 멀티턴 대화 지원

---

## 4. 기능별 프로세스 플로우

### 4.1 일반 채팅 (`/api/chat`)

```
사용자 메시지
    │
    ▼
ChatService.chat()
    │
    ├── 대화 히스토리 로드 (ConversationStore)
    ├── 시스템 프롬프트 + 히스토리 + 새 메시지 조합
    ├── LLM 호출 (chat_completion)
    ├── 응답을 히스토리에 저장
    │
    ▼
AI 응답 반환
```

**엔드포인트:**
- `POST /api/chat/` — 일반 대화
- `POST /api/chat/stream` — SSE 스트리밍 대화
- `POST /api/chat/context` — 컨텍스트(파일 등) 포함 대화
- `GET /api/chat/conversations` — 대화 목록
- `GET /api/chat/conversations/{id}` — 대화 내역 조회

### 4.2 RAG (문서 기반 질의응답) (`/api/rag`)

```
[문서 업로드 단계]
파일 업로드 (PDF/DOCX/XLSX)
    │
    ▼
DocumentLoader.load_and_chunk()
    │  텍스트 추출 + 1000자 청킹
    ▼
VectorStore.add_documents()
    │  bge-m3로 임베딩 → ChromaDB에 벡터 저장
    ▼
인덱싱 완료 (청크 수, doc_id 반환)


[질의 단계]
사용자 질문
    │
    ▼
VectorStore.search()
    │  질문을 bge-m3로 임베딩 → ChromaDB에서 top-k 유사 문서 검색
    ▼
컨텍스트 조합 (검색된 문서 청크들 연결)
    │
    ▼
LLM 호출 (시스템프롬프트 + 컨텍스트 + 질문)
    │
    ▼
답변 + 출처(파일명, 유사도 점수) 반환
```

**엔드포인트:**
- `POST /api/rag/upload` — 문서 업로드 & 인덱싱
- `POST /api/rag/query` — RAG 질의
- `GET /api/rag/collections` — 컬렉션 목록
- `DELETE /api/rag/collections/{id}` — 컬렉션 삭제

### 4.3 Text-to-SQL (`/api/text2sql`)

```
사용자 자연어 질문 ("이번 달 매출 합계는?")
    │
    ▼
Text2SqlService.generate_sql()
    │
    ├── 등록된 DB 스키마 정보 로드
    ├── 시스템 프롬프트 + 스키마 + 질문 → LLM 호출
    ├── LLM이 SQL 생성
    │
    ▼
생성된 SQL 반환 (실행 전 사용자 확인)
    │
    ▼ (사용자가 실행 승인)
Text2SqlService.execute_sql()
    │
    ├── SELECT 문만 허용 (안전 검증 — Deterministic Backbone)
    ├── SQLAlchemy + oracledb로 DB 연결 & 실행
    │
    ▼
결과 테이블 반환
```

**안전장치:**
- SELECT 문만 실행 가능 (INSERT/UPDATE/DELETE 차단)
- SQL 실행 전 반드시 사용자 확인 필요
- DB 스키마를 미리 등록해야 동작

**엔드포인트:**
- `POST /api/text2sql/generate` — 자연어 → SQL 생성
- `POST /api/text2sql/execute` — SQL 실행
- `POST /api/text2sql/schema` — DB 스키마 등록
- `GET /api/text2sql/schema` — 등록된 스키마 조회

### 4.4 코드 생성 (`/api/codegen`)

```
사용자 요청 ("FastAPI CRUD 엔드포인트 만들어줘")
    │
    ▼
CodegenService.generate()
    │
    ├── 프로젝트 템플릿 컨텍스트 로드 (기술 스택, 컨벤션, 샘플 코드)
    ├── 시스템 프롬프트 + 컨텍스트 + 요청 → LLM 호출
    │
    ▼
생성된 코드 반환
```

**엔드포인트:**
- `POST /api/codegen/generate` — 코드 생성

### 4.5 코드 리뷰 (`/api/review`)

```
코드 제출
    │
    ├── POST /api/review/ → 일반 코드 리뷰
    │     LLM이 버그, 성능, 보안, 가독성 분석
    │
    ├── POST /api/review/edge-cases → 엣지 케이스 분석
    │     LLM이 경계값, 예외 상황, 동시성 문제 분석
    │
    ▼
리뷰 결과 반환
```

### 4.6 Confluence 연동 (`/api/confluence`)

```
Confluence Space 동기화 요청
    │
    ▼
ConfluenceConnector.fetch_space_pages()
    │  REST API로 Confluence 페이지 목록 가져오기
    ▼
페이지별 HTML → 텍스트 변환 (BeautifulSoup)
    │
    ▼
변경 감지 (content hash 비교)
    │  변경된 페이지만 재인덱싱
    ▼
DocumentLoader.chunk → VectorStore에 저장
    │
    ▼
Confluence 문서도 RAG 검색 대상에 포함
```

**엔드포인트:**
- `POST /api/confluence/sync` — Space 동기화
- `GET /api/confluence/spaces` — 동기화된 Space 목록

### 4.7 빌드/배포 (`/api/build`)

```
빌드 명령 실행 요청
    │
    ▼
BuildService.execute()
    │  subprocess로 셸 명령 실행 (timeout 지원)
    │  결과를 JSON 파일로 저장
    ▼
빌드 결과 (stdout, stderr, exit_code) 반환
```

**엔드포인트:**
- `POST /api/build/execute` — 빌드 명령 실행
- `GET /api/build/history` — 빌드 이력 조회

### 4.8 설정 관리 (`/api/settings`)

- JSON 파일 기반 설정 CRUD
- 프론트엔드에서 설정 변경 가능

---

## 5. 프론트엔드 구조

### 5.1 Admin Platform (React + Vite + TypeScript)

| 페이지 | 파일 | 기능 |
|--------|------|------|
| Dashboard | `DashboardPage.tsx` | 시스템 상태 개요 |
| Chat | `ChatPage.tsx` | AI 대화 (스트리밍 지원) |
| RAG | `RagPage.tsx` | 문서 업로드 + 질의 |
| SQL | `SqlPage.tsx` | 자연어 → SQL 생성/실행 |
| Codegen | `CodegenPage.tsx` | 코드 생성 |
| Review | `ReviewPage.tsx` | 코드 리뷰 |
| Confluence | `ConfluencePage.tsx` | Confluence 동기화 |
| Build | `BuildPage.tsx` | 빌드/배포 |
| Settings | `SettingsPage.tsx` | 시스템 설정 |

**공통 컴포넌트:**
- `ChatInput.tsx` — 메시지 입력
- `ChatMessage.tsx` — 메시지 표시 (마크다운 렌더링)
- `CodeBlock.tsx` — 코드 구문 강조
- `FileUploader.tsx` — 파일 업로드
- `SqlResultTable.tsx` — SQL 결과 테이블
- `Sidebar.tsx` — 사이드바 네비게이션

### 5.2 Chat Widget (Vue.js)

- `ChatWidget.vue` — 사내 웹사이트에 임베드하는 채팅 위젯
- `index.js` — 위젯 초기화 스크립트
- iframe 또는 script 태그로 기존 사내 시스템에 삽입 가능

---

## 6. 기술 스택 요약

| 계층 | 기술 | 역할 |
|------|------|------|
| **Backend** | FastAPI + Python 3.11 | REST API 서버 |
| **LLM** | OpenAI SDK (호환) | LLM 호출 (OpenAI or GPT-OSS) |
| **Embedding** | BAAI/bge-m3 (sentence-transformers) | 문서/쿼리 임베딩 |
| **Vector DB** | ChromaDB | 벡터 저장/검색 |
| **Database** | SQLAlchemy + oracledb | Text-to-SQL 실행 |
| **문서처리** | pypdf, python-docx, openpyxl | PDF/DOCX/XLSX 파싱 |
| **Platform UI** | React + Vite + TypeScript | 관리 대시보드 |
| **Widget UI** | Vue.js | 사내 웹 임베드 채팅 |
| **인프라** | Docker Compose | 컨테이너 오케스트레이션 |

---

## 7. 디렉토리 구조

```
Product006_ClosedEnterpriseLLM/
│
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # FastAPI 앱 진입점
│   ├── config.py                 # 환경설정 (Pydantic Settings)
│   ├── llm_client.py             # LLM 호출 클라이언트
│   │
│   ├── core/                     # 핵심 모듈 (재사용 가능)
│   │   ├── vector_store.py       # ChromaDB + bge-m3 래퍼
│   │   ├── document_loader.py    # 멀티포맷 문서 로더
│   │   ├── conversation_store.py # 대화 히스토리 저장
│   │   └── prompts.py            # 시스템 프롬프트 모음
│   │
│   ├── routers/                  # API 엔드포인트 정의
│   │   ├── chat.py
│   │   ├── rag.py
│   │   ├── text2sql.py
│   │   ├── codegen.py
│   │   ├── confluence.py
│   │   ├── review.py
│   │   ├── build.py
│   │   └── settings.py
│   │
│   ├── services/                 # 비즈니스 로직
│   │   ├── chat_service.py
│   │   ├── rag_service.py
│   │   ├── text2sql_service.py
│   │   ├── codegen_service.py
│   │   ├── confluence_service.py
│   │   ├── review_service.py
│   │   ├── build_service.py
│   │   └── settings_service.py
│   │
│   └── connectors/               # 외부 시스템 연동
│       └── confluence.py         # Confluence REST API 클라이언트
│
├── platform/                     # Admin UI (React + Vite)
│   └── src/
│       ├── pages/                # 페이지별 컴포넌트
│       ├── components/           # 공통 UI 컴포넌트
│       ├── lib/api.ts            # API 클라이언트
│       └── layouts/              # 레이아웃
│
├── widget/                       # 채팅 위젯 (Vue.js)
│   └── src/
│       ├── ChatWidget.vue
│       └── index.js
│
├── models/embedding/             # bge-m3 임베딩 모델 (로컬)
├── scripts/                      # 설치/배포 스크립트
├── docs/                         # 문서
│
├── docker-compose.yml            # 개발용 Docker 구성
├── docker-compose.airgap.yml     # 폐쇄망용 Docker 구성
├── requirements.txt              # Python 의존성
├── .env.example                  # 환경변수 템플릿
└── CLAUDE.md                     # AI 작업 가이드
```

---

## 8. 데이터 흐름 전체 요약

```
사용자 → 브라우저(Platform/Widget)
            │
            ▼ HTTP
        FastAPI Router
            │
            ▼
        Service Layer ──────────────────┐
            │           │               │
            ▼           ▼               ▼
      LLM Client    VectorStore    DB Connector
      (OpenAI SDK)  (ChromaDB)    (SQLAlchemy)
            │           │               │
            ▼           ▼               ▼
      OpenAI/GPT-OSS  ChromaDB      Oracle DB
                     + bge-m3
```

**모든 AI 호출은 `llm_client.chat_completion()` 한 함수를 통과.**
**모든 벡터 연산은 `VectorStore` 한 클래스를 통과.**
**Deterministic Backbone**: SQL 안전검증, 파일 파싱, 청킹은 코드로 처리. AI는 생성/분석만 담당.

---

## 9. 빠진 것/확인 필요 사항

| 항목 | 상태 | 비고 |
|------|------|------|
| Backend (FastAPI) | ✅ 완성 | 8개 라우터, 8개 서비스 |
| LLM Client | ✅ 완성 | OpenAI/GPT-OSS 호환 |
| Embedding (bge-m3) | ✅ 모델 파일 준비됨 | 4.3GB, 오프라인 패키지 포함 |
| Vector Store (ChromaDB) | ✅ 완성 | Docker/로컬 모드 지원 |
| Document Loader | ✅ 완성 | PDF, DOCX, XLSX, 코드, 텍스트 |
| RAG Pipeline | ✅ 완성 | 업로드→청킹→임베딩→검색→답변 |
| Text-to-SQL | ✅ 완성 | SELECT-only 안전장치 포함 |
| Confluence 연동 | ✅ 완성 | 변경 감지 포함 |
| Admin Platform UI | ✅ 완성 | 9개 페이지 |
| Chat Widget | ✅ 완성 | Vue.js 임베드 위젯 |
| 오프라인 패키지 | ✅ 빌드 완료 | Linux + Windows |
| Docker Compose | ✅ 있음 | dev + airgap 구성 |
| **실 서버 테스트** | ❌ 미완료 | 로컬에서 서버 기동 테스트 필요 |
| **DB 스키마 등록** | ⚠️ 수동 | 폐쇄망에서 Oracle 스키마 등록 필요 |
| **Confluence 인증** | ⚠️ 환경별 | 폐쇄망 Confluence URL/토큰 필요 |
| **GPT-OSS 엔드포인트** | ⚠️ 환경별 | 폐쇄망 LLM 서버 주소 확인 필요 |

---

## 10. 로컬 테스트 순서

```bash
# 1. .env 설정
cp .env.example .env
# .env에서 LLM_API_KEY 설정, CHROMA_PORT=0 (로컬 모드)

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 백엔드 서버 시작
uvicorn app.main:app --reload --port 8000

# 4. 헬스체크
curl http://localhost:8000/health

# 5. 프론트엔드 (별도 터미널)
cd platform && npm run dev

# 6. 테스트
# - 브라우저에서 http://localhost:5173 접속
# - Chat 탭에서 대화 테스트
# - RAG 탭에서 문서 업로드 → 질의 테스트
```

---
