from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from realitylint import __version__
from realitylint.cli import main


class CliTests(unittest.TestCase):
    def make_repo(self) -> Path:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        (root / "README.md").write_text("See [missing](missing.md).", encoding="utf-8")
        return root

    def run_cli(self, args: list[str]) -> tuple[int, str]:
        out = StringIO()
        with redirect_stdout(out):
            code = main(args)
        return code, out.getvalue()

    def test_fail_on_error(self):
        root = self.make_repo()
        code, _ = self.run_cli([str(root), "--fail-on", "error"])
        self.assertEqual(code, 1)

    def test_fail_on_never(self):
        root = self.make_repo()
        code, _ = self.run_cli([str(root), "--fail-on", "never"])
        self.assertEqual(code, 0)

    def test_json_output(self):
        root = self.make_repo()
        code, output = self.run_cli([str(root), "--format", "json", "--fail-on", "never"])
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertIn("score", payload)
        self.assertEqual(payload["summary"]["errors"], 1)
        self.assertEqual(payload["tool"]["author"], "@voonterr")
        self.assertEqual(payload["tool"]["version"], __version__)
        self.assertFalse(output.startswith("RealityLint v"), "JSON stdout must not be contaminated by the human banner")


    def test_text_output_has_author_banner(self):
        root = self.make_repo()
        code, output = self.run_cli([str(root), "--fail-on", "never"])
        self.assertEqual(code, 0)
        self.assertTrue(output.startswith(f"RealityLint v{__version__} — by @voonterr\n"))

    def test_sarif_output_is_machine_readable_without_banner(self):
        root = self.make_repo()
        code, output = self.run_cli([str(root), "--format", "sarif", "--fail-on", "never"])
        self.assertEqual(code, 0)
        payload = json.loads(output)
        self.assertEqual(payload["runs"][0]["tool"]["driver"]["organization"], "@voonterr")

    def test_missing_readme_is_reported_not_traceback(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        code, output = self.run_cli([self.tmp.name, "--fail-on", "never"])
        self.assertEqual(code, 0)
        self.assertIn("RL000", output)


if __name__ == "__main__":
    unittest.main()
