import os

from loguru import logger


class DocumentLoader:
    """Load and chunk documents (PDF, Word, Excel, code files)."""

    CHUNK_SIZE = 1000  # characters per chunk
    CHUNK_OVERLAP = 200

    def load_and_chunk(self, file_path: str, filename: str) -> list[str]:
        """Load a file and split into chunks."""
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            text = self._load_pdf(file_path)
        elif ext == ".docx":
            text = self._load_docx(file_path)
        elif ext in (".xlsx", ".xls"):
            text = self._load_excel(file_path)
        elif ext in (".py", ".java", ".js", ".ts", ".vue", ".sql", ".sh", ".yaml", ".yml", ".json"):
            text = self._load_text(file_path)
        elif ext in (".txt", ".md", ".csv"):
            text = self._load_text(file_path)
        else:
            text = self._load_text(file_path)

        chunks = self._chunk_text(text)
        logger.info(f"Loaded {filename}: {len(text)} chars -> {len(chunks)} chunks")
        return chunks

    def _load_pdf(self, file_path: str) -> str:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _load_docx(self, file_path: str) -> str:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs)

    def _load_excel(self, file_path: str) -> str:
        from openpyxl import load_workbook
        wb = load_workbook(file_path, data_only=True)
        lines = []
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            lines.append(f"=== Sheet: {sheet} ===")
            for row in ws.iter_rows(values_only=True):
                line = "\t".join(str(cell) if cell is not None else "" for cell in row)
                if line.strip():
                    lines.append(line)
        return "\n".join(lines)

    def _load_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _chunk_text(self, text: str) -> list[str]:
        if not text.strip():
            return []

        chunks = []
        start = 0
        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk = text[start:end]
            if chunk.strip():
                chunks.append(chunk.strip())
            start += self.CHUNK_SIZE - self.CHUNK_OVERLAP

        return chunks
