"""Git 소스 코드 커넥터 — 로컬 또는 원격 저장소를 RAG로 색인합니다."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from loguru import logger

# 색인할 확장자 (바이너리/불필요 파일 제외)
INDEXABLE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".java", ".cs", ".go", ".rs", ".cpp", ".c", ".h",
    ".sql", ".yaml", ".yml", ".json", ".toml", ".md",
    ".sh", ".bat", ".ps1",
}

# 건너뛸 디렉토리
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", "dist", "build",
    ".venv", "venv", "env", ".idea", ".vscode", "coverage", ".pytest_cache",
    "target", "bin", "obj",
}

MAX_FILE_SIZE = 500_000  # 500KB 이상 파일 스킵


class GitConnector:
    """로컬 git 저장소에서 소스 파일을 읽어 청크 목록으로 반환."""

    def clone_or_pull(self, repo_url: str, local_path: str) -> str:
        """원격 저장소 clone 또는 pull. 로컬 경로 반환."""
        path = Path(local_path)
        if path.exists() and (path / ".git").exists():
            logger.info(f"Git pull: {local_path}")
            subprocess.run(["git", "-C", local_path, "pull"], capture_output=True)
        else:
            logger.info(f"Git clone: {repo_url} → {local_path}")
            path.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", repo_url, local_path], capture_output=True)
        return local_path

    def read_files(
        self,
        repo_path: str,
        extensions: set[str] | None = None,
        max_files: int = 500,
    ) -> list[dict]:
        """저장소의 소스 파일 목록을 읽어 반환.

        Returns:
            list of {path, content, language, size}
        """
        exts = extensions or INDEXABLE_EXTENSIONS
        root = Path(repo_path)
        files = []

        for filepath in root.rglob("*"):
            if len(files) >= max_files:
                break
            if not filepath.is_file():
                continue
            # 건너뛸 디렉토리 확인
            parts = set(filepath.parts)
            if parts & SKIP_DIRS:
                continue
            if filepath.suffix.lower() not in exts:
                continue
            if filepath.stat().st_size > MAX_FILE_SIZE:
                continue

            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
                if not content.strip():
                    continue
                rel_path = str(filepath.relative_to(root))
                files.append({
                    "path": rel_path,
                    "content": content,
                    "language": filepath.suffix.lstrip("."),
                    "size": filepath.stat().st_size,
                })
            except Exception as e:
                logger.debug(f"Skipping {filepath}: {e}")

        logger.info(f"Read {len(files)} source files from {repo_path}")
        return files

    def chunk_file(self, file: dict, chunk_size: int = 1000, overlap: int = 100) -> list[dict]:
        """소스 파일을 청크로 분할. 함수/클래스 경계를 최대한 보존."""
        content = file["content"]
        path = file["path"]
        lang = file["language"]

        # 짧은 파일은 그대로
        if len(content) <= chunk_size:
            return [{
                "content": f"// File: {path}\n{content}",
                "path": path,
                "chunk_index": 0,
                "language": lang,
            }]

        # 줄 단위로 분할 후 청크 합치기
        lines = content.splitlines(keepends=True)
        chunks = []
        current = [f"// File: {path}\n"]
        current_len = len(current[0])
        chunk_idx = 0

        for line in lines:
            if current_len + len(line) > chunk_size and current_len > len(current[0]):
                chunks.append({
                    "content": "".join(current),
                    "path": path,
                    "chunk_index": chunk_idx,
                    "language": lang,
                })
                chunk_idx += 1
                # overlap: 마지막 몇 줄 재사용
                overlap_lines = current[-5:] if len(current) > 5 else current[1:]
                current = [f"// File: {path} (continued)\n"] + overlap_lines
                current_len = sum(len(l) for l in current)

            current.append(line)
            current_len += len(line)

        if len(current) > 1:
            chunks.append({
                "content": "".join(current),
                "path": path,
                "chunk_index": chunk_idx,
                "language": lang,
            })

        return chunks
