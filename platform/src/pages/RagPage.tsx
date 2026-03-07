import { useState } from "react";
import { FileUploader } from "@/components/FileUploader";
import { ChatMessage } from "@/components/ChatMessage";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ragApi } from "@/lib/api";
import { Send, FileText, Trash2 } from "lucide-react";

interface Source {
  filename: string;
  score: number;
}

interface Collection {
  name: string;
  count: number;
}

export function RagPage() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [activeCollection, setActiveCollection] = useState("default");

  const handleUpload = async (files: File[]) => {
    setUploadStatus("업로드 중...");
    try {
      for (const file of files) {
        await ragApi.upload(file, activeCollection);
      }
      setUploadStatus(`${files.length}개 파일 업로드 완료`);
      loadCollections();
    } catch {
      setUploadStatus("업로드 실패. 백엔드를 확인해주세요.");
    }
  };

  const handleQuery = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setAnswer("");
    setSources([]);

    try {
      const res = await ragApi.query(query, activeCollection);
      setAnswer(res.data.answer);
      setSources(res.data.sources);
    } catch {
      setAnswer("질의 실패. 문서가 업로드되었는지 확인해주세요.");
    } finally {
      setLoading(false);
    }
  };

  const loadCollections = async () => {
    try {
      const res = await ragApi.listCollections();
      setCollections(res.data);
    } catch {
      // ignore
    }
  };

  const deleteCollection = async (name: string) => {
    try {
      await ragApi.deleteCollection(name);
      loadCollections();
    } catch {
      // ignore
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">RAG - 문서 기반 질의응답</h1>
        <p className="text-muted-foreground mt-1">
          문서를 업로드하고, 문서 내용을 기반으로 질문하세요
        </p>
      </div>

      <Tabs defaultValue="query">
        <TabsList>
          <TabsTrigger value="query">질의</TabsTrigger>
          <TabsTrigger value="upload">문서 업로드</TabsTrigger>
          <TabsTrigger value="collections" onClick={loadCollections}>컬렉션 관리</TabsTrigger>
        </TabsList>

        <TabsContent value="query" className="space-y-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex gap-2">
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="문서에 대해 질문하세요..."
                  onKeyDown={(e) => e.key === "Enter" && handleQuery()}
                />
                <Button onClick={handleQuery} disabled={loading || !query.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>

          {answer && (
            <Card>
              <CardContent className="pt-6">
                <ChatMessage role="assistant" content={answer} />
                {sources.length > 0 && (
                  <div className="mt-4 border-t pt-4">
                    <h4 className="text-sm font-medium mb-2">참고 문서</h4>
                    <div className="space-y-1">
                      {sources.map((s, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                          <FileText className="h-3 w-3" />
                          <span>{s.filename}</span>
                          <span className="text-xs">({(s.score * 100).toFixed(1)}%)</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="upload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">컬렉션</CardTitle>
            </CardHeader>
            <CardContent>
              <Input
                value={activeCollection}
                onChange={(e) => setActiveCollection(e.target.value)}
                placeholder="컬렉션 이름 (예: project-docs)"
              />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <FileUploader onUpload={handleUpload} />
              {uploadStatus && (
                <p className="text-sm text-muted-foreground mt-3">{uploadStatus}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="collections">
          <Card>
            <CardContent className="pt-6">
              {collections.length === 0 ? (
                <p className="text-sm text-muted-foreground">컬렉션이 없습니다</p>
              ) : (
                <div className="space-y-2">
                  {collections.map((c) => (
                    <div key={c.name} className="flex items-center justify-between rounded-lg border px-4 py-3">
                      <div>
                        <span className="font-medium">{c.name}</span>
                        <span className="text-sm text-muted-foreground ml-2">({c.count}개 문서)</span>
                      </div>
                      <Button variant="ghost" size="icon" onClick={() => deleteCollection(c.name)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
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
