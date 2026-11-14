from __future__ import annotations

import json
from typing import Any

import httpx

from .models import ModelResponse, ToolCall


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("api_key must not be empty")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        body = response.json()
        message = body["choices"][0]["message"]
        usage = body.get("usage") or {}

        calls: list[ToolCall] = []
        for raw_call in message.get("tool_calls") or []:
            function = raw_call["function"]
            raw_arguments = function.get("arguments") or "{}"
            arguments = json.loads(raw_arguments)
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be a JSON object")
            calls.append(
                ToolCall(
                    id=raw_call["id"],
                    name=function["name"],
                    arguments=arguments,
                )
            )

        return ModelResponse(
            text=message.get("content") or "",
            tool_calls=tuple(calls),
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )

