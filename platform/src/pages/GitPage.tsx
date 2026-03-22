import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChatMessage } from "@/components/ChatMessage";
import { gitApi, ragApi } from "@/lib/api";
import {
  GitBranch, FolderOpen, Send, Loader2, CheckCircle,
  AlertCircle, RefreshCw, Trash2,
} from "lucide-react";

interface Job { job_id: string; status: string; files_indexed: number; chunks_indexed: number; message: string }
interface Collection { name: string; count: number }

export function GitPage() {
  // ── Index tab ──
  const [repoPath, setRepoPath] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [collection, setCollection] = useState("");
  const [indexing, setIndexing] = useState(false);
  const [job, setJob] = useState<Job | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Collections tab ──
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loadingCols, setLoadingCols] = useState(false);

  // ── Query tab ──
  const [query, setQuery] = useState("");
  const [queryCollection, setQueryCollection] = useState("");
  const [answer, setAnswer] = useState("");
  const [querying, setQuerying] = useState(false);

  const loadCollections = useCallback(async () => {
    setLoadingCols(true);
    try {
      const res = await gitApi.listCollections();
      setCollections(res.data);
      if (res.data.length > 0 && !queryCollection) {
        setQueryCollection(res.data[0].name);
      }
    } catch { /* ignore */ } finally {
      setLoadingCols(false);
    }
  }, [queryCollection]);

  useEffect(() => {
    loadCollections();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [loadCollections]);

  const pollJob = useCallback((jobId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const res = await gitApi.indexStatus(jobId);
        setJob(res.data);
        if (res.data.status === "done" || res.data.status === "error") {
          clearInterval(pollRef.current!);
          setIndexing(false);
          if (res.data.status === "done") loadCollections();
        }
      } catch {
        clearInterval(pollRef.current!);
        setIndexing(false);
      }
    }, 1500);
  }, [loadCollections]);

  const handleIndex = async () => {
    if (!repoPath.trim() && !repoUrl.trim()) return;
    setIndexing(true);
    setJob(null);
    try {
      const res = await gitApi.indexRepo({
        repo_path: repoPath.trim() || undefined as unknown as string,
        repo_url: repoUrl.trim() || undefined,
        collection: collection.trim() || undefined,
      });
      setJob({ job_id: res.data.job_id ?? "", status: res.data.status ?? "running", files_indexed: 0, chunks_indexed: 0, message: "색인 시작..." });
      pollJob(res.data.job_id);
    } catch {
      setIndexing(false);
      setJob({ job_id: "", status: "error", files_indexed: 0, chunks_indexed: 0, message: "색인 요청 실패. 경로/URL을 확인해주세요." });
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    setQuerying(true);
    setAnswer("");
    try {
      const res = await ragApi.query(query, queryCollection);
      setAnswer(res.data.answer);
    } catch {
      setAnswer("질의 실패. 소스가 색인되어 있는지 확인해주세요.");
    } finally {
      setQuerying(false);
    }
  };

  const handleDeleteCollection = async (name: string) => {
    if (!confirm(`'${name}' 컬렉션을 삭제하시겠습니까?`)) return;
    try {
      await ragApi.deleteCollection(name);
      setCollections(prev => prev.filter(c => c.name !== name));
    } catch { /* ignore */ }
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <GitBranch className="h-6 w-6" />
          Git 코드 RAG
        </h1>
        <p className="text-muted-foreground mt-1">
          로컬 Git 저장소를 색인하고 소스코드에 대해 질문하세요
        </p>
      </div>

      <Tabs defaultValue="index">
        <TabsList>
          <TabsTrigger value="index">저장소 색인</TabsTrigger>
          <TabsTrigger value="query">코드 질의</TabsTrigger>
          <TabsTrigger value="collections" onClick={loadCollections}>색인 목록</TabsTrigger>
        </TabsList>

        {/* ── Index ── */}
        <TabsContent value="index" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <FolderOpen className="h-4 w-4" />
                저장소 정보
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <label className="text-xs font-medium mb-1 block">로컬 경로 (서버 기준)</label>
                <Input
                  value={repoPath}
                  onChange={e => setRepoPath(e.target.value)}
                  placeholder="예: /home/user/myproject 또는 C:\Sources\myproject"
                />
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>── 또는 ──</span>
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">원격 저장소 URL (git clone)</label>
                <Input
                  value={repoUrl}
                  onChange={e => setRepoUrl(e.target.value)}
                  placeholder="예: https://github.com/company/repo.git"
                />
              </div>
              <div>
                <label className="text-xs font-medium mb-1 block">컬렉션 이름 (선택, 기본: git_저장소명)</label>
                <Input
                  value={collection}
                  onChange={e => setCollection(e.target.value)}
                  placeholder="예: git_mes_backend"
                />
              </div>
              <Button onClick={handleIndex} disabled={indexing || (!repoPath.trim() && !repoUrl.trim())}>
                {indexing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <GitBranch className="h-4 w-4 mr-2" />}
                색인 시작
              </Button>
            </CardContent>
          </Card>

          {/* Job status */}
          {job && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  {job.status === "done" ? (
                    <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                  ) : job.status === "error" ? (
                    <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
                  ) : (
                    <Loader2 className="h-5 w-5 animate-spin text-primary flex-shrink-0 mt-0.5" />
                  )}
                  <div className="space-y-1">
                    <p className="text-sm font-medium">
                      {job.status === "done" ? "색인 완료" : job.status === "error" ? "색인 실패" : "색인 중..."}
                    </p>
                    <p className="text-sm text-muted-foreground">{job.message}</p>
                    {job.files_indexed > 0 && (
                      <p className="text-xs text-muted-foreground">
                        파일 {job.files_indexed}개 · 청크 {job.chunks_indexed}개
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── Query ── */}
        <TabsContent value="query" className="space-y-4">
          <Card>
            <CardContent className="pt-6 space-y-3">
              <div className="flex gap-2 items-center">
                <span className="text-sm text-muted-foreground whitespace-nowrap">컬렉션:</span>
                <select
                  className="h-9 rounded-md border bg-background px-3 text-sm"
                  value={queryCollection}
                  onChange={e => setQueryCollection(e.target.value)}
                >
                  <option value="">-- 컬렉션 선택 --</option>
                  {collections.map(c => (
                    <option key={c.name} value={c.name}>{c.name} ({c.count}청크)</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="예: 불량률 계산 로직이 어디 있어?"
                  onKeyDown={e => e.key === "Enter" && !querying && handleQuery()}
                  disabled={querying}
                />
                <Button onClick={handleQuery} disabled={querying || !query.trim()}>
                  {querying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
              </div>
            </CardContent>
          </Card>

          {answer && (
            <Card>
              <CardContent className="pt-6">
                <ChatMessage role="assistant" content={answer} />
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* ── Collections ── */}
        <TabsContent value="collections">
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center justify-between">
                색인된 Git 컬렉션
                <Button variant="ghost" size="sm" onClick={loadCollections} disabled={loadingCols}>
                  <RefreshCw className={`h-4 w-4 ${loadingCols ? "animate-spin" : ""}`} />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {collections.length === 0 ? (
                <p className="text-sm text-muted-foreground">색인된 저장소 없음</p>
              ) : (
                <div className="space-y-2">
                  {collections.map(c => (
                    <div key={c.name} className="flex items-center justify-between rounded-lg border px-4 py-3">
                      <div>
                        <span className="font-medium text-sm">{c.name}</span>
                        <span className="text-xs text-muted-foreground ml-2">{c.count} 청크</span>
                      </div>
                      <Button
                        variant="ghost" size="sm" className="text-red-500 hover:text-red-700"
                        onClick={() => handleDeleteCollection(c.name)}
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
