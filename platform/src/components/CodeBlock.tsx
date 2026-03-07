import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Copy, Check, Download } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CodeBlockProps {
  code: string;
  language: string;
  filename?: string;
}

export function CodeBlock({ code, language, filename }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || `code.${language}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-lg border overflow-hidden">
      <div className="flex items-center justify-between bg-zinc-800 px-4 py-2">
        <span className="text-xs text-zinc-400">{filename || language}</span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 px-2 text-zinc-400 hover:text-white">
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            <span className="ml-1 text-xs">{copied ? "Copied!" : "Copy"}</span>
          </Button>
          <Button variant="ghost" size="sm" onClick={handleDownload} className="h-7 px-2 text-zinc-400 hover:text-white">
            <Download className="h-3 w-3" />
          </Button>
        </div>
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{ margin: 0, borderRadius: 0, fontSize: "13px" }}
        showLineNumbers
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
