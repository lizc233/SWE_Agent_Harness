from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from swe_agent.agent import AgentLoop, BudgetExceeded, StepLimitReached
from swe_agent.models import ModelResponse, ToolCall
from swe_agent.tools import build_workspace_registry


class FakeModel:
    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = list(responses)
        self.seen_messages: list[list[dict]] = []

    def complete(self, messages: list[dict], tools: list[dict]) -> ModelResponse:
        self.seen_messages.append(list(messages))
        return self.responses.pop(0)


class AgentLoopTests(unittest.TestCase):
    def test_executes_tool_and_returns_final_answer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "sample.py").write_text("answer = 42\n", encoding="utf-8")
            model = FakeModel(
                [
                    ModelResponse(
                        tool_calls=(
                            ToolCall("call-1", "read_file", {"path": "sample.py"}),
                        )
                    ),
                    ModelResponse(text="The file assigns 42 to answer."),
                ]
            )
            agent = AgentLoop(
                model,
                build_workspace_registry(workspace),
                system_prompt="Inspect the workspace.",
            )

            result = agent.run("What is in sample.py?")

            self.assertEqual(result.steps, 2)
            self.assertEqual(result.tool_calls, 1)
            self.assertEqual(result.final_text, "The file assigns 42 to answer.")
            second_request = model.seen_messages[1]
            self.assertEqual(second_request[-1]["role"], "tool")
            self.assertEqual(second_request[-1]["tool_call_id"], "call-1")
            self.assertIn("answer = 42", second_request[-1]["content"])

    def test_raises_when_model_never_stops_calling_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "sample.py").write_text("pass\n", encoding="utf-8")
            response = ModelResponse(
                tool_calls=(ToolCall("call-1", "read_file", {"path": "sample.py"}),)
            )
            agent = AgentLoop(
                FakeModel([response, response]),
                build_workspace_registry(workspace),
                system_prompt="Inspect the workspace.",
                max_steps=2,
            )

            with self.assertRaises(StepLimitReached):
                agent.run("Keep reading forever.")

    def test_enforces_tool_call_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "sample.py").write_text("pass\n", encoding="utf-8")
            response = ModelResponse(
                tool_calls=(
                    ToolCall("call-1", "read_file", {"path": "sample.py"}),
                    ToolCall("call-2", "read_file", {"path": "sample.py"}),
                )
            )
            agent = AgentLoop(
                FakeModel([response]),
                build_workspace_registry(workspace),
                system_prompt="Inspect the workspace.",
                max_tool_calls=1,
            )

            with self.assertRaises(BudgetExceeded):
                agent.run("Read twice.")

    def test_aggregates_reported_model_tokens(self) -> None:
        model = FakeModel(
            [ModelResponse(text="done", prompt_tokens=12, completion_tokens=4)]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = AgentLoop(
                model,
                build_workspace_registry(Path(temp_dir)),
                system_prompt="Inspect.",
            )

            result = agent.run("Finish.")

            self.assertEqual(result.prompt_tokens, 12)
            self.assertEqual(result.completion_tokens, 4)


if __name__ == "__main__":
    unittest.main()

