from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from swe_agent.agent import AgentLoop
from swe_agent.models import ModelResponse, ToolCall
from swe_agent.permissions import ApprovalMode, PermissionPolicy
from swe_agent.tools import build_workspace_registry


class ScriptedRepairModel:
    def __init__(self) -> None:
        self.responses = [
            ModelResponse(tool_calls=(ToolCall("1", "list_files", {}),)),
            ModelResponse(
                tool_calls=(
                    ToolCall(
                        "2",
                        "search_text",
                        {"query": "def percentage", "file_pattern": "*.py"},
                    ),
                )
            ),
            ModelResponse(
                tool_calls=(ToolCall("3", "read_file", {"path": "buggy_math.py"}),)
            ),
            ModelResponse(
                tool_calls=(
                    ToolCall(
                        "4",
                        "edit_file",
                        {
                            "path": "buggy_math.py",
                            "old_text": (
                                "def percentage(part: float, total: float) -> float:\n"
                                "    return part / total * 100"
                            ),
                            "new_text": (
                                "def percentage(part: float, total: float) -> float:\n"
                                "    if total == 0:\n"
                                "        return 0.0\n"
                                "    return part / total * 100"
                            ),
                        },
                    ),
                )
            ),
            ModelResponse(
                tool_calls=(
                    ToolCall(
                        "5",
                        "run_command",
                        {
                            "command": [
                                sys.executable,
                                "-m",
                                "unittest",
                                "discover",
                                "-s",
                                "tests",
                                "-v",
                            ]
                        },
                    ),
                )
            ),
            ModelResponse(tool_calls=(ToolCall("6", "git_diff", {}),)),
            ModelResponse(text="Fixed zero-total handling and verified both tests."),
        ]

    def complete(self, messages, tools):
        return self.responses.pop(0)


@unittest.skipUnless(shutil.which("git"), "git unavailable")
class EndToEndRepairTests(unittest.TestCase):
    def test_agent_completes_search_edit_test_diff_loop(self) -> None:
        source = Path(__file__).parents[1] / "examples" / "demo_repo"
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir) / "repo"
            shutil.copytree(source, workspace)
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            subprocess.run(
                ["git", "config", "core.autocrlf", "false"], cwd=workspace, check=True
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=workspace,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"], cwd=workspace, check=True
            )
            subprocess.run(["git", "add", "."], cwd=workspace, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "baseline"], cwd=workspace, check=True
            )
            registry = build_workspace_registry(
                workspace,
                permission_policy=PermissionPolicy(ApprovalMode.AUTO_EDIT),
                approval_callback=lambda *args: True,
            )
            agent = AgentLoop(
                ScriptedRepairModel(),
                registry,
                system_prompt="Repair and verify the repository.",
                max_steps=10,
            )

            result = agent.run("Fix the failing zero-total percentage test.")

            self.assertEqual(result.tool_calls, 6)
            self.assertIn("verified", result.final_text)
            edited = (workspace / "buggy_math.py").read_text(encoding="utf-8")
            self.assertIn("if total == 0", edited)
            tool_outputs = [
                message["content"]
                for message in result.messages
                if message.get("role") == "tool"
            ]
            self.assertTrue(any("exit_code=0" in output and "OK" in output for output in tool_outputs))
            self.assertTrue(any("+    if total == 0:" in output for output in tool_outputs))

