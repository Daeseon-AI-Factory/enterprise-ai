import { useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { MainLayout } from "@/layouts/MainLayout";
import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { ChatPage } from "@/pages/ChatPage";
import { RagPage } from "@/pages/RagPage";
import { SqlPage } from "@/pages/SqlPage";
import { AnalyzePage } from "@/pages/AnalyzePage";
import { AskPage } from "@/pages/AskPage";
import { GitPage } from "@/pages/GitPage";
import { CodegenPage } from "@/pages/CodegenPage";
import { ConfluencePage } from "@/pages/ConfluencePage";
import { ReviewPage } from "@/pages/ReviewPage";
import { BuildPage } from "@/pages/BuildPage";
import { SettingsPage } from "@/pages/SettingsPage";

export function App() {
  const [user, setUser] = useState<string | null>(
    () => localStorage.getItem("auth_user")
  );
  const [lang, setLang] = useState<"ko" | "en">(
    () => (localStorage.getItem("ui_lang") as "ko" | "en") ?? "ko"
  );

  const handleLogin = (username: string) => setUser(username);

  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setUser(null);
  };

  const handleLangToggle = () => {
    const next = lang === "ko" ? "en" : "ko";
    setLang(next);
    localStorage.setItem("ui_lang", next);
  };

  if (!user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <Routes>
      <Route element={<MainLayout user={user} onLogout={handleLogout} lang={lang} onLangToggle={handleLangToggle} />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/rag" element={<RagPage />} />
        <Route path="/sql" element={<SqlPage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/ask" element={<AskPage />} />
        <Route path="/git" element={<GitPage />} />
        <Route path="/codegen" element={<CodegenPage />} />
        <Route path="/confluence" element={<ConfluencePage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/build" element={<BuildPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
