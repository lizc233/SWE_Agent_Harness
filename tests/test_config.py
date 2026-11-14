from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path

from swe_agent.config import (
    ConfigError,
    RuntimeConfig,
    load_env_file,
    load_runtime_config,
)
from swe_agent.permissions import ApprovalMode


class ConfigTests(unittest.TestCase):
    def test_uses_safe_defaults_without_a_file(self) -> None:
        config = load_runtime_config()

        self.assertEqual(config, RuntimeConfig())
        self.assertEqual(config.approval_mode, ApprovalMode.ASK)

    def test_loads_all_supported_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "agent.toml"
            path.write_text(
                """
[model]
base_url = "https://example.test/v1"
name = "model-x"
[agent]
max_steps = 10
max_tool_calls = 40
max_wall_seconds = 30.5
max_context_chars = 50000
trace_enabled = false
[permissions]
mode = "auto-edit"
""".strip(),
                encoding="utf-8",
            )

            config = load_runtime_config(path)

            self.assertEqual(config.base_url, "https://example.test/v1")
            self.assertEqual(config.model, "model-x")
            self.assertEqual(config.max_steps, 10)
            self.assertEqual(config.approval_mode, ApprovalMode.AUTO_EDIT)
            self.assertFalse(config.trace_enabled)

    def test_rejects_unknown_keys_and_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            unknown = Path(temp_dir) / "unknown.toml"
            unknown.write_text("[agent]\nmagic = true\n", encoding="utf-8")
            invalid = Path(temp_dir) / "invalid.toml"
            invalid.write_text("[agent]\nmax_steps = 0\n", encoding="utf-8")

            with self.assertRaises(ConfigError):
                load_runtime_config(unknown)
            with self.assertRaises(ConfigError):
                load_runtime_config(invalid)

    def test_loads_explicit_env_without_overriding_process_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".env"
            path.write_text(
                "# credentials\nTEST_SWE_KEY='from-file'\nTEST_SWE_MODEL=model-x\n",
                encoding="utf-8",
            )
            previous_key = os.environ.get("TEST_SWE_KEY")
            previous_model = os.environ.get("TEST_SWE_MODEL")
            os.environ["TEST_SWE_KEY"] = "from-process"
            os.environ.pop("TEST_SWE_MODEL", None)
            try:
                loaded = load_env_file(path)

                self.assertEqual(os.environ["TEST_SWE_KEY"], "from-process")
                self.assertEqual(os.environ["TEST_SWE_MODEL"], "model-x")
                self.assertEqual(loaded, ("TEST_SWE_MODEL",))
            finally:
                if previous_key is None:
                    os.environ.pop("TEST_SWE_KEY", None)
                else:
                    os.environ["TEST_SWE_KEY"] = previous_key
                if previous_model is None:
                    os.environ.pop("TEST_SWE_MODEL", None)
                else:
                    os.environ["TEST_SWE_MODEL"] = previous_model

    def test_rejects_malformed_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".env"
            path.write_text("NOT VALID\n", encoding="utf-8")

            with self.assertRaises(ConfigError):
                load_env_file(path)

