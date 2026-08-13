from __future__ import annotations

import re
import unittest
from pathlib import Path


class ActionMetadataTests(unittest.TestCase):
    def test_untrusted_inputs_are_passed_via_environment(self):
        text = Path("action.yml").read_text(encoding="utf-8")
        self.assertIn("REALITYLINT_README", text)
        self.assertIn("REALITYLINT_FAIL_ON", text)
        run_block = text.split("run:", 1)[1]
        self.assertNotIn('${{ inputs.readme }}', run_block)
        self.assertNotIn('${{ inputs.fail-on }}', run_block)

    def test_external_actions_are_pinned_to_full_commit_shas(self):
        files = [Path("action.yml"), *Path(".github/workflows").glob("*.yml")]
        external_use = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.M)
        full_sha = re.compile(r"^[^@]+@[0-9a-f]{40}$")
        for path in files:
            text = path.read_text(encoding="utf-8")
            for ref in external_use.findall(text):
                if ref.startswith("./"):
                    continue
                self.assertRegex(ref, full_sha, f"{path}: unpinned action {ref}")

    def test_workflows_use_read_only_contents_permission(self):
        for path in Path(".github/workflows").glob("*.yml"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("permissions:\n  contents: read", text, str(path))


if __name__ == "__main__":
    unittest.main()
