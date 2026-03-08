import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { confluenceApi } from "@/lib/api";
import { RefreshCw, Link, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

interface Space {
  key: string;
  name: string;
  type: string;
}

interface SyncResult {
  status: string;
  space_key: string;
  collection: string;
  synced: number;
  total_chunks: number;
}

export function ConfluencePage() {
  // Connection
  const [baseUrl, setBaseUrl] = useState("");
  const [username, setUsername] = useState("");
  const [apiToken, setApiToken] = useState("");

  // Spaces
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [loadingSpaces, setLoadingSpaces] = useState(false);
  const [connected, setConnected] = useState(false);

  // Sync
  const [selectedSpace, setSelectedSpace] = useState("");
  const [collection, setCollection] = useState("");
  const [fullSync, setFullSync] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncResult | null>(null);
  const [error, setError] = useState("");

  const handleConnect = async () => {
    if (!baseUrl.trim() || !username.trim() || !apiToken.trim()) return;
    setLoadingSpaces(true);
    setError("");
    try {
      const res = await confluenceApi.listSpaces({
        base_url: baseUrl,
        username,
        api_token: apiToken,
      });
      setSpaces(res.data);
      setConnected(true);
    } catch {
      setError("연결 실패. URL, 사용자명, API 토큰을 확인해주세요.");
      setConnected(false);
    } finally {
      setLoadingSpaces(false);
    }
  };

  const handleSync = async () => {
    if (!selectedSpace) return;
    setSyncing(true);
    setSyncResult(null);
    setError("");
    try {
      const res = await confluenceApi.sync({
        base_url: baseUrl,
        username,
        api_token: apiToken,
        space_key: selectedSpace,
        collection: collection || undefined,
        full_sync: fullSync,
      });
      setSyncResult(res.data);
    } catch {
      setError("동기화 실패. 네트워크 또는 권한을 확인해주세요.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">Confluence 연동</h1>
        <p className="text-muted-foreground mt-1">
          Confluence 문서를 자동으로 가져와 RAG 벡터 DB에 색인합니다
        </p>
      </div>

      {/* Connection */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Link className="h-4 w-4" />
            Confluence 연결 설정
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="Confluence URL (예: https://company.atlassian.net/wiki)"
          />
          <div className="grid grid-cols-2 gap-3">
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="사용자명 (이메일)"
            />
            <Input
              type="password"
              value={apiToken}
              onChange={(e) => setApiToken(e.target.value)}
              placeholder="API 토큰"
            />
          </div>
          <Button onClick={handleConnect} disabled={loadingSpaces}>
            {loadingSpaces ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Link className="h-4 w-4 mr-2" />
            )}
            연결 테스트
          </Button>
        </CardContent>
      </Card>

      {/* Space Selection + Sync */}
      {connected && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <RefreshCw className="h-4 w-4" />
              Space 동기화
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Space list */}
            <div>
              <label className="text-sm font-medium mb-2 block">Space 선택</label>
              <div className="grid grid-cols-1 gap-2 max-h-60 overflow-y-auto">
                {spaces.map((space) => (
                  <button
                    key={space.key}
                    onClick={() => setSelectedSpace(space.key)}
                    className={`flex items-center justify-between rounded-lg border px-4 py-3 text-left text-sm transition-colors ${
                      selectedSpace === space.key
                        ? "border-primary bg-primary/5"
                        : "hover:bg-accent"
                    }`}
                  >
                    <div>
                      <span className="font-medium">{space.name}</span>
                      <span className="text-muted-foreground ml-2">({space.key})</span>
                    </div>
                    <span className="text-xs text-muted-foreground">{space.type}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Options */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium mb-1 block">컬렉션 이름 (선택)</label>
                <Input
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
                  placeholder={selectedSpace ? `confluence_${selectedSpace.toLowerCase()}` : "자동 생성"}
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={fullSync}
                    onChange={(e) => setFullSync(e.target.checked)}
                    className="rounded"
                  />
                  전체 재색인 (변경 감지 무시)
                </label>
              </div>
            </div>

            {/* Sync button */}
            <Button
              onClick={handleSync}
              disabled={syncing || !selectedSpace}
              className="w-full"
            >
              {syncing ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              {syncing ? "동기화 중..." : "동기화 시작"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Result */}
      {syncResult && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-green-600 mb-3">
              <CheckCircle className="h-5 w-5" />
              <span className="font-medium">동기화 완료</span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Space:</span>{" "}
                <span className="font-medium">{syncResult.space_key}</span>
              </div>
              <div>
                <span className="text-muted-foreground">컬렉션:</span>{" "}
                <span className="font-medium">{syncResult.collection}</span>
              </div>
              <div>
                <span className="text-muted-foreground">동기화 페이지:</span>{" "}
                <span className="font-medium">{syncResult.synced}개</span>
              </div>
              <div>
                <span className="text-muted-foreground">생성된 청크:</span>{" "}
                <span className="font-medium">{syncResult.total_chunks}개</span>
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-3">
              RAG 페이지에서 컬렉션 "{syncResult.collection}"을 선택하여 질의할 수 있습니다.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
