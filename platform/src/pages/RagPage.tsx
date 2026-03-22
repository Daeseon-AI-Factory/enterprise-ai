import { useState, useEffect } from "react";
import { FileUploader } from "@/components/FileUploader";
import { ChatMessage } from "@/components/ChatMessage";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ragApi } from "@/lib/api";
import {
  Send, FileText, Trash2, ChevronDown, ChevronRight,
  FolderOpen, Eye, X, Loader2, ExternalLink,
} from "lucide-react";

interface Source { filename: string; collection: string; chunk_id: string; score: number; page_url?: string; source?: string }
interface Collection { name: string; count: number }
interface DocFile { filename: string; doc_id: string; chunks: number }
interface Chunk { chunk_index: number; content: string }

const SESSION_KEY = "rag_state";

function saveSession(data: object) {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(data)); } catch {}
}
function loadSession<T>(key: string, fallback: T): T {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (raw) return (JSON.parse(raw)[key] ?? fallback);
  } catch {}
  return fallback;
}

interface HistoryEntry { query: string; answer: string; sources: Source[]; timestamp: string }

export function RagPage() {
  const [query, setQuery] = useState("");
  const [history, setHistory] = useState<HistoryEntry[]>(() => loadSession("history", []));
  const [loadingStep, setLoadingStep] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [activeCollection, setActiveCollection] = useState(() => loadSession("activeCollection", "all"));
  const [expandedCol, setExpandedCol] = useState<string | null>(null);
  const [colDocs, setColDocs] = useState<Record<string, DocFile[]>>({});
  const [loadingDocs, setLoadingDocs] = useState<string | null>(null);

  // Document preview modal
  const [previewDoc, setPreviewDoc] = useState<{ filename: string; collection: string; doc_id: string; page_url?: string } | null>(null);
  const [previewChunks, setPreviewChunks] = useState<Chunk[]>([]);
  const [loadingPreview, setLoadingPreview] = useState(false);

  // Persist history
  useEffect(() => {
    saveSession({ history, activeCollection });
  }, [history, activeCollection]);

  const handleUpload = async (files: File[]) => {
    setUploadStatus("업로드 중...");
    try {
      for (const file of files) {
        await ragApi.upload(file, activeCollection === "all" ? "default" : activeCollection);
      }
      setUploadStatus(`✓ ${files.length}개 파일 업로드 완료`);
      loadCollections();
    } catch {
      setUploadStatus("✗ 업로드 실패. 백엔드를 확인해주세요.");
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    const currentQuery = query;
    setQuery("");
    setLoadingStep("문서 검색 중...");

    try {
      await new Promise(r => setTimeout(r, 300));
      setLoadingStep("관련 문서 분석 중...");

      const res = await ragApi.query(currentQuery, activeCollection);
      const entry: HistoryEntry = {
        query: currentQuery,
        answer: res.data.answer,
        sources: res.data.sources as Source[],
        timestamp: new Date().toLocaleTimeString("ko-KR"),
      };
      setHistory(prev => [...prev, entry]);
    } catch {
      const entry: HistoryEntry = {
        query: currentQuery,
        answer: "질의 실패. 문서가 업로드되었는지 확인해주세요.",
        sources: [],
        timestamp: new Date().toLocaleTimeString("ko-KR"),
      };
      setHistory(prev => [...prev, entry]);
    } finally {
      setLoadingStep("");
    }
  };

  const loadCollections = async () => {
    try {
      const res = await ragApi.listCollections();
      setCollections(res.data);
    } catch {}
  };

  const toggleCollection = async (name: string) => {
    if (expandedCol === name) { setExpandedCol(null); return; }
    setExpandedCol(name);
    if (colDocs[name] === undefined) {
      setLoadingDocs(name);
      try {
        const res = await ragApi.listDocuments(name);
        setColDocs(prev => ({ ...prev, [name]: res.data }));
      } catch {
        setColDocs(prev => ({ ...prev, [name]: [] }));
      } finally {
        setLoadingDocs(null);
      }
    }
  };

  const openPreview = async (doc: DocFile, collection: string) => {
    setPreviewDoc({ filename: doc.filename, collection, doc_id: doc.doc_id });
    setPreviewChunks([]);
    setLoadingPreview(true);
    try {
      const res = await ragApi.getDocumentChunks(collection, doc.doc_id);
      setPreviewChunks(res.data);
    } catch {
      setPreviewChunks([]);
    } finally {
      setLoadingPreview(false);
    }
  };

  const deleteCollection = async (name: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`'${name}' 컬렉션을 삭제하시겠습니까?`)) return;
    try {
      await ragApi.deleteCollection(name);
      setColDocs(prev => { const n = { ...prev }; delete n[name]; return n; });
      if (expandedCol === name) setExpandedCol(null);
      loadCollections();
    } catch {}
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">RAG - 문서 기반 질의응답</h1>
        <p className="text-muted-foreground mt-1">문서를 업로드하고, 문서 내용을 기반으로 질문하세요</p>
      </div>

      <Tabs defaultValue="query">
        <TabsList>
          <TabsTrigger value="query">질의</TabsTrigger>
          <TabsTrigger value="upload">문서 업로드</TabsTrigger>
          <TabsTrigger value="collections" onClick={loadCollections}>컬렉션 관리</TabsTrigger>
        </TabsList>

        {/* ── Query Tab ─────────────────────────────────── */}
        <TabsContent value="query" className="space-y-4">
          <Card>
            <CardContent className="pt-6 space-y-3">
              <div className="flex gap-2 items-center">
                <span className="text-sm text-muted-foreground whitespace-nowrap">검색 범위:</span>
                <Input
                  value={activeCollection}
                  onChange={e => setActiveCollection(e.target.value)}
                  placeholder="all (전체)"
                  className="max-w-[180px]"
                />
                <span className="text-xs text-muted-foreground">all = 전체, 또는 컬렉션명</span>
              </div>
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="문서에 대해 질문하세요..."
                  onKeyDown={e => e.key === "Enter" && !loadingStep && handleQuery()}
                  disabled={!!loadingStep}
                />
                <Button onClick={handleQuery} disabled={!!loadingStep || !query.trim()}>
                  {loadingStep
                    ? <Loader2 className="h-4 w-4 animate-spin" />
                    : <Send className="h-4 w-4" />
                  }
                </Button>
              </div>

              {/* Loading progress */}
              {loadingStep && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
                  <Loader2 className="h-3 w-3 animate-spin" />
                  <span>{loadingStep}</span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* History */}
          {history.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{history.length}개 질의</span>
                <Button variant="ghost" size="sm" className="text-xs" onClick={() => setHistory([])}>기록 지우기</Button>
              </div>
              {history.map((entry, idx) => (
                <Card key={idx}>
                  <CardContent className="pt-4 pb-3 space-y-3">
                    <div className="flex items-start gap-2">
                      <span className="text-xs font-medium bg-primary text-primary-foreground rounded px-1.5 py-0.5 mt-0.5">Q</span>
                      <p className="text-sm font-medium">{entry.query}</p>
                      <span className="text-xs text-muted-foreground ml-auto whitespace-nowrap">{entry.timestamp}</span>
                    </div>
                    <ChatMessage role="assistant" content={entry.answer} />
                    {entry.sources.length > 0 && (
                      <div className="border-t pt-3">
                        <h4 className="text-xs font-medium mb-1.5 text-muted-foreground">참고 문서 ({entry.sources.length}개)</h4>
                        <div className="space-y-1">
                          {entry.sources.map((s, i) => {
                            const docId = s.chunk_id?.replace(/_\d+$/, "") || s.filename;
                            return (
                              <div
                                key={i}
                                className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer hover:bg-muted/50 rounded px-2 py-1 -mx-2 transition-colors"
                                onClick={() => {
                                  openPreview({ filename: s.filename, doc_id: docId, chunks: 0 }, s.collection);
                                  if (s.page_url) setPreviewDoc(prev => prev ? { ...prev, page_url: s.page_url } : prev);
                                }}
                              >
                                <Eye className="h-3 w-3 flex-shrink-0 text-blue-500" />
                                <span className="font-medium text-foreground hover:underline">{s.filename}</span>
                                <span className="text-xs text-muted-foreground">({s.collection})</span>
                                {s.page_url && (
                                  <a href={s.page_url} target="_blank" rel="noopener noreferrer"
                                    className="ml-1 text-blue-500 hover:text-blue-700"
                                    onClick={e => e.stopPropagation()} title="Confluence 원본 열기">
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                )}
                                <span className="text-xs ml-auto">유사도 {(s.score * 100).toFixed(0)}%</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── Upload Tab ────────────────────────────────── */}
        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">업로드할 컬렉션</CardTitle></CardHeader>
            <CardContent>
              <Input
                value={activeCollection === "all" ? "default" : activeCollection}
                onChange={e => setActiveCollection(e.target.value)}
                placeholder="컬렉션 이름 (예: project-docs)"
              />
              <p className="text-xs text-muted-foreground mt-1">
                * 비워두면 "default" 컬렉션에 저장됩니다
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <FileUploader onUpload={handleUpload} />
              {uploadStatus && (
                <p className="text-sm mt-3 text-muted-foreground">{uploadStatus}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Collections Tab ───────────────────────────── */}
        <TabsContent value="collections">
          <Card>
            <CardContent className="pt-6">
              {collections.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  컬렉션 없음. 문서를 업로드하면 여기에 표시됩니다.
                </p>
              ) : (
                <div className="space-y-2">
                  {collections.map(c => (
                    <div key={c.name} className="rounded-lg border overflow-hidden">
                      {/* Collection row */}
                      <div
                        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-muted/50"
                        onClick={() => toggleCollection(c.name)}
                      >
                        <div className="flex items-center gap-2">
                          {expandedCol === c.name
                            ? <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            : <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          }
                          <FolderOpen className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{c.name}</span>
                          <span className="text-sm text-muted-foreground">({c.count}개 청크)</span>
                        </div>
                        <Button variant="ghost" size="icon" onClick={e => deleteCollection(c.name, e)}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>

                      {/* File list */}
                      {expandedCol === c.name && (
                        <div className="border-t bg-muted/20 px-4 py-2">
                          {loadingDocs === c.name ? (
                            <div className="flex items-center gap-2 py-2 text-sm text-muted-foreground">
                              <Loader2 className="h-3 w-3 animate-spin" />
                              <span>파일 목록 로딩 중...</span>
                            </div>
                          ) : (colDocs[c.name] ?? []).length === 0 ? (
                            <p className="text-sm text-muted-foreground py-2">파일 없음</p>
                          ) : (
                            <div className="space-y-1 py-1">
                              {(colDocs[c.name] ?? []).map((doc, i) => (
                                <div key={i} className="flex items-center gap-2 text-sm py-1 group">
                                  <FileText className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                                  <span className="flex-1 truncate">{doc.filename}</span>
                                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                                    {doc.chunks}청크
                                  </span>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 opacity-0 group-hover:opacity-100"
                                    title="내용 보기"
                                    onClick={() => openPreview(doc, c.name)}
                                  >
                                    <Eye className="h-3 w-3" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-6 w-6 opacity-0 group-hover:opacity-100 text-destructive"
                                    title="문서 삭제"
                                    onClick={async (e) => {
                                      e.stopPropagation();
                                      if (!confirm(`'${doc.filename}' 문서를 삭제하시겠습니까?`)) return;
                                      await ragApi.deleteDocument(c.name, doc.doc_id);
                                      setColDocs(prev => ({
                                        ...prev,
                                        [c.name]: (prev[c.name] ?? []).filter(d => d.doc_id !== doc.doc_id),
                                      }));
                                    }}
                                  >
                                    <Trash2 className="h-3 w-3" />
                                  </Button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ── Document Preview Modal ───────────────────────── */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-background rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between px-5 py-3 border-b">
              <div>
                <h3 className="font-semibold">{previewDoc.filename}</h3>
                <div className="flex items-center gap-2">
                  <p className="text-xs text-muted-foreground">컬렉션: {previewDoc.collection}</p>
                  {previewDoc.page_url && (
                    <a
                      href={previewDoc.page_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-500 hover:underline flex items-center gap-1"
                    >
                      <ExternalLink className="h-3 w-3" /> 원본 보기
                    </a>
                  )}
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setPreviewDoc(null)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="overflow-y-auto flex-1 p-5 space-y-4">
              {loadingPreview ? (
                <div className="flex items-center justify-center py-10 gap-2 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  <span>청크 로딩 중...</span>
                </div>
              ) : previewChunks.length === 0 ? (
                <p className="text-sm text-muted-foreground">내용 없음</p>
              ) : (
                previewChunks.map((chunk, i) => (
                  <div key={i} className="rounded-md border p-3 space-y-1">
                    <div className="text-xs text-muted-foreground font-mono">
                      청크 #{chunk.chunk_index + 1}
                    </div>
                    <pre className="text-sm whitespace-pre-wrap break-words font-sans leading-relaxed">
                      {chunk.content}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
