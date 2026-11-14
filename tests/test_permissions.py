from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swe_agent.permissions import ApprovalMode, PermissionPolicy
from swe_agent.tools import build_workspace_registry


class PermissionTests(unittest.TestCase):
    def test_read_only_mode_allows_observation_and_denies_edits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "file.py"
            target.write_text("before\n", encoding="utf-8")
            registry = build_workspace_registry(workspace)

            read_output = registry.execute("read_file", {"path": "file.py"})
            edit_output = registry.execute(
                "edit_file",
                {"path": "file.py", "old_text": "before", "new_text": "after"},
            )

            self.assertIn("before", read_output)
            self.assertIn("Permission denied", edit_output)
            self.assertEqual(target.read_text(encoding="utf-8"), "before\n")

    def test_ask_mode_uses_the_approval_callback(self) -> None:
        decisions: list[tuple[str, str]] = []

        def approve(tool_name, risk, arguments, reason):
            decisions.append((tool_name, risk.value))
            return True

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "file.py"
            target.write_text("before\n", encoding="utf-8")
            registry = build_workspace_registry(
                workspace,
                permission_policy=PermissionPolicy(ApprovalMode.ASK),
                approval_callback=approve,
            )

            output = registry.execute(
                "edit_file",
                {"path": "file.py", "old_text": "before", "new_text": "after"},
            )

            self.assertIn("Edited file.py", output)
            self.assertEqual(decisions, [("edit_file", "write")])

    def test_ask_mode_does_not_execute_after_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "file.py"
            target.write_text("before\n", encoding="utf-8")
            registry = build_workspace_registry(
                workspace,
                permission_policy=PermissionPolicy(ApprovalMode.ASK),
                approval_callback=lambda *args: False,
            )

            output = registry.execute(
                "edit_file",
                {"path": "file.py", "old_text": "before", "new_text": "after"},
            )

            self.assertIn("denied by user", output)
            self.assertEqual(target.read_text(encoding="utf-8"), "before\n")

    def test_auto_edit_still_requires_approval_for_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_workspace_registry(
                Path(temp_dir),
                permission_policy=PermissionPolicy(ApprovalMode.AUTO_EDIT),
            )

            output = registry.execute("run_command", {"command": ["python", "-V"]})

            self.assertIn("Approval required", output)

