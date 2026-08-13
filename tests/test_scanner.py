from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from realitylint.cli import github_annotations, render_markdown, render_sarif, score
from realitylint.models import Finding
from realitylint.scanner import MAX_README_BYTES, scan


class ScannerTests(unittest.TestCase):
    def make_repo(self) -> Path:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        return root

    def write(self, root: Path, path: str, text: str) -> Path:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def rules(self, root: Path, readme: str = "README.md") -> set[str]:
        return {f.rule for f in scan(root, readme)}

    def test_missing_script_and_env_template(self):
        root = self.make_repo()
        self.write(root, "package.json", json.dumps({"scripts": {"build": "vite build"}}))
        self.write(root, "package-lock.json", "{}")
        self.write(root, "README.md", """# Demo\n\n```bash\nnpm run dev\ncp .env.example .env\n```\n""")
        rules = self.rules(root)
        self.assertIn("RL001", rules)
        self.assertIn("RL003", rules)

    def test_missing_package_json_is_an_error_for_documented_script(self):
        root = self.make_repo()
        self.write(root, "README.md", "```bash\nnpm run dev\n```\n")
        findings = scan(root)
        self.assertTrue(any(f.rule == "RL001" and "no package.json" in f.message for f in findings))

    def test_empty_package_json_still_checks_scripts(self):
        root = self.make_repo()
        self.write(root, "package.json", "{}")
        self.write(root, "README.md", "```bash\nnpm run dev\n```\n")
        self.assertIn("RL001", self.rules(root))

    def test_invalid_package_json_warns_without_crashing(self):
        root = self.make_repo()
        self.write(root, "package.json", "{")
        self.write(root, "README.md", "```bash\nnpm run dev\n```\n")
        findings = scan(root)
        self.assertTrue(any(f.rule == "RL010" for f in findings))
        self.assertFalse(any(f.rule == "RL001" for f in findings))

    def test_non_object_scripts_field_does_not_crash(self):
        root = self.make_repo()
        self.write(root, "package.json", json.dumps({"scripts": ["dev"]}))
        self.write(root, "README.md", "```bash\nnpm run dev\n```\n")
        rules = self.rules(root)
        self.assertIn("RL010", rules)
        self.assertIn("RL001", rules)

    def test_yarn_run_parses_actual_script_not_run(self):
        root = self.make_repo()
        self.write(root, "package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "yarn.lock", "")
        self.write(root, "README.md", "```bash\nyarn run dev\n```\n")
        self.assertEqual(scan(root), [])

    def test_yarn_shorthand_script(self):
        root = self.make_repo()
        self.write(root, "package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "yarn.lock", "")
        self.write(root, "README.md", "```bash\nyarn dev\n```\n")
        self.assertEqual(scan(root), [])

    def test_npm_builtin_start_is_checked_as_script(self):
        root = self.make_repo()
        self.write(root, "package.json", json.dumps({"scripts": {}}))
        self.write(root, "README.md", "```bash\nnpm start\n```\n")
        self.assertIn("RL001", self.rules(root))

    def test_broken_relative_link(self):
        root = self.make_repo()
        self.write(root, "README.md", "See [guide](docs/guide.md).")
        findings = scan(root)
        self.assertEqual(findings[0].rule, "RL002")

    def test_nested_readme_link_is_relative_to_readme(self):
        root = self.make_repo()
        self.write(root, "docs/guide.md", "ok")
        self.write(root, "docs/README.md", "See [guide](guide.md).")
        self.assertEqual(scan(root, "docs/README.md"), [])

    def test_markdown_link_title_and_percent_encoded_space(self):
        root = self.make_repo()
        self.write(root, "docs/My File.md", "ok")
        self.write(root, "README.md", 'See [guide](docs/My%20File.md "Guide").')
        self.assertEqual(scan(root), [])

    def test_markdown_link_with_parentheses(self):
        root = self.make_repo()
        self.write(root, "docs/a(b).md", "ok")
        self.write(root, "README.md", "See [guide](docs/a(b).md).")
        self.assertEqual(scan(root), [])

    def test_markdown_link_inside_code_fence_is_ignored(self):
        root = self.make_repo()
        self.write(root, "README.md", "```markdown\n[x](missing.md)\n```\n")
        self.assertEqual(scan(root), [])

    def test_python_entry_and_version_pin(self):
        root = self.make_repo()
        self.write(root, "pyproject.toml", '[project]\nname="demo-tool"\nversion="1.2.0"\n')
        self.write(root, "README.md", "```bash\npip install demo_tool==1.1.0\npython scripts/start.py\n```\n")
        rules = self.rules(root)
        self.assertIn("RL005", rules)
        self.assertIn("RL007", rules)

    def test_python_m_pip_pin_is_checked(self):
        root = self.make_repo()
        self.write(root, "pyproject.toml", '[project]\nname="demo"\nversion="2.0.0"\n')
        self.write(root, "README.md", "```bash\npython -m pip install demo==1.0.0\n```\n")
        self.assertIn("RL007", self.rules(root))

    def test_invalid_pyproject_warns_not_crashes(self):
        root = self.make_repo()
        self.write(root, "pyproject.toml", "[project\n")
        self.write(root, "README.md", "```bash\npip install demo==1.0.0\n```\n")
        self.assertIn("RL010", self.rules(root))

    def test_pyproject_tool_section_version_is_not_mistaken_for_project_version(self):
        root = self.make_repo()
        self.write(root, "pyproject.toml", '[tool.demo]\nname="demo"\nversion="9.9.9"\n')
        self.write(root, "README.md", "```bash\npip install demo==1.0.0\n```\n")
        self.assertNotIn("RL007", self.rules(root))

    def test_python_entry_with_interpreter_flag(self):
        root = self.make_repo()
        self.write(root, "README.md", "```bash\npython -u scripts/start.py\n```\n")
        self.assertIn("RL005", self.rules(root))

    def test_make_target(self):
        root = self.make_repo()
        self.write(root, "Makefile", "build:\n\t@echo ok\n")
        self.write(root, "README.md", "```bash\nmake deploy\n```\n")
        self.assertIn("RL006", self.rules(root))

    def test_make_target_without_makefile_is_error(self):
        root = self.make_repo()
        self.write(root, "README.md", "```bash\nmake deploy\n```\n")
        self.assertIn("RL006", self.rules(root))

    def test_lowercase_makefile_is_recognized(self):
        root = self.make_repo()
        self.write(root, "makefile", "build:\n\t@echo ok\n")
        self.write(root, "README.md", "```bash\nmake build\n```\n")
        self.assertEqual(scan(root), [])

    def test_non_http_uri_scheme_is_ignored_as_remote_link(self):
        root = self.make_repo()
        self.write(root, "README.md", "Open [tool](vscode://file/something).")
        self.assertEqual(scan(root), [])

    def test_non_shell_fence_is_not_treated_as_commands(self):
        root = self.make_repo()
        self.write(root, "README.md", "```text\npython missing.py\n```\n")
        self.assertEqual(scan(root), [])

    def test_tilde_shell_fence_is_treated_as_commands(self):
        root = self.make_repo()
        self.write(root, "README.md", "~~~bash\npython missing.py\n~~~\n")
        self.assertIn("RL005", self.rules(root))

    def test_inline_shell_command_is_checked(self):
        root = self.make_repo()
        self.write(root, "README.md", "Run `python scripts/missing.py` to start.")
        self.assertIn("RL005", self.rules(root))

    def test_clean_repo(self):
        root = self.make_repo()
        self.write(root, "scripts/start.py", "print('ok')\n")
        self.write(root, ".env.example", "KEY=\n")
        self.write(root, "package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "package-lock.json", "{}")
        self.write(root, "README.md", "```bash\nnpm run dev\ncp .env.example .env\npython scripts/start.py\n```\n")
        self.assertEqual(scan(root), [])

    def test_windows_backslash_env_path(self):
        root = self.make_repo()
        self.write(root, "config/.env.example", "KEY=\n")
        self.write(root, "README.md", "```powershell\ncopy config\\.env.example .env\n```\n")
        self.assertEqual(scan(root), [])

    def test_cd_into_monorepo_subdir_changes_manifest_base(self):
        root = self.make_repo()
        self.write(root, "frontend/package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "frontend/package-lock.json", "{}")
        self.write(root, "README.md", "```bash\ncd frontend && npm run dev\n```\n")
        self.assertEqual(scan(root), [])

    def test_cd_persists_across_lines_within_same_fence(self):
        root = self.make_repo()
        self.write(root, "frontend/package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "README.md", "```bash\ncd frontend\nnpm run dev\n```\n")
        self.assertEqual(scan(root), [])


    def test_npm_prefix_uses_subdirectory_manifest(self):
        root = self.make_repo()
        self.write(root, "frontend/package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "frontend/package-lock.json", "{}")
        self.write(root, "README.md", "```bash\nnpm --prefix frontend run dev\n```\n")
        self.assertEqual(scan(root), [])

    def test_yarn_cwd_uses_subdirectory_manifest(self):
        root = self.make_repo()
        self.write(root, "frontend/package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "frontend/yarn.lock", "")
        self.write(root, "README.md", "```bash\nyarn --cwd frontend dev\n```\n")
        self.assertEqual(scan(root), [])

    def test_pnpm_dash_c_uses_subdirectory_manifest(self):
        root = self.make_repo()
        self.write(root, "frontend/package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "frontend/pnpm-lock.yaml", "lockfileVersion: '9.0'\n")
        self.write(root, "README.md", "```bash\npnpm -C frontend run dev\n```\n")
        self.assertEqual(scan(root), [])

    def test_bun_cwd_uses_subdirectory_manifest(self):
        root = self.make_repo()
        self.write(root, "frontend/package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "frontend/bun.lock", "")
        self.write(root, "README.md", "```bash\nbun --cwd frontend run dev\n```\n")
        self.assertEqual(scan(root), [])

    def test_make_dash_c_uses_subdirectory_makefile(self):
        root = self.make_repo()
        self.write(root, "backend/Makefile", "deploy:\n\t@echo ok\n")
        self.write(root, "README.md", "```bash\nmake -C backend deploy\n```\n")
        self.assertEqual(scan(root), [])

    def test_make_directory_long_option_is_checked(self):
        root = self.make_repo()
        self.write(root, "backend/Makefile", "build:\n\t@echo ok\n")
        self.write(root, "README.md", "```bash\nmake --directory=backend deploy\n```\n")
        self.assertIn("RL006", self.rules(root))

    def test_windows_cmd_prompt_is_stripped(self):
        root = self.make_repo()
        self.write(root, "package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "README.md", "```shell-session\nC:\\repo> npm run dev\n```\n")
        self.assertEqual(scan(root), [])

    def test_posix_prompt_is_stripped(self):
        root = self.make_repo()
        self.write(root, "package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "README.md", "```console\nuser@host:~/repo$ npm run dev\n```\n")
        self.assertEqual(scan(root), [])

    def test_package_manager_mismatch(self):
        root = self.make_repo()
        self.write(root, "package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "package-lock.json", "{}")
        self.write(root, "README.md", "```bash\nyarn dev\n```\n")
        self.assertIn("RL004", self.rules(root))

    def test_bun_lock_is_recognized(self):
        root = self.make_repo()
        self.write(root, "package.json", json.dumps({"scripts": {"dev": "vite"}}))
        self.write(root, "bun.lock", "")
        self.write(root, "README.md", "```bash\nbun run dev\n```\n")
        self.assertNotIn("RL004", self.rules(root))

    def test_inline_manager_cwd_flag_names_are_not_scripts(self):
        root = self.make_repo()
        self.write(root, "README.md", "Supports `npm --prefix`, `yarn --cwd`, `pnpm --dir`, `pnpm -C`, and `bun --cwd`.")
        self.assertEqual(scan(root), [])

    def test_package_manager_words_in_plain_prose_do_not_trigger_mismatch(self):
        root = self.make_repo()
        self.write(root, "package-lock.json", "{}")
        self.write(root, "README.md", "Some teams prefer yarn install, but this is not a command example.")
        self.assertNotIn("RL004", self.rules(root))

    def test_license_directory_does_not_count_as_license_file(self):
        root = self.make_repo()
        (root / "LICENSE").mkdir()
        self.write(root, "README.md", "Released under the MIT License.")
        self.assertIn("RL008", self.rules(root))

    def test_license_file_passes(self):
        root = self.make_repo()
        self.write(root, "LICENSE", "MIT")
        self.write(root, "README.md", "Released under the MIT License.")
        self.assertEqual(scan(root), [])

    def test_inline_windows_path_notice(self):
        root = self.make_repo()
        self.write(root, "README.md", "Config lives at `config\\app.toml`.")
        self.assertIn("RL009", self.rules(root))

    def test_readme_parent_traversal_is_rejected(self):
        root = self.make_repo()
        outside = root.parent / (root.name + "-outside.md")
        outside.write_text("secret", encoding="utf-8")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        findings = scan(root, f"../{outside.name}")
        self.assertEqual(findings[0].rule, "RL000")
        self.assertIn("escapes", findings[0].message)

    def test_absolute_readme_is_rejected(self):
        root = self.make_repo()
        findings = scan(root, str((root / "README.md").resolve()))
        self.assertEqual(findings[0].rule, "RL000")

    def test_readme_directory_is_handled_without_traceback(self):
        root = self.make_repo()
        (root / "README.md").mkdir()
        findings = scan(root)
        self.assertEqual(findings[0].rule, "RL000")

    def test_oversized_readme_is_rejected(self):
        root = self.make_repo()
        with (root / "README.md").open("wb") as fh:
            fh.truncate(MAX_README_BYTES + 1)
        findings = scan(root)
        self.assertEqual(findings[0].rule, "RL000")
        self.assertIn("too large", findings[0].message)

    def test_root_file_is_rejected(self):
        root = self.make_repo()
        file_root = self.write(root, "repo.txt", "x")
        findings = scan(file_root)
        self.assertEqual(findings[0].rule, "RL000")

    def test_score_penalties(self):
        root = self.make_repo()
        self.write(root, "README.md", "See [missing](docs/nope.md).")
        findings = scan(root)
        self.assertEqual(score(findings), 85)

    def test_github_annotation_escapes_properties_and_data(self):
        finding = Finding("RL:1,evil", "error", "bad%\nmessage", "README,evil.md", 2)
        line = github_annotations([finding])[0]
        self.assertNotIn("\n", line)
        self.assertIn("RL%3A1%2Cevil", line)
        self.assertIn("README%2Cevil.md", line)
        self.assertIn("bad%25%0Amessage", line)

    def test_markdown_renderer_escapes_cells_and_html(self):
        finding = Finding("RL001", "error", "bad | <script>alert(1)</script>\nnext", "README.md", 1)
        output = render_markdown([finding])
        self.assertIn("bad \\| &lt;script&gt;alert(1)&lt;/script&gt; next", output)
        self.assertNotIn("<script>", output)
        self.assertIn("by @voonterr", output)

    def test_sarif_is_valid_json_and_has_start_line(self):
        finding = Finding("RL001", "error", "bad", "README.md", 3)
        payload = json.loads(render_sarif([finding]))
        run = payload["runs"][0]
        result = run["results"][0]
        self.assertEqual(result["locations"][0]["physicalLocation"]["region"]["startLine"], 3)
        self.assertEqual(run["tool"]["driver"]["organization"], "@voonterr")
        self.assertEqual(run["tool"]["driver"]["informationUri"], "https://github.com/voonterr/realitylint")


if __name__ == "__main__":
    unittest.main()
