from __future__ import annotations

from pathlib import Path
from typing import Any

from .execution import CommandRunner
from .permissions import ApprovalCallback, PermissionPolicy, RiskLevel
from .tooling import Tool, ToolRegistry
from .workspace import Workspace


def build_workspace_registry(
    workspace: Path,
    *,
    permission_policy: PermissionPolicy | None = None,
    approval_callback: ApprovalCallback | None = None,
    trace: Any | None = None,
) -> ToolRegistry:
    workspace_api = Workspace(workspace)
    command_runner = CommandRunner(workspace_api)
    registry = ToolRegistry(
        permission_policy=permission_policy,
        approval_callback=approval_callback,
        trace=trace,
    )
    registry.register(
        Tool(
            "read_file",
            "Read a UTF-8 text file inside the workspace with line numbers.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path relative to the workspace."},
                    "start_line": {"type": "integer", "minimum": 1},
                    "end_line": {"type": "integer", "minimum": 1},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
            workspace_api.read_file,
        )
    )
    registry.register(
        Tool(
            "list_files",
            "Recursively list files as sorted workspace-relative paths.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "max_entries": {"type": "integer", "minimum": 1, "maximum": 1000},
                },
                "additionalProperties": False,
            },
            workspace_api.list_files,
        )
    )
    registry.register(
        Tool(
            "search_text",
            "Search UTF-8 files for literal text and return path:line:text matches.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "minLength": 1},
                    "path": {"type": "string"},
                    "file_pattern": {"type": "string"},
                    "case_sensitive": {"type": "boolean"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 1000},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            workspace_api.search_text,
        )
    )
    registry.register(
        Tool(
            "edit_file",
            "Atomically replace exact text with an expected replacement count.",
            {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string", "minLength": 1},
                    "new_text": {"type": "string"},
                    "expected_replacements": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 100,
                    },
                },
                "required": ["path", "old_text", "new_text"],
                "additionalProperties": False,
            },
            workspace_api.edit_file,
            RiskLevel.WRITE,
        )
    )
    registry.register(
        Tool(
            "run_command",
            "Run one executable directly without a shell for tests and builds.",
            {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                        "minItems": 1,
                        "maxItems": 100,
                    },
                    "cwd": {"type": "string"},
                    "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 600},
                },
                "required": ["command"],
                "additionalProperties": False,
            },
            command_runner.run_command,
            RiskLevel.EXECUTE,
        )
    )
    registry.register(
        Tool(
            "git_status",
            "Show concise Git branch and working-tree status.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            command_runner.git_status,
        )
    )
    registry.register(
        Tool(
            "git_diff",
            "Show unstaged or staged Git changes without external diff tools.",
            {
                "type": "object",
                "properties": {"staged": {"type": "boolean"}},
                "additionalProperties": False,
            },
            command_runner.git_diff,
        )
    )
    return registry


build_read_only_registry = build_workspace_registry


__all__ = ["Tool", "ToolRegistry", "build_workspace_registry", "build_read_only_registry"]

