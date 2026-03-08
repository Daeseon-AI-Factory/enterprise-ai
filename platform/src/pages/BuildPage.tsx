import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { buildApi } from "@/lib/api";
import {
  Hammer,
  Rocket,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
} from "lucide-react";

interface BuildRecord {
  build_id: string;
  name: string;
  status: string;
  command: string;
  started_at: string;
  finished_at: string;
  return_code: number;
}

interface BuildDetail extends BuildRecord {
  stdout: string;
  stderr: string;
  project_path: string;
}

export function BuildPage() {
  // Build form
  const [projectPath, setProjectPath] = useState("");
  const [buildCommand, setBuildCommand] = useState("npm run build");
  const [buildName, setBuildName] = useState("");
  const [building, setBuilding] = useState(false);

  // Deploy form
  const [deployCommand, setDeployCommand] = useState("");
  const [deploying, setDeploying] = useState(false);

  // History
  const [history, setHistory] = useState<BuildRecord[]>([]);
  const [selectedBuild, setSelectedBuild] = useState<BuildDetail | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const loadHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await buildApi.history();
      setHistory(res.data);
    } catch {
      // ignore
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleBuild = async () => {
    if (!projectPath.trim() || !buildCommand.trim()) return;
    setBuilding(true);
    try {
      await buildApi.run(projectPath, buildCommand, buildName);
      await loadHistory();
    } catch {
      // ignore
    } finally {
      setBuilding(false);
    }
  };

  const handleDeploy = async () => {
    if (!projectPath.trim() || !deployCommand.trim()) return;
    setDeploying(true);
    try {
      await buildApi.deploy(projectPath, deployCommand, buildName);
      await loadHistory();
    } catch {
      // ignore
    } finally {
      setDeploying(false);
    }
  };

  const handleViewDetail = async (buildId: string) => {
    try {
      const res = await buildApi.detail(buildId);
      setSelectedBuild(res.data);
    } catch {
      // ignore
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "timeout":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <Loader2 className="h-4 w-4 animate-spin" />;
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">빌드 & 배포</h1>
        <p className="text-muted-foreground mt-1">
          폐쇄망 환경에서 프로젝트를 빌드하고 배포합니다
        </p>
      </div>

      {/* Build/Deploy form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">빌드/배포 실행</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <label className="text-sm font-medium mb-1 block">프로젝트 경로</label>
            <Input
              value={projectPath}
              onChange={(e) => setProjectPath(e.target.value)}
              placeholder="/home/user/my-project"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium mb-1 block">빌드 명령어</label>
              <Input
                value={buildCommand}
                onChange={(e) => setBuildCommand(e.target.value)}
                placeholder="npm run build"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">배포 명령어</label>
              <Input
                value={deployCommand}
                onChange={(e) => setDeployCommand(e.target.value)}
                placeholder="docker-compose up -d --build"
              />
            </div>
          </div>
          <div>
            <label className="text-sm font-medium mb-1 block">이름 (선택)</label>
            <Input
              value={buildName}
              onChange={(e) => setBuildName(e.target.value)}
              placeholder="Platform v1.2 빌드"
            />
          </div>
          <div className="flex gap-3">
            <Button onClick={handleBuild} disabled={building || !projectPath.trim()}>
              {building ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Hammer className="h-4 w-4 mr-2" />
              )}
              빌드 실행
            </Button>
            <Button
              onClick={handleDeploy}
              disabled={deploying || !projectPath.trim() || !deployCommand.trim()}
              variant="outline"
            >
              {deploying ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <Rocket className="h-4 w-4 mr-2" />
              )}
              배포 실행
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center justify-between">
            <span>빌드 히스토리</span>
            <Button variant="ghost" size="sm" onClick={loadHistory} disabled={loadingHistory}>
              <RefreshCw className={`h-4 w-4 ${loadingHistory ? "animate-spin" : ""}`} />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-sm text-muted-foreground">빌드 기록이 없습니다</p>
          ) : (
            <div className="space-y-2">
              {history.map((build) => (
                <button
                  key={build.build_id}
                  onClick={() => handleViewDetail(build.build_id)}
                  className={`w-full flex items-center justify-between rounded-lg border px-4 py-3 text-left text-sm transition-colors hover:bg-accent ${
                    selectedBuild?.build_id === build.build_id ? "border-primary bg-primary/5" : ""
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {statusIcon(build.status)}
                    <div>
                      <span className="font-medium">{build.name || build.command}</span>
                      <span className="text-muted-foreground ml-2 text-xs">
                        {new Date(build.started_at).toLocaleString("ko-KR")}
                      </span>
                    </div>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded ${
                      build.status === "success"
                        ? "bg-green-100 text-green-700"
                        : build.status === "failed"
                          ? "bg-red-100 text-red-700"
                          : "bg-yellow-100 text-yellow-700"
                    }`}
                  >
                    {build.status}
                  </span>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Build detail */}
      {selectedBuild && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              빌드 상세 — {selectedBuild.build_id}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">명령어:</span>{" "}
                <code className="bg-muted px-1.5 py-0.5 rounded text-xs">
                  {selectedBuild.command}
                </code>
              </div>
              <div>
                <span className="text-muted-foreground">경로:</span>{" "}
                <span className="font-mono text-xs">{selectedBuild.project_path}</span>
              </div>
              <div>
                <span className="text-muted-foreground">종료 코드:</span>{" "}
                <span className="font-medium">{selectedBuild.return_code}</span>
              </div>
              <div>
                <span className="text-muted-foreground">상태:</span>{" "}
                <span className="font-medium">{selectedBuild.status}</span>
              </div>
            </div>

            {selectedBuild.stdout && (
              <div>
                <label className="text-sm font-medium mb-1 block">stdout</label>
                <pre className="bg-muted rounded-lg p-4 text-xs overflow-auto max-h-64 font-mono">
                  {selectedBuild.stdout}
                </pre>
              </div>
            )}

            {selectedBuild.stderr && (
              <div>
                <label className="text-sm font-medium mb-1 block text-red-600">stderr</label>
                <pre className="bg-red-50 dark:bg-red-950/20 rounded-lg p-4 text-xs overflow-auto max-h-64 font-mono text-red-800 dark:text-red-300">
                  {selectedBuild.stderr}
                </pre>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
