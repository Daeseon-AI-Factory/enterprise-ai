# Enterprise LLM Platform — 파이프라인 레이어 상세 문서

> 마지막 업데이트: 2026-03-13

이 문서는 플랫폼의 **모든 데이터 처리 파이프라인**을 레이어 단위로 분해하여 설명한다.
각 레이어가 무엇을 하는지, 어디서 처리하는지, 어떤 설정이 영향을 미치는지, 현재 한계와 개선 방향까지 포함한다.

---

## 전체 레이어 맵 (16 Layers)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          사용자 요청                                 │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 1: Ingestion (데이터 수집)                                    │
│  파일 업로드 / Confluence API / OCR / 음성 / DB 스키마               │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 2: Extraction (텍스트 추출)                                   │
│  PDF → pypdf / Word → python-docx / Excel → openpyxl / HTML → BS4  │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 3: Preprocessing (전처리)                                     │
│  인코딩 정규화 / 특수문자 처리 / 공백 정리 / 메타데이터 추출          │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 4: Chunking (청킹)                                           │
│  텍스트를 검색 가능한 단위로 분할                                    │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 5: Embedding (임베딩)                                        │
│  텍스트 → 1024차원 벡터 변환 (bge-m3)                               │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 6: Indexing (인덱싱)                                         │
│  벡터 + 메타데이터를 ChromaDB에 저장                                 │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
  ═══════════════════════════  저장 완료  ═══════════════════════════
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 7: Query Understanding (질의 이해)                            │
│  사용자 질문 파싱 / 의도 분류 / 도구 선택                            │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 8: Retrieval (검색)                                          │
│  질문 임베딩 → 벡터 유사도 검색 → top-k 후보 반환                    │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 9: Reranking (재순위화) ← 현재 미구현                        │
│  후보 문서를 Cross-encoder로 재정렬하여 정확도 향상                   │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 10: Context Assembly (컨텍스트 조립)                          │
│  검색된 청크들을 LLM 입력용으로 조합                                 │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 11: Prompt Engineering (프롬프트 구성)                        │
│  시스템 프롬프트 + 컨텍스트 + 히스토리 + 질문 조합                   │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 12: LLM Inference (모델 추론)                                │
│  OpenAI SDK → GPT-4o / GPT-OSS / vLLM 등                           │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 13: Tool Execution (도구 실행) — Agent/Function Calling      │
│  LLM이 요청한 도구 실행 → 결과를 다시 LLM에 전달                    │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 14: Post-processing (후처리)                                 │
│  응답 정제 / 출처 매핑 / 포맷 변환 / 안전성 검증                     │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 15: Response Delivery (응답 전달)                             │
│  일반 JSON / SSE 스트리밍 / 에러 핸들링                              │
└─────────────┬───────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Layer 16: Persistence & Feedback (영속화 & 피드백)                  │
│  대화 저장 / 빌드 이력 / 스케줄 상태 / 학습 데이터 수집              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Ingestion (데이터 수집)

### 역할
외부 소스에서 원본 데이터를 시스템 안으로 가져오는 첫 단계.

### 수집 경로

| 소스 | API | 처리 서비스 | 파일 저장 위치 |
|------|-----|-----------|--------------|
| 파일 업로드 (PDF/Word/Excel/코드) | `POST /api/rag/upload` | `RagService` | `./uploads/{uuid}_{filename}` |
| Confluence 위키 | `POST /api/confluence/sync` | `ConfluenceService` | 메모리 (직접 ChromaDB로) |
| 이미지/스캔 문서 (OCR) | `POST /api/ocr/upload` | `OcrService` | `./uploads/ocr/{uuid}_{filename}` |
| 음성 파일 (STT) | `POST /api/stt/transcribe` | `SttService` | `./uploads/audio/{uuid}_{filename}` |
| 이미지 (Vision) | `POST /api/vision/analyze` | `VisionService` | `./uploads/vision/{uuid}_{filename}` |
| DB 스키마 (Text2SQL) | `POST /api/text2sql/schema` | `Text2SqlService` | 메모리 (dict) |
| 코드 템플릿 (Codegen) | `POST /api/codegen/templates` | `CodegenService` | 메모리 (dict) |
| Webhook 이벤트 | `POST /api/webhook/*` | `WebhookService` | 없음 (트리거만) |

### 코드 위치
- `app/routers/rag.py:21-28` — 파일 업로드 엔드포인트
- `app/connectors/confluence.py:30-89` — Confluence REST API 호출
- `app/services/ocr_service.py` — OCR 수집
- `app/services/stt_service.py` — 음성 수집

### 설정
- `CHROMA_HOST`, `CHROMA_PORT` — 벡터 DB 위치
- Confluence: 요청 시 `base_url`, `username`, `api_token` 전달

### 한계 & 개선 방향
| 현재 한계 | 개선 방향 |
|-----------|----------|
| 파일 1개씩만 업로드 | 폴더/zip 일괄 업로드 |
| 파일 크기 제한 없음 (메모리 부족 위험) | 파일 크기 제한 + 청크 업로드 |
| 중복 업로드 감지 없음 | 파일 해시로 중복 체크 |

---

## Layer 2: Extraction (텍스트 추출)

### 역할
각 파일 형식에서 순수 텍스트를 추출하는 단계.

### 형식별 추출 방법

| 형식 | 라이브러리 | 추출 방식 | 한계 |
|------|-----------|----------|------|
| PDF | `pypdf` | 페이지별 텍스트 | 스캔 PDF 처리 불가 (→ OCR 필요) |
| Word (.docx) | `python-docx` | 문단별 텍스트 | 표/이미지 내 텍스트 무시 |
| Excel (.xlsx) | `openpyxl` | 시트 → 행 → 탭 구분 | 수식 결과만 (수식 자체 X) |
| HTML (Confluence) | `BeautifulSoup` | `get_text(separator="\n")` | JS 렌더링 콘텐츠 불가 |
| 코드 파일 | 직접 읽기 | UTF-8 텍스트 | 바이너리 파일 처리 불가 |
| 이미지 | PaddleOCR / Tesseract | 이미지 → 텍스트 | 손글씨/저해상도 정확도 낮음 |
| 음성 | Whisper | 음성 → 텍스트 | 배경 소음 시 정확도 하락 |

### 코드 위치
- `app/core/document_loader.py:12-58` — 형식별 텍스트 추출
- `app/connectors/confluence.py:134-140` — HTML → 텍스트
- `app/services/ocr_service.py:82-119` — 이미지 OCR

### 상세 처리 흐름
```python
# PDF
PdfReader(file_path) → page.extract_text() → "\n".join(pages)

# Word
Document(file_path) → para.text → "\n".join(paragraphs)

# Excel
load_workbook(file_path) → 시트별 → row → "\t".join(cells) → "\n".join(rows)

# HTML (Confluence)
BeautifulSoup(html) → script/style 태그 제거 → get_text(separator="\n")

# OCR (PaddleOCR)
PaddleOCR(lang="korean") → ocr(image_path) → line[1][0] → "\n".join(lines)
```

### 개선 방향
| 현재 | 개선 |
|------|------|
| PDF 테이블 인식 안 됨 | `tabula-py` 또는 `camelot` 추가 |
| Word 표 텍스트 누락 | `table.rows` 처리 추가 |
| Excel 차트/그래프 무시 | 차트 → 이미지 → OCR 파이프라인 |
| 한국어 OCR 정확도 | PaddleOCR fine-tuned 모델 적용 |

---

## Layer 3: Preprocessing (전처리)

### 역할
추출된 원시 텍스트를 정리하여 청킹/임베딩 품질을 높이는 단계.

### 현재 구현 (최소한)
```python
# document_loader.py의 _chunk_text에서 암묵적으로 수행
chunk.strip()  # 앞뒤 공백 제거
if chunk.strip():  # 빈 청크 제거
```

### 이상적인 전처리 (미구현, 확장 필요)

| 처리 | 목적 | 예시 |
|------|------|------|
| Unicode 정규화 | 같은 문자의 다른 표현 통일 | `NFC` 정규화 (한국어 자모 결합) |
| 연속 공백/개행 정리 | 노이즈 제거 | `\n\n\n` → `\n\n` |
| 헤더/푸터 제거 | PDF 반복 요소 제거 | 페이지 번호, 회사 로고 텍스트 |
| 특수문자 정리 | 검색 정확도 향상 | `\x00`, `\ufeff` 제거 |
| 언어 감지 | 다국어 처리 | 한국어/영어 혼합 문서 분류 |
| 개인정보 마스킹 | 보안 | 주민번호, 전화번호 패턴 `***` 처리 |

### 코드 위치
- `app/core/document_loader.py:60-73` — 현재는 `strip()` 수준만

### 개선 우선순위
1. Unicode NFC 정규화 (한국어 필수) — 1줄 추가
2. 연속 개행 정리 — regex 1줄
3. 개인정보 마스킹 — 정규식 패턴

---

## Layer 4: Chunking (청킹)

### 역할
긴 텍스트를 검색에 적합한 크기의 조각으로 분할하는 **핵심 단계**.
청킹 품질이 RAG 성능의 70%를 결정한다.

### 현재 구현: Fixed-size Chunking

```python
CHUNK_SIZE = 1000     # 문자 수
CHUNK_OVERLAP = 200   # 오버랩 문자 수

def _chunk_text(self, text):
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += CHUNK_SIZE - CHUNK_OVERLAP  # 800씩 이동
    return chunks
```

### 작동 원리
```
원본 텍스트 (3000자):
[==============================================]

청크 1: [==========]           (0~1000)
청크 2:     [==========]       (800~1800)  ← 200자 오버랩
청크 3:         [==========]   (1600~2600)
청크 4:             [======]   (2400~3000)

오버랩이 있으면 문장이 잘리는 경계에서도 문맥을 유지할 수 있다.
```

### 코드 위치
- `app/core/document_loader.py:60-73`

### 청킹 전략 비교 (현재 vs 가능한 개선)

| 전략 | 장점 | 단점 | 적용 난이도 |
|------|------|------|-----------|
| **Fixed-size (현재)** | 구현 간단, 예측 가능 | 문장 중간에서 잘림 | - |
| Sentence-based | 문장 경계 존중 | 문장 길이 불균일 | 하 |
| Paragraph-based | 의미 단위 보존 | 청크 크기 편차 큼 | 하 |
| **Semantic Chunking** | 의미 변화 지점에서 분할 | 임베딩 호출 필요 (느림) | 중 |
| Recursive Splitting | 구분자 우선순위로 분할 | 설정 복잡 | 중 |
| Document-aware | 제목/섹션 구조 인식 | 형식마다 파서 필요 | 상 |

### 각 전략 상세

#### Sentence-based (문장 기반)
```python
# 한국어: 마침표/물음표/느낌표로 분할
import re
sentences = re.split(r'(?<=[.?!。])\s+', text)
```
- 한국어는 `다.`, `요.`, `니다.` 등 어미 패턴 활용
- 짧은 문장 여러 개를 합쳐서 최소 크기 보장

#### Semantic Chunking (의미 기반)
```python
# 연속된 문장의 임베딩 유사도를 계산
# 유사도가 급격히 떨어지는 지점에서 분할
for i in range(len(sentences) - 1):
    sim = cosine_similarity(embed(sentences[i]), embed(sentences[i+1]))
    if sim < threshold:
        # 여기서 청크 분할
```
- 가장 정확하지만 임베딩 호출 비용 발생
- bge-m3의 Dense 벡터를 사용하면 가능

#### Recursive Splitting (계층적 분할)
```python
separators = ["\n\n", "\n", ". ", " ", ""]
# 1차: 문단 단위로 분할
# 2차: 아직 큰 청크는 줄바꿈으로 분할
# 3차: 아직 큰 청크는 문장으로 분할
# 4차: 그래도 크면 단어 단위
```
- LangChain의 `RecursiveCharacterTextSplitter` 방식

### 최적 설정 가이드

| 문서 유형 | 추천 청크 크기 | 추천 오버랩 | 이유 |
|-----------|-------------|-----------|------|
| 법률/계약서 | 1500자 | 300자 | 조항이 길고 맥락이 중요 |
| 기술 문서 | 1000자 | 200자 | 코드 블록 포함, 적정 크기 |
| FAQ/매뉴얼 | 500자 | 100자 | 질문-답변이 짧음 |
| 코드 파일 | 함수 단위 | 0 | 함수/클래스 경계로 분할이 이상적 |
| 회의록 | 800자 | 150자 | 발언 단위 보존 |

---

## Layer 5: Embedding (임베딩)

### 역할
텍스트 청크를 고차원 벡터(숫자 배열)로 변환하여 의미 기반 검색을 가능하게 하는 단계.

### 현재 구현

```python
# vector_store.py
embedding_fn = SentenceTransformerEmbeddingFunction(
    model_name=settings.EMBEDDING_MODEL_PATH  # "./models/embedding" (bge-m3)
)
```

### 모델: BAAI/bge-m3

| 속성 | 값 |
|------|-----|
| 모델 | BAAI/bge-m3 |
| 벡터 차원 | 1024 |
| 최대 입력 길이 | 8192 토큰 |
| 지원 언어 | 100+ (한국어 상위권) |
| 모델 크기 | 4.3GB |
| 검색 방식 | Dense + Sparse + ColBERT |
| 라이선스 | MIT |

### 임베딩 프로세스
```
텍스트 청크 ("MES 시스템의 생산 실적 조회 방법은...")
        │
        ▼
   Tokenization (토큰화)
   ["MES", "시스템", "의", "생산", "실적", "조회", "방법", "은", ...]
        │
        ▼
   Transformer Encoder (12-layer)
   각 토큰의 문맥을 고려한 표현 생성
        │
        ▼
   Pooling (평균/CLS 풀링)
   모든 토큰 표현을 하나의 벡터로 축약
        │
        ▼
   1024차원 벡터
   [0.023, -0.156, 0.891, ..., 0.045]
```

### 코드 위치
- `app/core/vector_store.py:14-22` — 임베딩 모델 로드
- ChromaDB가 내부적으로 `embedding_fn`을 호출하여 자동 임베딩

### 성능 특성
| 항목 | 값 |
|------|-----|
| 첫 로딩 시간 | ~10초 (모델 메모리 적재) |
| 이후 임베딩 속도 | ~50ms/청크 (CPU) |
| GPU 사용 시 | ~5ms/청크 |
| 메모리 사용 | ~2GB |

### 개선 방향
| 현재 | 개선 |
|------|------|
| Dense 벡터만 사용 | bge-m3의 Sparse + Dense **Hybrid** 활용 |
| CPU만 사용 | GPU 가용 시 자동 활용 |
| 단일 모델 | 도메인별 fine-tuned 임베딩 모델 |

---

## Layer 6: Indexing (인덱싱)

### 역할
임베딩된 벡터와 메타데이터를 벡터 DB에 저장하여 검색 가능하게 만드는 단계.

### 현재 구현: ChromaDB

```python
# vector_store.py
col = client.get_or_create_collection(name=collection, embedding_function=embedding_fn)
col.add(
    documents=chunks,           # 원본 텍스트 (검색 결과 표시용)
    ids=["doc_uuid_0", ...],    # 고유 ID
    metadatas=[{                # 메타데이터
        "filename": "manual.pdf",
        "chunk_index": 0,
        "doc_id": "uuid",
    }, ...],
)
```

### 저장 구조

```
ChromaDB Collection: "default"
┌────────────┬──────────────────────┬─────────────────┬────────────────────┐
│ ID         │ Document (원본 텍스트) │ Embedding (벡터) │ Metadata           │
├────────────┼──────────────────────┼─────────────────┼────────────────────┤
│ doc1_0     │ "MES 시스템은..."     │ [0.02, -0.15..] │ {filename: "a.pdf"}│
│ doc1_1     │ "생산 실적 조회..."   │ [0.11, 0.08..]  │ {filename: "a.pdf"}│
│ conf_pg5_0 │ "배포 절차는..."     │ [-0.03, 0.22..] │ {source: "conflu"} │
└────────────┴──────────────────────┴─────────────────┴────────────────────┘
```

### 두 가지 모드

| 모드 | 설정 | 저장 위치 | 용도 |
|------|------|----------|------|
| Local Persistent | `CHROMA_PORT=0` | `./chroma_data/` 디렉토리 | Docker 없이 테스트 |
| Docker HTTP | `CHROMA_HOST=chromadb`, `PORT=8100` | Docker 볼륨 | 프로덕션 |

### 배치 인서트
```python
# 5000개씩 배치 (ChromaDB 제한: ~41666/배치)
batch_size = 5000
for start in range(0, len(documents), batch_size):
    col.add(documents[start:end], ids[start:end], metadatas[start:end])
```

### 코드 위치
- `app/core/vector_store.py:50-68` — 문서 추가
- `app/core/vector_store.py:25-37` — 클라이언트 초기화

### 개선 방향
| 현재 | 개선 |
|------|------|
| 컬렉션 단위 관리만 | 문서 단위 업데이트/삭제 |
| 메타데이터 기본적 | 날짜, 작성자, 태그 등 풍부한 메타 |
| 인덱스 설정 없음 | HNSW 파라미터 튜닝 (ef, M) |

---

## Layer 7: Query Understanding (질의 이해)

### 역할
사용자 질문을 분석하여 어떤 처리가 필요한지 결정하는 단계.

### 현재 구현

**RAG**: 사용자가 수동으로 RAG 페이지에서 질의 → 무조건 벡터 검색
**Agent**: LLM이 ReAct 패턴으로 어떤 도구를 쓸지 자율 판단
**Smart Chat**: LLM이 Function Calling으로 도구 필요 여부 판단

```
사용자: "지난달 A라인 불량률 알려줘"
        │
        ├── RAG 모드: 그냥 벡터 검색 (문서에 있으면 답변)
        ├── Agent 모드: LLM이 판단 → query_database 도구 호출
        └── Smart Chat 모드: LLM이 판단 → <tool_call> 태그로 도구 호출
```

### 질의 라우팅 (현재 수동, 향후 자동화)

| 질의 유형 | 현재 | 이상적 |
|-----------|------|--------|
| 문서 질문 | 사용자가 RAG 페이지 사용 | 자동 감지 → RAG |
| DB 질문 | 사용자가 SQL 페이지 사용 | 자동 감지 → Text2SQL |
| 코드 요청 | 사용자가 Codegen 페이지 사용 | 자동 감지 → Codegen |
| 복합 질문 | Agent 사용 | Agent 자동 진입 |

### 코드 위치
- `app/core/agent_executor.py:68-130` — ReAct 판단 루프
- `app/services/function_chat_service.py:118-158` — Prompt-based 도구 판단

### 개선 방향
- **Intent Classification**: 질문 의도를 먼저 분류하는 경량 모델 추가
- **Query Rewriting**: 검색 전에 질문을 검색에 최적화된 형태로 변환
  - "불량률 알려줘" → "A라인 불량률 통계 현황"

---

## Layer 8: Retrieval (검색)

### 역할
질문과 가장 관련 있는 문서 청크를 벡터 DB에서 찾아오는 단계.

### 현재 구현: Dense Retrieval

```python
# vector_store.py
results = col.query(
    query_texts=[query],    # 질문 텍스트 (자동 임베딩)
    n_results=top_k,        # 반환할 결과 수 (기본 5)
)
# 반환: ids, documents, metadatas, distances
```

### 검색 프로세스
```
질문: "MES 생산 실적 조회 방법"
        │
        ▼
   bge-m3로 임베딩 → [0.15, -0.08, ...]
        │
        ▼
   ChromaDB에서 코사인 유사도 검색
   모든 저장된 벡터와 비교하여 가장 가까운 top-k 반환
        │
        ▼
   결과: [
     {doc: "MES에서 생산 실적을 조회하려면...", score: 0.92},
     {doc: "생산 현황 대시보드 사용법...", score: 0.85},
     {doc: "실적 데이터 수집 프로세스...", score: 0.78},
   ]
```

### 유사도 계산
```
코사인 유사도 = (A · B) / (||A|| × ||B||)

값 범위: -1 ~ 1
1에 가까울수록 = 의미적으로 유사
0 = 무관
-1 = 반대 의미
```

### 코드 위치
- `app/core/vector_store.py:70-93` — 검색 메서드

### 검색 전략 비교

| 전략 | 장점 | 단점 | 구현 상태 |
|------|------|------|----------|
| **Dense (현재)** | 의미 검색 가능 | 키워드 정확 매칭 약함 | ✅ |
| Sparse (BM25) | 키워드 정확 매칭 강함 | 동의어/유사어 검색 불가 | ❌ |
| **Hybrid (Dense+Sparse)** | 양쪽 장점 결합 | 구현 복잡 | ❌ (확장 대상) |
| Multi-vector | 문서의 여러 측면 검색 | 저장 공간 ↑ | ❌ |

### Hybrid Search 구현 방법 (향후)
```python
# bge-m3는 Dense + Sparse 벡터를 동시에 생성할 수 있음
from FlagEmbedding import BGEM3FlagModel
model = BGEM3FlagModel('BAAI/bge-m3')
output = model.encode(["검색할 텍스트"])
dense_vector = output['dense_vecs']    # 코사인 유사도 검색
sparse_vector = output['lexical_weights']  # BM25 유사 검색

# 두 점수를 가중 합산
final_score = α * dense_score + (1-α) * sparse_score
```

---

## Layer 9: Reranking (재순위화)

### 역할
1차 검색(Retrieval) 결과를 더 정교한 모델로 재정렬하여 정확도를 높이는 단계.

### 현재 상태: **미구현**

### 왜 필요한가?
```
1차 검색 (Dense Retrieval):
  결과 1: "MES 시스템 설치 방법" (score: 0.91) ← 설치 방법, 질문과 다름
  결과 2: "생산 실적 조회 프로세스" (score: 0.88) ← 정답
  결과 3: "MES 개요 및 기능 소개" (score: 0.85)

Reranking 후:
  결과 1: "생산 실적 조회 프로세스" (score: 0.95) ← 정답이 1위로
  결과 2: "MES 시스템 설치 방법" (score: 0.72)
  결과 3: "MES 개요 및 기능 소개" (score: 0.65)
```

### 구현 방법 (향후)

#### Cross-encoder Reranking
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('BAAI/bge-reranker-v2-m3')  # bge-m3와 같은 시리즈

# 1차 검색 결과 top-20을 가져와서
pairs = [(query, doc["content"]) for doc in initial_results]
scores = reranker.predict(pairs)

# 점수순 재정렬
reranked = sorted(zip(initial_results, scores), key=lambda x: x[1], reverse=True)
final_results = [doc for doc, score in reranked[:5]]
```

#### 추천 Reranker 모델
| 모델 | 크기 | 한국어 | 설명 |
|------|------|--------|------|
| `BAAI/bge-reranker-v2-m3` | ~560MB | ✅ | bge-m3와 동일 시리즈, 최고 호환 |
| `cross-encoder/ms-marco-MiniLM-L-12-v2` | ~130MB | △ | 영어 최적화, 한국어 약함 |

---

## Layer 10: Context Assembly (컨텍스트 조립)

### 역할
검색된 청크들을 LLM이 이해할 수 있는 형태의 프롬프트로 조합하는 단계.

### 현재 구현

```python
# rag_service.py
context_parts = []
sources = []
for doc in results:
    context_parts.append(doc["content"])
    sources.append({
        "filename": doc.get("filename", "unknown"),
        "chunk_id": doc.get("id", ""),
        "score": doc.get("score", 0),
    })
context = "\n\n---\n\n".join(context_parts)
```

### 조립 결과 예시
```
Context:
MES 시스템에서 생산 실적을 조회하려면 다음 단계를 따르세요...

---

생산 현황 대시보드에서 일별/월별 실적을 확인할 수 있습니다...

---

실적 데이터는 매 시간 자동으로 수집되며...

Question: MES 생산 실적 조회 방법은?
```

### 코드 위치
- `app/services/rag_service.py:58-79` — 컨텍스트 조립

### 개선 방향

| 현재 | 개선 |
|------|------|
| 단순 연결 (`---` 구분) | 각 청크에 출처 정보 포함 (`[문서: manual.pdf, 페이지 3]`) |
| 전체 청크 포함 | 토큰 수 제한에 맞게 잘라내기 |
| 순서 무관 | 관련도 높은 청크를 앞에 배치 (LLM 시작 부분에 집중) |
| 컨텍스트만 | 관련 없는 청크 필터링 (score 임계값) |

### 컨텍스트 윈도우 관리
```
LLM 컨텍스트 윈도우: 8192 토큰 (GPT-OSS 기준)

시스템 프롬프트:  ~200 토큰
대화 히스토리:    ~1000 토큰 (최근 5턴)
검색 컨텍스트:    ~4000 토큰 (5개 청크 × 800토큰)
질문:            ~100 토큰
응답 여유:        ~2892 토큰

→ 청크 5개 × 1000자 ≈ 4000토큰이 안전한 상한
```

---

## Layer 11: Prompt Engineering (프롬프트 구성)

### 역할
시스템 프롬프트, 컨텍스트, 대화 히스토리, 사용자 질문을 최적의 순서와 형식으로 조합.

### 현재 프롬프트 구조

```python
messages = [
    {"role": "system", "content": SYSTEM_RAG},       # 시스템 역할 정의
    # ...대화 히스토리 (멀티턴)...
    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
]
```

### 시스템 프롬프트 목록 (`app/core/prompts.py`)

| 프롬프트 | 용도 | 핵심 규칙 |
|---------|------|----------|
| `SYSTEM_CHAT` | 일반 채팅 | 한/영 자동 전환, 간결 전문적 |
| `SYSTEM_RAG` | 문서 Q&A | **컨텍스트만 사용**, 출처 인용 |
| `SYSTEM_TEXT2SQL` | SQL 생성 | SELECT만, Oracle 문법, 주석 |
| `SYSTEM_CODEGEN` | 코드 생성 | 타입 힌트, 에러 핸들링, 완전한 코드 |
| `SYSTEM_CODE_REVIEW` | 코드 리뷰 | 라인 번호, 심각도, 구체적 수정안 |
| `SYSTEM_EDGE_CASE` | 엣지 케이스 | 카테고리별, 우선순위, 테스트 케이스 |
| `REACT_SYSTEM_PROMPT` | Agent | ReAct 형식, 도구 설명, 반복 루프 |
| `FUNCTION_CHAT_SYSTEM` | Smart Chat | `<tool_call>` XML 형식 |

### 프롬프트 최적화 원칙

1. **역할 정의가 먼저**: "당신은 ___입니다"
2. **규칙은 구체적으로**: "만약 ___하면 ___하라"
3. **출력 형식 명시**: JSON, 마크다운, 코드 블록 등
4. **제약 조건 마지막**: "절대 ___하지 마라"
5. **Few-shot 예시**: 원하는 형식의 예시 1~2개 포함

### 코드 위치
- `app/core/prompts.py` — 전체 프롬프트 정의

---

## Layer 12: LLM Inference (모델 추론)

### 역할
조합된 프롬프트를 LLM에 보내서 응답을 생성하는 단계.

### 현재 구현

```python
# llm_client.py
client = OpenAI(
    base_url=settings.LLM_API_BASE,  # OpenAI or GPT-OSS
    api_key=settings.LLM_API_KEY,
)

response = client.chat.completions.create(
    model=settings.LLM_MODEL,
    messages=messages,
    temperature=0.7,
    max_tokens=2048,
    stream=False,  # or True for SSE
)
```

### 호출 파라미터

| 파라미터 | 기본값 | 용도별 설정 |
|---------|--------|-----------|
| `temperature` | 0.7 | 채팅: 0.7 / SQL: 0.1 / 코드: 0.3 / 리뷰: 0.3 |
| `max_tokens` | 2048 | 리뷰: 4096 / 일반: 2048 |
| `stream` | false | 채팅 UI: true / API 호출: false |

### LLM 엔드포인트 전환

```
인터넷 환경:  base_url = https://api.openai.com/v1     model = gpt-4o-mini
폐쇄망:      base_url = http://localhost:8000/v1       model = gpt-oss-120b
Ollama:     base_url = http://localhost:11434/v1      model = llama3.1
vLLM:       base_url = http://gpu-server:8000/v1      model = Qwen2.5-72B
```

### 코드 위치
- `app/llm_client.py` — 모든 LLM 호출의 단일 진입점

### 성능 특성
| 항목 | OpenAI (gpt-4o-mini) | GPT-OSS 120B | Ollama (llama3.1) |
|------|---------------------|--------------|-------------------|
| 첫 토큰 지연 | ~500ms | ~2s | ~1s |
| 생성 속도 | ~100토큰/s | ~30토큰/s | ~50토큰/s |
| 한국어 품질 | 최상 | 상 | 중상 |

---

## Layer 13: Tool Execution (도구 실행)

### 역할
Agent/Function Calling에서 LLM이 요청한 도구를 실행하고 결과를 반환하는 단계.

### 현재 등록된 도구 (6개)

| 도구 | 설명 | 호출하는 서비스 |
|------|------|---------------|
| `search_docs` | 문서 검색 | `RagService.query()` |
| `query_database` | SQL 생성/실행 | `Text2SqlService.generate()` |
| `generate_code` | 코드 생성 | `CodegenService.generate()` |
| `review_code` | 코드 리뷰 | `ReviewService.code_review()` |
| `list_collections` | 컬렉션 목록 | `VectorStore.list_collections()` |
| `list_schemas` | 스키마 목록 | `Text2SqlService.list_schemas()` |

### 실행 흐름 (Agent 모드)

```
LLM 응답: "Action: search_docs\nAction Input: {\"query\": \"불량률\"}"
        │
        ▼
   AgentExecutor._parse_response()
   → action = "search_docs", action_input = '{"query": "불량률"}'
        │
        ▼
   ToolRegistry.execute("search_docs", {"query": "불량률"})
        │
        ▼
   RagService.query(query="불량률") → 벡터 검색 → LLM 답변
        │
        ▼
   결과 문자열 (3000자 이내로 truncate)
        │
        ▼
   LLM에게 "Observation: {결과}" 로 전달 → 다음 판단
```

### 안전장치
- 도구 실행 타임아웃: 30초
- 결과 truncation: 3000자 초과 시 잘라냄
- 최대 반복: 10회 (무한 루프 방지)
- SQL: SELECT만 허용 (Deterministic Backbone)

### 코드 위치
- `app/core/tool_registry.py` — 도구 정의 + 실행
- `app/core/agent_executor.py` — ReAct 루프
- `app/services/agent_service.py` — 도구 등록

---

## Layer 14: Post-processing (후처리)

### 역할
LLM 응답을 정제하고, 출처 정보를 매핑하고, 안전성을 검증하는 단계.

### 현재 구현

#### RAG 응답 후처리
```python
# rag_service.py
return {
    "answer": answer,           # LLM 답변
    "sources": [                # 출처 정보
        {"filename": "doc.pdf", "chunk_id": "xxx_0", "score": 0.85},
    ],
}
```

#### Text2SQL 안전 검증 (Deterministic Backbone)
```python
def _is_safe_sql(self, sql):
    normalized = sql.strip().upper()
    dangerous = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "EXEC"]
    for keyword in dangerous:
        if normalized.startswith(keyword):
            return False
    return True
```

#### Agent 응답 파싱
```python
# agent_executor.py
# "Final Answer:" 이후의 텍스트를 최종 답변으로 추출
final_match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
```

#### Smart Chat 도구 호출 파싱
```python
# function_chat_service.py
# <tool_call> XML 태그에서 도구 호출 추출
pattern = r"<tool_call>\s*(.*?)\s*</tool_call>"
# 최종 응답에서 tool_call 태그 제거
clean_reply = re.sub(r"<tool_call>.*?</tool_call>", "", reply)
```

### 코드 위치
- `app/services/rag_service.py:66-89` — 출처 매핑
- `app/services/text2sql_service.py:309-317` — SQL 안전 검증
- `app/core/agent_executor.py:117-148` — Agent 응답 파싱
- `app/services/function_chat_service.py:152-168` — 도구 호출 파싱

### 개선 방향
| 현재 | 개선 |
|------|------|
| SQL 시작 키워드만 체크 | SQL 파서로 완전한 분석 |
| 할루시네이션 감지 없음 | 답변-컨텍스트 일치도 검증 |
| 출처 정보 청크 ID만 | 페이지 번호, 섹션 제목 포함 |

---

## Layer 15: Response Delivery (응답 전달)

### 역할
최종 응답을 클라이언트에게 전달하는 단계.

### 두 가지 모드

#### 1. 일반 JSON 응답
```python
@router.post("/query", response_model=RagQueryResponse)
async def query(req: RagQueryRequest):
    result = await service.query(...)
    return result  # FastAPI가 자동으로 JSON 직렬화
```

#### 2. SSE 스트리밍 (Server-Sent Events)
```python
@router.post("/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(
        service.chat_stream(...),
        media_type="text/event-stream",
    )

# 스트리밍 데이터 형식
async def chat_stream(...):
    for chunk in stream:
        yield f"data: {json.dumps({'content': delta})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"
```

### SSE 프로토콜
```
HTTP/1.1 200 OK
Content-Type: text/event-stream

data: {"content": "MES"}

data: {"content": " 시스템에서"}

data: {"content": " 생산 실적을"}

data: {"done": true, "conversation_id": "abc-123"}
```

### 에러 응답
```python
# FastAPI 자동 에러 처리
# 422: Pydantic 검증 실패
# 500: 서버 내부 에러
# 서비스 레벨에서는 try-except로 잡아서 에러 메시지 반환
```

### 코드 위치
- `app/routers/chat.py:34-43` — SSE 스트리밍
- `app/routers/agent.py:56-78` — Agent SSE 스트리밍
- 모든 라우터 — JSON 응답

---

## Layer 16: Persistence & Feedback (영속화 & 피드백)

### 역할
대화 이력, 빌드 결과, 스케줄 상태, 학습 데이터를 파일로 저장하는 단계.

### 저장소 구조

```
./data/
├── conversations/          # 대화 히스토리
│   └── {conv_id}.json     # [{"role": "user", "content": "..."}, ...]
│
├── builds/                 # 빌드/배포 이력
│   └── {timestamp}_{id}.json
│
├── settings/               # 사용자 설정
│   └── {key}.json
│
├── confluence/             # Confluence 동기화 상태
│   └── {space_key}.json   # {page_id: content_hash, ...}
│
├── finetune/               # Fine-tuning 데이터셋
│   ├── {dataset_id}.jsonl  # Q&A 쌍 (JSONL)
│   └── {dataset_id}.meta.json
│
├── schedules.json          # 스케줄러 설정
│
└── schedule_history/       # 스케줄 실행 이력
    └── {schedule_name}.jsonl

./chroma_data/              # ChromaDB 벡터 데이터 (로컬 모드)
./uploads/                  # 업로드된 원본 파일
./models/embedding/         # bge-m3 모델 파일
```

### 각 저장소의 역할

| 저장소 | 서비스 | 형식 | 용도 |
|--------|--------|------|------|
| `conversations/` | `ConversationStore` | JSON | 멀티턴 대화 기억 |
| `builds/` | `BuildService` | JSON | 빌드 결과 + 로그 |
| `settings/` | `SettingsService` | JSON | Confluence 연결 정보 등 |
| `confluence/` | `ConfluenceConnector` | JSON | 변경 감지용 해시 |
| `finetune/` | `TrainingDataStore` | JSONL | 학습 데이터 |
| `schedules.json` | `SchedulerService` | JSON | 반복 작업 설정 |

### 코드 위치
- `app/core/conversation_store.py` — 대화 저장
- `app/services/build_service.py:97-105` — 빌드 이력
- `app/services/settings_service.py` — 설정 CRUD
- `app/core/training_data_store.py` — 학습 데이터

### 개선 방향
| 현재 | 개선 |
|------|------|
| JSON 파일 기반 | SQLite 또는 PostgreSQL로 전환 |
| 동시 쓰기 충돌 가능 | 파일 잠금 또는 DB 트랜잭션 |
| 피드백 수집 없음 | 사용자 평가 (👍/👎) 저장 |
| 사용 통계 없음 | API 호출 횟수, 응답 시간 로깅 |

---

## 부록: 각 기능별 레이어 사용 매핑

### RAG (문서 Q&A)
```
L1 → L2 → L3 → L4 → L5 → L6 (저장)
                                    L7 → L8 → (L9) → L10 → L11 → L12 → L14 → L15 → L16
```
**거치는 레이어: 14/16**

### Chat (일반 대화)
```
L7 → L11 → L12 → L14 → L15 → L16
```
**거치는 레이어: 6/16**

### Agent (자율 작업)
```
L7 → L11 → L12 → L13 → (L8/L12 반복) → L14 → L15 → L16
```
**거치는 레이어: 8/16 (+ 반복)**

### Text2SQL
```
L7 → L11 → L12 → L14 (SQL 안전검증) → L15
```
**거치는 레이어: 5/16**

### Confluence → RAG
```
L1 (API) → L2 (HTML→텍스트) → L3 → L4 → L5 → L6 → L16
```
**거치는 레이어: 7/16**

### OCR → RAG
```
L1 (이미지) → L2 (OCR) → L3 → L4 → L5 → L6 → L16
```
**거치는 레이어: 7/16**

---

## 부록: 성능 병목 지점

| 레이어 | 병목 원인 | 소요 시간 | 해결 방법 |
|--------|---------|----------|----------|
| L5 (Embedding) | 모델 첫 로딩 | ~10초 | 앱 시작 시 미리 로딩 |
| L5 (Embedding) | 대량 문서 임베딩 | ~50ms/청크 | GPU 사용, 배치 처리 |
| L8 (Retrieval) | 대규모 컬렉션 검색 | <100ms | ChromaDB HNSW 자동 최적화 |
| L12 (LLM) | 모델 추론 | 1~10초 | 더 빠른 모델, 양자화 |
| L13 (Tool) | 도구 실행 (특히 DB) | 가변 | 쿼리 최적화, 캐싱 |
