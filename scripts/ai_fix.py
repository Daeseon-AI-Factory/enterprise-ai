"""
폐쇄망 AI 코드 수정 도구
사용법: python scripts/ai_fix.py "에러 메시지나 수정 요청"

파일을 읽고, LLM에게 수정 요청하고, 결과를 보여줍니다.
"""
import sys
import os
import json
import glob
import requests

# .env에서 설정 읽기
API_BASE = os.getenv("LLM_API_BASE", "http://localhost:8000/v1")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[파일 읽기 실패: {e}]"


def find_project_files(base_dir: str, extensions: list[str]) -> list[str]:
    """프로젝트 주요 파일 목록"""
    files = []
    for ext in extensions:
        files.extend(glob.glob(f"{base_dir}/**/*{ext}", recursive=True))
    # node_modules, __pycache__ 제외
    return [f for f in files if "node_modules" not in f and "__pycache__" not in f]


def ask_llm(question: str, context_files: dict[str, str]) -> str:
    """LLM에게 질문"""
    file_context = ""
    for path, content in context_files.items():
        file_context += f"\n--- {path} ---\n{content}\n"

    messages = [
        {
            "role": "system",
            "content": (
                "너는 코드 수정 전문가다. 에러를 분석하고 정확한 수정 방법을 알려줘. "
                "수정할 파일명과 변경할 코드를 명확히 보여줘."
            ),
        },
        {
            "role": "user",
            "content": f"프로젝트 파일:\n{file_context}\n\n요청: {question}",
        },
    ]

    try:
        resp = requests.post(
            f"{API_BASE}/chat/completions",
            json={"model": MODEL, "messages": messages, "max_tokens": 4096},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LLM 호출 실패: {e}"


def main():
    if len(sys.argv) < 2:
        print("사용법: python scripts/ai_fix.py \"에러 메시지나 수정 요청\"")
        print("옵션:")
        print("  --files file1.py file2.ts  : 특정 파일만 컨텍스트로 전달")
        print("")
        print("예시:")
        print('  python scripts/ai_fix.py "vite proxy가 안됨"')
        print('  python scripts/ai_fix.py "ERRNO 11003" --files platform/vite.config.ts')
        sys.exit(1)

    question = sys.argv[1]

    # --files 옵션 처리
    context_files = {}
    if "--files" in sys.argv:
        idx = sys.argv.index("--files")
        file_list = sys.argv[idx + 1:]
        for f in file_list:
            context_files[f] = read_file(f)
    else:
        # 기본: 설정 파일들 자동 포함
        default_files = [
            "platform/vite.config.ts",
            "platform/package.json",
            "platform/src/lib/api.ts",
            "app/main.py",
            "app/config.py",
            ".env",
        ]
        for f in default_files:
            if os.path.exists(f):
                context_files[f] = read_file(f)

    print(f"\n질문: {question}")
    print(f"컨텍스트 파일: {list(context_files.keys())}")
    print("LLM에게 질문 중...\n")

    answer = ask_llm(question, context_files)
    print("=" * 60)
    print(answer)
    print("=" * 60)


if __name__ == "__main__":
    main()
