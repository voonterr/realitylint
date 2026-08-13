from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ACTION_ROOT))

from realitylint.cli import main, render_markdown  # noqa: E402
from realitylint.scanner import scan  # noqa: E402


def _parse_context(args: list[str]) -> tuple[Path, str]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--readme", default="README.md")
    parsed, _unknown = parser.parse_known_args(args)
    return Path(parsed.root), parsed.readme


def run() -> int:
    args = sys.argv[1:]
    root, readme = _parse_context(args)
    findings = scan(root, readme)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write(render_markdown(findings) + "\n")
        except OSError as exc:
            print(f"RealityLint: could not write GITHUB_STEP_SUMMARY: {exc}", file=sys.stderr)
    return main(args + ["--github-annotations"])


if __name__ == "__main__":
    raise SystemExit(run())
