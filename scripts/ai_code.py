"""
폐쇄망 AI 코딩 에이전트 (Claude Code 경량 버전)

파일 읽기/쓰기 + 명령어 실행 + LLM 반복 루프

사용법:
  python scripts/ai_code.py

환경변수:
  LLM_API_BASE=http://GPU서버:포트/v1
  LLM_MODEL=openai/gpt-oss-120b
"""
import os
import re
import json
import subprocess
import requests

API_BASE = os.getenv("LLM_API_BASE", "http://localhost:8000/v1")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")

SYSTEM_PROMPT = """너는 코딩 에이전트다. 사용자의 요청을 수행하기 위해 도구를 사용할 수 있다.

사용 가능한 도구:
1. READ_FILE: 파일 읽기
2. WRITE_FILE: 파일 생성/덮어쓰기
3. EDIT_FILE: 파일 일부 수정
4. RUN_CMD: 명령어 실행
5. DONE: 작업 완료

도구 사용 형식 (반드시 이 형식을 따라):

[TOOL: READ_FILE]
path: 파일경로
[/TOOL]

[TOOL: WRITE_FILE]
path: 파일경로
content:
파일 전체 내용
[/TOOL]

[TOOL: EDIT_FILE]
path: 파일경로
old: 기존 코드
new: 새 코드
[/TOOL]

[TOOL: RUN_CMD]
cmd: 실행할 명령어
[/TOOL]

[TOOL: DONE]
summary: 완료 요약
[/TOOL]

규칙:
- 한 번에 하나의 도구만 사용
- 파일을 수정하기 전에 반드시 먼저 읽어라
- 위험한 명령어(rm -rf, del /s 등)는 실행하지 마라
- 작업이 끝나면 반드시 DONE을 사용하라
"""

conversation = [{"role": "system", "content": SYSTEM_PROMPT}]


def call_llm(messages: list) -> str:
    try:
        resp = requests.post(
            f"{API_BASE}/chat/completions",
            json={"model": MODEL, "messages": messages, "max_tokens": 4096, "temperature": 0},
            timeout=180,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"[LLM 호출 실패: {e}]"


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            numbered = [f"{i+1:4d} | {line}" for i, line in enumerate(lines)]
            return "".join(numbered)
    except Exception as e:
        return f"[에러: {e}]"


def write_file(path: str, content: str) -> str:
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"[파일 저장 완료: {path}]"
    except Exception as e:
        return f"[에러: {e}]"


def edit_file(path: str, old: str, new: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if old.strip() not in content:
            return f"[에러: 기존 코드를 찾을 수 없음]\n검색한 내용:\n{old.strip()}"
        content = content.replace(old.strip(), new.strip(), 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"[파일 수정 완료: {path}]"
    except Exception as e:
        return f"[에러: {e}]"


def run_cmd(cmd: str) -> str:
    # 위험한 명령어 차단
    dangerous = ["rm -rf", "del /s", "format", "rmdir /s", "drop table", "drop database"]
    for d in dangerous:
        if d.lower() in cmd.lower():
            return f"[차단됨: 위험한 명령어 '{d}']"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30, encoding="utf-8"
        )
        output = result.stdout + result.stderr
        if len(output) > 3000:
            output = output[:3000] + "\n...(truncated)"
        return output or "[명령어 실행 완료 (출력 없음)]"
    except subprocess.TimeoutExpired:
        return "[타임아웃: 30초 초과]"
    except Exception as e:
        return f"[에러: {e}]"


def parse_tool(response: str) -> tuple[str, dict] | None:
    pattern = r'\[TOOL:\s*(\w+)\](.*?)\[/TOOL\]'
    match = re.search(pattern, response, re.DOTALL)
    if not match:
        return None

    tool_name = match.group(1).strip()
    body = match.group(2).strip()

    if tool_name == "READ_FILE":
        path_match = re.search(r'path:\s*(.+)', body)
        return ("READ_FILE", {"path": path_match.group(1).strip()}) if path_match else None

    elif tool_name == "WRITE_FILE":
        path_match = re.search(r'path:\s*(.+)', body)
        content_match = re.search(r'content:\n(.*)', body, re.DOTALL)
        if path_match and content_match:
            return ("WRITE_FILE", {"path": path_match.group(1).strip(), "content": content_match.group(1)})
        return None

    elif tool_name == "EDIT_FILE":
        path_match = re.search(r'path:\s*(.+)', body)
        old_match = re.search(r'old:\s*\n?(.*?)\nnew:', body, re.DOTALL)
        new_match = re.search(r'new:\s*\n?(.*)', body, re.DOTALL)
        if path_match and old_match and new_match:
            return ("EDIT_FILE", {
                "path": path_match.group(1).strip(),
                "old": old_match.group(1),
                "new": new_match.group(1),
            })
        return None

    elif tool_name == "RUN_CMD":
        cmd_match = re.search(r'cmd:\s*(.+)', body)
        return ("RUN_CMD", {"cmd": cmd_match.group(1).strip()}) if cmd_match else None

    elif tool_name == "DONE":
        return ("DONE", {"summary": body})

    return None


def execute_tool(tool_name: str, params: dict) -> str:
    if tool_name == "READ_FILE":
        return read_file(params["path"])
    elif tool_name == "WRITE_FILE":
        return write_file(params["path"], params["content"])
    elif tool_name == "EDIT_FILE":
        return edit_file(params["path"], params["old"], params["new"])
    elif tool_name == "RUN_CMD":
        return run_cmd(params["cmd"])
    elif tool_name == "DONE":
        return params.get("summary", "완료")
    return "[알 수 없는 도구]"


def main():
    print("=" * 60)
    print("  AI 코딩 에이전트 (폐쇄망 버전)")
    print(f"  모델: {MODEL}")
    print(f"  API: {API_BASE}")
    print("  종료: quit 또는 exit")
    print("=" * 60)

    while True:
        print()
        user_input = input(">>> ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("종료합니다.")
            break

        conversation.append({"role": "user", "content": user_input})

        # 에이전트 루프: 최대 20회 반복
        for step in range(20):
            print(f"\n[Step {step + 1}] LLM 응답 대기 중...")
            response = call_llm(conversation)

            # 도구 호출 파싱
            tool = parse_tool(response)

            if tool is None:
                # 도구 호출 없이 텍스트 응답
                print(f"\n{response}")
                conversation.append({"role": "assistant", "content": response})
                break

            tool_name, params = tool
            print(f"[도구: {tool_name}]", end=" ")

            if tool_name == "DONE":
                summary = params.get("summary", "완료")
                print(f"\n\n작업 완료: {summary}")
                conversation.append({"role": "assistant", "content": response})
                break

            if tool_name == "READ_FILE":
                print(f"→ {params['path']}")
            elif tool_name == "WRITE_FILE":
                confirm = input(f"→ {params['path']} 에 쓰기 (y/n): ").strip().lower()
                if confirm != "y":
                    conversation.append({"role": "assistant", "content": response})
                    conversation.append({"role": "user", "content": "[사용자가 파일 쓰기를 거부함]"})
                    continue
            elif tool_name == "EDIT_FILE":
                print(f"→ {params['path']}")
                print(f"  old: {params['old'][:80]}...")
                print(f"  new: {params['new'][:80]}...")
                confirm = input("  적용? (y/n): ").strip().lower()
                if confirm != "y":
                    conversation.append({"role": "assistant", "content": response})
                    conversation.append({"role": "user", "content": "[사용자가 수정을 거부함]"})
                    continue
            elif tool_name == "RUN_CMD":
                print(f"→ {params['cmd']}")
                confirm = input("  실행? (y/n): ").strip().lower()
                if confirm != "y":
                    conversation.append({"role": "assistant", "content": response})
                    conversation.append({"role": "user", "content": "[사용자가 명령어 실행을 거부함]"})
                    continue

            # 도구 실행
            result = execute_tool(tool_name, params)
            if tool_name == "READ_FILE" and len(result) > 200:
                print(f"  ({len(result.splitlines())}줄 읽음)")
            else:
                print(f"  결과: {result[:200]}")

            # 결과를 대화에 추가
            conversation.append({"role": "assistant", "content": response})
            conversation.append({"role": "user", "content": f"[도구 결과]\n{result}"})
        else:
            print("\n[경고] 최대 반복 횟수 도달")


if __name__ == "__main__":
    main()
