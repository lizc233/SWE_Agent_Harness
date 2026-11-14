from __future__ import annotations

import os
import subprocess

from .workspace import Workspace


MAX_COMMAND_OUTPUT_CHARS = 50_000


class CommandRunner:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run_command(
        self,
        command: list[str],
        cwd: str = ".",
        timeout_seconds: int = 120,
    ) -> str:
        if not isinstance(command, list) or not command:
            raise ValueError("command must be a non-empty array")
        if len(command) > 100 or any(
            not isinstance(part, str) or not part for part in command
        ):
            raise ValueError("command must contain 1 to 100 non-empty strings")
        if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool):
            raise ValueError("timeout_seconds must be an integer")
        if not (1 <= timeout_seconds <= 600):
            raise ValueError("timeout_seconds must be between 1 and 600")
        working_directory = self.workspace.resolve(cwd)
        if not working_directory.is_dir():
            raise ValueError(f"cwd is not a directory: {cwd}")
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        try:
            result = subprocess.run(
                command,
                cwd=working_directory,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout_seconds,
                shell=False,
                creationflags=creation_flags,
            )
        except subprocess.TimeoutExpired as error:
            partial = "".join(
                value.decode(errors="replace") if isinstance(value, bytes) else value or ""
                for value in (error.stdout, error.stderr)
            )
            return self._limit_output(
                f"Timed out after {timeout_seconds}s\n{partial}".rstrip()
            )
        except FileNotFoundError:
            return f"Error: executable not found: {command[0]}"
        combined = (result.stdout + result.stderr).rstrip()
        header = f"exit_code={result.returncode}"
        return self._limit_output(f"{header}\n{combined}" if combined else header)

    def git_status(self) -> str:
        return self.run_command(
            ["git", "status", "--short", "--branch"], timeout_seconds=30
        )

    def git_diff(self, staged: bool = False) -> str:
        command = ["git", "diff", "--no-ext-diff"]
        if staged:
            command.append("--cached")
        return self.run_command(command, timeout_seconds=30)

    @staticmethod
    def _limit_output(output: str) -> str:
        if len(output) <= MAX_COMMAND_OUTPUT_CHARS:
            return output
        omitted = len(output) - MAX_COMMAND_OUTPUT_CHARS
        return output[:MAX_COMMAND_OUTPUT_CHARS] + f"\n... ({omitted} chars omitted)"

