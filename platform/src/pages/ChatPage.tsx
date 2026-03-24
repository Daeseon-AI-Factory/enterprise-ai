import { useState, useRef, useEffect, useCallback } from "react";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { chatApi } from "@/lib/api";
import { MessageSquare, Plus, Trash2, Loader2, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";

const VISIBLE_BATCH = 30; // Render this many messages at a time

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Conversation {
  id: string;
  preview: string;
  message_count: number;
  modified: number;
}

export function ChatPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | undefined>(
    () => localStorage.getItem("chat_active_id") || undefined
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [visibleCount, setVisibleCount] = useState(VISIBLE_BATCH);
  const bottomRef = useRef<HTMLDivElement>(null);

  // 대화 목록 불러오기
  const fetchConversations = useCallback(async () => {
    try {
      const res = await chatApi.listConversations();
      setConversations(res.data);
    } catch {}
  }, []);

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // 대화 선택 시 히스토리 불러오기
  useEffect(() => {
    if (!activeId) {
      setMessages([]);
      return;
    }
    localStorage.setItem("chat_active_id", activeId);
    setLoadingHistory(true);
    chatApi.getConversation(activeId)
      .then(res => setMessages(res.data as Message[]))
      .catch(() => setMessages([]))
      .finally(() => setLoadingHistory(false));
  }, [activeId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleNew = () => {
    setActiveId(undefined);
    setMessages([]);
    setVisibleCount(VISIBLE_BATCH);
    localStorage.removeItem("chat_active_id");
  };

  const handleSelect = (id: string) => {
    if (id === activeId) return;
    setActiveId(id);
  };

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    await chatApi.deleteConversation(id);
    if (id === activeId) handleNew();
    fetchConversations();
  };

  const handleSend = async (text: string) => {
    setMessages(prev => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const response = await chatApi.stream(text, activeId);
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = "";

      setMessages(prev => [...prev, { role: "assistant", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        for (const line of chunk.split("\n")) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.content) {
              assistantMessage += data.content;
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: "assistant", content: assistantMessage };
                return updated;
              });
            }
            if (data.conversation_id && data.conversation_id !== activeId) {
              setActiveId(data.conversation_id);
              localStorage.setItem("chat_active_id", data.conversation_id);
            }
          } catch {}
        }
      }

      // 대화 목록 갱신 (새 대화 or 기존 대화 업데이트)
      fetchConversations();
    } catch {
      setMessages(prev => [
        ...prev,
        { role: "assistant", content: "연결에 문제가 발생했습니다. 백엔드가 실행 중인지 확인해주세요." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return "방금";
    if (diff < 3600000) return `${Math.floor(diff / 60000)}분 전`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}시간 전`;
    return d.toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
  };

  return (
    <div className="flex h-full">
      {/* ── Sidebar ── */}
      <div className="w-60 flex-shrink-0 border-r flex flex-col bg-muted/30">
        <div className="p-3 border-b">
          <Button variant="outline" className="w-full justify-start gap-2" onClick={handleNew}>
            <Plus className="h-4 w-4" />
            새 대화
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {conversations.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center mt-6 px-4">대화 기록 없음</p>
          ) : (
            conversations.map(conv => (
              <div
                key={conv.id}
                onClick={() => handleSelect(conv.id)}
                className={`group flex items-start gap-2 px-3 py-2.5 cursor-pointer hover:bg-muted/60 ${
                  activeId === conv.id ? "bg-muted" : ""
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5 mt-0.5 flex-shrink-0 text-muted-foreground" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs truncate leading-snug">
                    {conv.preview || "새 대화"}
                  </p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">
                    {formatTime(conv.modified)} · {conv.message_count}개
                  </p>
                </div>
                <button
                  onClick={e => handleDelete(conv.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-0.5 hover:text-destructive"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── Chat area ── */}
      <div className="flex flex-1 flex-col min-w-0">
        <div className="flex-1 overflow-y-auto">
          {loadingHistory ? (
            <div className="flex h-full items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center px-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 mb-4">
                <MessageSquare className="h-8 w-8 text-primary" />
              </div>
              <h2 className="text-xl font-semibold mb-2">AI Chat</h2>
              <p className="text-muted-foreground max-w-md">
                무엇이든 물어보세요. 문서가 업로드되어 있으면 자동으로 참고하며,
                일반 질문에도 답변합니다.
              </p>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl">
              {messages.length > visibleCount && (
                <div className="flex justify-center py-3">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs gap-1"
                    onClick={() => setVisibleCount(v => v + VISIBLE_BATCH)}
                  >
                    <ChevronUp className="h-3 w-3" />
                    이전 메시지 더 보기 ({messages.length - visibleCount}개)
                  </Button>
                </div>
              )}
              {messages.slice(-visibleCount).map((msg, i) => (
                <ChatMessage key={messages.length - visibleCount + i} role={msg.role} content={msg.content} />
              ))}
              {loading && messages[messages.length - 1]?.role === "user" && (
                <div className="flex gap-4 px-4 py-6 bg-muted/50">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-white">
                    <div className="flex gap-1">
                      <span className="h-1.5 w-1.5 rounded-full bg-white animate-bounce" />
                      <span className="h-1.5 w-1.5 rounded-full bg-white animate-bounce [animation-delay:0.2s]" />
                      <span className="h-1.5 w-1.5 rounded-full bg-white animate-bounce [animation-delay:0.4s]" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <ChatInput onSend={handleSend} disabled={loading} />
      </div>
    </div>
  );
}
