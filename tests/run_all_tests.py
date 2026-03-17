"""Run all test levels with a summary report.

Usage: python tests/run_all_tests.py [--include-integration] [--include-load]
"""

import subprocess
import sys
import time

PYTHON = sys.executable


def run_level(name: str, marker: str, extra_args: list[str] | None = None):
    """Run a test level and return (passed, total, elapsed)."""
    args = [PYTHON, "-m", "pytest", "-v", "--tb=short", f"-m={marker}"]
    if extra_args:
        args.extend(extra_args)

    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    start = time.time()
    result = subprocess.run(args, capture_output=False)
    elapsed = time.time() - start

    return result.returncode == 0, elapsed


def main():
    include_integration = "--include-integration" in sys.argv
    include_load = "--include-load" in sys.argv

    results = []

    # Level 1: Smoke
    ok, t = run_level("Level 1: Smoke Tests", "smoke")
    results.append(("Smoke", ok, t))

    # Level 2: Unit
    ok, t = run_level("Level 2: Unit Tests", "unit")
    results.append(("Unit", ok, t))

    # Level 3: Integration (optional)
    if include_integration:
        ok, t = run_level("Level 3: Integration Tests", "integration")
        results.append(("Integration", ok, t))
    else:
        results.append(("Integration", None, 0))

    # Level 4: Chaos
    ok, t = run_level("Level 4: Chaos Tests", "chaos")
    results.append(("Chaos", ok, t))

    # Level 5: Load (optional, separate tool)
    if include_load:
        print("\n" + "="*60)
        print("  Level 5: Load Tests (Locust)")
        print("="*60)
        start = time.time()
        result = subprocess.run([
            PYTHON, "-m", "locust",
            "-f", "tests/test_05_load.py",
            "--headless", "-u", "20", "-r", "5", "-t", "30s",
            "--host", "http://localhost:8000",
        ], capture_output=False)
        t = time.time() - start
        results.append(("Load", result.returncode == 0, t))
    else:
        results.append(("Load", None, 0))

    # Summary
    print(f"\n{'='*60}")
    print("  TEST SUMMARY")
    print(f"{'='*60}")
    for name, ok, t in results:
        if ok is None:
            status = "SKIPPED"
        elif ok:
            status = "PASSED"
        else:
            status = "FAILED"
        print(f"  {name:15s} {status:8s}  ({t:.1f}s)")

    failed = [r for r in results if r[1] is False]
    if failed:
        print(f"\n  {len(failed)} level(s) FAILED")
        sys.exit(1)
    else:
        print(f"\n  All tests PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
