import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeBlock } from "@/components/CodeBlock";
import { codegenApi } from "@/lib/api";
import { Code2, Sparkles } from "lucide-react";

const LANGUAGES = [
  { value: "python", label: "Python" },
  { value: "java", label: "Java" },
  { value: "javascript", label: "JavaScript" },
  { value: "typescript", label: "TypeScript" },
  { value: "sql", label: "SQL" },
];

const FRAMEWORKS: Record<string, string[]> = {
  python: ["FastAPI", "Django", "Flask"],
  java: ["Spring Boot", "None"],
  javascript: ["Express", "Vue", "React"],
  typescript: ["FastAPI", "Express", "React", "Vue"],
  sql: ["Oracle", "PostgreSQL", "MySQL"],
};

export function CodegenPage() {
  const [prompt, setPrompt] = useState("");
  const [language, setLanguage] = useState("python");
  const [framework, setFramework] = useState("FastAPI");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setCode("");

    try {
      const res = await codegenApi.generate(prompt, language, framework);
      setCode(res.data.code);
    } catch {
      setCode("// 코드 생성 실패. 백엔드를 확인해주세요.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Code2 className="h-6 w-6" />
          Code Generator
        </h1>
        <p className="text-muted-foreground mt-1">
          프로젝트 컨텍스트에 맞는 코드를 자동 생성합니다
        </p>
      </div>

      {/* Input */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">코드 생성 요청</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Language & Framework */}
          <div className="flex gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium">언어</label>
              <select
                value={language}
                onChange={(e) => {
                  setLanguage(e.target.value);
                  setFramework(FRAMEWORKS[e.target.value]?.[0] || "");
                }}
                className="flex h-10 w-40 rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>{l.label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">프레임워크</label>
              <select
                value={framework}
                onChange={(e) => setFramework(e.target.value)}
                className="flex h-10 w-40 rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {(FRAMEWORKS[language] || []).map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Prompt */}
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="예: PRODUCTION 테이블에 대한 CRUD API를 만들어줘. 컬럼은 id, product_name, quantity, status, created_at"
            rows={4}
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
          />

          <Button onClick={handleGenerate} disabled={loading || !prompt.trim()}>
            <Sparkles className="h-4 w-4 mr-2" />
            {loading ? "생성 중..." : "코드 생성"}
          </Button>
        </CardContent>
      </Card>

      {/* Generated Code */}
      {code && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">생성된 코드</CardTitle>
          </CardHeader>
          <CardContent>
            <CodeBlock code={code} language={language} filename={`generated.${language === "typescript" ? "ts" : language === "javascript" ? "js" : language}`} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
