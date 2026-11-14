from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from .context import compact_tool_outputs
from .models import ModelClient, ToolCall
from .tools import ToolRegistry
from .trace import NullTrace


class StepLimitReached(RuntimeError):
    """Raised when the model keeps requesting actions beyond the allowed budget."""


class BudgetExceeded(RuntimeError):
    """Raised when a tool-call or wall-clock budget is exhausted."""


@dataclass(frozen=True)
class AgentResult:
    final_text: str
    steps: int
    tool_calls: int
    messages: tuple[dict[str, Any], ...]
    prompt_tokens: int = 0
    completion_tokens: int = 0


class AgentLoop:
    def __init__(
        self,
        model: ModelClient,
        tools: ToolRegistry,
        *,
        system_prompt: str,
        max_steps: int = 8,
        max_tool_calls: int = 32,
        max_wall_seconds: float = 900,
        max_context_chars: int = 200_000,
        trace: Any | None = None,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be at least 1")
        if max_wall_seconds <= 0:
            raise ValueError("max_wall_seconds must be positive")
        if max_context_chars < 1:
            raise ValueError("max_context_chars must be positive")
        self.model = model
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.max_tool_calls = max_tool_calls
        self.max_wall_seconds = max_wall_seconds
        self.max_context_chars = max_context_chars
        self.trace = trace or NullTrace()

    def run(self, user_prompt: str) -> AgentResult:
        if not user_prompt.strip():
            raise ValueError("user_prompt must not be empty")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        total_tool_calls = 0
        prompt_tokens = 0
        completion_tokens = 0
        started = perf_counter()
        self.trace.record(
            "run_started",
            max_steps=self.max_steps,
            max_tool_calls=self.max_tool_calls,
            max_wall_seconds=self.max_wall_seconds,
        )

        for step in range(1, self.max_steps + 1):
            self._check_wall_budget(started)
            compacted_chars = compact_tool_outputs(messages, self.max_context_chars)
            if compacted_chars:
                self.trace.record(
                    "context_compacted",
                    step=step,
                    compacted_chars=compacted_chars,
                    message_count=len(messages),
                )
            self.trace.record("model_requested", step=step, message_count=len(messages))
            response = self.model.complete(messages, self.tools.definitions())
            prompt_tokens += response.prompt_tokens
            completion_tokens += response.completion_tokens
            messages.append(self._assistant_message(response.text, response.tool_calls))

            if not response.tool_calls:
                self.trace.record(
                    "run_finished",
                    status="completed",
                    steps=step,
                    tool_calls=total_tool_calls,
                    duration_ms=round((perf_counter() - started) * 1000, 2),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
                return AgentResult(
                    final_text=response.text,
                    steps=step,
                    tool_calls=total_tool_calls,
                    messages=tuple(messages),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )

            for call in response.tool_calls:
                self._check_wall_budget(started)
                if total_tool_calls >= self.max_tool_calls:
                    self.trace.record(
                        "run_finished",
                        status="tool_budget_exceeded",
                        steps=step,
                        tool_calls=total_tool_calls,
                    )
                    raise BudgetExceeded(
                        f"agent reached max_tool_calls={self.max_tool_calls}"
                    )
                total_tool_calls += 1
                self.trace.record(
                    "tool_requested",
                    step=step,
                    tool_call_id=call.id,
                    tool=call.name,
                )
                output = self.tools.execute(call.name, call.arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": output,
                    }
                )

        self.trace.record(
            "run_finished",
            status="step_limit_reached",
            steps=self.max_steps,
            tool_calls=total_tool_calls,
        )
        raise StepLimitReached(
            f"agent reached max_steps={self.max_steps} without a final answer"
        )

    def _check_wall_budget(self, started: float) -> None:
        elapsed = perf_counter() - started
        if elapsed <= self.max_wall_seconds:
            return
        self.trace.record(
            "run_finished",
            status="wall_budget_exceeded",
            duration_ms=round(elapsed * 1000, 2),
        )
        raise BudgetExceeded(
            f"agent reached max_wall_seconds={self.max_wall_seconds}"
        )

    @staticmethod
    def _assistant_message(
        text: str,
        tool_calls: tuple[ToolCall, ...],
    ) -> dict[str, Any]:
        message: dict[str, Any] = {
            "role": "assistant",
            "content": text or None,
        }
        if tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=False),
                    },
                }
                for call in tool_calls
            ]
        return message

