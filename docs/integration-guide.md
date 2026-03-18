# LLM × Oracle MES/WMS 연동 실전 가이드

> **발표용 문서** | 작성일: 2026-03-18

---

## 1. 연동 시나리오별 사용 방법

### 시나리오 1: "데이터 분석 질문" (Text-to-SQL)

**목표**: 자연어로 Oracle DB를 조회한다.

**사전 준비** (최초 1회)
1. `http://localhost:3000` 접속 → **SQL** 메뉴
2. **DB 연결/스키마 탐색** 탭 클릭
3. 아래 정보 입력 후 **스키마 자동 탐색** 클릭

```
DB 종류  : Oracle
Host     : localhost
Port     : 1521
Service  : XEPDB1
User     : MESADMIN
Password : mesadmin123
```

4. PRODUCTION_ORDERS, DEFECTS 등 11개 테이블 자동 감지 확인
5. **저장** 클릭 → Schema ID 발급

**사용 예시**
```
질문: "A라인 이번달 불량률 알려줘"
→ LLM이 SELECT 생성 → Oracle 실행 → 숫자로 답변

질문: "재고 부족한 품목 리스트 뽑아줘"
→ INVENTORY JOIN ITEMS → CURRENT_QTY < SAFETY_STOCK 조건 SQL 생성

질문: "지난 30일간 불량이 가장 많은 설비가 어디야?"
→ DEFECTS JOIN EQUIPMENT → GROUP BY 집계 SQL 생성
```

---

### 시나리오 2: "소스코드 질문" (Git RAG)

**목표**: MES/WMS 소스코드를 AI가 이해하고 답변한다.

**사전 준비** (최초 1회)
1. `http://localhost:3000` → **Git Code RAG** 메뉴
2. 로컬 경로 입력: `C:/Sources/SampleMESWMS`
3. **색인 시작** 클릭 → 백그라운드 처리 (수십 초)
4. 진행률 폴링 → `done` 확인

**사용 예시**
```
질문: "출고 처리 로직이 어디 있어?"
→ wms.py의 /outbound 엔드포인트 코드 청크 반환

질문: "DEFECTS 테이블에 데이터 어떻게 INSERT 돼?"
→ 02_data.sql PL/SQL 블록 청크 반환

질문: "FastAPI에서 Oracle 연결을 어떻게 설정했어?"
→ database.py 내용 반환
```

---

### 시나리오 3: "종합 분석" (통합 진단 — 핵심)

**목표**: 문서 지식 + 실제 데이터를 동시에 조합해서 답변한다.

**사전 준비**: 시나리오 1 + 2 완료 후

1. `http://localhost:3000` → **통합 진단** 메뉴
2. Schema ID 선택, 컬렉션 선택 (또는 전체)
3. 자연어 질문 입력

**사용 예시**
```
질문: "A라인 불량이 2월부터 급증한 이유가 뭐야?"
→ RAG: 소스코드에서 A라인 관련 로직 추출
→ SQL: SELECT 월별 불량률 FROM DEFECTS WHERE LINE='L001'
→ LLM: 코드 분석 + 실제 수치 조합 → 종합 분석 답변

질문: "재고 부족인데 오늘 출고 계획이 있는 품목 있어?"
→ RAG: 재고 처리 로직 추출
→ SQL: INVENTORY SAFETY_STOCK 미달 + 오늘 OUTBOUND 조인
→ LLM: "P001 반도체패키지가 재고 721개이나 오늘 출고 계획 150개..."
```

---

## 2. 발표 시 강조 포인트

### "왜 이게 가치 있는가?"

```
기존 방식:
  생산팀 → ERP 로그인 → 메뉴 찾기 → 필터 설정 → 엑셀 다운 → 분석
  (최소 10~15분)

이 시스템:
  생산팀 → 채팅창에 질문 → 즉시 답변
  (30초)
```

### "AI가 잘못된 SQL을 만들면?"

- Text-to-SQL 결과는 사용자에게 SQL 먼저 보여줌
- **확인 후 실행** 방식 (SELECT만 허용, INSERT/UPDATE/DELETE 차단)
- 결과가 이상하면 "다시 쓸게" 피드백 → LLM 재생성

### "사내 데이터가 외부로 나가는가?"

- LLM API를 사내 서버(Ollama 등)로 설정 가능 (`LLM_API_BASE` 환경변수)
- `MODE=airgap` 설정 시 완전 폐쇄망 동작
- ChromaDB, Oracle 모두 로컬

---

## 3. 질의응답 대비

| 예상 질문 | 답변 |
|-----------|------|
| "Oracle 말고 다른 DB도 되나?" | PostgreSQL, MySQL도 지원. Text-to-SQL 스키마 탐색기가 DB 종류별로 동작 |
| "임베딩 모델이 뭐야?" | SentenceTransformer 로컬 모델. 서버에서만 돌고 외부 전송 없음 |
| "검색 정확도는?" | Hybrid RAG (Dense + BM25 + RRF + 재순위) 적용. 단순 벡터 검색 대비 정밀도 향상 |
| "대용량 데이터는?" | ChromaDB HTTP 모드로 별도 서버 분리 가능. Oracle은 기존 쿼리 최적화 그대로 적용 |
| "실시간 데이터 반영되나?" | SQL은 실시간. RAG는 재색인 필요 (Confluence는 스케줄 자동 동기화) |
