import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { reviewApi } from "@/lib/api";
import { Shield, Bug, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";

export function ReviewPage() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("python");
  const [context, setContext] = useState("");

  // Code review
  const [reviewResult, setReviewResult] = useState("");
  const [reviewLoading, setReviewLoading] = useState(false);

  // Edge case
  const [edgeResult, setEdgeResult] = useState("");
  const [edgeLoading, setEdgeLoading] = useState(false);

  const handleCodeReview = async () => {
    if (!code.trim()) return;
    setReviewLoading(true);
    setReviewResult("");
    try {
      const res = await reviewApi.codeReview(code, language, context);
      setReviewResult(res.data.review);
    } catch {
      setReviewResult("코드 리뷰 실행 중 오류가 발생했습니다.");
    } finally {
      setReviewLoading(false);
    }
  };

  const handleEdgeCases = async () => {
    if (!code.trim()) return;
    setEdgeLoading(true);
    setEdgeResult("");
    try {
      const res = await reviewApi.edgeCases(code, language, context);
      setEdgeResult(res.data.analysis);
    } catch {
      setEdgeResult("엣지 케이스 분석 중 오류가 발생했습니다.");
    } finally {
      setEdgeLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">AI 코드 리뷰</h1>
        <p className="text-muted-foreground mt-1">
          AI가 코드를 분석하여 버그, 보안 이슈, 엣지 케이스를 찾아냅니다
        </p>
      </div>

      {/* Input */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">코드 입력</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1 block">언어</label>
              <Input
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                placeholder="python, java, typescript, ..."
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">컨텍스트 (선택)</label>
              <Input
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="이 코드의 역할이나 배경 설명"
              />
            </div>
          </div>
          <textarea
            className="w-full h-64 rounded-lg border bg-muted/50 p-4 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="리뷰할 코드를 붙여넣으세요..."
          />
          <div className="flex gap-3">
            <Button onClick={handleCodeReview} disabled={reviewLoading || !code.trim()}>
              {reviewLoading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Shield className="h-4 w-4 mr-2" />
              )}
              코드 리뷰
            </Button>
            <Button
              onClick={handleEdgeCases}
              disabled={edgeLoading || !code.trim()}
              variant="outline"
            >
              {edgeLoading ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Bug className="h-4 w-4 mr-2" />
              )}
              엣지 케이스 분석
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {reviewResult && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Shield className="h-4 w-4" />
                코드 리뷰 결과
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{reviewResult}</ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        )}

        {edgeResult && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Bug className="h-4 w-4" />
                엣지 케이스 분석 결과
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{edgeResult}</ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
