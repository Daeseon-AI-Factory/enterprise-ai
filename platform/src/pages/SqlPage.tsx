import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CodeBlock } from "@/components/CodeBlock";
import { SqlResultTable } from "@/components/SqlResultTable";
import { sqlApi } from "@/lib/api";
import {
  Database, Play, Sparkles, CheckCircle, AlertCircle,
  Loader2, Trash2, RefreshCw, Plug,
} from "lucide-react";

interface Schema { schema_id: string; table_count: number; description?: string }

interface DbConn {
  db_type: string; host: string; port: string;
  database: string; username: string; password: string;
  owner: string; description: string; schema_id: string;
}

const DEFAULT_CONN: DbConn = {
  db_type: "oracle", host: "localhost", port: "1521",
  database: "XEPDB1", username: "MESADMIN", password: "mesadmin123",
  owner: "", description: "", schema_id: "mes_oracle",
};

interface SqlHistoryEntry {
  question: string; sql: string; explanation: string;
  columns: string[]; rows: Record<string, unknown>[]; timestamp: string;
}

function loadSql<T>(key: string, fallback: T): T {
  try { const v = sessionStorage.getItem(`sql_${key}`); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
}

export function SqlPage() {
  // ── Query tab ──
  const [question, setQuestion] = useState(() => loadSql("question", ""));
  const [schemaId, setSchemaId] = useState(() => loadSql("schemaId", ""));
  const [sql, setSql] = useState(() => loadSql("sql", ""));
  const [explanation, setExplanation] = useState(() => loadSql("explanation", ""));
  const [columns, setColumns] = useState<string[]>(() => loadSql("columns", []));
  const [rows, setRows] = useState<Record<string, unknown>[]>(() => loadSql("rows", []));
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [sqlHistory, setSqlHistory] = useState<SqlHistoryEntry[]>(() => loadSql("history", []));

  // Persist query state
  useEffect(() => {
    sessionStorage.setItem("sql_question", JSON.stringify(question));
    sessionStorage.setItem("sql_schemaId", JSON.stringify(schemaId));
    sessionStorage.setItem("sql_sql", JSON.stringify(sql));
    sessionStorage.setItem("sql_explanation", JSON.stringify(explanation));
    sessionStorage.setItem("sql_columns", JSON.stringify(columns));
    sessionStorage.setItem("sql_rows", JSON.stringify(rows));
    sessionStorage.setItem("sql_history", JSON.stringify(sqlHistory));
  }, [question, schemaId, sql, explanation, columns, rows, sqlHistory]);

  // ── Schema tab ──
  const [schemas, setSchemas] = useState<Schema[]>([]);
  const [loadingSchemas, setLoadingSchemas] = useState(false);

  // ── Connection tab ──
  const [conn, setConn] = useState<DbConn>(DEFAULT_CONN);
  const [testResult, setTestResult] = useState<{ ok: boolean; msg: string } | null>(null);
  const [testing, setTesting] = useState(false);
  const [discovering, setDiscovering] = useState(false);
  const [discoverResult, setDiscoverResult] = useState<string | null>(null);

  const loadSchemas = useCallback(async () => {
    setLoadingSchemas(true);
    try {
      const res = await sqlApi.listSchemas();
      setSchemas(res.data);
    } catch {
      /* ignore */
    } finally {
      setLoadingSchemas(false);
    }
  }, []);

  useEffect(() => { loadSchemas(); }, [loadSchemas]);

  const handleGenerate = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setSql(""); setExplanation(""); setColumns([]); setRows([]);
    try {
      const res = await sqlApi.generate(question, schemaId || undefined);
      setSql(res.data.sql);
      setExplanation(res.data.explanation);
    } catch {
      setExplanation("SQL 생성 실패. 백엔드를 확인해주세요.");
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    if (!sql) return;
    setExecuting(true);
    try {
      const res = await sqlApi.execute(sql);
      const cols = res.data.columns || [];
      const rws = res.data.rows || [];
      setColumns(cols);
      setRows(rws);
      if (res.data.message) setExplanation(res.data.message);
      // 히스토리에 저장
      setSqlHistory(prev => [...prev, {
        question, sql, explanation,
        columns: cols, rows: rws,
        timestamp: new Date().toLocaleTimeString("ko-KR"),
      }]);
    } catch {
      setExplanation("SQL 실행 실패.");
    } finally {
      setExecuting(false);
    }
  };

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const res = await sqlApi.testConnection({
        db_type: conn.db_type,
        host: conn.host,
        port: parseInt(conn.port) || 1521,
        name: conn.database,
        user: conn.username,
        password: conn.password,
      });
      if (res.data.ok) {
        setTestResult({ ok: true, msg: "연결 성공" });
      } else {
        setTestResult({ ok: false, msg: res.data.error || "연결 실패" });
      }
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "연결 실패";
      setTestResult({ ok: false, msg });
    } finally {
      setTesting(false);
    }
  };

  const handleDiscover = async () => {
    if (!conn.schema_id.trim()) {
      setDiscoverResult("스키마 ID를 입력해주세요");
      return;
    }
    setDiscovering(true);
    setDiscoverResult(null);
    try {
      const res = await sqlApi.discoverSchema({
        schema_id: conn.schema_id,
        db_type: conn.db_type,
        host: conn.host,
        port: parseInt(conn.port) || 1521,
        name: conn.database,
        user: conn.username,
        password: conn.password,
        owner: conn.owner || undefined,
        description: conn.description || undefined,
      });
      setDiscoverResult(`✓ ${res.data.tables}개 테이블 탐색 완료 (ID: ${res.data.schema_id})`);
      loadSchemas();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "스키마 탐색 실패";
      setDiscoverResult(`✗ ${msg}`);
    } finally {
      setDiscovering(false);
    }
  };

  const handleDeleteSchema = async (id: string) => {
    if (!confirm(`스키마 '${id}'를 삭제하시겠습니까?`)) return;
    try {
      await sqlApi.deleteSchema(id);
      setSchemas(prev => prev.filter(s => s.schema_id !== id));
    } catch { /* ignore */ }
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Database className="h-6 w-6" />
          Text-to-SQL
        </h1>
        <p className="text-muted-foreground mt-1">
          자연어로 질문하면 SQL 쿼리를 생성합니다
        </p>
      </div>

      <Tabs defaultValue="query">
        <TabsList>
          <TabsTrigger value="query">질의</TabsTrigger>
          <TabsTrigger value="connection">DB 연결 / 스키마 탐색</TabsTrigger>
          <TabsTrigger value="schemas" onClick={loadSchemas}>등록된 스키마</TabsTrigger>
        </TabsList>

        {/* ── Query ── */}
        <TabsContent value="query" className="space-y-4">
          <Card>
            <CardContent className="pt-6 space-y-3">
              <div className="flex gap-2 items-center">
                <span className="text-sm text-muted-foreground whitespace-nowrap">스키마:</span>
                <select
                  className="h-9 rounded-md border bg-background px-3 text-sm max-w-[200px]"
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
              <div className="flex gap-2">
                <Input
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  placeholder="예: 지난달 A라인 불량률 보여줘"
                  onKeyDown={e => e.key === "Enter" && !loading && handleGenerate()}
                  disabled={loading}
                />
                <Button onClick={handleGenerate} disabled={loading || !question.trim()}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4 mr-1" />}
                  생성
                </Button>
              </div>
            </CardContent>
          </Card>

          {sql && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">생성된 SQL</CardTitle>
                  <Button onClick={handleExecute} disabled={executing} size="sm">
                    {executing ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Play className="h-3 w-3 mr-1" />}
                    실행
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <CodeBlock code={sql} language="sql" />
                {explanation && <p className="text-sm text-muted-foreground mt-3">{explanation}</p>}
              </CardContent>
            </Card>
          )}

          {columns.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">실행 결과</CardTitle>
              </CardHeader>
              <CardContent>
                <SqlResultTable columns={columns} rows={rows} />
              </CardContent>
            </Card>
          )}

          {/* 질의 히스토리 */}
          {sqlHistory.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{sqlHistory.length}개 질의 기록</span>
                <Button variant="ghost" size="sm" className="text-xs" onClick={() => setSqlHistory([])}>기록 지우기</Button>
              </div>
              {[...sqlHistory].reverse().map((entry, idx) => (
                <Card key={idx} className="bg-muted/30">
                  <CardContent className="pt-4 pb-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium">{entry.question}</p>
                      <span className="text-xs text-muted-foreground">{entry.timestamp}</span>
                    </div>
                    <CodeBlock code={entry.sql} language="sql" />
                    {entry.columns.length > 0 && (
                      <SqlResultTable columns={entry.columns} rows={entry.rows} />
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── DB Connection ── */}
        <TabsContent value="connection" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Plug className="h-4 w-4" />
                DB 연결 정보
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium mb-1 block">DB 종류</label>
                  <select
                    className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                    value={conn.db_type}
                    onChange={e => setConn({ ...conn, db_type: e.target.value, port: e.target.value === "oracle" ? "1521" : e.target.value === "postgresql" ? "5432" : "3306" })}
                  >
                    <option value="oracle">Oracle</option>
                    <option value="postgresql">PostgreSQL</option>
                    <option value="mysql">MySQL</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium mb-1 block">호스트</label>
                  <Input value={conn.host} onChange={e => setConn({ ...conn, host: e.target.value })} placeholder="localhost" />
                </div>
                <div>
                  <label className="text-xs font-medium mb-1 block">포트</label>
                  <Input value={conn.port} onChange={e => setConn({ ...conn, port: e.target.value })} placeholder="1521" />
                </div>
                <div>
                  <label className="text-xs font-medium mb-1 block">
                    {conn.db_type === "oracle" ? "서비스명 / SID" : "데이터베이스명"}
                  </label>
                  <Input value={conn.database} onChange={e => setConn({ ...conn, database: e.target.value })} placeholder="ORCL" />
                </div>
                <div>
                  <label className="text-xs font-medium mb-1 block">사용자명</label>
                  <Input value={conn.username} onChange={e => setConn({ ...conn, username: e.target.value })} />
                </div>
                <div>
                  <label className="text-xs font-medium mb-1 block">비밀번호</label>
                  <Input type="password" value={conn.password} onChange={e => setConn({ ...conn, password: e.target.value })} />
                </div>
              </div>

              <div className="flex gap-3 items-center">
                <Button variant="outline" onClick={handleTestConnection} disabled={testing}>
                  {testing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Plug className="h-4 w-4 mr-2" />}
                  연결 테스트
                </Button>
                {testResult && (
                  <span className={`flex items-center gap-1 text-sm ${testResult.ok ? "text-green-600" : "text-red-600"}`}>
                    {testResult.ok ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                    {testResult.msg}
                  </span>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">스키마 자동 탐색</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium mb-1 block">스키마 ID (저장 이름)</label>
                  <Input
                    value={conn.schema_id}
                    onChange={e => setConn({ ...conn, schema_id: e.target.value })}
                    placeholder="예: mes_prod"
                  />
                </div>
                {conn.db_type === "oracle" && (
                  <div>
                    <label className="text-xs font-medium mb-1 block">Owner (스키마 소유자, 선택)</label>
                    <Input
                      value={conn.owner}
                      onChange={e => setConn({ ...conn, owner: e.target.value })}
                      placeholder="예: MES_OWNER (비우면 전체)"
                    />
                  </div>
                )}
                <div className="col-span-2">
                  <label className="text-xs font-medium mb-1 block">설명 (선택)</label>
                  <Input
                    value={conn.description}
                    onChange={e => setConn({ ...conn, description: e.target.value })}
                    placeholder="예: MES 생산 데이터베이스"
                  />
                </div>
              </div>
              <div className="flex gap-3 items-center">
                <Button onClick={handleDiscover} disabled={discovering || !conn.schema_id.trim()}>
                  {discovering ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Database className="h-4 w-4 mr-2" />}
                  테이블 자동 탐색 및 저장
                </Button>
                {discoverResult && (
                  <span className={`text-sm ${discoverResult.startsWith("✓") ? "text-green-600" : "text-red-600"}`}>
                    {discoverResult}
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                탐색한 스키마는 서버에 저장되며, Text-to-SQL 질의 시 컨텍스트로 사용됩니다.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Schemas ── */}
        <TabsContent value="schemas">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center justify-between">
                등록된 스키마
                <Button variant="ghost" size="sm" onClick={loadSchemas} disabled={loadingSchemas}>
                  <RefreshCw className={`h-4 w-4 ${loadingSchemas ? "animate-spin" : ""}`} />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {schemas.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  등록된 스키마 없음. "DB 연결 / 스키마 탐색" 탭에서 자동 탐색하세요.
                </p>
              ) : (
                <div className="space-y-2">
                  {schemas.map(s => (
                    <div key={s.schema_id} className="flex items-center justify-between rounded-lg border px-4 py-3">
                      <div>
                        <span className="font-medium text-sm">{s.schema_id}</span>
                        <span className="text-xs text-muted-foreground ml-2">{s.table_count}개 테이블</span>
                        {s.description && (
                          <span className="text-xs text-muted-foreground ml-2">— {s.description}</span>
                        )}
                      </div>
                      <Button
                        variant="ghost" size="sm" className="text-red-500 hover:text-red-700"
                        onClick={() => handleDeleteSchema(s.schema_id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
