import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/CodeBlock";
import { SqlResultTable } from "@/components/SqlResultTable";
import { sqlApi } from "@/lib/api";
import { Database, Play, Sparkles } from "lucide-react";

export function SqlPage() {
  const [question, setQuestion] = useState("");
  const [sql, setSql] = useState("");
  const [explanation, setExplanation] = useState("");
  const [columns, setColumns] = useState<string[]>([]);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);

  const handleGenerate = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setSql("");
    setExplanation("");
    setColumns([]);
    setRows([]);

    try {
      const res = await sqlApi.generate(question);
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
      if (res.data.columns) setColumns(res.data.columns);
      if (res.data.rows) setRows(res.data.rows);
      if (res.data.message) setExplanation(res.data.message);
    } catch {
      setExplanation("SQL 실행 실패.");
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Database className="h-6 w-6" />
          Text-to-SQL
        </h1>
        <p className="text-muted-foreground mt-1">
          자연어로 질문하면 SQL 쿼리를 생성합니다. SELECT만 허용됩니다.
        </p>
      </div>

      {/* Input */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="예: 지난달 A라인 불량률 보여줘"
              onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
            />
            <Button onClick={handleGenerate} disabled={loading || !question.trim()}>
              <Sparkles className="h-4 w-4 mr-2" />
              생성
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Generated SQL */}
      {sql && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">생성된 SQL</CardTitle>
              <Button onClick={handleExecute} disabled={executing} size="sm">
                <Play className="h-3 w-3 mr-1" />
                실행
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <CodeBlock code={sql} language="sql" />
            {explanation && (
              <p className="text-sm text-muted-foreground mt-3">{explanation}</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Results */}
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
    </div>
  );
}
