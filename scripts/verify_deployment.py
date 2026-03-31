"""
Deployment Verification Script
ZIP 배포 전 반드시 실행. 하나라도 FAIL이면 배포 금지.

Usage:
    python scripts/verify_deployment.py
"""
import subprocess
import sys
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
RESULTS = []

# Windows console encoding fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name: str, passed: bool, detail: str = ""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((name, passed, detail))
    icon = "[PASS]" if passed else "[FAIL]"
    print(f"  {icon} {name}" + (f" -- {detail}" if detail else ""))


def step(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def main():
    print("\n" + "=" * 60)
    print("  DEPLOYMENT VERIFICATION")
    print("  배포 전 검증 스크립트")
    print("=" * 60)

    # ─────────────────────────────────────────────
    step("1. Import vs Requirements 대조")
    # ─────────────────────────────────────────────
    app_dir = ROOT / "app"
    imports = set()
    for py_file in app_dir.rglob("*.py"):
        with open(py_file, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("from ") and "import" in line:
                    pkg = line.split()[1].split(".")[0]
                    if not pkg.startswith(("app", ".")):
                        imports.add(pkg)
                elif line.startswith("import "):
                    pkg = line.split()[1].split(".")[0].rstrip(",")
                    if not pkg.startswith(("app", ".")):
                        imports.add(pkg)

    # 표준 라이브러리 제외
    stdlib = {
        "os", "sys", "re", "json", "time", "datetime", "pathlib", "typing",
        "uuid", "hashlib", "hmac", "asyncio", "subprocess", "base64",
        "collections", "dataclasses", "functools", "io", "math", "pickle",
        "secrets", "shutil", "tempfile", "threading", "traceback", "urllib",
        "logging", "copy", "enum", "abc", "contextlib", "itertools",
        "__future__", "base", "concurrent",
    }
    external_imports = imports - stdlib

    # 패키지명 매핑 (import 이름 → pip 패키지명)
    IMPORT_TO_PKG = {
        "jose": "python-jose",
        "bs4": "beautifulsoup4",
        "yaml": "pyyaml",
        "lxml": "lxml",
        "PIL": "pillow",
        "sklearn": "scikit-learn",
        "cv2": "opencv-python",
        "dotenv": "python-dotenv",
        "pydantic_settings": "pydantic-settings",
    }

    req_file = ROOT / "requirements_full.txt"
    if req_file.exists():
        req_text = req_file.read_text().lower()
    else:
        req_text = ""
        check("requirements_full.txt", False, "파일 없음!")

    missing_pkgs = []
    for imp in sorted(external_imports):
        pkg_name = IMPORT_TO_PKG.get(imp, imp).lower()
        # requirements에서 패키지명 검색 (- 와 _ 호환)
        pkg_variants = [pkg_name, pkg_name.replace("-", "_"), pkg_name.replace("_", "-")]
        found = any(v in req_text for v in pkg_variants)
        if not found:
            missing_pkgs.append(f"{imp} (pip: {pkg_name})")

    if missing_pkgs:
        check("Import vs Requirements", False, f"누락: {', '.join(missing_pkgs)}")
    else:
        check("Import vs Requirements", True, f"{len(external_imports)}개 외부 패키지 전부 포함")

    # ─────────────────────────────────────────────
    step("2. Offline Packages (.whl) 존재 여부")
    # ─────────────────────────────────────────────
    pkg_dir = ROOT / "offline_packages"
    if pkg_dir.exists():
        whl_files = list(pkg_dir.glob("*.whl"))
        check("offline_packages/ 존재", True, f"{len(whl_files)}개 .whl 파일")

        # requirements_full.txt의 각 패키지가 whl로 있는지
        if req_file.exists():
            req_lines = [
                l.strip().split("==")[0].lower().replace("-", "_")
                for l in req_file.read_text().splitlines()
                if l.strip() and not l.startswith("#")
            ]
            whl_names = [f.name.lower().split("-")[0].replace("-", "_") for f in whl_files]
            missing_whl = [r for r in req_lines if r not in whl_names]
            if missing_whl:
                check("WHL 파일 매칭", False, f"누락: {', '.join(missing_whl[:5])}...")
            else:
                check("WHL 파일 매칭", True, f"{len(req_lines)}개 전부 매칭")
    else:
        check("offline_packages/ 존재", False, "폴더 없음")

    # ─────────────────────────────────────────────
    step("3. 핵심 파일 존재 여부")
    # ─────────────────────────────────────────────
    critical_files = [
        "app/main.py",
        "app/core/auth.py",
        "app/core/vector_store.py",
        "app/llm_client.py",
        "app/services/text2sql_service.py",
        "app/services/rag_service.py",
        "app/services/chat_service.py",
        "app/services/multi_agent_service.py",
        "platform/src/App.tsx",
        "platform/src/lib/api.ts",
        "platform/src/components/Sidebar.tsx",
        "platform/vite.config.ts",
        "platform/tailwind.config.ts",
        "platform/postcss.config.js",
        "platform/package.json",
        "requirements.txt",
        "requirements_full.txt",
        ".env.airgap",
        "start.bat",
        "install.bat",
        "README.md",
    ]

    missing_files = [f for f in critical_files if not (ROOT / f).exists()]
    if missing_files:
        for f in missing_files:
            check(f"파일: {f}", False, "없음")
    else:
        check("핵심 파일 전부 존재", True, f"{len(critical_files)}개")

    # ─────────────────────────────────────────────
    step("4. 빌드된 프론트엔드 (platform/dist/)")
    # ─────────────────────────────────────────────
    dist_dir = ROOT / "platform" / "dist"
    if dist_dir.exists():
        index_html = dist_dir / "index.html"
        assets = list((dist_dir / "assets").glob("*")) if (dist_dir / "assets").exists() else []
        check("platform/dist/ 존재", True)
        check("dist/index.html", index_html.exists())
        check("dist/assets/", len(assets) > 0, f"{len(assets)}개 파일")
    else:
        check("platform/dist/", False, "빌드 안 됨 — npm run build 필요")

    # ─────────────────────────────────────────────
    step("5. Import 실행 테스트")
    # ─────────────────────────────────────────────
    test_imports = [
        "fastapi", "uvicorn", "sqlalchemy", "openai", "chromadb",
        "loguru", "bcrypt", "httpx", "oracledb", "jose",
        "sentence_transformers", "pydantic", "bs4", "tiktoken",
    ]
    for pkg in test_imports:
        try:
            result = subprocess.run(
                [sys.executable, "-c", f"import {pkg}"],
                capture_output=True, text=True, timeout=10
            )
            check(f"import {pkg}", result.returncode == 0,
                  result.stderr.strip()[:80] if result.returncode != 0 else "")
        except Exception as e:
            check(f"import {pkg}", False, str(e)[:80])

    # ─────────────────────────────────────────────
    step("6. app.main import 테스트")
    # ─────────────────────────────────────────────
    try:
        result = subprocess.run(
            [sys.executable, "-c", "from app.main import app; print('app.main OK')"],
            capture_output=True, text=True, timeout=30,
            cwd=str(ROOT)
        )
        if result.returncode == 0:
            check("from app.main import app", True)
        else:
            err = result.stderr.strip().split("\n")[-1][:100]
            check("from app.main import app", False, err)
    except Exception as e:
        check("from app.main import app", False, str(e)[:80])

    # ─────────────────────────────────────────────
    step("7. .env.airgap 설정 확인")
    # ─────────────────────────────────────────────
    env_file = ROOT / ".env.airgap"
    if env_file.exists():
        env_text = env_file.read_text(encoding="utf-8", errors="ignore")
        check("LLM_API_BASE 설정", "LLM_API_BASE" in env_text)
        check("LLM_MODEL 설정", "LLM_MODEL" in env_text)
        check("EMBEDDING_MODEL_PATH 설정", "EMBEDDING_MODEL_PATH" in env_text)
    else:
        check(".env.airgap", False, "파일 없음")

    # ─────────────────────────────────────────────
    # 최종 결과
    # ─────────────────────────────────────────────
    total = len(RESULTS)
    passed = sum(1 for _, p, _ in RESULTS if p)
    failed = total - passed

    print(f"\n{'='*60}")
    if failed == 0:
        print(f"  [OK] ALL {total} CHECKS PASSED -- READY TO DEPLOY")
    else:
        print(f"  [NG] {failed}/{total} CHECKS FAILED -- DO NOT DEPLOY")
        print(f"\n  Failed items:")
        for name, p, detail in RESULTS:
            if not p:
                print(f"    [FAIL] {name}: {detail}")
    print(f"{'='*60}\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
