import { useState, useEffect } from "react";
import { agentApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Bot, Send, Loader2, Clock,
  CheckCircle, ChevronDown, ChevronUp,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Agent {
  id: string; name: string; icon: string;
  tools: string[]; tables: string[]; collections: string[];
  domain: string;
}

interface AgentResult {
  agent_id: string; agent_name: string; icon: string;
  answer: string; tools_used: string[];
  tables_scope: string[]; collections_scope: string[];
  elapsed: number;
}

interface OrchestrateResult {
  question: string; agents_used: string[];
  results: AgentResult[]; final_answer: string; elapsed: number;
}

function loadSession<T>(key: string, fallback: T): T {
  try {
    const v = sessionStorage.getItem(`ask_${key}`);
    return v ? JSON.parse(v) : fallback;
  } catch { return fallback; }
}
function saveSession(key: string, value: unknown) {
  sessionStorage.setItem(`ask_${key}`, JSON.stringify(value));
}

export function AskPage() {
  const [question, setQuestion] = useState(() => loadSession("question", ""));
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OrchestrateResult | null>(() => loadSession("result", null));
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>(() => loadSession("selectedAgents", []));
  const [autoMode, setAutoMode] = useState(() => loadSession("autoMode", true));
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(
    () => new Set(loadSession<string[]>("expandedAgents", []))
  );

  // Persist state on change
  useEffect(() => {
    saveSession("question", question);
    saveSession("result", result);
    saveSession("selectedAgents", selectedAgents);
    saveSession("autoMode", autoMode);
    saveSession("expandedAgents", Array.from(expandedAgents));
  }, [question, result, selectedAgents, autoMode, expandedAgents]);

  useEffect(() => {
    agentApi.list().then(r => setAgents(r.data)).catch(() => {});
  }, []);

  const handleAsk = async () => {
    if (!question.trim() || loading) return;
    setLoading(true);
    setResult(null);
    setExpandedAgents(new Set());
    try {
      const res = await agentApi.ask(
        question,
        autoMode ? undefined : selectedAgents.length > 0 ? selectedAgents : undefined
      );
      setResult(res.data);
      // Auto-expand all agents
      setExpandedAgents(new Set(res.data.results.map((r: AgentResult) => r.agent_id)));
    } catch {
      setResult({
        question, agents_used: [], results: [],
        final_answer: "오류가 발생했습니다. 백엔드 로그를 확인해주세요.", elapsed: 0,
      });
    } finally {
      setLoading(false);
    }
  };

  const toggleAgent = (id: string) => {
    setSelectedAgents(prev =>
      prev.includes(id) ? prev.filter(a => a !== id) : [...prev, id]
    );
  };

  const toggleExpand = (id: string) => {
    setExpandedAgents(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">업무 질의</h1>
        <p className="text-muted-foreground text-sm mt-1">
          멀티에이전트가 RAG + DB를 종합하여 답변합니다. 에이전트 설정은 에이전트 관리 메뉴에서 가능합니다.
        </p>
      </div>

      {/* Agent selector */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-3 mb-3">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox" checked={autoMode}
                onChange={e => setAutoMode(e.target.checked)} className="rounded"
              />
              자동 에이전트 선택 (AI가 판단)
            </label>
          </div>
          {!autoMode && (
            <div className="flex flex-wrap gap-2">
              {agents.map(a => (
                <button key={a.id} onClick={() => toggleAgent(a.id)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                    selectedAgents.includes(a.id)
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-muted border-border hover:bg-muted/80"
                  }`}>
                  {a.icon} {a.name}
                  <span className="ml-1 opacity-60">
                    {a.tables?.length ? `${a.tables.length}T` : ""}
                    {a.collections?.length ? ` ${a.collections.length}C` : ""}
                  </span>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Question input */}
      <div className="flex gap-2">
        <Textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          placeholder="예: A라인 불량 급증 원인 분석하고 관련 SOP 찾아서 보고서 써줘"
          className="min-h-[80px] flex-1"
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleAsk(); } }}
        />
        <Button onClick={handleAsk} disabled={loading || !question.trim()} className="self-end">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </Button>
      </div>

      {/* Loading */}
      {loading && (
        <Card>
          <CardContent className="py-8 text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
            <p className="text-sm text-muted-foreground mt-3">에이전트 협업 중...</p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-4">
          {/* Agent timeline */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2">
                <Bot className="h-4 w-4" />
                에이전트 실행 결과 ({result.results.length}개)
                <span className="text-xs text-muted-foreground ml-auto flex items-center gap-1">
                  <Clock className="h-3 w-3" /> 총 {result.elapsed}초
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {result.results.map(r => (
                <div key={r.agent_id} className="border rounded-lg">
                  <button onClick={() => toggleExpand(r.agent_id)}
                    className="w-full flex items-center gap-3 p-3 hover:bg-muted/50 transition-colors">
                    <span className="text-lg">{r.icon}</span>
                    <div className="flex-1 text-left">
                      <span className="text-sm font-medium">{r.agent_name}</span>
                      <span className="text-xs text-muted-foreground ml-2">
                        {r.tools_used.map(t => t.toUpperCase()).join(", ") || "LLM only"}
                      </span>
                      {r.tables_scope && r.tables_scope[0] !== "ALL" && (
                        <span className="text-xs text-amber-600 ml-2">
                          T: {r.tables_scope.join(",")}
                        </span>
                      )}
                      {r.collections_scope && r.collections_scope[0] !== "ALL" && (
                        <span className="text-xs text-emerald-600 ml-2">
                          C: {r.collections_scope.join(",")}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">{r.elapsed}초</span>
                      <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                      {expandedAgents.has(r.agent_id)
                        ? <ChevronUp className="h-3.5 w-3.5" />
                        : <ChevronDown className="h-3.5 w-3.5" />}
                    </div>
                  </button>
                  {expandedAgents.has(r.agent_id) && (
                    <div className="px-4 pb-4 border-t bg-muted/20">
                      <div className="prose prose-sm max-w-none mt-3 dark:prose-invert">
                        <ReactMarkdown>{r.answer}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Final answer */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">최종 답변</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm max-w-none dark:prose-invert">
                <ReactMarkdown>{result.final_answer}</ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
