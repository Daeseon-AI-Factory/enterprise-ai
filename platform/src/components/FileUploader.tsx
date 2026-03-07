import { useCallback, useState } from "react";
import { Upload, FileText, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileUploaderProps {
  onUpload: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  disabled?: boolean;
}

export function FileUploader({
  onUpload,
  accept = ".pdf,.docx,.xlsx,.txt,.md,.py,.java,.js,.ts,.vue,.sql",
  multiple = true,
  disabled = false,
}: FileUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState<File[]>([]);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;

      const droppedFiles = Array.from(e.dataTransfer.files);
      setFiles((prev) => [...prev, ...droppedFiles]);
    },
    [disabled]
  );

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selected = Array.from(e.target.files);
      setFiles((prev) => [...prev, ...selected]);
    }
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = () => {
    if (files.length > 0) {
      onUpload(files);
      setFiles([]);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={cn(
          "flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors",
          dragOver ? "border-primary bg-primary/5" : "border-border",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <Upload className="h-10 w-10 text-muted-foreground mb-3" />
        <p className="text-sm font-medium">
          파일을 여기에 끌어다 놓거나{" "}
          <label className="text-primary cursor-pointer hover:underline">
            직접 선택
            <input
              type="file"
              className="hidden"
              accept={accept}
              multiple={multiple}
              onChange={handleFileInput}
              disabled={disabled}
            />
          </label>
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          PDF, Word, Excel, 코드 파일 지원
        </p>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg border px-3 py-2">
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm">{file.name}</span>
                <span className="text-xs text-muted-foreground">
                  ({(file.size / 1024).toFixed(1)} KB)
                </span>
              </div>
              <button onClick={() => removeFile(i)} className="text-muted-foreground hover:text-destructive">
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
          <button
            onClick={handleUpload}
            className="w-full rounded-lg bg-primary py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            {files.length}개 파일 업로드
          </button>
        </div>
      )}
    </div>
  );
}
