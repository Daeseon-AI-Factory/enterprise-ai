import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { settingsApi, healthApi, confluenceApi, buildApi, ragApi } from "@/lib/api";
import {
  Settings,
  Globe,
  Hammer,
  Database,
  Save,
  Loader2,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Trash2,
  Plus,
  Server,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ConfluenceConfig {
  base_url: string;
  username: string;
  api_token: string;
  spaces: string[]; // space keys to sync
}

interface BuildPreset {
  id: string;
  name: string;
  project_path: string;
  build_command: string;
  deploy_command: string;
}

interface PlatformInfo {
  status: string;
  mode: string;
  model: string;
}

type Tab = "platform" | "confluence" | "build" | "data";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("platform");
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<{ type: "ok" | "err"; msg: string } | null>(null);

  const flash = (type: "ok" | "err", msg: string) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 3000);
  };

  // ---- Platform info ----
  const [platform, setPlatform] = useState<PlatformInfo | null>(null);

  const loadPlatform = useCallback(async () => {
    try {
      const res = await healthApi.check();
      setPlatform(res.data);
    } catch {
      /* ignore */
    }
  }, []);

  // ---- Confluence ----
  const [confluence, setConfluence] = useState<ConfluenceConfig>({
    base_url: "",
    username: "",
    api_token: "",
    spaces: [],
  });
  const [confTestOk, setConfTestOk] = useState<boolean | null>(null);
  const [confTesting, setConfTesting] = useState(false);

  const loadConfluence = useCallback(async () => {
    try {
      const res = await settingsApi.get("confluence");
      if (res.data.data) setConfluence(res.data.data as ConfluenceConfig);
    } catch {
      /* first time */
    }
  }, []);

  const saveConfluence = async () => {
    setSaving(true);
    try {
      await settingsApi.save("confluence", confluence);
      flash("ok", "Confluence 설정 저장 완료");
    } catch {
      flash("err", "저장 실패");
    } finally {
      setSaving(false);
    }
  };

  const testConfluence = async () => {
    setConfTesting(true);
    setConfTestOk(null);
    try {
      await confluenceApi.listSpaces({
        base_url: confluence.base_url,
        username: confluence.username,
        api_token: confluence.api_token,
      });
      setConfTestOk(true);
    } catch {
      setConfTestOk(false);
    } finally {
      setConfTesting(false);
    }
  };

  // ---- Build Presets ----
  const [presets, setPresets] = useState<BuildPreset[]>([]);

  const loadPresets = useCallback(async () => {
    try {
      const res = await settingsApi.get("build_presets");
      if (res.data.data) setPresets(res.data.data as BuildPreset[]);
    } catch {
      /* first time */
    }
  }, []);

  const savePresets = async (updated: BuildPreset[]) => {
    setPresets(updated);
    await settingsApi.save("build_presets", updated);
    flash("ok", "빌드 프리셋 저장 완료");
  };

  const addPreset = () => {
    const newP: BuildPreset = {
      id: crypto.randomUUID().slice(0, 8),
      name: "",
      project_path: "",
      build_command: "npm run build",
      deploy_command: "docker-compose up -d --build",
    };
    setPresets([...presets, newP]);
  };

  const updatePreset = (id: string, field: keyof BuildPreset, value: string) => {
    setPresets(presets.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  };

  const removePreset = (id: string) => {
    const updated = presets.filter((p) => p.id !== id);
    savePresets(updated);
  };

  const runPresetBuild = async (preset: BuildPreset) => {
    try {
      await buildApi.run(preset.project_path, preset.build_command, preset.name);
      flash("ok", `"${preset.name}" 빌드 시작`);
    } catch {
      flash("err", "빌드 실행 실패");
    }
  };

  const runPresetDeploy = async (preset: BuildPreset) => {
    try {
      await buildApi.deploy(preset.project_path, preset.deploy_command, preset.name);
      flash("ok", `"${preset.name}" 배포 시작`);
    } catch {
      flash("err", "배포 실행 실패");
    }
  };

  // ---- Data management ----
  const [collections, setCollections] = useState<Array<{ name: string; count: number }>>([]);

  const loadCollections = useCallback(async () => {
    try {
      const res = await ragApi.listCollections();
      setCollections(res.data);
    } catch {
      /* ignore */
    }
  }, []);

  const deleteCollection = async (name: string) => {
    try {
      await ragApi.deleteCollection(name);
      setCollections(collections.filter((c) => c.name !== name));
      flash("ok", `컬렉션 "${name}" 삭제 완료`);
    } catch {
      flash("err", "삭제 실패");
    }
  };

  // ---- Init ----
  useEffect(() => {
    loadPlatform();
    loadConfluence();
    loadPresets();
    loadCollections();
  }, [loadPlatform, loadConfluence, loadPresets, loadCollections]);

  // ---- Tabs ----
  const tabs: { key: Tab; label: string; icon: React.ElementType }[] = [
    { key: "platform", label: "플랫폼", icon: Server },
    { key: "confluence", label: "Confluence", icon: Globe },
    { key: "build", label: "빌드/배포", icon: Hammer },
    { key: "data", label: "데이터 관리", icon: Database },
  ];

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Settings className="h-6 w-6" /> 설정
          </h1>
          <p className="text-muted-foreground mt-1">
            플랫폼 전체 설정을 한 곳에서 관리합니다
          </p>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className={`flex items-center gap-2 rounded-lg border px-4 py-3 text-sm ${
            toast.type === "ok"
              ? "border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950/30 dark:text-green-300"
              : "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950/30 dark:text-red-300"
          }`}
        >
          {toast.type === "ok" ? (
            <CheckCircle className="h-4 w-4" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          {toast.msg}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 rounded-lg bg-muted p-1">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-background text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* ============================================================== */}
      {/* TAB: Platform */}
      {/* ============================================================== */}
      {activeTab === "platform" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              플랫폼 상태
              <Button variant="ghost" size="sm" onClick={loadPlatform}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {platform ? (
              <div className="grid grid-cols-3 gap-6">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">상태</p>
                  <p className="flex items-center gap-2 font-medium">
                    <span className="h-2 w-2 rounded-full bg-green-500" />
                    {platform.status}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">모드</p>
                  <p className="font-medium">
                    {platform.mode === "airgap" ? "폐쇄망 (Air-gapped)" : "로컬 (Local)"}
                  </p>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">LLM 모델</p>
                  <p className="font-mono text-sm">{platform.model}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">로딩 중...</p>
            )}
            <div className="mt-6 rounded-lg bg-muted/50 p-4 text-sm text-muted-foreground">
              <p className="font-medium text-foreground mb-2">환경 변수 (서버에서 설정)</p>
              <code className="text-xs block space-y-1">
                <div>MODE=airgap</div>
                <div>LLM_API_BASE=http://gpt-oss:8080/v1</div>
                <div>LLM_API_KEY=sk-xxx</div>
                <div>LLM_MODEL=gpt-4o-mini</div>
                <div>CHROMA_HOST=chromadb</div>
                <div>CHROMA_PORT=8100</div>
              </code>
              <p className="mt-2 text-xs">
                * .env 파일이나 docker-compose 환경 변수로 변경. 변경 후 서버 재시작 필요.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ============================================================== */}
      {/* TAB: Confluence */}
      {/* ============================================================== */}
      {activeTab === "confluence" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Globe className="h-4 w-4" />
              Confluence 연결 설정
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Confluence URL</label>
              <Input
                value={confluence.base_url}
                onChange={(e) => setConfluence({ ...confluence, base_url: e.target.value })}
                placeholder="https://confluence.internal.company.com (폐쇄망 내부 주소)"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium mb-1 block">사용자명</label>
                <Input
                  value={confluence.username}
                  onChange={(e) => setConfluence({ ...confluence, username: e.target.value })}
                  placeholder="사용자 이메일 또는 ID"
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-1 block">API 토큰 / 비밀번호</label>
                <Input
                  type="password"
                  value={confluence.api_token}
                  onChange={(e) => setConfluence({ ...confluence, api_token: e.target.value })}
                  placeholder="API token 또는 비밀번호"
                />
              </div>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">동기화 Space Keys (쉼표 구분)</label>
              <Input
                value={confluence.spaces.join(", ")}
                onChange={(e) =>
                  setConfluence({
                    ...confluence,
                    spaces: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  })
                }
                placeholder="DEV, HR, OPS"
              />
            </div>
            <div className="flex gap-3">
              <Button onClick={saveConfluence} disabled={saving}>
                {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
                저장
              </Button>
              <Button variant="outline" onClick={testConfluence} disabled={confTesting}>
                {confTesting ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <RefreshCw className="h-4 w-4 mr-2" />
                )}
                연결 테스트
              </Button>
              {confTestOk === true && (
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" /> 연결 성공
                </span>
              )}
              {confTestOk === false && (
                <span className="flex items-center gap-1 text-sm text-red-600">
                  <AlertCircle className="h-4 w-4" /> 연결 실패
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ============================================================== */}
      {/* TAB: Build/Deploy */}
      {/* ============================================================== */}
      {activeTab === "build" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-medium">빌드/배포 프리셋</h2>
            <Button variant="outline" size="sm" onClick={addPreset}>
              <Plus className="h-4 w-4 mr-1" /> 추가
            </Button>
          </div>

          {presets.length === 0 ? (
            <Card>
              <CardContent className="pt-6 text-center text-sm text-muted-foreground">
                프리셋이 없습니다. "추가" 버튼을 눌러 빌드/배포 설정을 등록하세요.
              </CardContent>
            </Card>
          ) : (
            presets.map((preset) => (
              <Card key={preset.id}>
                <CardContent className="pt-6 space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium mb-1 block">이름</label>
                      <Input
                        value={preset.name}
                        onChange={(e) => updatePreset(preset.id, "name", e.target.value)}
                        placeholder="Platform Frontend"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium mb-1 block">프로젝트 경로</label>
                      <Input
                        value={preset.project_path}
                        onChange={(e) => updatePreset(preset.id, "project_path", e.target.value)}
                        placeholder="/home/user/project"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs font-medium mb-1 block">빌드 명령어</label>
                      <Input
                        value={preset.build_command}
                        onChange={(e) => updatePreset(preset.id, "build_command", e.target.value)}
                        placeholder="npm run build"
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium mb-1 block">배포 명령어</label>
                      <Input
                        value={preset.deploy_command}
                        onChange={(e) => updatePreset(preset.id, "deploy_command", e.target.value)}
                        placeholder="docker-compose up -d --build"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => runPresetBuild(preset)}>
                      <Hammer className="h-3 w-3 mr-1" /> 빌드
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => runPresetDeploy(preset)}>
                      <Server className="h-3 w-3 mr-1" /> 배포
                    </Button>
                    <div className="flex-1" />
                    <Button size="sm" variant="ghost" className="text-red-500" onClick={() => removePreset(preset.id)}>
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}

          {presets.length > 0 && (
            <Button onClick={() => savePresets(presets)} className="w-full">
              <Save className="h-4 w-4 mr-2" /> 프리셋 전체 저장
            </Button>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB: Data Management */}
      {/* ============================================================== */}
      {activeTab === "data" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Database className="h-4 w-4" />
                벡터 DB 컬렉션
              </span>
              <Button variant="ghost" size="sm" onClick={loadCollections}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {collections.length === 0 ? (
              <p className="text-sm text-muted-foreground">컬렉션이 없습니다</p>
            ) : (
              <div className="space-y-2">
                {collections.map((col) => (
                  <div
                    key={col.name}
                    className="flex items-center justify-between rounded-lg border px-4 py-3"
                  >
                    <div>
                      <span className="font-medium text-sm">{col.name}</span>
                      <span className="text-muted-foreground text-xs ml-2">{col.count} chunks</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-500 hover:text-red-700"
                      onClick={() => deleteCollection(col.name)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
