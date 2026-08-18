from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from realitylint.cli import main, render_junit
from realitylint.models import Finding


class V05CliTests(unittest.TestCase):
    def repo(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def write(self, root: Path, path: str, text: str) -> Path:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def capture(self, argv: list[str]) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(argv)
        return code, out.getvalue()

    def test_rules_command(self):
        code, output = self.capture(["rules"])
        self.assertEqual(code, 0)
        self.assertIn("RL012", output)
        self.assertIn("Docker Compose service exists", output)

    def test_explain_command(self):
        code, output = self.capture(["explain", "RL014"])
        self.assertEqual(code, 0)
        self.assertIn("Environment variable", output)

    def test_junit_renderer(self):
        output = render_junit([Finding("RL012", "error", "missing", "README.md", 2)])
        self.assertIn("<testsuite", output)
        self.assertIn("<failure", output)

    def test_write_and_auto_apply_baseline(self):
        root = self.repo()
        self.write(root, "README.md", "`docker compose up fake`\n")
        self.write(root, "compose.yml", "services:\n  web:\n    image: nginx\n")
        code, output = self.capture([str(root), "--write-baseline"])
        self.assertEqual(code, 0)
        self.assertIn("baseline", output.lower())
        baseline = root / ".realitylint-baseline.json"
        self.assertTrue(baseline.is_file())
        data = json.loads(baseline.read_text(encoding="utf-8"))
        self.assertTrue(data["fingerprints"])
        code, output = self.capture([str(root)])
        self.assertEqual(code, 0)
        self.assertIn("No verifiable documentation drift", output)

    def test_init_is_idempotent(self):
        root = self.repo()
        code, _ = self.capture(["init", str(root)])
        self.assertEqual(code, 0)
        self.assertTrue((root / ".realitylint.toml").is_file())
        self.assertTrue((root / ".github/workflows/realitylint.yml").is_file())
        before = (root / ".realitylint.toml").read_text(encoding="utf-8")
        code, _ = self.capture(["init", str(root)])
        self.assertEqual(code, 0)
        self.assertEqual(before, (root / ".realitylint.toml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
