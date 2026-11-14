from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable

from .permissions import (
    ApprovalCallback,
    PermissionDecision,
    PermissionPolicy,
    RiskLevel,
)
from .trace import NullTrace


ToolHandler = Callable[..., str]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    risk: RiskLevel = RiskLevel.OBSERVE

    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(
        self,
        *,
        permission_policy: PermissionPolicy | None = None,
        approval_callback: ApprovalCallback | None = None,
        trace: Any | None = None,
    ) -> None:
        self._tools: dict[str, Tool] = {}
        self.permission_policy = permission_policy or PermissionPolicy()
        self.approval_callback = approval_callback
        self.trace = trace or NullTrace()

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def definitions(self) -> list[dict[str, Any]]:
        return [tool.definition() for tool in self._tools.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'"
        permission = self.permission_policy.evaluate(tool.name, tool.risk)
        if permission.decision is PermissionDecision.DENY:
            self.trace.record(
                "permission_denied",
                tool=name,
                risk=tool.risk.value,
                reason=permission.reason,
            )
            return f"Permission denied: {permission.reason}"
        if permission.decision is PermissionDecision.ASK:
            if self.approval_callback is None:
                self.trace.record(
                    "approval_required",
                    tool=name,
                    risk=tool.risk.value,
                    reason=permission.reason,
                )
                return f"Approval required: {permission.reason}"
            if not self.approval_callback(name, tool.risk, arguments, permission.reason):
                self.trace.record(
                    "approval_rejected", tool=name, risk=tool.risk.value
                )
                return f"Permission denied by user: {name}"

        started = perf_counter()
        try:
            output = tool.handler(**arguments)
            self.trace.record(
                "tool_finished",
                tool=name,
                risk=tool.risk.value,
                ok=_output_is_success(output),
                duration_ms=round((perf_counter() - started) * 1000, 2),
                output_chars=len(output),
            )
            return output
        except (OSError, TypeError, ValueError) as error:
            self.trace.record(
                "tool_finished",
                tool=name,
                risk=tool.risk.value,
                ok=False,
                duration_ms=round((perf_counter() - started) * 1000, 2),
                error_type=type(error).__name__,
            )
            return f"Error: {error}"


def _output_is_success(output: str) -> bool:
    if output.startswith(("Error:", "Timed out", "Permission denied", "Approval required")):
        return False
    if output.startswith("exit_code="):
        first_line = output.partition("\n")[0]
        try:
            return int(first_line.partition("=")[2]) == 0
        except ValueError:
            return False
    return True

