from __future__ import annotations

import os
import stat
import tempfile
from hashlib import sha256
from pathlib import Path


MAX_SEARCH_FILE_BYTES = 1_000_000
MAX_MATCH_LINE_CHARS = 500
MAX_EDIT_FILE_BYTES = 2_000_000
EXCLUDED_DIRECTORIES = frozenset(
    {".git", ".venv", ".swe-agent", "__pycache__", "node_modules", "build", "dist"}
)


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def resolve(self, path: str) -> Path:
        requested_path = Path(path)
        if requested_path.is_absolute():
            raise ValueError(f"path must be relative to workspace: {path}")
        target = (self.root / requested_path).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"path escapes workspace: {path}")
        return target

    def read_file(self, path: str, start_line: int = 1, end_line: int = 200) -> str:
        if start_line < 1:
            raise ValueError("start_line must be at least 1")
        if end_line < start_line:
            raise ValueError("end_line must not be smaller than start_line")
        if end_line - start_line + 1 > 400:
            raise ValueError("a single read may contain at most 400 lines")
        target = self.resolve(path)
        if not target.is_file():
            raise ValueError(f"file does not exist: {path}")
        lines = target.read_text(encoding="utf-8").splitlines()
        selected = lines[start_line - 1 : end_line]
        if not selected:
            return "(no lines in requested range)"
        return "\n".join(
            f"{line_number:>4}: {line}"
            for line_number, line in enumerate(selected, start=start_line)
        )

    def list_files(self, path: str = ".", max_entries: int = 200) -> str:
        if not (1 <= max_entries <= 1000):
            raise ValueError("max_entries must be between 1 and 1000")
        target = self.resolve(path)
        if not target.exists():
            raise ValueError(f"path does not exist: {path}")
        if not target.is_dir():
            raise ValueError(f"path is not a directory: {path}")
        file_paths = sorted(
            entry.relative_to(self.root).as_posix()
            for entry in target.rglob("*")
            if entry.is_file()
            and not EXCLUDED_DIRECTORIES.intersection(
                entry.relative_to(self.root).parts[:-1]
            )
        )
        selected = file_paths[:max_entries]
        return "\n".join(selected) if selected else "(no files)"

    def search_text(
        self,
        query: str,
        path: str = ".",
        file_pattern: str = "*",
        case_sensitive: bool = False,
        max_results: int = 200,
    ) -> str:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if not isinstance(file_pattern, str) or not file_pattern.strip():
            raise ValueError("file_pattern must be a non-empty string")
        if not isinstance(case_sensitive, bool):
            raise ValueError("case_sensitive must be a boolean")
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            raise ValueError("max_results must be an integer")
        if not (1 <= max_results <= 1000):
            raise ValueError("max_results must be between 1 and 1000")
        target = self.resolve(path)
        if not target.exists():
            raise ValueError(f"path does not exist: {path}")
        if not target.is_dir():
            raise ValueError(f"path is not a directory: {path}")

        needle = query if case_sensitive else query.casefold()
        matches: list[str] = []
        candidates = sorted(
            entry
            for entry in target.rglob("*")
            if entry.is_file()
            and entry.relative_to(target).match(file_pattern)
            and not EXCLUDED_DIRECTORIES.intersection(
                entry.relative_to(self.root).parts[:-1]
            )
        )
        for candidate in candidates:
            resolved_candidate = candidate.resolve()
            if not resolved_candidate.is_relative_to(self.root):
                continue
            if resolved_candidate.stat().st_size > MAX_SEARCH_FILE_BYTES:
                continue
            try:
                lines = resolved_candidate.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            relative_path = candidate.relative_to(self.root).as_posix()
            for line_number, line in enumerate(lines, start=1):
                haystack = line if case_sensitive else line.casefold()
                if needle not in haystack:
                    continue
                displayed_line = line.rstrip()
                if len(displayed_line) > MAX_MATCH_LINE_CHARS:
                    displayed_line = displayed_line[:MAX_MATCH_LINE_CHARS] + "..."
                matches.append(f"{relative_path}:{line_number}:{displayed_line}")
                if len(matches) > max_results:
                    selected = matches[:max_results]
                    selected.append(f"... (results truncated at {max_results})")
                    return "\n".join(selected)
        return "\n".join(matches) if matches else "(no matches)"

    def edit_file(
        self,
        path: str,
        old_text: str,
        new_text: str,
        expected_replacements: int = 1,
    ) -> str:
        if not old_text:
            raise ValueError("old_text must be non-empty")
        if not isinstance(expected_replacements, int) or isinstance(expected_replacements, bool):
            raise ValueError("expected_replacements must be an integer")
        if not (1 <= expected_replacements <= 100):
            raise ValueError("expected_replacements must be between 1 and 100")
        requested_path = Path(path)
        if requested_path.is_absolute():
            raise ValueError(f"path must be relative to workspace: {path}")
        if any(
            component.is_symlink()
            for component in (
                self.root.joinpath(*requested_path.parts[:index])
                for index in range(1, len(requested_path.parts) + 1)
            )
        ):
            raise ValueError(f"symlink editing is not allowed: {path}")
        target = self.resolve(path)
        if target.is_symlink():
            raise ValueError(f"symlink editing is not allowed: {path}")
        if not target.is_file():
            raise ValueError(f"file does not exist: {path}")
        if target.stat().st_size > MAX_EDIT_FILE_BYTES:
            raise ValueError(f"file is too large to edit (limit: {MAX_EDIT_FILE_BYTES} bytes)")

        original_bytes = target.read_bytes()
        original_digest = sha256(original_bytes).digest()
        original = original_bytes.decode("utf-8")
        actual_replacements = original.count(old_text)
        if actual_replacements != expected_replacements:
            raise ValueError(
                "replacement count mismatch: "
                f"expected {expected_replacements}, found {actual_replacements}"
            )
        updated = original.replace(old_text, new_text, expected_replacements)
        if updated == original:
            return f"No changes needed in {path}"

        temporary_path: str | None = None
        file_mode = stat.S_IMODE(target.stat().st_mode)
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = temporary.name
                temporary.write(updated)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.chmod(temporary_path, file_mode)
            if sha256(target.read_bytes()).digest() != original_digest:
                raise ValueError(f"file changed during edit; refusing to overwrite: {path}")
            os.replace(temporary_path, target)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass
        return f"Edited {path}: replaced {actual_replacements} occurrence(s)"

