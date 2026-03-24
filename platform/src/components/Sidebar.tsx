import { NavLink } from "react-router-dom";
import {
  MessageSquare, FileText, Database, Code2, LayoutDashboard,
  Bot, Globe, Shield, Hammer, Settings, GitBranch, LogOut, User,
  Layers, Languages,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/",          icon: LayoutDashboard, ko: "대시보드",     en: "Dashboard" },
  { to: "/chat",      icon: MessageSquare,   ko: "AI 채팅",      en: "AI Chat" },
  { to: "/rag",       icon: FileText,        ko: "RAG 문서",     en: "RAG Docs" },
  { to: "/sql",       icon: Database,        ko: "텍스트→SQL",   en: "Text-to-SQL" },
  { to: "/ask",       icon: Bot,             ko: "업무 질의",    en: "Ask (Multi-Agent)" },
  { to: "/analyze",   icon: Layers,          ko: "통합 진단",    en: "Analyze" },
  { to: "/git",       icon: GitBranch,       ko: "Git 코드 RAG", en: "Git Code RAG" },
  { to: "/codegen",   icon: Code2,           ko: "코드 생성",    en: "Code Gen" },
  { to: "/confluence",icon: Globe,           ko: "Confluence",   en: "Confluence" },
  { to: "/review",    icon: Shield,          ko: "AI 리뷰",      en: "AI Review" },
  { to: "/build",     icon: Hammer,          ko: "빌드/배포",    en: "Build" },
  { to: "/settings",  icon: Settings,        ko: "설정",         en: "Settings" },
];

interface SidebarProps {
  user?: string;
  onLogout?: () => void;
  lang?: "ko" | "en";
  onLangToggle?: () => void;
}

export function Sidebar({ user, onLogout, lang = "ko", onLangToggle }: SidebarProps) {
  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-card">
      {/* Logo */}
      <div className="flex h-14 items-center gap-3 border-b px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <Bot className="h-4 w-4 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-sm font-bold">Enterprise AI</h1>
          <p className="text-xs text-muted-foreground">Platform</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )
            }
          >
            <item.icon className="h-4 w-4 flex-shrink-0" />
            {lang === "ko" ? item.ko : item.en}
          </NavLink>
        ))}
      </nav>

      {/* User / Logout / Lang */}
      <div className="border-t p-3 space-y-1">
        {/* Language toggle */}
        <button
          onClick={onLangToggle}
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          <Languages className="h-3.5 w-3.5" />
          {lang === "ko" ? "English" : "한국어"}
        </button>

        {user && (
          <div className="flex items-center gap-2 px-2 py-1.5">
            <User className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground truncate">{user}</span>
          </div>
        )}
        {onLogout && (
          <button
            onClick={onLogout}
            className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
          >
            <LogOut className="h-3.5 w-3.5" />
            {lang === "ko" ? "로그아웃" : "Logout"}
          </button>
        )}
      </div>
    </aside>
  );
}
