import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  MessageSquare, FileText, Database, Code2, Activity,
  Globe, GitBranch, Layers, Clock, CheckCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { healthApi, ragApi, chatApi, sqlApi } from "@/lib/api";

interface HealthInfo { status: string; mode: string; model: string; }
interface Stat { label: string; value: string | number; icon: React.ElementType; color: string; }

const quickLinks = [
  { to: "/chat",      icon: MessageSquare, title: "AI Chat",       desc: "대화 기록 이어서 질문", color: "bg-blue-500" },
  { to: "/rag",       icon: FileText,      title: "RAG",           desc: "문서 기반 질의응답",     color: "bg-emerald-500" },
  { to: "/sql",       icon: Database,      title: "Text-to-SQL",   desc: "자연어로 DB 조회",       color: "bg-amber-500" },
  { to: "/analyze",   icon: Layers,        title: "통합 진단",      desc: "RAG + DB 동시 분석",    color: "bg-rose-500" },
  { to: "/git",       icon: GitBranch,     title: "Git Code RAG",  desc: "소스코드 색인 & 질의",   color: "bg-orange-500" },
  { to: "/confluence",icon: Globe,         title: "Confluence",    desc: "사내 문서 동기화",       color: "bg-blue-400" },
];

export function DashboardPage() {
  const [health, setHealth]           = useState<HealthInfo | null>(null);
  const [collections, setCollections] = useState<Array<{ name: string; count: number }>>([]);
  const [conversations, setConversations] = useState<number>(0);
  const [schemaCount, setSchemaCount] = useState<number>(0);
  const [loading, setLoading]         = useState(true);

  useEffect(() => {
    Promise.all([
      healthApi.check().then(r => setHealth(r.data)).catch(() => {}),
      ragApi.listCollections().then(r => setCollections(r.data)).catch(() => {}),
      chatApi.listConversations().then(r => setConversations(r.data.length)).catch(() => {}),
      sqlApi.listSchemas().then(r => setSchemaCount(r.data.length)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const totalChunks = collections.reduce((s, c) => s + c.count, 0);
  const gitCollections = collections.filter(c => c.name.startsWith("git_"));
  const docCollections = collections.filter(c => !c.name.startsWith("git_"));

  const stats: Stat[] = [
    { label: "RAG 컬렉션", value: docCollections.length, icon: FileText, color: "text-emerald-600" },
    { label: "Git 소스 색인", value: gitCollections.length, icon: GitBranch, color: "text-orange-600" },
    { label: "DB 스키마", value: schemaCount, icon: Database, color: "text-blue-600" },
    { label: "색인된 청크", value: totalChunks.toLocaleString(), icon: Layers, color: "text-purple-600" },
    { label: "대화 기록", value: conversations, icon: MessageSquare, color: "text-slate-600" },
    { label: "LLM 모델", value: health?.model ?? "...", icon: Activity, color: "text-amber-600" },
  ];

  return (
    <div className="p-8 space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Enterprise AI Platform</h1>
          <p className="text-muted-foreground text-sm mt-1">
            {health
              ? <span className="flex items-center gap-1.5">
                  <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  백엔드 정상 · {health.mode === "airgap" ? "폐쇄망 모드" : "로컬 모드"}
                </span>
              : "백엔드 연결 중..."
            }
          </p>
        </div>
        <div className="text-xs text-muted-foreground flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {new Date().toLocaleString("ko-KR")}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className={`text-2xl font-bold mt-1 ${s.color}`}>{loading ? "..." : s.value}</p>
                </div>
                <s.icon className={`h-8 w-8 opacity-20 ${s.color}`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Collections */}
      {collections.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Layers className="h-4 w-4" /> RAG 컬렉션 현황
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-2">
              {collections.map(c => (
                <div key={c.name} className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
                  <div className="flex items-center gap-2">
                    {c.name.startsWith("confluence_") ? <Globe className="h-3 w-3 text-blue-500" /> :
                     c.name.startsWith("git_") ? <GitBranch className="h-3 w-3 text-orange-500" /> :
                     <FileText className="h-3 w-3 text-muted-foreground" />}
                    <span className="text-xs font-medium truncate max-w-[120px]">{c.name}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">{c.count.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick links */}
      <div>
        <h2 className="text-sm font-medium text-muted-foreground mb-3">바로가기</h2>
        <div className="grid grid-cols-3 gap-3">
          {quickLinks.map((item) => (
            <Link key={item.to} to={item.to}>
              <Card className="hover:shadow-md transition-shadow cursor-pointer">
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center gap-3">
                    <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${item.color}`}>
                      <item.icon className="h-4 w-4 text-white" />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{item.title}</p>
                      <p className="text-xs text-muted-foreground">{item.desc}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
