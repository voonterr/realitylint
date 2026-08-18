from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ACTION_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ACTION_ROOT))

from realitylint.cli import main, render_markdown  # noqa: E402
from realitylint.engine import scan_project  # noqa: E402


def _parse_context(args: list[str]) -> tuple[Path, str, bool, list[str], str | None]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--all-docs", action="store_true")
    parser.add_argument("--docs", action="append")
    parser.add_argument("--config")
    parsed, _unknown = parser.parse_known_args(args)
    patterns: list[str] = []
    for value in parsed.docs or []:
        patterns.extend(part.strip() for part in value.split(",") if part.strip())
    return Path(parsed.root), parsed.readme, parsed.all_docs, patterns, parsed.config


def run() -> int:
    args = sys.argv[1:]
    root, readme, all_docs, patterns, config = _parse_context(args)
    findings = scan_project(root, readme, all_docs=all_docs, patterns=patterns, config_path=config)
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
