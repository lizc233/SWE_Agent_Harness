from __future__ import annotations

import tomllib
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .permissions import ApprovalMode


class ConfigError(ValueError):
    """Raised when a configuration file is invalid."""


ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class RuntimeConfig:
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    max_steps: int = 8
    max_tool_calls: int = 32
    max_wall_seconds: float = 900
    max_context_chars: int = 200_000
    approval_mode: ApprovalMode = ApprovalMode.ASK
    trace_enabled: bool = True


ALLOWED_KEYS = {
    "model": {"base_url", "name"},
    "agent": {
        "max_steps",
        "max_tool_calls",
        "max_wall_seconds",
        "max_context_chars",
        "trace_enabled",
    },
    "permissions": {"mode"},
}


def load_runtime_config(path: Path | None = None) -> RuntimeConfig:
    if path is None:
        return RuntimeConfig()
    if not path.is_file():
        raise ConfigError(f"config file does not exist: {path}")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"cannot read config: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError("config root must be a TOML table")
    _reject_unknown_keys(data)

    model = _table(data, "model")
    agent = _table(data, "agent")
    permissions = _table(data, "permissions")
    defaults = RuntimeConfig()
    try:
        config = RuntimeConfig(
            base_url=model.get("base_url", defaults.base_url),
            model=model.get("name", defaults.model),
            max_steps=agent.get("max_steps", defaults.max_steps),
            max_tool_calls=agent.get("max_tool_calls", defaults.max_tool_calls),
            max_wall_seconds=agent.get(
                "max_wall_seconds", defaults.max_wall_seconds
            ),
            max_context_chars=agent.get(
                "max_context_chars", defaults.max_context_chars
            ),
            approval_mode=ApprovalMode(
                permissions.get("mode", defaults.approval_mode.value)
            ),
            trace_enabled=agent.get("trace_enabled", defaults.trace_enabled),
        )
    except (TypeError, ValueError) as error:
        raise ConfigError(f"invalid config value: {error}") from error
    _validate(config)
    return config


def load_env_file(path: Path) -> tuple[str, ...]:
    """Load an explicitly selected env file without overriding the process env."""
    if not path.is_file():
        raise ConfigError(f"env file does not exist: {path}")
    loaded: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ConfigError(f"cannot read env file: {error}") from error
    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ConfigError(f"invalid env line {line_number}: expected NAME=VALUE")
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not ENV_NAME.fullmatch(name):
            raise ConfigError(f"invalid env name on line {line_number}: {name!r}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if name not in os.environ:
            os.environ[name] = value
            loaded.append(name)
    return tuple(loaded)


def _table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a TOML table")
    return value


def _reject_unknown_keys(data: dict[str, Any]) -> None:
    unknown_sections = set(data) - set(ALLOWED_KEYS)
    if unknown_sections:
        raise ConfigError(
            "unknown config section(s): " + ", ".join(sorted(unknown_sections))
        )
    for section, allowed in ALLOWED_KEYS.items():
        table = _table(data, section)
        unknown = set(table) - allowed
        if unknown:
            raise ConfigError(
                f"unknown key(s) in [{section}]: " + ", ".join(sorted(unknown))
            )


def _validate(config: RuntimeConfig) -> None:
    if not isinstance(config.base_url, str) or not config.base_url.strip():
        raise ConfigError("model.base_url must be a non-empty string")
    if not isinstance(config.model, str) or not config.model.strip():
        raise ConfigError("model.name must be a non-empty string")
    integer_fields = {
        "agent.max_steps": config.max_steps,
        "agent.max_tool_calls": config.max_tool_calls,
        "agent.max_context_chars": config.max_context_chars,
    }
    for name, value in integer_fields.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ConfigError(f"{name} must be a positive integer")
    if (
        not isinstance(config.max_wall_seconds, (int, float))
        or isinstance(config.max_wall_seconds, bool)
        or config.max_wall_seconds <= 0
    ):
        raise ConfigError("agent.max_wall_seconds must be positive")
    if not isinstance(config.trace_enabled, bool):
        raise ConfigError("agent.trace_enabled must be a boolean")

