from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class RiskLevel(str, Enum):
    OBSERVE = "observe"
    WRITE = "write"
    EXECUTE = "execute"
    DESTRUCTIVE = "destructive"


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class ApprovalMode(str, Enum):
    READ_ONLY = "read-only"
    ASK = "ask"
    AUTO_EDIT = "auto-edit"


@dataclass(frozen=True)
class PermissionResult:
    decision: PermissionDecision
    reason: str


ApprovalCallback = Callable[[str, RiskLevel, dict[str, Any], str], bool]


class PermissionPolicy:
    def __init__(self, mode: ApprovalMode = ApprovalMode.READ_ONLY) -> None:
        self.mode = mode

    def evaluate(self, tool_name: str, risk: RiskLevel) -> PermissionResult:
        if risk is RiskLevel.OBSERVE:
            return PermissionResult(PermissionDecision.ALLOW, "read-only observation")
        if risk is RiskLevel.DESTRUCTIVE:
            return PermissionResult(
                PermissionDecision.DENY,
                "destructive tools are disabled by policy",
            )
        if self.mode is ApprovalMode.READ_ONLY:
            return PermissionResult(
                PermissionDecision.DENY,
                f"{risk.value} tools are disabled in read-only mode",
            )
        if risk is RiskLevel.WRITE and self.mode is ApprovalMode.AUTO_EDIT:
            return PermissionResult(
                PermissionDecision.ALLOW,
                "workspace file edits are allowed in auto-edit mode",
            )
        return PermissionResult(
            PermissionDecision.ASK,
            f"{tool_name} requires approval because it can {risk.value}",
        )

