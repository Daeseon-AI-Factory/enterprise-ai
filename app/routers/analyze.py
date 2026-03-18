"""
RAG + DB 통합 진단 엔드포인트.

동작 방식:
  1. 질문을 벡터DB에서 관련 문서 검색 (RAG)
  2. 질문에서 SQL 자동 생성 후 실제 DB 조회
  3. 문서 컨텍스트 + DB 실제 데이터를 합쳐서 LLM에 전달
  4. 정확한 진단/답변 반환
"""
from fastapi import APIRouter
from pydantic import BaseModel
from loguru import logger

from app.llm_client import chat_completion
from app.core.vector_store import get_vector_store
from app.services.text2sql_service import Text2SqlService

router = APIRouter()

_vector_store = get_vector_store()
_sql_service = Text2SqlService()

SYSTEM_ANALYZE = """당신은 기업 데이터 분석 전문가입니다.
아래에 두 가지 컨텍스트가 제공됩니다:

1. [문서 지식]: Confluence, 매뉴얼, 사내 문서에서 검색된 관련 내용
2. [DB 실제 데이터]: 질문과 관련하여 데이터베이스에서 직접 조회한 결과

## 규칙
- 문서와 DB 데이터를 종합하여 정확하고 구체적인 답변을 제공하세요
- DB 데이터가 있으면 반드시 수치/현황을 포함해 답변하세요
- 출처를 명시하세요 (예: "[DB 조회 결과]", "[온보딩 가이드]")
- 사용자 질문과 동일한 언어로 답변하세요
"""


class AnalyzeRequest(BaseModel):
    question: str
    schema_id: str | None = None          # 어떤 DB 스키마 사용할지
    collections: list[str] | None = None  # 어떤 RAG 컬렉션 검색할지 (None = 전체)
    top_k: int = 5
    run_sql: bool = True                   # DB 조회 실행 여부


@router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """RAG 문서 + 실제 DB 데이터를 결합한 통합 진단."""

    # ── 1. RAG 검색 ──────────────────────────────────────
    rag_context = ""
    rag_sources = []
    try:
        if req.collections:
            all_hits = []
            for col in req.collections:
                hits = _vector_store.hybrid_search(col, req.question, top_k=req.top_k)
                for h in hits:
                    h["collection"] = col
                all_hits.extend(hits)
            all_hits.sort(key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True)
            hits = all_hits[:req.top_k]
        else:
            hits = []
            for col in _vector_store.list_collections():
                col_name = col["name"]
                try:
                    col_hits = _vector_store.hybrid_search(col_name, req.question, top_k=3)
                    for h in col_hits:
                        h["collection"] = col_name
                    hits.extend(col_hits)
                except Exception:
                    pass
            hits.sort(key=lambda x: x.get("rerank_score", x.get("score", 0)), reverse=True)
            hits = hits[:req.top_k]

        if hits:
            parts = []
            for h in hits:
                src = f"[{h.get('collection','?')}/{h.get('filename','?')}]"
                parts.append(f"{src}\n{h['content']}")
                rag_sources.append({
                    "collection": h.get("collection", ""),
                    "filename": h.get("filename", ""),
                    "score": round(h.get("score", 0), 3),
                })
            rag_context = "\n\n---\n\n".join(parts)
    except Exception as e:
        logger.warning(f"RAG search failed: {e}")

    # ── 2. Text-to-SQL + DB 조회 ─────────────────────────
    db_context = ""
    db_sql = ""
    db_rows = []
    if req.run_sql:
        try:
            sql_result = await _sql_service.generate(req.question, schema_id=req.schema_id)
            db_sql = sql_result.get("sql", "")
            if db_sql:
                exec_result = await _sql_service.execute(db_sql)
                if not exec_result.get("error"):
                    rows = exec_result.get("rows", [])
                    cols = exec_result.get("columns", [])
                    db_rows = rows
                    if rows:
                        header = " | ".join(cols)
                        lines = [header, "-" * len(header)]
                        for row in rows[:20]:  # max 20 rows in context
                            lines.append(" | ".join(str(row.get(c, "")) for c in cols))
                        db_context = "\n".join(lines)
                        if len(rows) > 20:
                            db_context += f"\n... 외 {len(rows)-20}건"
                    else:
                        db_context = "(조회 결과 없음)"
                else:
                    db_context = f"(SQL 실행 오류: {exec_result.get('error','')})"
        except Exception as e:
            logger.warning(f"DB query failed: {e}")

    # ── 3. 통합 LLM 호출 ─────────────────────────────────
    context_blocks = []
    if rag_context:
        context_blocks.append(f"## 문서 지식\n{rag_context}")
    if db_context:
        context_blocks.append(f"## DB 실제 데이터 (SQL: {db_sql})\n{db_context}")
    if not context_blocks:
        context_blocks.append("(참고 가능한 문서 및 DB 데이터 없음 — 일반 지식으로 답변)")

    messages = [
        {"role": "system", "content": SYSTEM_ANALYZE},
        {"role": "user", "content": "\n\n".join(context_blocks) + f"\n\n## 질문\n{req.question}"},
    ]

    try:
        response = chat_completion(messages=messages)
        answer = response.choices[0].message.content or ""
    except Exception as e:
        answer = f"LLM 호출 실패: {e}"

    logger.info(
        f"Analyze: '{req.question[:50]}' | "
        f"RAG:{len(rag_sources)} docs | DB:{len(db_rows)} rows"
    )

    return {
        "answer": answer,
        "rag_sources": rag_sources,
        "db_sql": db_sql,
        "db_rows": db_rows[:50],
        "db_row_count": len(db_rows),
    }
