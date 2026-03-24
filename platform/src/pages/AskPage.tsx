import { useState, useEffect } from "react";
import { agentApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Bot, Send, Loader2, Clock, Plus, Trash2, Save,
  CheckCircle, ChevronDown, ChevronUp,
} from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Agent {
  id: string;
  name: string;
  name_en: string;
  role: string;
  system_prompt: string;
  tools: string[];
  domain: string;
  icon: string;
}

interface AgentResult {
  agent_id: string;
  agent_name: string;
  icon: string;
  answer: string;
  tools_used: string[];
  elapsed: number;
}

interface OrchestrateResult {
  question: string;
  agents_used: string[];
  results: AgentResult[];
  final_answer: string;
  elapsed: number;
}

export function AskPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OrchestrateResult | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [autoMode, setAutoMode] = useState(true);
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());

  // Agent management
  const [editAgent, setEditAgent] = useState<Agent | null>(null);
  const [newAgent, setNewAgent] = useState(false);

  useEffect(() => {
    agentApi.list().then(r => setAgents(r.data)).catch(() => {});
  }, []);

  const handleAsk = async () => {
    if (!question.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await agentApi.ask(
        question,
        autoMode ? undefined : selectedAgents.length > 0 ? selectedAgents : undefined
      );
      setResult(res.data);
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

  const handleSaveAgent = async (agent: Agent) => {
    try {
      if (newAgent) {
        await agentApi.create(agent);
      } else {
        await agentApi.update(agent.id, agent);
      }
      const res = await agentApi.list();
      setAgents(res.data);
      setEditAgent(null);
      setNewAgent(false);
    } catch {}
  };

  const handleDeleteAgent = async (id: string) => {
    await agentApi.delete(id);
    const res = await agentApi.list();
    setAgents(res.data);
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">업무 질의</h1>
        <p className="text-muted-foreground text-sm mt-1">
          멀티에이전트가 RAG + DB + 문서를 종합하여 답변합니다
        </p>
      </div>

      <Tabs defaultValue="ask">
        <TabsList>
          <TabsTrigger value="ask">질의</TabsTrigger>
          <TabsTrigger value="agents">에이전트 관리</TabsTrigger>
        </TabsList>

        {/* ── 질의 탭 ── */}
        <TabsContent value="ask" className="space-y-4">
          {/* Agent selector */}
          <Card>
            <CardContent className="pt-4">
              <div className="flex items-center gap-3 mb-3">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={autoMode}
                    onChange={e => setAutoMode(e.target.checked)}
                    className="rounded"
                  />
                  자동 에이전트 선택 (AI가 판단)
                </label>
              </div>
              {!autoMode && (
                <div className="flex flex-wrap gap-2">
                  {agents.map(a => (
                    <button
                      key={a.id}
                      onClick={() => toggleAgent(a.id)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                        selectedAgents.includes(a.id)
                          ? "bg-primary text-primary-foreground border-primary"
                          : "bg-muted border-border hover:bg-muted/80"
                      }`}
                    >
                      {a.icon} {a.name}
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

          {/* Loading indicator */}
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
              {/* Agent execution timeline */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Bot className="h-4 w-4" />
                    에이전트 실행 결과
                    <span className="text-xs text-muted-foreground ml-auto flex items-center gap-1">
                      <Clock className="h-3 w-3" /> 총 {result.elapsed}초
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {result.results.map((r, i) => (
                    <div key={r.agent_id} className="border rounded-lg">
                      <button
                        onClick={() => toggleExpand(r.agent_id)}
                        className="w-full flex items-center gap-3 p-3 hover:bg-muted/50 transition-colors"
                      >
                        <span className="text-lg">{r.icon}</span>
                        <div className="flex-1 text-left">
                          <span className="text-sm font-medium">{r.agent_name}</span>
                          <span className="text-xs text-muted-foreground ml-2">
                            {r.tools_used.map(t => t.toUpperCase()).join(", ") || "LLM only"}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">{r.elapsed}초</span>
                          <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                          {expandedAgents.has(r.agent_id)
                            ? <ChevronUp className="h-3.5 w-3.5" />
                            : <ChevronDown className="h-3.5 w-3.5" />
                          }
                        </div>
                      </button>
                      {expandedAgents.has(r.agent_id) && (
                        <div className="px-3 pb-3 border-t bg-muted/20">
                          <div className="prose prose-sm max-w-none mt-2 dark:prose-invert">
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
        </TabsContent>

        {/* ── 에이전트 관리 탭 ── */}
        <TabsContent value="agents" className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-muted-foreground">등록된 에이전트 {agents.length}개</p>
            <Button size="sm" variant="outline" onClick={() => {
              setNewAgent(true);
              setEditAgent({
                id: "", name: "", name_en: "", role: "",
                system_prompt: "", tools: [], domain: "COMMON", icon: "🤖",
              });
            }}>
              <Plus className="h-3.5 w-3.5 mr-1" /> 새 에이전트
            </Button>
          </div>

          {/* Edit form */}
          {editAgent && (
            <Card className="border-primary">
              <CardContent className="pt-4 space-y-3">
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="text-xs text-muted-foreground">ID</label>
                    <input
                      value={editAgent.id}
                      onChange={e => setEditAgent({ ...editAgent, id: e.target.value })}
                      disabled={!newAgent}
                      className="w-full mt-1 px-2 py-1.5 text-sm border rounded bg-background"
                      placeholder="quality_analyst"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">이름</label>
                    <input
                      value={editAgent.name}
                      onChange={e => setEditAgent({ ...editAgent, name: e.target.value })}
                      className="w-full mt-1 px-2 py-1.5 text-sm border rounded bg-background"
                      placeholder="품질 분석관"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">도메인</label>
                    <input
                      value={editAgent.domain}
                      onChange={e => setEditAgent({ ...editAgent, domain: e.target.value })}
                      className="w-full mt-1 px-2 py-1.5 text-sm border rounded bg-background"
                      placeholder="MES"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">역할 설명</label>
                  <input
                    value={editAgent.role}
                    onChange={e => setEditAgent({ ...editAgent, role: e.target.value })}
                    className="w-full mt-1 px-2 py-1.5 text-sm border rounded bg-background"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">시스템 프롬프트</label>
                  <Textarea
                    value={editAgent.system_prompt}
                    onChange={e => setEditAgent({ ...editAgent, system_prompt: e.target.value })}
                    className="min-h-[100px] mt-1 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">도구</label>
                  <div className="flex gap-2 mt-1">
                    {["sql", "rag", "confluence"].map(tool => (
                      <label key={tool} className="flex items-center gap-1 text-xs">
                        <input
                          type="checkbox"
                          checked={editAgent.tools.includes(tool)}
                          onChange={e => {
                            const tools = e.target.checked
                              ? [...editAgent.tools, tool]
                              : editAgent.tools.filter(t => t !== tool);
                            setEditAgent({ ...editAgent, tools });
                          }}
                        />
                        {tool.toUpperCase()}
                      </label>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2 justify-end">
                  <Button size="sm" variant="ghost" onClick={() => { setEditAgent(null); setNewAgent(false); }}>
                    취소
                  </Button>
                  <Button size="sm" onClick={() => handleSaveAgent(editAgent)}>
                    <Save className="h-3.5 w-3.5 mr-1" /> 저장
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Agent list */}
          <div className="space-y-2">
            {agents.map(a => (
              <Card key={a.id}>
                <CardContent className="py-3 flex items-center gap-3">
                  <span className="text-2xl">{a.icon}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{a.name}</span>
                      <span className="text-xs bg-muted px-1.5 py-0.5 rounded">{a.domain}</span>
                      {a.tools.map(t => (
                        <span key={t} className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 px-1.5 py-0.5 rounded">
                          {t}
                        </span>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{a.role}</p>
                  </div>
                  <div className="flex gap-1">
                    <Button size="sm" variant="ghost" onClick={() => { setEditAgent(a); setNewAgent(false); }}>
                      편집
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDeleteAgent(a.id)}>
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
