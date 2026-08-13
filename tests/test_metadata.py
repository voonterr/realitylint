from __future__ import annotations

import re
import unittest
from pathlib import Path

from realitylint import __author__, __repository__, __version__

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib


class MetadataTests(unittest.TestCase):
    def test_package_and_pyproject_version_match(self):
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["project"]["version"], __version__)

    def test_author_and_repository_metadata(self):
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["project"]["authors"][0]["name"], "voonterr")
        self.assertEqual(__author__, "@voonterr")
        self.assertEqual(__repository__, "https://github.com/voonterr/realitylint")
        self.assertEqual(data["project"]["urls"]["Repository"], __repository__)

    def test_no_release_placeholders_remain(self):
        text_extensions = {".md", ".toml", ".yml", ".yaml", ".py", ".txt"}
        offenders: list[str] = []
        for path in Path(".").rglob("*"):
            if not path.is_file() or path.suffix.lower() not in text_extensions:
                continue
            if any(part in {".git", "dist", "build", ".venv"} for part in path.parts):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            placeholder = "YOUR_GITHUB_" + "USERNAME"
            old_author = "RealityLint " + "contributors"
            if placeholder in text or old_author in text:
                offenders.append(str(path))
        self.assertEqual(offenders, [])

    def test_action_author_is_voonterr(self):
        text = Path("action.yml").read_text(encoding="utf-8")
        self.assertRegex(text, re.compile(r"^author:\s*voonterr\s*$", re.M))

    def test_codeowners_points_to_voonterr(self):
        self.assertEqual(Path(".github/CODEOWNERS").read_text(encoding="utf-8").strip(), "* @voonterr")

    def test_bilingual_readmes_and_demo_assets_exist(self):
        english = Path("README.md").read_text(encoding="utf-8")
        russian = Path("README.ru.md").read_text(encoding="utf-8")
        self.assertIn("[Русский](README.ru.md)", english)
        self.assertIn("[English](README.md)", russian)
        self.assertIn("docs/assets/demo.gif", english)
        self.assertIn("docs/assets/demo.gif", russian)
        self.assertGreater(Path("docs/assets/demo.gif").stat().st_size, 1024)
        self.assertIn("by @voonterr", Path("docs/assets/banner.svg").read_text(encoding="utf-8"))

    def test_social_preview_is_1200_by_630_png(self):
        data = Path("docs/assets/social-preview.png").read_bytes()
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))
        width = int.from_bytes(data[16:20], "big")
        height = int.from_bytes(data[20:24], "big")
        self.assertEqual((width, height), (1200, 630))

    def test_public_repository_setup_files_exist(self):
        required = [
            "GITHUB_SETUP.md",
            "RELEASE_NOTES_v0.1.2.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/release.yml",
        ]
        self.assertEqual([name for name in required if not Path(name).is_file()], [])


if __name__ == "__main__":
    unittest.main()
