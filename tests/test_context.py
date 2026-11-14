from __future__ import annotations

import unittest

from swe_agent.context import ContextBudgetExceeded, compact_tool_outputs


class ContextTests(unittest.TestCase):
    def test_compacts_tool_content_without_dropping_protocol_messages(self) -> None:
        messages = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "task"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "call-1", "type": "function"}],
            },
            {"role": "tool", "tool_call_id": "call-1", "content": "x" * 5000},
        ]

        compacted = compact_tool_outputs(messages, 2500, keep_each_side=500)

        self.assertGreater(compacted, 0)
        self.assertEqual([message["role"] for message in messages], ["system", "user", "assistant", "tool"])
        self.assertEqual(messages[-1]["tool_call_id"], "call-1")
        self.assertIn("chars compacted", messages[-1]["content"])

    def test_raises_when_non_tool_context_alone_exceeds_budget(self) -> None:
        messages = [{"role": "user", "content": "x" * 5000}]

        with self.assertRaises(ContextBudgetExceeded):
            compact_tool_outputs(messages, 100)

