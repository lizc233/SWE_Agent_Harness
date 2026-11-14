from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from swe_agent.provider import OpenAICompatibleClient


class ProviderTests(unittest.TestCase):
    @patch("swe_agent.provider.httpx.post")
    def test_parses_text_tool_calls_and_usage(self, post: Mock) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "checking",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "read_file",
                                    "arguments": '{"path":"app.py"}',
                                },
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 5},
        }
        post.return_value = response
        client = OpenAICompatibleClient(
            api_key="test-key",
            base_url="https://example.test/v1/",
            model="test-model",
        )

        result = client.complete(
            [{"role": "user", "content": "read"}],
            [{"type": "function", "function": {"name": "read_file"}}],
        )

        self.assertEqual(result.text, "checking")
        self.assertEqual(result.tool_calls[0].name, "read_file")
        self.assertEqual(result.tool_calls[0].arguments, {"path": "app.py"})
        self.assertEqual(result.prompt_tokens, 20)
        self.assertEqual(result.completion_tokens, 5)
        self.assertEqual(
            post.call_args.args[0], "https://example.test/v1/chat/completions"
        )

    @patch("swe_agent.provider.httpx.post")
    def test_rejects_non_object_tool_arguments(self, post: Mock) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {
                                    "name": "read_file",
                                    "arguments": "[]",
                                },
                            }
                        ],
                    }
                }
            ]
        }
        post.return_value = response
        client = OpenAICompatibleClient(
            api_key="test-key",
            base_url="https://example.test",
            model="test-model",
        )

        with self.assertRaises(ValueError):
            client.complete([], [])

