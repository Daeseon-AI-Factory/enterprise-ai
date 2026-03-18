# 데이터 흐름 상세 — 코드 레벨 추적

> **발표용 문서** | 작성일: 2026-03-18

---

## 통합 진단 API 전체 흐름 (`POST /api/analyze`)

### 요청
```json
{
  "question": "A라인 불량이 2월부터 왜 급증했어?",
  "schema_id": "mesadmin_xepdb1",
  "collections": ["git_SampleMESWMS"],
  "top_k": 5,
  "run_sql": true
}
```

### 내부 처리 순서

```
app/routers/analyze.py
  │
  ├─ [Step 1] RAG 검색
  │   core/vector_store.py → hybrid_search()
  │   │
  │   ├─ ChromaDB dense search (SentenceTransformer 임베딩)
  │   ├─ BM25 keyword search
  │   ├─ RRF(k=60) 점수 병합
  │   └─ Bi-encoder 재순위 → top_k 청크 반환
  │
  ├─ [Step 2] Text-to-SQL
  │   services/text2sql_service.py
  │   │
  │   ├─ schema 파일 로드 (./data/schemas/{id}.json)
  │   ├─ LLM 호출: system="너는 Oracle SQL 전문가" + 스키마 + 질문
  │   └─ SQL 추출 (```sql ... ``` 파싱)
  │
  ├─ [Step 3] SQL 실행 (run_sql=True이고 SELECT문이면)
  │   connectors/db_connector.py
  │   │
  │   └─ oracle+oracledb://MESADMIN:...@localhost:1521/?service_name=XEPDB1
  │       → 결과 rows 반환 (최대 50행)
  │
  └─ [Step 4] 최종 LLM 호출
      llm_client.py → chat_completion()
      │
      ├─ system: "당신은 기업 데이터 분석 전문가입니다"
      ├─ context:
      │   [문서 지식]
      │   - (청크1) wms.py:45 — 불량 처리 로직...
      │   - (청크2) 02_data.sql — A라인 불량 시뮬레이션 주석...
      │   [DB 실제 데이터]
      │   - SQL: SELECT LINE_NAME, DEFECT_RATE ...
      │   - 결과: [{"LINE_NAME":"A라인","DEFECT_RATE":6.77}, ...]
      └─ user: 원래 질문
```

### 응답
```json
{
  "answer": "A라인의 불량률은 1월 2.3%에서 2월 5.8%, 3월 6.77%로 급증했습니다...",
  "rag_sources": [
    {"collection": "git_SampleMESWMS", "filename": "02_data.sql", "score": 0.92},
    {"collection": "git_SampleMESWMS", "filename": "routers/mes.py", "score": 0.87}
  ],
  "db_sql": "SELECT LINE_NAME, ROUND(...) AS DEFECT_RATE FROM ...",
  "db_rows": [{"LINE_NAME": "A라인(SMT)", "DEFECT_RATE": 6.77}],
  "db_row_count": 1
}
```

---

## Text-to-SQL 스키마 자동 탐색 흐름

### `POST /api/text2sql/schema/discover` 호출 시

```
1. DB 연결 테스트
   oracle+oracledb://MESADMIN@localhost:1521/?service_name=XEPDB1

2. 테이블 목록 조회
   SELECT TABLE_NAME FROM USER_TABLES ORDER BY TABLE_NAME
   → ['DEFECTS', 'EQUIPMENT', 'INBOUND', 'INVENTORY', ...]

3. 각 테이블 컬럼 조회
   SELECT COLUMN_NAME, DATA_TYPE, NULLABLE
   FROM USER_TAB_COLUMNS
   WHERE TABLE_NAME = :table_name
   ORDER BY COLUMN_ID

4. JSON 스키마로 변환 후 저장
   ./data/schemas/mesadmin_xepdb1.json
   {
     "tables": {
       "PRODUCTION_ORDERS": {
         "columns": [
           {"name": "ORDER_ID", "type": "NUMBER", "nullable": "N"},
           {"name": "ORDER_NO", "type": "VARCHAR2", "nullable": "N"},
           {"name": "LINE_ID",  "type": "VARCHAR2", "nullable": "N"},
           ...
         ]
       },
       ...
     }
   }

5. 이후 LLM 프롬프트에 스키마 주입
   → LLM이 컬럼명/타입을 알고 정확한 SQL 생성
```

---

## Git RAG 색인 흐름

### `POST /api/git/index` 호출 시

```
1. 저장소 파일 스캔
   connectors/git_connector.py → read_files()
   - 경로: C:/Sources/SampleMESWMS
   - 스킵: node_modules, .git, __pycache__, dist
   - 최대: 500개 파일, 500KB 이하

2. 파일별 청킹
   chunk_file() → 1000줄 단위, 100줄 오버랩
   예) database.py (41줄) → 1개 청크
       02_data.sql (306줄) → 1~2개 청크

3. ChromaDB에 저장
   vector_store.add_documents(
     collection="git_SampleMESWMS",
     documents=["def wms_dashboard(): ..."],
     doc_id=uuid,
     filename="backend/routers/wms.py"
   )

4. BM25 인덱스 동시 갱신
   → 키워드 검색용 역색인 메모리에 유지

5. 완료 상태 반환
   {
     "status": "done",
     "files_indexed": 23,
     "chunks_indexed": 47,
     "message": "컬렉션 'git_SampleMESWMS'에 색인 완료"
   }
```

---

## Oracle 연결 핵심 설정

### 왜 `/?service_name=XEPDB1` 인가?

```
Oracle 21c XE Docker 구조:
  XE (CDB Root) — SID 방식 접속 대상
  └── XEPDB1 (PDB) — 실제 앱 데이터 위치
                     Service Name 방식으로만 접속 가능

잘못된 방식 (SID로 오해):
  oracle+oracledb://user:pass@host:1521/XEPDB1
  → DPY-6003: SID "XEPDB1" is not registered 에러

올바른 방식 (Service Name 명시):
  oracle+oracledb://user:pass@host:1521/?service_name=XEPDB1
  → 정상 접속
```

### python-oracledb thin mode 장점
- Oracle Instant Client 설치 불필요
- Docker 이미지 크기 대폭 감소
- pip install oracledb 만으로 완료
