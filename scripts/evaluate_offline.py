from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from shutil import copytree, which

from swe_agent.agent import AgentLoop
from swe_agent.models import ModelResponse, ToolCall
from swe_agent.permissions import ApprovalMode, PermissionPolicy
from swe_agent.tools import build_workspace_registry


class ScriptedModel:
    def __init__(self) -> None:
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
                        {"command": [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]},
                    ),
                )
            ),
            ModelResponse(tool_calls=(ToolCall("5", "git_diff", {}),)),
            ModelResponse(text="offline evaluation complete"),
        ]

    def complete(self, messages, tools):
        return self.responses.pop(0)


def main() -> int:
    if which("git") is None:
        print(json.dumps({"ok": False, "error": "git unavailable"}))
        return 2
    project_root = Path(__file__).parents[1]
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir) / "repo"
        copytree(project_root / "examples" / "demo_repo", workspace)
        subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
        subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=workspace, check=True)
        subprocess.run(["git", "config", "user.email", "eval@example.com"], cwd=workspace, check=True)
        subprocess.run(["git", "config", "user.name", "Eval"], cwd=workspace, check=True)
        subprocess.run(["git", "add", "."], cwd=workspace, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=workspace, check=True)
        registry = build_workspace_registry(
            workspace,
            permission_policy=PermissionPolicy(ApprovalMode.AUTO_EDIT),
            approval_callback=lambda *args: True,
        )
        result = AgentLoop(
            ScriptedModel(),
            registry,
            system_prompt="Repair and verify.",
            max_steps=8,
        ).run("Fix the zero-total test.")
        test_passed = any(
            message.get("role") == "tool"
            and "exit_code=0" in message.get("content", "")
            and "OK" in message.get("content", "")
            for message in result.messages
        )
        report = {
            "ok": test_passed,
            "steps": result.steps,
            "tool_calls": result.tool_calls,
            "test_passed": test_passed,
        }
        print(json.dumps(report, ensure_ascii=False))
        return 0 if test_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
