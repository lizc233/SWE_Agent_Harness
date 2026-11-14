from __future__ import annotations

import tempfile
import unittest
import os
from pathlib import Path

from swe_agent.permissions import ApprovalMode, PermissionPolicy
from swe_agent.tools import build_read_only_registry, build_workspace_registry


def build_edit_registry(workspace: Path):
    return build_workspace_registry(
        workspace,
        permission_policy=PermissionPolicy(ApprovalMode.AUTO_EDIT),
    )


class ReadFileToolTests(unittest.TestCase):
    def test_reads_numbered_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "notes.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")
            registry = build_read_only_registry(workspace)

            output = registry.execute(
                "read_file",
                {"path": "notes.txt", "start_line": 2, "end_line": 3},
            )

            self.assertEqual(output, "   2: two\n   3: three")

    def test_blocks_path_outside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_read_only_registry(Path(temp_dir))

            output = registry.execute("read_file", {"path": "../secret.txt"})

            self.assertIn("escapes workspace", output)

    def test_rejects_unknown_tool(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_read_only_registry(Path(temp_dir))

            output = registry.execute("delete_everything", {})

            self.assertEqual(output, "Error: unknown tool 'delete_everything'")


class ListFilesToolTests(unittest.TestCase):
    def test_is_registered_with_the_expected_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_read_only_registry(Path(temp_dir))

            definitions = {
                item["function"]["name"]: item["function"]
                for item in registry.definitions()
            }

            self.assertIn("list_files", definitions)
            schema = definitions["list_files"]["parameters"]
            self.assertEqual(set(schema["properties"]), {"path", "max_entries"})
            self.assertEqual(schema["properties"]["max_entries"]["maximum"], 1000)
            self.assertFalse(schema["additionalProperties"])

    def test_lists_sorted_workspace_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "nested").mkdir()
            (workspace / "z.py").write_text("", encoding="utf-8")
            (workspace / "nested" / "b.py").write_text("", encoding="utf-8")
            (workspace / "a.py").write_text("", encoding="utf-8")
            registry = build_read_only_registry(workspace)

            output = registry.execute("list_files", {})

            self.assertEqual(output, "a.py\nnested/b.py\nz.py")

    def test_lists_a_subdirectory_and_honors_the_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "src").mkdir()
            for name in ("c.py", "a.py", "b.py"):
                (workspace / "src" / name).write_text("", encoding="utf-8")
            registry = build_read_only_registry(workspace)

            output = registry.execute(
                "list_files", {"path": "src", "max_entries": 2}
            )

            self.assertEqual(output, "src/a.py\nsrc/b.py")

    def test_rejects_paths_outside_the_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_read_only_registry(Path(temp_dir))

            output = registry.execute("list_files", {"path": ".."})

            self.assertIn("escapes workspace", output)

    def test_rejects_a_file_instead_of_a_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "file.py").write_text("", encoding="utf-8")
            registry = build_read_only_registry(workspace)

            output = registry.execute("list_files", {"path": "file.py"})

            self.assertIn("not a directory", output)

    def test_rejects_invalid_entry_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_read_only_registry(Path(temp_dir))

            too_small = registry.execute("list_files", {"max_entries": 0})
            too_large = registry.execute("list_files", {"max_entries": 1001})

            self.assertIn("between 1 and 1000", too_small)
            self.assertIn("between 1 and 1000", too_large)

    def test_reports_an_empty_directory_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_read_only_registry(Path(temp_dir))

            output = registry.execute("list_files", {})

            self.assertEqual(output, "(no files)")


class SearchTextToolTests(unittest.TestCase):
    def test_is_registered_with_the_expected_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_read_only_registry(Path(temp_dir))

            definitions = {
                item["function"]["name"]: item["function"]
                for item in registry.definitions()
            }

            self.assertIn("search_text", definitions)
            schema = definitions["search_text"]["parameters"]
            self.assertEqual(schema["required"], ["query"])
            self.assertEqual(schema["properties"]["max_results"]["maximum"], 1000)
            self.assertFalse(schema["additionalProperties"])

    def test_finds_case_insensitive_matches_in_stable_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "b.py").write_text("TARGET second\n", encoding="utf-8")
            (workspace / "a.py").write_text(
                "first target\nno match\nTarget third\n", encoding="utf-8"
            )
            registry = build_read_only_registry(workspace)

            output = registry.execute("search_text", {"query": "target"})

            self.assertEqual(
                output,
                "a.py:1:first target\na.py:3:Target third\nb.py:1:TARGET second",
            )

    def test_supports_case_sensitive_search(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "case.txt").write_text(
                "Token\ntoken\nTOKEN\n", encoding="utf-8"
            )
            registry = build_read_only_registry(workspace)

            output = registry.execute(
                "search_text", {"query": "Token", "case_sensitive": True}
            )

            self.assertEqual(output, "case.txt:1:Token")

    def test_scopes_search_by_directory_and_file_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "src").mkdir()
            (workspace / "docs").mkdir()
            (workspace / "src" / "app.py").write_text("needle\n", encoding="utf-8")
            (workspace / "src" / "app.txt").write_text("needle\n", encoding="utf-8")
            (workspace / "docs" / "guide.py").write_text("needle\n", encoding="utf-8")
            registry = build_read_only_registry(workspace)

            output = registry.execute(
                "search_text",
                {"query": "needle", "path": "src", "file_pattern": "*.py"},
            )

            self.assertEqual(output, "src/app.py:1:needle")

    def test_truncates_results_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "many.txt").write_text(
                "match\nmatch\nmatch\n", encoding="utf-8"
            )
            registry = build_read_only_registry(workspace)

            output = registry.execute(
                "search_text", {"query": "match", "max_results": 2}
            )

            self.assertEqual(
                output,
                "many.txt:1:match\nmany.txt:2:match\n... (results truncated at 2)",
            )

    def test_rejects_invalid_query_path_and_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "file.txt").write_text("text\n", encoding="utf-8")
            registry = build_read_only_registry(workspace)

            empty_query = registry.execute("search_text", {"query": "  "})
            escaped_path = registry.execute(
                "search_text", {"query": "text", "path": ".."}
            )
            file_path = registry.execute(
                "search_text", {"query": "text", "path": "file.txt"}
            )
            invalid_limit = registry.execute(
                "search_text", {"query": "text", "max_results": 0}
            )

            self.assertIn("non-empty string", empty_query)
            self.assertIn("escapes workspace", escaped_path)
            self.assertIn("not a directory", file_path)
            self.assertIn("between 1 and 1000", invalid_limit)

    def test_skips_binary_files_and_generated_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / ".git").mkdir()
            (workspace / ".git" / "config").write_text("secret target\n", encoding="utf-8")
            (workspace / "binary.bin").write_bytes(b"target\xff\xfe")
            (workspace / "source.py").write_text("visible target\n", encoding="utf-8")
            registry = build_read_only_registry(workspace)

            output = registry.execute("search_text", {"query": "target"})

            self.assertEqual(output, "source.py:1:visible target")

    def test_reports_no_matches_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            (workspace / "source.py").write_text("content\n", encoding="utf-8")
            registry = build_read_only_registry(workspace)

            output = registry.execute("search_text", {"query": "missing"})

            self.assertEqual(output, "(no matches)")


class EditFileToolTests(unittest.TestCase):
    def test_is_registered_with_the_expected_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_read_only_registry(Path(temp_dir))
            definitions = {
                item["function"]["name"]: item["function"]
                for item in registry.definitions()
            }

            self.assertIn("edit_file", definitions)
            schema = definitions["edit_file"]["parameters"]
            self.assertEqual(
                schema["required"], ["path", "old_text", "new_text"]
            )
            self.assertEqual(
                set(schema["properties"]),
                {"path", "old_text", "new_text", "expected_replacements"},
            )
            self.assertFalse(schema["additionalProperties"])

    def test_replaces_one_exact_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "sample.py"
            target.write_text("value = 1\n", encoding="utf-8")
            registry = build_edit_registry(workspace)

            output = registry.execute(
                "edit_file",
                {"path": "sample.py", "old_text": "value = 1", "new_text": "value = 2"},
            )

            self.assertEqual(output, "Edited sample.py: replaced 1 occurrence(s)")
            self.assertEqual(target.read_text(encoding="utf-8"), "value = 2\n")

    def test_requires_the_expected_number_of_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "sample.py"
            original = "value = 1\nvalue = 1\n"
            target.write_text(original, encoding="utf-8")
            registry = build_edit_registry(workspace)

            output = registry.execute(
                "edit_file",
                {"path": "sample.py", "old_text": "value = 1", "new_text": "value = 2"},
            )

            self.assertIn("replacement count mismatch", output)
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_can_explicitly_replace_multiple_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "sample.py"
            target.write_text("value = 1\nvalue = 1\n", encoding="utf-8")
            registry = build_edit_registry(workspace)

            output = registry.execute(
                "edit_file",
                {
                    "path": "sample.py",
                    "old_text": "value = 1",
                    "new_text": "value = 2",
                    "expected_replacements": 2,
                },
            )

            self.assertEqual(output, "Edited sample.py: replaced 2 occurrence(s)")
            self.assertEqual(
                target.read_text(encoding="utf-8"), "value = 2\nvalue = 2\n"
            )

    def test_mismatch_does_not_modify_the_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "sample.py"
            original = "value = 1\n"
            target.write_text(original, encoding="utf-8")
            registry = build_edit_registry(workspace)

            output = registry.execute(
                "edit_file",
                {"path": "sample.py", "old_text": "missing", "new_text": "changed"},
            )

            self.assertIn("replacement count mismatch", output)
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_rejects_workspace_escape_and_empty_old_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = build_edit_registry(Path(temp_dir))

            escaped = registry.execute(
                "edit_file",
                {"path": "../outside.py", "old_text": "a", "new_text": "b"},
            )
            empty = registry.execute(
                "edit_file",
                {"path": "file.py", "old_text": "", "new_text": "b"},
            )

            self.assertIn("escapes workspace", escaped)
            self.assertIn("old_text must be non-empty", empty)

    def test_rejects_symlink_editing_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            target = workspace / "target.py"
            link = workspace / "link.py"
            target.write_text("before\n", encoding="utf-8")
            try:
                os.symlink(target, link)
            except (OSError, NotImplementedError):
                self.skipTest("symbolic links are unavailable in this environment")
            registry = build_edit_registry(workspace)

            output = registry.execute(
                "edit_file",
                {"path": "link.py", "old_text": "before", "new_text": "after"},
            )

            self.assertIn("symlink editing is not allowed", output)
            self.assertEqual(target.read_text(encoding="utf-8"), "before\n")


if __name__ == "__main__":
    unittest.main()

