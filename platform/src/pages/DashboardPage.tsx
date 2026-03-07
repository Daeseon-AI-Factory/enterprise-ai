import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { MessageSquare, FileText, Database, Code2, Activity } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { healthApi } from "@/lib/api";

interface HealthInfo {
  status: string;
  mode: string;
  model: string;
}

const features = [
  { to: "/chat", icon: MessageSquare, title: "AI Chat", desc: "AI와 대화하세요", color: "bg-blue-500" },
  { to: "/rag", icon: FileText, title: "RAG", desc: "문서 기반 질의응답", color: "bg-emerald-500" },
  { to: "/sql", icon: Database, title: "Text-to-SQL", desc: "자연어로 SQL 생성", color: "bg-amber-500" },
  { to: "/codegen", icon: Code2, title: "Code Gen", desc: "코드 자동 생성", color: "bg-purple-500" },
];

export function DashboardPage() {
  const [health, setHealth] = useState<HealthInfo | null>(null);

  useEffect(() => {
    healthApi.check().then((res) => setHealth(res.data)).catch(() => {});
  }, []);

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Enterprise AI Platform</h1>
        <p className="text-muted-foreground mt-1">폐쇄망 AI 플랫폼에 오신 것을 환영합니다</p>
      </div>

      {/* Status */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4" />
            시스템 상태
          </CardTitle>
        </CardHeader>
        <CardContent>
          {health ? (
            <div className="flex gap-6 text-sm">
              <div>
                <span className="text-muted-foreground">상태: </span>
                <span className="inline-flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  {health.status}
                </span>
              </div>
              <div>
                <span className="text-muted-foreground">모드: </span>
                <span className="font-medium">{health.mode}</span>
              </div>
              <div>
                <span className="text-muted-foreground">모델: </span>
                <span className="font-mono text-xs">{health.model}</span>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">백엔드에 연결 중...</p>
          )}
        </CardContent>
      </Card>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {features.map((f) => (
          <Link key={f.to} to={f.to}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
              <CardContent className="pt-6">
                <div className={`${f.color} w-10 h-10 rounded-lg flex items-center justify-center mb-3`}>
                  <f.icon className="h-5 w-5 text-white" />
                </div>
                <h3 className="font-semibold">{f.title}</h3>
                <p className="text-sm text-muted-foreground mt-1">{f.desc}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
