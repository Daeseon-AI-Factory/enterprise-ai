# Enterprise LLM Platform — 전체 아키텍처 개요

> **발표용 문서** | 작성일: 2026-03-18 | 작성자: Jason

---

## 1. 한 줄 요약

> "자연어로 질문하면, 사내 문서와 실제 DB 데이터를 동시에 검색해서 LLM이 답변한다."

---

## 2. 시스템 구성 전체 그림

```
┌─────────────────────────────────────────────────────────────────────┐
│                        사용자 (브라우저)                              │
│                    http://localhost:3000                              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Enterprise LLM Platform (Product006)                    │
│                   FastAPI  |  port 8080                              │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │
│  │  Chat    │  │   RAG    │  │Text-to   │  │  통합 진단        │    │
│  │ (대화)   │  │(문서검색)│  │  SQL     │  │ /api/analyze      │    │
│  └──────────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘    │
│                     │             │                  │              │
└─────────────────────┼─────────────┼──────────────────┼─────────────┘
                      │             │                  │
          ┌───────────┘    ┌────────┘         ┌────────┘
          ▼                ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐
│  ChromaDB    │  │  Oracle XE   │  │          LLM API              │
│ (벡터 DB)    │  │  (XEPDB1)    │  │  OpenAI / 로컬 모델 선택 가능 │
│ port 8100    │  │  port 1521   │  │                               │
│              │  │              │  │  gpt-4o-mini (기본값)         │
│ - 문서 청크  │  │ MESADMIN 스키마│  │  또는 사내 폐쇄망 모델        │
│ - 코드 청크  │  │ - 생산 데이터 │  └──────────────────────────────┘
│ - 매뉴얼    │  │ - 재고 데이터 │
└──────────────┘  │ - 불량 데이터 │
                  └──────────────┘
                        ▲
                        │ Oracle에 실제 데이터 존재
                  ┌─────┴──────┐
                  │ SampleMESWMS│
                  │ MES/WMS 앱  │
                  │ port 8090   │
                  │ port 3100   │
                  └─────────────┘
```

---

## 3. 핵심 컴포넌트 설명

### 3-1. Enterprise LLM Platform (Product006)

| 컴포넌트 | 역할 | 기술 |
|---------|------|------|
| FastAPI 백엔드 | 모든 AI 기능의 API 서버 | Python 3.11 |
| React 프론트엔드 | 사용자 UI (채팅, RAG, SQL, 분석) | React 18 + Vite + Tailwind |
| ChromaDB | 문서/코드의 벡터 검색 DB | HTTP 클라이언트 모드 |
| LLM Client | OpenAI 호환 API 통합 | openai SDK |
| JWT Auth | 로그인/토큰 인증 | python-jose + bcrypt |

### 3-2. SampleMESWMS (연동 대상 시스템)

| 컴포넌트 | 역할 | 기술 |
|---------|------|------|
| Oracle XE 21c | 실제 MES/WMS 데이터 저장소 | Docker (gvenzl/oracle-xe:21-slim) |
| FastAPI 백엔드 | MES/WMS REST API | Python + python-oracledb |
| React 프론트엔드 | MES/WMS 대시보드 UI | React 18 + Recharts |

---

## 4. 데이터 흐름 — 3가지 경로

### 경로 A: RAG (문서/코드 기반 답변)

```
사용자: "배터리셀 생산 공정 코드 어떻게 되어 있어?"
         │
         ▼
    [1] 질문을 벡터(숫자)로 변환
        (SentenceTransformer 임베딩 모델)
         │
         ▼
    [2] ChromaDB에서 유사 문서 검색
        - Dense Search (의미 기반)
        - BM25 Search (키워드 기반)
        - RRF 알고리즘으로 두 결과 병합
        - Bi-encoder로 최종 재순위
         │
         ▼
    [3] 상위 5개 관련 청크 추출
        예) "wms.py:83 — 배터리셀 BC-500 출고 처리..."
         │
         ▼
    [4] LLM에 전달: 질문 + 관련 문서 컨텍스트
         │
         ▼
    [5] LLM이 문서 기반으로 답변 생성
```

**RAG에 색인할 수 있는 소스:**
- Git 저장소 소스코드 (`/api/git/index`)
- Confluence 문서 (`/api/confluence/sync`)
- 직접 파일 업로드 (`/api/rag/upload`)

---

### 경로 B: Text-to-SQL (DB 데이터 기반 답변)

```
사용자: "A라인 이번달 불량률이 얼마야?"
         │
         ▼
    [1] 등록된 Oracle 스키마 로드
        (PRODUCTION_ORDERS, DEFECTS, PRODUCTION_LINES 테이블 구조)
         │
         ▼
    [2] LLM이 자연어 → SQL 변환
        ┌─────────────────────────────────────┐
        │ SELECT L.LINE_NAME,                  │
        │   ROUND(SUM(D.DEFECT_QTY) /          │
        │   NULLIF(SUM(W.GOOD_QTY+D.DEFECT_QTY),0)*100,2) │
        │ FROM MESADMIN.DEFECTS D              │
        │ JOIN ...                             │
        │ WHERE L.LINE_ID = 'L001'             │
        │   AND TRUNC(D.DETECTED_AT,'MM') = .. │
        └─────────────────────────────────────┘
         │
         ▼
    [3] Oracle XE(XEPDB1)에 SQL 실행
        → 실제 결과: [{"LINE_NAME":"A라인", "DEFECT_RATE":6.77}]
         │
         ▼
    [4] LLM이 결과를 자연어로 설명
        "A라인의 이번달 불량률은 6.77%로, 전월 대비 3%p 상승했습니다."
```

---

### 경로 C: 통합 진단 (RAG + SQL 동시 실행) ← 핵심 기능

```
사용자: "A라인 불량이 왜 2월부터 급증했는지 분석해줘"
         │
         ├──────────────────┬────────────────────
         ▼                  ▼
    [RAG 실행]          [Text-to-SQL 실행]
    관련 문서 검색       SQL 생성 → Oracle 조회
    - 설비 점검 기록     - 라인별 월별 불량률 추이
    - 공정 매뉴얼        - 설비 OEE 데이터
    - 과거 불량 분석서   - 작업자별 불량 현황
         │                  │
         └────────┬──────────┘
                  ▼
    [최종 LLM 호출]
    System: "당신은 기업 데이터 분석 전문가입니다"
    Context:
      [문서 지식]
        - 설비 E001(SMT 마운터 #1) 3월 정비 예정 초과...
        - 납땜 페이스트 교체 주기 가이드라인...
      [DB 실제 데이터]
        - 1월 불량률: 2.3%, 2월 불량률: 5.8%, 3월 불량률: 6.77%
        - 납땜불량 유형이 전체의 42% 차지
    Question: "A라인 불량이 왜 2월부터 급증했는지 분석해줘"
         │
         ▼
    종합 답변:
    "문서와 데이터를 종합하면, A라인 불량 급증의 주요 원인은
     SMT 마운터 E001의 정비 주기 초과(마지막 정비: 2025-12-01)와
     납땜 페이스트 교체 지연으로 판단됩니다.
     실제 데이터에서 납땜불량이 42%로 가장 높으며..."
```

---

## 5. RAG 검색 알고리즘 상세

### 왜 단순 벡터 검색이 아닌가?

| 방식 | 장점 | 단점 |
|------|------|------|
| Dense Search만 | 의미적 유사성 포착 | 정확한 키워드 놓침 |
| BM25만 | 키워드 정확 매칭 | 의미 파악 못함 |
| **Hybrid (현재 방식)** | 두 장점 결합 | 구현 복잡 |

### Hybrid 검색 파이프라인

```
질문
 │
 ├─► Dense Search (ChromaDB)  → Top 15개 후보
 │   (SentenceTransformer 임베딩)
 │
 ├─► BM25 Search              → Top 15개 후보
 │   (TF-IDF 기반 키워드)
 │
 └─► RRF 병합 (Reciprocal Rank Fusion, k=60)
      각 후보의 순위를 역수로 합산
       │
       ▼
     Bi-encoder 재순위 (코사인 유사도)
       │
       ▼
     최종 Top 5 반환
```

---

## 6. 색인(Index) 구조

### 어떤 데이터가 ChromaDB에 들어가는가

```
ChromaDB Collection 구조:

git_SampleMESWMS (컬렉션명)
├── chunk_001: "def wms_dashboard(): ..." (wms.py 1-50번 줄)
├── chunk_002: "class Inventory(Base): ..." (models.py)
├── chunk_003: "INSERT INTO DEFECTS ..." (02_data.sql)
└── ...

confluence_engineering (컬렉션명)
├── chunk_001: "설비 점검 절차서 — SMT 마운터..."
├── chunk_002: "불량 처리 가이드라인..."
└── ...

rag_documents (컬렉션명)
├── chunk_001: "MES 운영 매뉴얼 3장..."
└── ...
```

### 청킹(Chunking) 방식

- **단위**: 1000줄 / 오버랩 100줄
- **메타데이터**: 파일경로, 언어, 청크 번호, doc_id
- **지원 언어**: .py, .ts, .tsx, .js, .java, .cs, .go, .sql, .md 등 20종

---

## 7. Oracle 연동 상세

### SampleMESWMS 데이터베이스 구조

```
Oracle XE 21c (Docker)
└── XEPDB1 (PDB — 실제 접속 대상)
    └── MESADMIN (스키마)
        │
        ├── [MES 테이블]
        │   ├── PRODUCTION_LINES  — 생산라인 (L001~L005)
        │   ├── PRODUCTS          — 제품 마스터 (P001~P008)
        │   ├── PRODUCTION_ORDERS — 생산 지시 (90일치)
        │   ├── WORK_RESULTS      — 작업 실적 (교대별)
        │   ├── DEFECTS           — 불량 내역
        │   └── EQUIPMENT         — 설비 현황 (E001~E011)
        │
        └── [WMS 테이블]
            ├── WAREHOUSES        — 창고 (WH01~WH05)
            ├── ITEMS             — 품목 마스터 (원자재+완제품)
            ├── INVENTORY         — 현재 재고
            ├── INBOUND           — 입고 이력 (60일치)
            └── OUTBOUND          — 출고 이력 (60일치)
```

### LLM Platform → Oracle 연결 방식

```
LLM Platform (.env 설정)
  DB_TYPE=oracle
  DB_HOST=localhost
  DB_PORT=1521
  DB_NAME=XEPDB1       ← PDB Service Name
  DB_USER=MESADMIN
  DB_PASSWORD=mesadmin123

Text-to-SQL 서비스
  1. 스키마 등록: /api/text2sql/schema/discover
     → Oracle에서 테이블/컬럼 자동 추출
     → JSON으로 저장 (./data/schemas/{id}.json)

  2. SQL 생성: /api/text2sql/generate
     → 저장된 스키마 + 질문 → LLM → SQL

  3. SQL 실행: /api/text2sql/execute
     → python-oracledb (thin mode, Oracle Client 불필요)
     → oracle+oracledb://user:pass@host:1521/?service_name=XEPDB1
```

---

## 8. 시스템 구동 순서

```bash
# 1. SampleMESWMS Oracle DB + 앱 실행
cd C:/Sources/SampleMESWMS
docker compose up -d
# → Oracle XE (port 1521), MES Backend (port 8090), Frontend (port 3100)

# 2. Enterprise LLM Platform 실행
cd C:/Sources/Product006_ClosedEnterpriseLLM
docker compose up -d   # 또는 로컬 실행
# → LLM Backend (port 8080), ChromaDB (port 8100), Frontend (port 3000)

# 3. LLM Platform에서 스키마 등록
# http://localhost:3000 → SQL 메뉴 → DB 연결/스키마 탐색 → 저장

# 4. Git 소스 색인
# http://localhost:3000 → Git 메뉴 → C:/Sources/SampleMESWMS → 색인 시작

# 5. 통합 진단 사용
# http://localhost:3000 → 통합 진단 메뉴 → 자연어 질문
```

---

## 9. 포트 정리

| 서비스 | 포트 | 설명 |
|--------|------|------|
| LLM Platform 프론트엔드 | 3000 | React UI |
| MES/WMS 프론트엔드 | 3100 | React UI |
| LLM Platform 백엔드 | 8080 | FastAPI |
| MES/WMS 백엔드 | 8090 | FastAPI |
| ChromaDB | 8100 | 벡터 DB |
| Oracle XE | 1521 | Oracle DB |

---

## 10. 기술 스택 요약

### Backend
| 기술 | 용도 |
|------|------|
| Python 3.11 + FastAPI | API 서버 |
| python-oracledb (thin) | Oracle 연결 (클라이언트 설치 불필요) |
| SQLAlchemy 2.x | ORM / 쿼리 실행 |
| openai SDK | LLM API 호출 |
| sentence-transformers | 텍스트 임베딩 |
| chromadb | 벡터 검색 |
| rank-bm25 | 키워드 검색 |
| python-jose + bcrypt | JWT 인증 |
| GitPython | Git 저장소 처리 |

### Frontend
| 기술 | 용도 |
|------|------|
| React 18 + TypeScript | UI |
| Vite | 빌드 도구 |
| Tailwind CSS | 스타일 |
| Recharts | 차트 (MES/WMS 대시보드) |
| axios | HTTP 클라이언트 |

### Infrastructure
| 기술 | 용도 |
|------|------|
| Docker + Docker Compose | 컨테이너 실행 |
| Oracle XE 21c | MES/WMS 데이터 |
| gvenzl/oracle-xe:21-slim | Oracle Docker 이미지 |
