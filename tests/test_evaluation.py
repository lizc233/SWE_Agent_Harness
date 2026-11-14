from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class EvaluationScriptTests(unittest.TestCase):
    def test_versioned_suite_emits_a_passing_report(self) -> None:
        root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_evaluation.py",
                    "--output",
                    str(output),
                ],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["suite"], "offline-repair-v1")
            self.assertEqual(report["passed"], report["total"])

