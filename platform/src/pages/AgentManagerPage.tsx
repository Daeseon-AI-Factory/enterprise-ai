import { useState, useEffect } from "react";
import { agentApi, ragApi, sqlApi } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Plus, Trash2, Save, X } from "lucide-react";

interface Agent {
  id: string;
  name: string;
  name_en: string;
  role: string;
  system_prompt: string;
  tools: string[];
  tables: string[];
  collections: string[];
  domain: string;
  icon: string;
}

export function AgentManagerPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [editAgent, setEditAgent] = useState<Agent | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [availableTables, setAvailableTables] = useState<string[]>([]);
  const [availableCollections, setAvailableCollections] = useState<string[]>([]);

  useEffect(() => {
    agentApi.list().then(r => setAgents(r.data)).catch(() => {});
    // Load available tables from schemas
    sqlApi.listSchemas().then(r => {
      if (r.data.length > 0) {
        const schemaId = r.data[0].schema_id;
        sqlApi.generate("list all table names", schemaId); // triggers schema load
      }
    }).catch(() => {});
    // Load available collections
    ragApi.listCollections().then(r => {
      setAvailableCollections(r.data.map((c: { name: string }) => c.name));
    }).catch(() => {});
  }, []);

  const handleSave = async (agent: Agent) => {
    try {
      if (isNew) {
        await agentApi.create(agent);
      } else {
        await agentApi.update(agent.id, agent);
      }
      const res = await agentApi.list();
      setAgents(res.data);
      setEditAgent(null);
      setIsNew(false);
    } catch {}
  };

  const handleDelete = async (id: string) => {
    if (!confirm("이 에이전트를 삭제하시겠습니까?")) return;
    await agentApi.delete(id);
    const res = await agentApi.list();
    setAgents(res.data);
  };

  const startNew = () => {
    setIsNew(true);
    setEditAgent({
      id: "", name: "", name_en: "", role: "",
      system_prompt: "", tools: [], tables: [], collections: [],
      domain: "COMMON", icon: "🤖",
    });
  };

  const toggleItem = (list: string[], item: string): string[] =>
    list.includes(item) ? list.filter(x => x !== item) : [...list, item];

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold">에이전트 관리</h1>
          <p className="text-muted-foreground text-sm mt-1">
            도메인별 에이전트를 생성하고, 접근 가능한 테이블과 문서 컬렉션을 지정합니다
          </p>
        </div>
        <Button onClick={startNew}>
          <Plus className="h-4 w-4 mr-1" /> 새 에이전트
        </Button>
      </div>

      {/* Edit/Create Form */}
      {editAgent && (
        <Card className="border-primary">
          <CardContent className="pt-5 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-semibold">{isNew ? "새 에이전트 생성" : `편집: ${editAgent.name}`}</h3>
              <Button size="sm" variant="ghost" onClick={() => { setEditAgent(null); setIsNew(false); }}>
                <X className="h-4 w-4" />
              </Button>
            </div>

            {/* Basic info */}
            <div className="grid grid-cols-4 gap-3">
              <div>
                <label className="text-xs text-muted-foreground">ID</label>
                <input value={editAgent.id} disabled={!isNew}
                  onChange={e => setEditAgent({ ...editAgent, id: e.target.value })}
                  className="w-full mt-1 px-2 py-1.5 text-sm border rounded bg-background" placeholder="quality_analyst" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">이름 (KO)</label>
                <input value={editAgent.name}
                  onChange={e => setEditAgent({ ...editAgent, name: e.target.value })}
                  className="w-full mt-1 px-2 py-1.5 text-sm border rounded bg-background" placeholder="품질 분석관" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">도메인</label>
                <input value={editAgent.domain}
                  onChange={e => setEditAgent({ ...editAgent, domain: e.target.value })}
                  className="w-full mt-1 px-2 py-1.5 text-sm border rounded bg-background" placeholder="MES" />
              </div>
              <div>
                <label className="text-xs text-muted-foreground">아이콘</label>
                <input value={editAgent.icon}
                  onChange={e => setEditAgent({ ...editAgent, icon: e.target.value })}
                  className="w-full mt-1 px-2 py-1.5 text-sm border rounded bg-background" placeholder="🔍" />
              </div>
            </div>

            <div>
              <label className="text-xs text-muted-foreground">역할 설명</label>
              <input value={editAgent.role}
                onChange={e => setEditAgent({ ...editAgent, role: e.target.value })}
                className="w-full mt-1 px-2 py-1.5 text-sm border rounded bg-background"
                placeholder="Oracle DB에서 불량 데이터를 분석합니다" />
            </div>

            <div>
              <label className="text-xs text-muted-foreground">시스템 프롬프트</label>
              <Textarea value={editAgent.system_prompt}
                onChange={e => setEditAgent({ ...editAgent, system_prompt: e.target.value })}
                className="min-h-[100px] mt-1 text-sm" />
            </div>

            {/* Tools */}
            <div>
              <label className="text-xs text-muted-foreground mb-1 block">도구</label>
              <div className="flex gap-2">
                {["sql", "rag"].map(tool => (
                  <button key={tool}
                    onClick={() => setEditAgent({ ...editAgent, tools: toggleItem(editAgent.tools, tool) })}
                    className={`px-3 py-1.5 rounded text-xs font-medium border ${
                      editAgent.tools.includes(tool)
                        ? "bg-blue-600 text-white border-blue-600"
                        : "bg-muted border-border"
                    }`}>
                    {tool.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            {/* Tables scope */}
            {editAgent.tools.includes("sql") && (
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">
                  SQL 범위 — 접근 가능한 테이블 (비어있으면 전체)
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {(availableTables.length > 0 ? availableTables : [
                    "PRODUCTION_LINES", "PRODUCTS", "PRODUCTION_ORDERS",
                    "WORK_RESULTS", "DEFECTS", "EQUIPMENT",
                    "WAREHOUSES", "ITEMS", "INVENTORY", "INBOUND", "OUTBOUND",
                  ]).map(table => (
                    <button key={table}
                      onClick={() => setEditAgent({ ...editAgent, tables: toggleItem(editAgent.tables, table) })}
                      className={`px-2 py-1 rounded text-xs border ${
                        editAgent.tables.includes(table)
                          ? "bg-amber-600 text-white border-amber-600"
                          : "bg-muted border-border"
                      }`}>
                      {table}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Collections scope */}
            {editAgent.tools.includes("rag") && (
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">
                  RAG 범위 — 검색할 컬렉션 (비어있으면 전체)
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {availableCollections.map(col => (
                    <button key={col}
                      onClick={() => setEditAgent({ ...editAgent, collections: toggleItem(editAgent.collections, col) })}
                      className={`px-2 py-1 rounded text-xs border ${
                        editAgent.collections.includes(col)
                          ? "bg-emerald-600 text-white border-emerald-600"
                          : "bg-muted border-border"
                      }`}>
                      {col}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" onClick={() => { setEditAgent(null); setIsNew(false); }}>취소</Button>
              <Button onClick={() => handleSave(editAgent)}>
                <Save className="h-4 w-4 mr-1" /> 저장
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Agent List */}
      <div className="space-y-3">
        {agents.map(a => (
          <Card key={a.id}>
            <CardContent className="py-4">
              <div className="flex items-start gap-3">
                <span className="text-3xl">{a.icon}</span>
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold">{a.name}</span>
                    <span className="text-xs bg-muted px-2 py-0.5 rounded">{a.domain}</span>
                    {a.tools?.map(t => (
                      <span key={t} className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 px-2 py-0.5 rounded">
                        {t.toUpperCase()}
                      </span>
                    ))}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{a.role}</p>
                  <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                    {a.tables && a.tables.length > 0 && (
                      <span>테이블: {a.tables.join(", ")}</span>
                    )}
                    {a.collections && a.collections.length > 0 && (
                      <span>컬렉션: {a.collections.join(", ")}</span>
                    )}
                    {(!a.tables || a.tables.length === 0) && a.tools?.includes("sql") && (
                      <span>테이블: 전체</span>
                    )}
                    {(!a.collections || a.collections.length === 0) && a.tools?.includes("rag") && (
                      <span>컬렉션: 전체</span>
                    )}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button size="sm" variant="outline" onClick={() => { setEditAgent(a); setIsNew(false); }}>
                    편집
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => handleDelete(a.id)}>
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
