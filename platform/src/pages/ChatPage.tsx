import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { chatApi } from "@/lib/api";
import { MessageSquare } from "lucide-react";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text: string) => {
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      // Use streaming
      const response = await chatApi.stream(text, conversationId);
      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMessage = "";

      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.content) {
                assistantMessage += data.content;
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1] = {
                    role: "assistant",
                    content: assistantMessage,
                  };
                  return updated;
                });
              }
              if (data.conversation_id) {
                setConversationId(data.conversation_id);
              }
            } catch {
              // skip malformed JSON
            }
          }
        }
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "연결에 문제가 발생했습니다. 백엔드가 실행 중인지 확인해주세요." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center px-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 mb-4">
              <MessageSquare className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-xl font-semibold mb-2">AI Chat</h2>
            <p className="text-muted-foreground max-w-md">
              무엇이든 물어보세요. 코드 설명, 문서 요약, 아이디어 브레인스토밍 등
              다양한 작업을 도와드립니다.
            </p>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl">
            {messages.map((msg, i) => (
              <ChatMessage key={i} role={msg.role} content={msg.content} />
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

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={loading} />
    </div>
  );
}
