import os
import re

from loguru import logger


class DocumentLoader:
    """Load and chunk documents with semantic awareness."""

    CHUNK_SIZE = 800      # target characters per chunk
    CHUNK_OVERLAP = 150   # overlap between chunks
    MIN_CHUNK_SIZE = 100  # discard chunks smaller than this

    def load_and_chunk(self, file_path: str, filename: str) -> list[str]:
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            text = self._load_pdf(file_path)
        elif ext == ".docx":
            text = self._load_docx(file_path)
        elif ext in (".xlsx", ".xls"):
            text = self._load_excel(file_path)
        else:
            text = self._load_text(file_path)

        chunks = self._semantic_chunk(text)
        logger.info(f"Loaded {filename}: {len(text):,} chars → {len(chunks)} semantic chunks")
        return chunks

    # ── Loaders ─────────────────────────────────────────────

    def _load_pdf(self, file_path: str) -> str:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[Page {i+1}]\n{text}")
        return "\n\n".join(pages)

    def _load_docx(self, file_path: str) -> str:
        from docx import Document
        doc = Document(file_path)
        parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                parts.append(para.text)
        return "\n\n".join(parts)

    def _load_excel(self, file_path: str) -> str:
        from openpyxl import load_workbook
        wb = load_workbook(file_path, data_only=True)
        lines = []
        for sheet in wb.sheetnames:
            ws = wb[sheet]
            lines.append(f"=== Sheet: {sheet} ===")
            for row in ws.iter_rows(values_only=True):
                line = "\t".join(str(c) if c is not None else "" for c in row)
                if line.strip():
                    lines.append(line)
        return "\n".join(lines)

    def _load_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    # ── Semantic Chunking ────────────────────────────────────

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences (Korean + English aware)."""
        # Split on: .  !  ?  。  \n
        parts = re.split(r'(?<=[.!?。])\s+|(?<=\n)\n+', text)
        sentences = []
        for p in parts:
            p = p.strip()
            if p:
                sentences.append(p)
        return sentences if sentences else [text]

    def _semantic_chunk(self, text: str) -> list[str]:
        """
        Semantic chunking strategy:
        1. Split by paragraph boundaries (\\n\\n or section headers)
        2. If a paragraph exceeds CHUNK_SIZE, split by sentences
        3. Merge small paragraphs up to CHUNK_SIZE
        4. Add CHUNK_OVERLAP between chunks for context continuity
        """
        if not text.strip():
            return []

        # Step 1: split into paragraphs
        paragraphs = re.split(r'\n{2,}', text.strip())
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        # Step 2: break oversized paragraphs into sentences
        units: list[str] = []
        for para in paragraphs:
            if len(para) <= self.CHUNK_SIZE:
                units.append(para)
            else:
                sentences = self._split_sentences(para)
                units.extend(sentences)

        # Step 3: merge units into chunks up to CHUNK_SIZE
        chunks: list[str] = []
        current_parts: list[str] = []
        current_size = 0

        for unit in units:
            unit_len = len(unit)

            if current_size + unit_len > self.CHUNK_SIZE and current_parts:
                # Flush current chunk
                chunks.append("\n\n".join(current_parts))

                # Overlap: carry over trailing units up to CHUNK_OVERLAP chars
                overlap_parts: list[str] = []
                overlap_size = 0
                for part in reversed(current_parts):
                    if overlap_size + len(part) <= self.CHUNK_OVERLAP:
                        overlap_parts.insert(0, part)
                        overlap_size += len(part)
                    else:
                        break
                current_parts = overlap_parts
                current_size = overlap_size

            current_parts.append(unit)
            current_size += unit_len

        if current_parts:
            chunks.append("\n\n".join(current_parts))

        # Step 4: filter tiny chunks
        result = [c for c in chunks if len(c) >= self.MIN_CHUNK_SIZE]
        return result
