import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Bot, User, Copy, Check } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
}

export function ChatMessage({ role, content }: ChatMessageProps) {
  return (
    <div
      className={cn(
        "flex gap-4 px-4 py-6",
        role === "user" ? "bg-background" : "bg-muted/50"
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
          role === "user"
            ? "bg-primary text-primary-foreground"
            : "bg-emerald-600 text-white"
        )}
      >
        {role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className="flex-1 space-y-2 overflow-hidden">
        <ReactMarkdown
          components={{
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || "");
              const codeString = String(children).replace(/\n$/, "");

              if (match) {
                return (
                  <CodeBlockWithCopy language={match[1]} code={codeString} />
                );
              }
              return (
                <code
                  className="rounded bg-muted px-1.5 py-0.5 text-sm font-mono"
                  {...props}
                >
                  {children}
                </code>
              );
            },
            p({ children }) {
              return <p className="leading-7">{children}</p>;
            },
            ul({ children }) {
              return <ul className="list-disc pl-6 space-y-1">{children}</ul>;
            },
            ol({ children }) {
              return <ol className="list-decimal pl-6 space-y-1">{children}</ol>;
            },
            h1({ children }) {
              return <h1 className="text-xl font-bold mt-4 mb-2">{children}</h1>;
            },
            h2({ children }) {
              return <h2 className="text-lg font-bold mt-3 mb-2">{children}</h2>;
            },
            h3({ children }) {
              return <h3 className="text-base font-bold mt-2 mb-1">{children}</h3>;
            },
            table({ children }) {
              return (
                <div className="overflow-x-auto my-2">
                  <table className="w-full border-collapse border border-border text-sm">
                    {children}
                  </table>
                </div>
              );
            },
            th({ children }) {
              return (
                <th className="border border-border bg-muted px-3 py-2 text-left font-medium">
                  {children}
                </th>
              );
            },
            td({ children }) {
              return (
                <td className="border border-border px-3 py-2">{children}</td>
              );
            },
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}

function CodeBlockWithCopy({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-2 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between bg-zinc-800 px-4 py-2 text-xs text-zinc-400">
        <span>{language}</span>
        <button onClick={handleCopy} className="flex items-center gap-1 hover:text-white transition-colors">
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{ margin: 0, borderRadius: 0, fontSize: "13px" }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
