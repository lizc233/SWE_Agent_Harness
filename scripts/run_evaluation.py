from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from shutil import copytree, which

from swe_agent.agent import AgentLoop
from swe_agent.models import ModelResponse, ToolCall
from swe_agent.permissions import ApprovalMode, PermissionPolicy
from swe_agent.tools import build_workspace_registry


class CaseModel:
    def __init__(self, case_id: str) -> None:
        if case_id != "zero-total-percentage":
            raise ValueError(f"unsupported case: {case_id}")
        self.responses = [
            ModelResponse(tool_calls=(ToolCall("1", "list_files", {}),)),
            ModelResponse(tool_calls=(ToolCall("2", "read_file", {"path": "buggy_math.py"}),)),
            ModelResponse(
                tool_calls=(
                    ToolCall(
                        "3",
                        "edit_file",
                        {
                            "path": "buggy_math.py",
                            "old_text": "    return part / total * 100",
                            "new_text": "    if total == 0:\n        return 0.0\n    return part / total * 100",
                        },
                    ),
                )
            ),
            ModelResponse(
                tool_calls=(
                    ToolCall(
                        "4",
                        "run_command",
                        {"command": [sys.executable, "-m", "unittest", "discover", "-s", "tests"]},
                    ),
                )
            ),
            ModelResponse(tool_calls=(ToolCall("5", "git_diff", {}),)),
            ModelResponse(text="completed"),
        ]

    def complete(self, messages, tools):
        return self.responses.pop(0)


def run_case(case_id: str, source: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir) / "repo"
        copytree(source, workspace)
        for command in (
            ["git", "init", "-q"],
            ["git", "config", "core.autocrlf", "false"],
            ["git", "config", "user.email", "eval@example.com"],
            ["git", "config", "user.name", "Evaluation"],
        ):
            subprocess.run(command, cwd=workspace, check=True)
        subprocess.run(["git", "add", "."], cwd=workspace, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=workspace, check=True)
        registry = build_workspace_registry(
            workspace,
            permission_policy=PermissionPolicy(ApprovalMode.AUTO_EDIT),
            approval_callback=lambda *args: True,
        )
        result = AgentLoop(
            CaseModel(case_id),
            registry,
            system_prompt="Repair and verify.",
            max_steps=8,
        ).run("Fix the failing test.")
        outputs = [
            message.get("content", "")
            for message in result.messages
            if message.get("role") == "tool"
        ]
        tests_passed = any("exit_code=0" in output for output in outputs)
        diff_contains_guard = any(
            "+    if total == 0:" in output for output in outputs
        )
        return {
            "id": case_id,
            "ok": tests_passed and diff_contains_guard,
            "steps": result.steps,
            "tool_calls": result.tool_calls,
            "tests_passed": tests_passed,
            "diff_contains_guard": diff_contains_guard,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run versioned offline evaluation cases.")
    parser.add_argument("--suite", type=Path, default=Path("evaluations/suite.json"))
    parser.add_argument("--case", default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if which("git") is None:
        raise SystemExit("git is required for the evaluation")
    suite_path = args.suite.resolve()
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    cases = [
        case
        for case in suite["cases"]
        if args.case is None or case["id"] == args.case
    ]
    if not cases:
        raise SystemExit("no evaluation cases selected")
    project_root = suite_path.parents[1]
    results = [
        run_case(case["id"], project_root / case["repository"]) for case in cases
    ]
    report = {
        "suite": suite["suite"],
        "version": suite["version"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": results,
        "passed": sum(bool(result["ok"]) for result in results),
        "total": len(results),
    }
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if report["passed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

