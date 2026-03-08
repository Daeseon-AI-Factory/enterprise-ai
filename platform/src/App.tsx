import { Routes, Route } from "react-router-dom";
import { MainLayout } from "@/layouts/MainLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { ChatPage } from "@/pages/ChatPage";
import { RagPage } from "@/pages/RagPage";
import { SqlPage } from "@/pages/SqlPage";
import { CodegenPage } from "@/pages/CodegenPage";
import { ConfluencePage } from "@/pages/ConfluencePage";
import { ReviewPage } from "@/pages/ReviewPage";
import { BuildPage } from "@/pages/BuildPage";
import { SettingsPage } from "@/pages/SettingsPage";

export function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/rag" element={<RagPage />} />
        <Route path="/sql" element={<SqlPage />} />
        <Route path="/codegen" element={<CodegenPage />} />
        <Route path="/confluence" element={<ConfluencePage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/build" element={<BuildPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
