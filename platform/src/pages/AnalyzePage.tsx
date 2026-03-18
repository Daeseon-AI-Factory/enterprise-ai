import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChatMessage } from "@/components/ChatMessage";
import { SqlResultTable } from "@/components/SqlResultTable";
import { CodeBlock } from "@/components/CodeBlock";
import { analyzeApi, ragApi, sqlApi } from "@/lib/api";
import {
  Layers, Send, Loader2, FileText, Database, CheckSquare,
} from "lucide-react";

interface RagSource { collection: string; filename: string; score: number }
interface Schema { schema_id: string; table_count: number }
interface Collection { name: string; count: number }

export function AnalyzePage() {
  const [question, setQuestion] = useState("");
  const [schemaId, setSchemaId] = useState("");
  const [runSql, setRunSql] = useState(true);
  const [loading, setLoading] = useState(false);

  // Results
  const [answer, setAnswer] = useState("");
  const [ragSources, setRagSources] = useState<RagSource[]>([]);
  const [dbSql, setDbSql] = useState("");
  const [dbRows, setDbRows] = useState<Record<string, unknown>[]>([]);
  const [dbRowCount, setDbRowCount] = useState(0);

  // Options
  const [schemas, setSchemas] = useState<Schema[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);

  const loadOptions = useCallback(async () => {
    try {
      const [sc, co] = await Promise.all([
        sqlApi.listSchemas(),
        ragApi.listCollections(),
      ]);
      setSchemas(sc.data);
      setCollections(co.data);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { loadOptions(); }, [loadOptions]);

  const handleAnalyze = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setAnswer(""); setRagSources([]); setDbSql(""); setDbRows([]); setDbRowCount(0);

    try {
      const res = await analyzeApi.query({
        question,
        schema_id: schemaId || undefined,
        run_sql: runSql,
      });
      setAnswer(res.data.answer);
      setRagSources(res.data.rag_sources ?? []);
      setDbSql(res.data.db_sql ?? "");
      setDbRows(res.data.db_rows ?? []);
      setDbRowCount(res.data.db_row_count ?? 0);
    } catch {
      setAnswer("분석 실패. 백엔드를 확인해주세요.");
    } finally {
      setLoading(false);
    }
  };

  const dbColumns = dbRows.length > 0 ? Object.keys(dbRows[0]) : [];

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Layers className="h-6 w-6" />
          통합 진단
        </h1>
        <p className="text-muted-foreground mt-1">
          RAG 문서 지식 + DB 실시간 데이터를 동시에 조회해 정밀 답변을 생성합니다
        </p>
      </div>

      {/* Query card */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          {/* Options row */}
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground whitespace-nowrap">DB 스키마:</span>
              <select
                className="h-9 rounded-md border bg-background px-3 text-sm"
                value={schemaId}
                onChange={e => setSchemaId(e.target.value)}
              >
                <option value="">-- 선택 안함 --</option>
                {schemas.map(s => (
                  <option key={s.schema_id} value={s.schema_id}>
                    {s.schema_id} ({s.table_count}테이블)
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="runSql"
                checked={runSql}
                onChange={e => setRunSql(e.target.checked)}
                className="h-4 w-4"
              />
              <label htmlFor="runSql" className="text-sm text-muted-foreground cursor-pointer flex items-center gap-1">
                <CheckSquare className="h-3.5 w-3.5" />
                SQL 실행
              </label>
            </div>
            {collections.length > 0 && (
              <span className="text-xs text-muted-foreground">
                RAG: {collections.length}개 컬렉션 ({collections.reduce((a, c) => a + c.count, 0)}청크)
              </span>
            )}
          </div>

          {/* Question input */}
          <div className="flex gap-2">
            <Input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="예: 오늘 A라인 불량률이 왜 높은지 원인을 분석해줘"
              onKeyDown={e => e.key === "Enter" && !loading && handleAnalyze()}
              disabled={loading}
            />
            <Button onClick={handleAnalyze} disabled={loading || !question.trim()}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>

          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>문서 검색 + DB 조회 + LLM 분석 중...</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Answer */}
      {answer && (
        <Card>
          <CardContent className="pt-6">
            <ChatMessage role="assistant" content={answer} />
          </CardContent>
        </Card>
      )}

      {/* Sources + SQL side by side */}
      {(ragSources.length > 0 || dbSql) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* RAG sources */}
          {ragSources.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  참고 문서 ({ragSources.length}개)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {ragSources.map((s, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs py-1">
                      <FileText className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                      <span className="font-medium truncate">{s.filename}</span>
                      <span className="text-muted-foreground whitespace-nowrap">({s.collection})</span>
                      <span className="ml-auto text-muted-foreground whitespace-nowrap">
                        {(s.score * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Generated SQL */}
          {dbSql && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  실행된 SQL
                  {dbRowCount > 0 && (
                    <span className="ml-auto text-xs text-muted-foreground font-normal">
                      {dbRowCount}행
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <CodeBlock code={dbSql} language="sql" />
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* DB result table */}
      {dbColumns.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">DB 조회 결과</CardTitle>
          </CardHeader>
          <CardContent>
            <SqlResultTable columns={dbColumns} rows={dbRows} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
