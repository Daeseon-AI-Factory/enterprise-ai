import { Routes, Route } from "react-router-dom";
import { MainLayout } from "@/layouts/MainLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { ChatPage } from "@/pages/ChatPage";
import { RagPage } from "@/pages/RagPage";
import { SqlPage } from "@/pages/SqlPage";
import { CodegenPage } from "@/pages/CodegenPage";

export function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/rag" element={<RagPage />} />
        <Route path="/sql" element={<SqlPage />} />
        <Route path="/codegen" element={<CodegenPage />} />
      </Route>
    </Routes>
  );
}
