"""OCR Service — extract text from images and scanned PDFs.

Supports PaddleOCR (best for Korean) and Tesseract as fallback.
Can feed extracted text directly into RAG pipeline.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from loguru import logger

from app.config import settings
from app.core.document_loader import DocumentLoader
from app.core.vector_store import VectorStore

_UPLOAD_DIR = Path("./uploads/ocr")


class OcrService:
    def __init__(self):
        self._vector_store = VectorStore()
        self._doc_loader = DocumentLoader()
        self._ocr_engine = None
        _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def _get_engine(self):
        """Lazy-load OCR engine."""
        if self._ocr_engine is not None:
            return self._ocr_engine

        if settings.OCR_ENGINE == "paddleocr":
            try:
                from paddleocr import PaddleOCR
                self._ocr_engine = PaddleOCR(
                    use_angle_cls=True,
                    lang="korean",
                    use_gpu=False,
                    show_log=False,
                )
                logger.info("PaddleOCR loaded (Korean)")
                return self._ocr_engine
            except ImportError:
                logger.warning("PaddleOCR not installed, falling back to Tesseract")

        # Tesseract fallback
        try:
            import pytesseract
            self._ocr_engine = "tesseract"
            logger.info("Using Tesseract OCR")
            return self._ocr_engine
        except ImportError:
            logger.error("No OCR engine available. Install paddleocr or pytesseract.")
            return None

    async def extract_text(self, file_path: str, language: str = "korean") -> dict:
        """Extract text from an image file."""
        engine = self._get_engine()
        if engine is None:
            return {"status": "error", "message": "No OCR engine available"}

        ext = Path(file_path).suffix.lower()

        if ext == ".pdf":
            text = self._ocr_pdf(file_path)
        elif ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"):
            text = self._ocr_image(file_path)
        else:
            return {"status": "error", "message": f"Unsupported file type: {ext}"}

        return {
            "status": "ok",
            "text": text,
            "length": len(text),
            "file": os.path.basename(file_path),
        }

    async def extract_and_index(
        self,
        file_path: str,
        filename: str,
        collection: str = "default",
    ) -> dict:
        """OCR + chunk + index into vector DB."""
        result = await self.extract_text(file_path)
        if result["status"] != "ok" or not result["text"].strip():
            return {"status": "error", "message": "OCR extraction failed or empty"}

        # Chunk the extracted text
        chunks = self._doc_loader._chunk_text(result["text"])
        if not chunks:
            return {"status": "error", "message": "No chunks generated from OCR text"}

        # Index into vector DB
        doc_id = str(uuid.uuid4())
        self._vector_store.add_documents(
            collection=collection,
            documents=chunks,
            doc_id=doc_id,
            filename=f"[OCR] {filename}",
        )

        return {
            "status": "indexed",
            "filename": filename,
            "text_length": len(result["text"]),
            "chunks": len(chunks),
            "collection": collection,
            "doc_id": doc_id,
        }

    def _ocr_image(self, image_path: str) -> str:
        """Run OCR on a single image."""
        engine = self._get_engine()

        if engine == "tesseract":
            import pytesseract
            from PIL import Image
            img = Image.open(image_path)
            return pytesseract.image_to_string(img, lang="kor+eng")

        # PaddleOCR
        result = engine.ocr(image_path, cls=True)
        if not result or not result[0]:
            return ""
        lines = []
        for line in result[0]:
            text = line[1][0]  # (box, (text, confidence))
            lines.append(text)
        return "\n".join(lines)

    def _ocr_pdf(self, pdf_path: str) -> str:
        """Run OCR on each page of a PDF (for scanned PDFs)."""
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path)
        except ImportError:
            logger.error("pdf2image not installed. Cannot OCR PDFs.")
            return ""
        except Exception as e:
            logger.error(f"Failed to convert PDF to images: {e}")
            return ""

        all_text = []
        for i, img in enumerate(images):
            # Save temp image
            temp_path = str(_UPLOAD_DIR / f"_temp_page_{i}.png")
            img.save(temp_path)
            text = self._ocr_image(temp_path)
            all_text.append(f"=== Page {i + 1} ===\n{text}")
            # Cleanup temp
            try:
                os.remove(temp_path)
            except OSError:
                pass

        return "\n\n".join(all_text)
