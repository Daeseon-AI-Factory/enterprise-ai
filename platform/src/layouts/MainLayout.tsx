import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/Sidebar";

interface MainLayoutProps {
  user?: string;
  onLogout?: () => void;
  lang?: "ko" | "en";
  onLangToggle?: () => void;
}

export function MainLayout({ user, onLogout, lang, onLangToggle }: MainLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar user={user} onLogout={onLogout} lang={lang} onLangToggle={onLangToggle} />
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
