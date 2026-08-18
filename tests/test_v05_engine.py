from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from realitylint.engine import discover_docs, scan_project
from realitylint.rules.docker import scan_docker_drift
from realitylint.rules.env import scan_environment_drift
from realitylint.rules.go import scan_go_drift
from realitylint.rules.rust import scan_rust_drift


class V05RuleTests(unittest.TestCase):
    def repo(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Path(tmp.name)

    def write(self, root: Path, path: str, text: str) -> Path:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def test_docker_missing_service(self):
        root = self.repo()
        doc = self.write(root, "README.md", "```bash\ndocker compose up api\n```\n")
        self.write(root, "compose.yml", "services:\n  web:\n    image: nginx\n")
        findings = scan_docker_drift(root, doc)
        self.assertTrue(any(f.rule == "RL012" and '"api"' in f.message for f in findings))

    def test_docker_missing_env_file(self):
        root = self.repo()
        doc = self.write(root, "README.md", "```bash\ndocker compose up web\n```\n")
        self.write(root, "compose.yaml", "services:\n  web:\n    image: nginx\n    env_file: .env.runtime\n")
        findings = scan_docker_drift(root, doc)
        self.assertIn("RL013", {f.rule for f in findings})

    def test_explicit_missing_compose_file(self):
        root = self.repo()
        doc = self.write(root, "README.md", "```bash\ndocker compose -f deploy/compose.yml up web\n```\n")
        findings = scan_docker_drift(root, doc)
        self.assertIn("RL011", {f.rule for f in findings})

    def test_environment_drift_uses_docs_templates_and_source(self):
        root = self.repo()
        doc = self.write(root, "README.md", "Set `DATABASE_URL` before starting.\n")
        self.write(root, ".env.example", "REDIS_URL=redis://localhost\n")
        self.write(root, "app.py", 'import os\nvalue = os.getenv("DATABASE_URL")\n')
        findings = scan_environment_drift(root, [doc])
        finding = next(f for f in findings if f.rule == "RL014")
        self.assertEqual(finding.severity, "error")
        self.assertIn("source code", finding.evidence or "")

    def test_environment_drift_does_not_require_template(self):
        root = self.repo()
        doc = self.write(root, "README.md", "Set `DATABASE_URL`.\n")
        self.assertEqual(scan_environment_drift(root, [doc]), [])

    def test_go_run_missing_target(self):
        root = self.repo()
        doc = self.write(root, "README.md", "```bash\ngo run ./cmd/server\n```\n")
        self.assertIn("RL015", {f.rule for f in scan_go_drift(root, doc)})

    def test_go_run_existing_package(self):
        root = self.repo()
        doc = self.write(root, "README.md", "```bash\ngo run ./cmd/server\n```\n")
        self.write(root, "cmd/server/main.go", "package main\n")
        self.assertEqual(scan_go_drift(root, doc), [])

    def test_cargo_missing_bin_and_feature(self):
        root = self.repo()
        doc = self.write(root, "README.md", "```bash\ncargo run --bin api --features postgres\n```\n")
        self.write(root, "Cargo.toml", '[package]\nname="demo"\nversion="0.1.0"\n\n[features]\ndefault=[]\n')
        rules = {f.rule for f in scan_rust_drift(root, doc)}
        self.assertIn("RL017", rules)
        self.assertIn("RL018", rules)

    def test_docker_profile_and_port_drift(self):
        root = self.repo()
        doc = self.write(root, "README.md", "```bash\ndocker compose --profile prod up web\n```\nOpen http://localhost:9999 after startup.\n")
        self.write(root, "compose.yml", "services:\n  web:\n    image: nginx\n    profiles: [dev]\n    ports: [\"8080:80\"]\n")
        rules = {f.rule for f in scan_docker_drift(root, doc)}
        self.assertIn("RL019", rules)
        self.assertIn("RL020", rules)

    def test_go_version_claim_drift(self):
        root = self.repo()
        doc = self.write(root, "README.md", "Requires Go 1.23+.\n")
        self.write(root, "go.mod", "module example.com/demo\ngo 1.22\n")
        self.assertIn("RL021", {f.rule for f in scan_go_drift(root, doc)})

    def test_rust_msrv_claim_drift(self):
        root = self.repo()
        doc = self.write(root, "README.md", "Requires Rust 1.80+.\n")
        self.write(root, "Cargo.toml", '[package]\nname="demo"\nversion="0.1.0"\nrust-version="1.78"\n')
        self.assertIn("RL022", {f.rule for f in scan_rust_drift(root, doc)})

    def test_multi_doc_discovery(self):
        root = self.repo().resolve(strict=False)
        self.write(root, "README.md", "# root\n")
        self.write(root, "README.ru.md", "# ru\n")
        self.write(root, "docs/setup.md", "# setup\n")
        docs = discover_docs(root, all_docs=True)
        self.assertEqual({p.relative_to(root).as_posix() for p in docs}, {"README.md", "README.ru.md", "docs/setup.md"})

    def test_ignore_next_line_suppresses_new_rule(self):
        root = self.repo()
        self.write(root, "compose.yml", "services:\n  web:\n    image: nginx\n")
        self.write(root, "README.md", "<!-- realitylint-ignore-next-line RL012 -->\n`docker compose up fake`\n")
        self.assertNotIn("RL012", {f.rule for f in scan_project(root)})

    def test_config_can_exclude_doc_glob(self):
        root = self.repo()
        self.write(root, "README.md", "# ok\n")
        self.write(root, "docs/vendor/bad.md", "`docker compose up fake`\n")
        self.write(root, "compose.yml", "services:\n  web:\n    image: nginx\n")
        self.write(root, ".realitylint.toml", '[realitylint]\nexclude=["docs/vendor/**"]\n')
        self.assertNotIn("RL012", {f.rule for f in scan_project(root, all_docs=True)})

    def test_config_can_disable_rule(self):
        root = self.repo()
        self.write(root, "compose.yml", "services:\n  web:\n    image: nginx\n")
        self.write(root, "README.md", "`docker compose up fake`\n")
        self.write(root, ".realitylint.toml", '[severity]\nRL012="off"\n')
        self.assertNotIn("RL012", {f.rule for f in scan_project(root)})


if __name__ == "__main__":
    unittest.main()
