# 폐쇄망 Enterprise AI 완전 활용 가이드

> 마지막 업데이트: 2026-03-13
> 작성: Jason + Claude

이 문서는 폐쇄망에서 AI를 **제대로** 쓰기 위한 전체 방법론을 다룬다.
RAG만이 AI가 아니다. 현재 플랫폼이 지원하는 것과, 추가로 가능한 것 전부를 정리한다.

---

## 목차

1. [현재 플랫폼 아키텍처 요약](#1-현재-플랫폼-아키텍처-요약)
2. [AI 활용 레벨 — 지금 할 수 있는 것 vs 확장 가능한 것](#2-ai-활용-레벨)
3. [Level 1: 기본 채팅 (완성)](#3-level-1-기본-채팅)
4. [Level 2: RAG — 사내 문서 기반 Q&A (완성)](#4-level-2-rag)
5. [Level 3: Text2SQL — 자연어로 DB 조회 (완성)](#5-level-3-text2sql)
6. [Level 4: 코드 생성 + 리뷰 (완성)](#6-level-4-코드-생성--리뷰)
7. [Level 5: Confluence 자동 동기화 (완성)](#7-level-5-confluence-자동-동기화)
8. [Level 6: AI Agent — 자율 작업 수행 (미구현, 확장)](#8-level-6-ai-agent)
9. [Level 7: Function Calling — LLM이 도구 사용 (미구현, 확장)](#9-level-7-function-calling)
10. [Level 8: Fine-tuning — 사내 데이터로 모델 커스텀 (미구현, 확장)](#10-level-8-fine-tuning)
11. [Level 9: Workflow Automation — n8n 연동 (부분 구현)](#11-level-9-workflow-automation)
12. [Level 10: Multi-Modal — 이미지/음성 처리 (미구현, 확장)](#12-level-10-multi-modal)
13. [데이터 투입 전체 방법 정리](#13-데이터-투입-전체-방법)
14. [프롬프트 엔지니어링 가이드](#14-프롬프트-엔지니어링-가이드)
15. [보안 고려사항](#15-보안-고려사항)
16. [로컬 테스트 → 폐쇄망 배포 프로세스](#16-배포-프로세스)

---

## 1. 현재 플랫폼 아키텍처 요약

```
┌─────────────────────────────────────────────────────────┐
│                    사용자 브라우저                         │
│  ┌───────────┐    ┌──────────────────────────────────┐  │
│  │Chat Widget│    │  Platform (관리 대시보드, React)    │  │
│  └─────┬─────┘    └───────────────┬──────────────────┘  │
└────────┼──────────────────────────┼─────────────────────┘
         └────────────┬─────────────┘
                      ▼
         ┌────────────────────────┐
         │  FastAPI Backend :8080 │
         │  8개 API 모듈           │
         └─────┬──────┬──────┬───┘
               │      │      │
          ┌────┘      │      └────┐
          ▼           ▼           ▼
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ LLM 서버  │ │ ChromaDB │ │ Oracle   │
    │ GPT-OSS  │ │ 벡터 DB   │ │ 업무 DB  │
    │ :8000    │ │ :8100    │ │ :1521    │
    └──────────┘ └──────────┘ └──────────┘
```

**핵심 구성요소:**
- **LLM**: OpenAI SDK 호환 → `base_url`만 바꾸면 OpenAI/GPT-OSS/vLLM/Ollama 전환
- **Embedding**: BAAI/bge-m3 (한국어 최고 수준, 로컬 파일 4.3GB)
- **Vector DB**: ChromaDB (Docker 또는 로컬 파일)
- **업무 DB**: Oracle (Text2SQL용, SELECT만 허용)

---

## 2. AI 활용 레벨

| Level | 기능 | 현재 상태 | 난이도 |
|-------|------|----------|--------|
| 1 | 기본 채팅 | ✅ 완성 | - |
| 2 | RAG (문서 Q&A) | ✅ 완성 | - |
| 3 | Text2SQL (자연어→SQL) | ✅ 완성 | - |
| 4 | 코드 생성 + 리뷰 | ✅ 완성 | - |
| 5 | Confluence 동기화 | ✅ 완성 | - |
| 6 | AI Agent | ❌ 미구현 | 중 |
| 7 | Function Calling | ❌ 미구현 | 중 |
| 8 | Fine-tuning | ❌ 미구현 | 상 |
| 9 | Workflow (n8n) | ⚠️ Docker만 | 하 |
| 10 | Multi-Modal | ❌ 미구현 | 상 |

---

## 3. Level 1: 기본 채팅

### 뭘 할 수 있나?
- 일반 대화, 번역, 요약, 설명
- 멀티턴 대화 (이전 대화 기억)
- SSE 스트리밍 (실시간 타이핑 효과)

### API
```
POST /api/chat          → 일반 대화
POST /api/chat/stream   → 스트리밍 대화
POST /api/chat/with-context → 페이지 컨텍스트 포함 (위젯)
```

### 프로세스
```
사용자 메시지 → 대화 히스토리 로드 → 시스템 프롬프트 + 히스토리 + 메시지
    → LLM 호출 → 응답 저장 → 반환
```

### 제한
- LLM의 학습 데이터까지만 답변 가능 (사내 정보 모름)
- → Level 2 RAG로 해결

---

## 4. Level 2: RAG

### 뭘 할 수 있나?
- 사내 문서(PDF, Word, Excel, 코드)를 업로드
- 업로드한 문서를 기반으로 질문/답변
- 출처(어떤 문서의 어떤 부분)까지 표시

### 데이터 투입 방법
```
POST /api/rag/upload (파일 업로드)
    → DocumentLoader (텍스트 추출)
        → 청킹 (1000자, 200자 오버랩)
            → bge-m3 임베딩 (1024차원 벡터)
                → ChromaDB 저장
```

### 질의 프로세스
```
질문 → bge-m3 임베딩 → ChromaDB 코사인 유사도 검색 → top-5 청크
    → "이 문서만 보고 답변하라" 시스템 프롬프트 + 청크 + 질문
        → LLM 답변 생성 → 출처와 함께 반환
```

### 지원 파일 형식
| 형식 | 처리 |
|------|------|
| PDF | pypdf (페이지별 텍스트) |
| Word (.docx) | python-docx (문단별) |
| Excel (.xlsx) | openpyxl (시트별, 행별) |
| 코드 (.py, .java, .js, .ts, .sql 등) | UTF-8 텍스트 |
| 텍스트 (.txt, .md, .csv) | UTF-8 텍스트 |

### 컬렉션 관리
- 문서를 그룹(컬렉션)별로 분류 가능
- 예: "HR문서", "개발가이드", "생산매뉴얼" 등
- 질의 시 특정 컬렉션만 검색 가능

### 현재 한계와 개선 방향
| 한계 | 개선 방향 |
|------|----------|
| 단순 문자 수 기준 청킹 | Semantic chunking (의미 단위 분할) |
| 키워드 검색 미지원 | Hybrid search (벡터 + BM25) |
| 리랭킹 없음 | Cross-encoder 리랭커 추가 |
| 대량 문서 배치 업로드 없음 | 폴더 단위 일괄 업로드 |

---

## 5. Level 3: Text2SQL

### 뭘 할 수 있나?
- 한국어/영어로 질문하면 SQL 자동 생성
- "이번 달 생산 실적 보여줘" → `SELECT ... FROM PRODUCTION_ORDER WHERE ...`
- 생성된 SQL을 사용자 확인 후 실행, 결과 테이블로 표시

### 사전 준비: DB 스키마 등록
```json
POST /api/text2sql/schema
{
    "schema_id": "mes_production",
    "description": "MES 생산관리 시스템",
    "tables": [
        {
            "name": "PRODUCTION_ORDER",
            "columns": [
                {"name": "ORDER_ID", "type": "NUMBER", "description": "주문번호"},
                {"name": "PRODUCT_CODE", "type": "VARCHAR2(50)", "description": "제품코드"},
                {"name": "QTY", "type": "NUMBER", "description": "수량"},
                {"name": "CREATED_DATE", "type": "DATE", "description": "생성일"}
            ]
        }
    ]
}
```

**중요: 스키마 정보를 상세히 등록할수록 SQL 정확도가 올라간다.**
컬럼 설명에 한국어로 비즈니스 의미를 적어야 LLM이 이해한다.

### 안전장치 (Deterministic Backbone)
- SELECT 문만 허용 (INSERT/UPDATE/DELETE/DROP 전부 차단)
- SQL 실행 전 반드시 사용자 확인 필요 (`confirmed: true`)
- DB 접속은 read-only 계정 사용 권장

### .env 설정
```bash
DB_TYPE=oracle
DB_HOST=10.x.x.x
DB_PORT=1521
DB_NAME=MESDB
DB_USER=readonly_user
DB_PASSWORD=your-password
```

---

## 6. Level 4: 코드 생성 + 리뷰

### 코드 생성
```json
POST /api/codegen/generate
{
    "prompt": "Oracle에서 일별 생산실적 집계하는 PL/SQL 프로시저",
    "language": "sql",
    "framework": "oracle",
    "project_id": "mes_project"  // 등록된 템플릿 참조
}
```

프로젝트 템플릿을 미리 등록하면 사내 코딩 컨벤션에 맞는 코드 생성:
```json
POST /api/codegen/templates
{
    "project_id": "mes_project",
    "tech_stack": "C# + Oracle + WinForms",
    "conventions": "- 변수명: camelCase\n- 메서드명: PascalCase\n- SQL은 대문자",
    "sample_code": "public class ProductionService { ... }"
}
```

### 코드 리뷰
```json
POST /api/review/code
{
    "code": "여기에 리뷰할 코드",
    "language": "python",
    "context": "MES 생산관리 시스템의 일배치 처리 로직"
}
```

분석 항목:
- 버그 & 로직 오류
- 보안 (SQL 인젝션, XSS 등)
- 성능 (N+1 쿼리, 불필요 할당 등)
- 가독성 (네이밍, 복잡도)
- 모범사례 (에러 핸들링, 리소스 정리)

### 엣지 케이스 분석
```json
POST /api/review/edge-cases
{
    "code": "여기에 분석할 코드",
    "language": "java"
}
```
- 입력 경계값 (빈 문자열, null, 0, 음수, 최대값)
- 컬렉션 (빈 리스트, 단일 요소, 중복)
- 동시성 (레이스 컨디션, 데드락)
- 외부 의존성 (네트워크 타임아웃, 디스크 풀)
- 비즈니스 로직 (날짜 경계, 타임존, 통화 반올림)

---

## 7. Level 5: Confluence 자동 동기화

### MCP 필요 없음
Confluence REST API를 직접 호출한다. MCP는 Claude Desktop용이지 서버 앱에선 불필요.

### 동기화 프로세스
```
POST /api/confluence/sync
    → Confluence REST API로 Space의 페이지 목록 가져옴
        → 각 페이지 HTML → BeautifulSoup → 텍스트 변환
            → MD5 해시로 변경 감지 (변경된 것만 처리)
                → 청킹 → 임베딩 → ChromaDB 저장
```

### 설정
```json
{
    "base_url": "https://company.atlassian.net/wiki",
    "username": "user@company.com",
    "api_token": "confluence-api-token",
    "space_key": "DEV",
    "collection": "confluence_dev",
    "labels": ["important"],
    "full_sync": false
}
```

### 폐쇄망에서 Confluence가 내부에 있으면
- `base_url`을 내부 URL로 변경하면 바로 동작
- 예: `http://confluence.internal:8090`

### 폐쇄망에서 Confluence가 외부에만 있으면
- Confluence에서 PDF로 Space 내보내기
- PDF 파일을 `/api/rag/upload`로 수동 업로드

---

## 8. Level 6: AI Agent (미구현, 확장)

### Agent란?
LLM이 **스스로 판단해서 여러 도구를 순차적으로 사용**하는 것.
현재는 사용자가 "문서 업로드 → RAG 질의"를 수동으로 하지만,
Agent는 "이 이슈 분석해줘"라고 하면 알아서:

1. 관련 문서 검색 (RAG)
2. DB 조회 (Text2SQL)
3. Confluence에서 추가 정보 수집
4. 종합 분석 보고서 작성

### 구현 방법 (향후)
```python
# Agent Loop (ReAct 패턴)
while not done:
    # 1. LLM에게 상황 설명 + 사용 가능한 도구 알려줌
    response = llm.chat(
        system="당신은 도구를 사용할 수 있는 AI 에이전트입니다.",
        tools=[
            {"name": "search_docs", "description": "문서 검색"},
            {"name": "query_db", "description": "DB 조회"},
            {"name": "search_confluence", "description": "Confluence 검색"},
        ],
        messages=conversation,
    )

    # 2. LLM이 도구 사용을 요청하면 실행
    if response.tool_calls:
        for tool_call in response.tool_calls:
            result = execute_tool(tool_call)
            conversation.append(tool_result(result))
    else:
        # 3. 최종 답변
        done = True
```

### 필요한 것
- GPT-OSS가 Function Calling / Tool Use를 지원해야 함
- 현재 코드에 Agent Loop 추가 (새 서비스 + 라우터)
- 예상 작업량: 2-3일

---

## 9. Level 7: Function Calling (미구현, 확장)

### Function Calling이란?
LLM이 "이 함수를 호출해달라"고 구조화된 요청을 보내는 것.
Agent의 핵심 기능이자, 현재 채팅을 더 똑똑하게 만드는 방법.

### 예시: 스마트 채팅
현재: 사용자가 수동으로 RAG 페이지 → SQL 페이지를 왔다갔다
Function Calling 적용 후:

```
사용자: "지난달 A라인 불량률 알려줘. 관련 SOP 문서도 찾아줘."

LLM 판단:
1. query_database("지난달 A라인 불량률") → SQL 실행 → 불량률 2.3%
2. search_documents("A라인 불량률 SOP") → RAG 검색 → 관련 문서 3건
3. 종합 답변 생성
```

### 필요한 것
- GPT-OSS의 Function Calling 지원 여부 확인 필요
- vLLM은 일부 모델에서 tool_use 지원
- 지원 안 되면 프롬프트 기반 파싱으로 대체 가능 (정확도 ↓)

---

## 10. Level 8: Fine-tuning (미구현, 확장)

### Fine-tuning이란?
LLM 자체를 사내 데이터로 추가 학습시키는 것.
RAG와 다른 점: RAG는 "검색 후 참고", Fine-tuning은 "모델이 직접 학습".

### 언제 필요한가?
| 상황 | RAG로 충분 | Fine-tuning 필요 |
|------|-----------|-----------------|
| 사내 문서 Q&A | ✅ | ❌ |
| 특수 용어/은어 이해 | △ | ✅ |
| 특정 답변 스타일/톤 | △ | ✅ |
| 반복적 패턴 작업 | △ | ✅ |
| 도메인 전문 판단 | ❌ | ✅ |

### RAG vs Fine-tuning 판단 기준
```
"검색하면 찾을 수 있는 정보인가?"
    → YES: RAG로 충분
    → NO: Fine-tuning 검토

"모델의 행동/스타일을 바꿔야 하나?"
    → YES: Fine-tuning
    → NO: 프롬프트 엔지니어링으로 충분할 수 있음
```

### 폐쇄망에서 Fine-tuning 방법
1. **LoRA/QLoRA** — GPU 1~2장으로 가능, 가장 현실적
2. **Full Fine-tuning** — GPU 클러스터 필요, 비현실적
3. 학습 데이터: 사내 문서를 Q&A 쌍으로 가공 필요

### 필요한 인프라
- GPU 서버 (최소 A100 40GB 1장, 권장 2장)
- 학습 프레임워크: Hugging Face Transformers + PEFT
- 학습 데이터: 최소 1,000개 이상의 Q&A 쌍

---

## 11. Level 9: Workflow Automation (n8n)

### n8n이란?
코드 없이 워크플로우를 만드는 자동화 도구. Docker Compose에 이미 포함.

### 활용 예시
```
[매일 아침 9시]
    → Confluence 변경 페이지 감지
        → 변경된 페이지 자동 RAG 인덱싱
            → 슬랙/메일로 "새 문서 3건 인덱싱 완료" 알림

[JIRA 이슈 생성 시]
    → 이슈 내용을 RAG로 검색
        → 관련 문서/코드 자동 댓글 추가

[빌드 실패 시]
    → 에러 로그를 LLM에 전달
        → 원인 분석 + 해결 방안 제시
```

### 접근 방법
```
http://localhost:5678  (n8n 대시보드)
```

n8n에서 FastAPI의 API를 HTTP 노드로 호출하면 됨.

---

## 12. Level 10: Multi-Modal (미구현, 확장)

### 가능한 것들
| 기능 | 설명 | 필요한 것 |
|------|------|----------|
| 이미지 분석 | 설비 사진 → 불량 판정 | Vision 모델 (GPT-4V 또는 LLaVA) |
| 도면 이해 | CAD 도면 → 부품 목록 추출 | Vision 모델 + OCR |
| 음성 입력 | 음성 → 텍스트 → AI 답변 | Whisper 모델 (로컬 가능) |
| OCR | 스캔 문서 → 텍스트 추출 → RAG | Tesseract 또는 PaddleOCR |

### 가장 현실적인 확장: OCR → RAG
```
스캔된 PDF/이미지 → PaddleOCR (한국어 지원) → 텍스트 추출
    → DocumentLoader → 청킹 → 임베딩 → ChromaDB
```
스캔 문서가 많은 제조업 환경에서 매우 유용.

---

## 13. 데이터 투입 전체 방법

### 정리표

| 데이터 소스 | 투입 방법 | API | 자동화 |
|------------|----------|-----|--------|
| PDF/Word/Excel | 파일 업로드 | `POST /api/rag/upload` | 수동 (n8n으로 자동화 가능) |
| 코드 파일 | 파일 업로드 | `POST /api/rag/upload` | 수동 |
| Confluence | Space 동기화 | `POST /api/confluence/sync` | 반자동 (변경분만) |
| DB 스키마 | JSON 등록 | `POST /api/text2sql/schema` | 수동 (1회) |
| 프로젝트 템플릿 | JSON 등록 | `POST /api/codegen/templates` | 수동 (1회) |
| 설정값 | JSON 저장 | `PUT /api/settings` | 수동 |

### DB 정보는 어떻게 넣나?

**Text2SQL용 (Oracle 등):**
1. `.env`에 DB 접속 정보 설정
2. `POST /api/text2sql/schema`로 테이블/컬럼 정보 등록
3. LLM이 스키마 보고 SQL 생성 → 사용자 확인 → 실행

**RAG에 DB 내용을 넣으려면:**
- DB에서 데이터 추출 → CSV/Excel로 저장 → `/api/rag/upload`로 업로드
- 또는 커스텀 스크립트로 DB → 텍스트 변환 → VectorStore에 직접 저장

### Confluence는 MCP 없이 가능
현재 코드가 Confluence REST API를 직접 호출함. MCP 불필요.

---

## 14. 프롬프트 엔지니어링 가이드

### 현재 시스템 프롬프트 (`app/core/prompts.py`)

| 프롬프트 | 용도 | 주요 규칙 |
|---------|------|----------|
| SYSTEM_CHAT | 일반 채팅 | 한/영 자동 전환, 간결하고 전문적 |
| SYSTEM_RAG | 문서 Q&A | 제공된 컨텍스트만 사용, 출처 인용 |
| SYSTEM_TEXT2SQL | SQL 생성 | SELECT만, Oracle 문법, 주석 포함 |
| SYSTEM_CODEGEN | 코드 생성 | 타입 힌트, 에러 핸들링, 완전한 코드 |
| SYSTEM_CODE_REVIEW | 코드 리뷰 | 라인 번호 참조, 심각도 표시 |
| SYSTEM_EDGE_CASE | 엣지 케이스 | 카테고리별 분석, 우선순위 표시 |

### 프롬프트 커스텀 방법
`app/core/prompts.py`를 수정하면 LLM의 답변 스타일을 바꿀 수 있음.

예시 — MES 전문 채팅봇으로 바꾸기:
```python
SYSTEM_CHAT = """당신은 SK AX MES/WMS 시스템 전문 AI 어시스턴트입니다.

전문 분야:
- 생산 실행 시스템 (MES) 운영 및 트러블슈팅
- 창고 관리 시스템 (WMS) 프로세스
- Oracle DB 쿼리 최적화
- C#/Java 레거시 코드 분석

규칙:
- 제조 도메인 용어를 정확히 사용하라
- SQL은 Oracle 문법으로 작성하라
- 코드 예시는 회사 컨벤션을 따르라
- 모르면 모른다고 하라
"""
```

### 프롬프트 설계 원칙
1. **역할 정의**: "당신은 ___입니다" 로 시작
2. **규칙 나열**: 반드시 지켜야 할 것들 bullet point로
3. **출력 형식**: 원하는 답변 구조 명시
4. **제약**: 하지 말아야 할 것 명시
5. **언어 규칙**: 한국어/영어 전환 기준

---

## 15. 보안 고려사항

### Deterministic Backbone 원칙
AI가 판단하는 부분과 코드가 확정하는 부분을 엄격히 분리:

| 항목 | 처리 | 이유 |
|------|------|------|
| SQL 안전 검증 | 코드 (규칙 기반) | AI가 "이건 안전합니다" 판단 불가 |
| 파일 형식 파싱 | 코드 (라이브러리) | 확정적 결과 필요 |
| 텍스트 청킹 | 코드 (문자 수 기준) | 일관성 필요 |
| 답변 생성 | AI (LLM) | 창의성/판단 필요 |
| SQL 생성 | AI (LLM) | 자연어 이해 필요 |
| 코드 리뷰 | AI (LLM) | 맥락 이해 필요 |

### 접근 제어
- Text2SQL: **read-only DB 계정** 사용 필수
- 빌드/배포: 명령 실행 권한 관리 필요
- 설정: `.env` 파일에 민감 정보, git에 커밋 금지
- Confluence: API 토큰은 Settings에 저장 (평문 — 향후 암호화 필요)

### 데이터 유출 방지
- 폐쇄망이므로 외부 전송 불가
- LLM 서버가 내부에 있으므로 데이터가 외부로 나가지 않음
- ChromaDB 데이터도 로컬 저장

---

## 16. 배포 프로세스

### Step 1: 로컬 테스트 (인터넷 환경)
```bash
# .env 설정
cp .env.example .env
# LLM_API_KEY에 OpenAI 키 입력
# CHROMA_PORT=0 (로컬 모드, Docker 없이)

# Python 의존성
pip install -r requirements.txt

# 백엔드 시작
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# 프론트엔드 (별도 터미널)
cd platform && npm run dev

# 테스트
# http://localhost:8080/health  → 헬스체크
# http://localhost:8080/docs    → Swagger API 문서
# http://localhost:3000         → Platform UI
```

### Step 2: 오프라인 패키지 전송
```
_offline_build/enterprise-llm-offline-linux/   → Linux 폐쇄망
_offline_build/enterprise-llm-offline-windows/  → Windows 폐쇄망
```
USB, 망간전송, 또는 VDI 드라이브 공유로 전달.

### Step 3: 폐쇄망 설치
Linux:
```bash
sudo bash install.sh
```

Windows:
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

### Step 4: 환경 설정
```bash
# .env 수정
MODE=airgap
LLM_API_BASE=http://[GPT-OSS 서버 IP]:8000/v1
LLM_API_KEY=not-needed
LLM_MODEL=gpt-oss-120b
EMBEDDING_MODEL_PATH=./models/embedding
CHROMA_HOST=localhost
CHROMA_PORT=0
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1

# DB (Text2SQL 사용 시)
DB_TYPE=oracle
DB_HOST=[Oracle 서버 IP]
DB_PORT=1521
DB_NAME=MESDB
DB_USER=readonly_user
DB_PASSWORD=[비밀번호]
```

### Step 5: 서비스 시작
```bash
# Docker 있으면
docker compose -f docker-compose.airgap.yml up -d

# Docker 없으면 (직접 실행)
uvicorn app.main:app --host 0.0.0.0 --port 8080
cd platform && npm run build && npx serve -s dist -l 3000
```

### Step 6: 데이터 투입
1. Platform UI에서 문서 업로드 (RAG)
2. DB 스키마 등록 (Text2SQL)
3. Confluence 동기화 (연결 가능한 경우)
4. 프로젝트 템플릿 등록 (Codegen)

---

## 부록: 기능 확장 우선순위 제안

| 순위 | 기능 | 이유 | 난이도 | 예상 기간 |
|------|------|------|--------|----------|
| 1 | Hybrid Search (벡터+키워드) | RAG 정확도 대폭 향상 | 하 | 1일 |
| 2 | 폴더 일괄 업로드 | 대량 문서 투입 | 하 | 0.5일 |
| 3 | OCR (PaddleOCR) | 스캔 문서 처리 | 중 | 1-2일 |
| 4 | Function Calling | 스마트 채팅 | 중 | 2-3일 |
| 5 | AI Agent | 자율 작업 수행 | 중 | 3-5일 |
| 6 | Whisper (음성 입력) | 현장 활용도 | 중 | 1-2일 |
| 7 | Fine-tuning 파이프라인 | 도메인 특화 | 상 | 1-2주 |
