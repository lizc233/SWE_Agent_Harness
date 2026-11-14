from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
COMMANDS = (
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
    [sys.executable, "-m", "compileall", "-q", "src", "tests", "scripts"],
    [
        sys.executable,
        "scripts/run_evaluation.py",
        "--output",
        ".swe-agent/reports/ci.json",
    ],
)


def main() -> int:
    environment = os.environ.copy()
    source_path = str(ROOT / "src")
    existing_path = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path
        if not existing_path
        else os.pathsep.join((source_path, existing_path))
    )
    for command in COMMANDS:
        print(f"\n> {' '.join(command)}", flush=True)
        result = subprocess.run(command, cwd=ROOT, env=environment, check=False)
        if result.returncode != 0:
            return result.returncode
    print("\nAll local CI checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

