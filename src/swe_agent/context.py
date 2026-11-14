from __future__ import annotations

import json
from typing import Any


class ContextBudgetExceeded(RuntimeError):
    """Raised when context cannot fit even after safe tool-output compaction."""


def context_size(messages: list[dict[str, Any]]) -> int:
    return len(json.dumps(messages, ensure_ascii=False, default=str))


def compact_tool_outputs(
    messages: list[dict[str, Any]],
    max_chars: int,
    *,
    keep_each_side: int = 800,
) -> int:
    """Compact old tool content in place without removing protocol messages."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    before = context_size(messages)
    if before <= max_chars:
        return 0

    compacted = 0
    tool_messages = [message for message in messages if message.get("role") == "tool"]
    for message in tool_messages:
        content = message.get("content")
        if not isinstance(content, str) or len(content) <= keep_each_side * 2:
            continue
        omitted = len(content) - keep_each_side * 2
        message["content"] = (
            content[:keep_each_side]
            + f"\n... ({omitted} chars compacted) ...\n"
            + content[-keep_each_side:]
        )
        compacted += omitted
        if context_size(messages) <= max_chars:
            return compacted

    if context_size(messages) > max_chars:
        raise ContextBudgetExceeded(
            f"context exceeds max_context_chars={max_chars} after safe compaction"
        )
    return compacted

