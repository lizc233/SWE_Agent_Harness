from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from . import __version__
from .agent import AgentLoop, BudgetExceeded, StepLimitReached
from .config import ConfigError, load_env_file, load_runtime_config
from .context import ContextBudgetExceeded
from .permissions import ApprovalMode, PermissionPolicy, RiskLevel
from .provider import OpenAICompatibleClient
from .tools import build_workspace_registry
from .trace import JsonlTrace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SWE Agent Harness against a local workspace."
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("prompt", nargs="+", help="Task for the agent")
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional TOML configuration file",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Explicit env file for API credentials; never loaded automatically",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace the read tool is allowed to access",
    )
    parser.add_argument("--max-steps", type=int)
    parser.add_argument("--max-tool-calls", type=int)
    parser.add_argument("--max-wall-seconds", type=float)
    parser.add_argument("--max-context-chars", type=int)
    parser.add_argument(
        "--approval-mode",
        choices=[mode.value for mode in ApprovalMode],
        help="read-only denies mutations; ask prompts; auto-edit allows edit_file",
    )
    parser.add_argument(
        "--no-trace",
        action="store_true",
        help="Disable JSONL run trace creation",
    )
    return parser


def ask_for_approval(
    tool_name: str,
    risk: RiskLevel,
    arguments: dict[str, Any],
    reason: str,
) -> bool:
    print(f"\nApproval required: {reason}")
    print(f"Tool: {tool_name} [{risk.value}]")
    print(f"Arguments: {arguments}")
    return input("Allow once? [y/N] ").strip().lower() in {"y", "yes"}


def main() -> int:
    args = build_parser().parse_args()
    try:
        config = load_runtime_config(args.config)
        if args.env_file is not None:
            load_env_file(args.env_file)
    except ConfigError as error:
        raise SystemExit(f"Invalid configuration: {error}") from error
    workspace = args.workspace.resolve()
    if not workspace.is_dir():
        raise SystemExit(f"Workspace does not exist: {workspace}")

    api_key = os.getenv("OPENAI_COMPATIBLE_API_KEY") or os.getenv(
        "DEEPSEEK_API_KEY", ""
    )
    if not api_key:
        raise SystemExit(
            "Set OPENAI_COMPATIBLE_API_KEY or DEEPSEEK_API_KEY before running."
        )

    model = OpenAICompatibleClient(
        api_key=api_key,
        base_url=os.getenv("OPENAI_COMPATIBLE_BASE_URL", config.base_url),
        model=os.getenv("MODEL_ID", config.model),
    )
    trace = None
    trace_path = None
    if config.trace_enabled and not args.no_trace:
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        trace_path = workspace / ".swe-agent" / "runs" / f"{run_id}.jsonl"
        trace = JsonlTrace(trace_path)

    approval_mode = ApprovalMode(args.approval_mode) if args.approval_mode else config.approval_mode
    permission_policy = PermissionPolicy(approval_mode)
    tools = build_workspace_registry(
        workspace,
        permission_policy=permission_policy,
        approval_callback=ask_for_approval,
        trace=trace,
    )
    agent = AgentLoop(
        model,
        tools,
        system_prompt=(
            "You are a software engineering agent. Inspect before editing, make "
            "minimal changes, run relevant tests, inspect Git diff, and report "
            "failures honestly. Tool permissions are enforced by the harness. "
            f"The workspace is {workspace}."
        ),
        max_steps=config.max_steps if args.max_steps is None else args.max_steps,
        max_tool_calls=(
            config.max_tool_calls
            if args.max_tool_calls is None
            else args.max_tool_calls
        ),
        max_wall_seconds=(
            config.max_wall_seconds
            if args.max_wall_seconds is None
            else args.max_wall_seconds
        ),
        max_context_chars=(
            config.max_context_chars
            if args.max_context_chars is None
            else args.max_context_chars
        ),
        trace=trace,
    )

    try:
        result = agent.run(" ".join(args.prompt))
    except (StepLimitReached, BudgetExceeded, ContextBudgetExceeded) as error:
        print(f"Stopped: {error}")
        return 2

    print(result.final_text)
    print(
        f"\n[steps={result.steps}, tool_calls={result.tool_calls}, "
        f"prompt_tokens={result.prompt_tokens}, "
        f"completion_tokens={result.completion_tokens}]"
    )
    if trace_path is not None:
        print(f"[trace={trace_path}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

