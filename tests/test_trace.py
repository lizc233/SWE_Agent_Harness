from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from swe_agent.agent import AgentLoop
from swe_agent.models import ModelResponse, ToolCall
from swe_agent.tools import build_workspace_registry
from swe_agent.trace import JsonlTrace
from swe_agent.permissions import ApprovalMode, PermissionPolicy


class FakeModel:
    def __init__(self) -> None:
        self.responses = [
            ModelResponse(
                tool_calls=(ToolCall("call-1", "read_file", {"path": "file.py"}),)
            ),
            ModelResponse(text="done"),
        ]

    def complete(self, messages, tools):
        return self.responses.pop(0)


class TraceTests(unittest.TestCase):
    def test_writes_structured_run_and_tool_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "file.py").write_text("pass\n", encoding="utf-8")
            trace_path = workspace / "trace.jsonl"
            trace = JsonlTrace(trace_path)
            registry = build_workspace_registry(workspace, trace=trace)
            agent = AgentLoop(
                FakeModel(),
                registry,
                system_prompt="Inspect.",
                trace=trace,
            )

            agent.run("Read the file.")

            events = [
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
            ]
            event_names = [event["event"] for event in events]
            self.assertIn("run_started", event_names)
            self.assertIn("tool_requested", event_names)
            self.assertIn("tool_finished", event_names)
            self.assertEqual(event_names[-1], "run_finished")
            requested = events[event_names.index("tool_requested")]
            self.assertNotIn("arguments", requested)

    def test_nonzero_command_exit_is_recorded_as_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            trace_path = workspace / "trace.jsonl"
            trace = JsonlTrace(trace_path)
            registry = build_workspace_registry(
                workspace,
                permission_policy=PermissionPolicy(ApprovalMode.ASK),
                approval_callback=lambda *args: True,
                trace=trace,
            )

            output = registry.execute(
                "run_command",
                {"command": [sys.executable, "-c", "raise SystemExit(7)"]},
            )

            self.assertEqual(output, "exit_code=7")
            event = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(event["event"], "tool_finished")
            self.assertFalse(event["ok"])

