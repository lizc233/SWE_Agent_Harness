from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from swe_agent.permissions import ApprovalMode, PermissionPolicy
from swe_agent.tools import build_workspace_registry


class ExecutionToolTests(unittest.TestCase):
    def build_registry(self, workspace: Path):
        return build_workspace_registry(
            workspace,
            permission_policy=PermissionPolicy(ApprovalMode.ASK),
            approval_callback=lambda *args: True,
        )

    def test_runs_argument_array_without_shell_interpolation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self.build_registry(Path(temp_dir))

            output = registry.execute(
                "run_command",
                {"command": [sys.executable, "-c", "print('ok')"]},
            )

            self.assertEqual(output, "exit_code=0\nok")

    def test_reports_nonzero_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self.build_registry(Path(temp_dir))

            output = registry.execute(
                "run_command",
                {"command": [sys.executable, "-c", "raise SystemExit(3)"]},
            )

            self.assertEqual(output, "exit_code=3")

    def test_enforces_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self.build_registry(Path(temp_dir))

            output = registry.execute(
                "run_command",
                {
                    "command": [sys.executable, "-c", "import time; time.sleep(3)"],
                    "timeout_seconds": 1,
                },
            )

            self.assertIn("Timed out after 1s", output)

    def test_rejects_cwd_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = self.build_registry(Path(temp_dir))

            output = registry.execute(
                "run_command", {"command": [sys.executable, "-V"], "cwd": ".."}
            )

            self.assertIn("escapes workspace", output)

    @unittest.skipUnless(shutil.which("git"), "git unavailable")
    def test_git_status_is_observational_and_needs_no_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
            registry = build_workspace_registry(workspace)

            output = registry.execute("git_status", {})

            self.assertIn("exit_code=0", output)

