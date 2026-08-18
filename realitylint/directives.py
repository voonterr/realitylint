from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .models import Finding

DIRECTIVE_RE = re.compile(r"<!--\s*realitylint-(ignore-next-line|disable|enable)(?:\s+([^>]+?))?\s*-->", re.I)


def _rules(raw: str | None) -> set[str] | None:
    if raw is None or not raw.strip():
        return None
    return {part.upper() for part in re.split(r"[\s,]+", raw.strip()) if part}


def ignored_lines(text: str) -> dict[int, set[str] | None]:
    ignored: dict[int, set[str] | None] = {}
    disabled_all = False
    disabled_rules: set[str] = set()
    lines = text.splitlines()
    for line_no, line in enumerate(lines, 1):
        match = DIRECTIVE_RE.search(line)
        if match:
            action = match.group(1).lower()
            rules = _rules(match.group(2))
            if action == "ignore-next-line":
                ignored[line_no + 1] = rules
            elif action == "disable":
                if rules is None:
                    disabled_all = True
                else:
                    disabled_rules.update(rules)
            elif action == "enable":
                if rules is None:
                    disabled_all = False
                    disabled_rules.clear()
                else:
                    disabled_rules.difference_update(rules)
        if disabled_all:
            ignored[line_no] = None
        elif disabled_rules:
            ignored[line_no] = set(disabled_rules)
    return ignored


def apply_directives(root: Path, findings: Iterable[Finding]) -> list[Finding]:
    cache: dict[str, dict[int, set[str] | None]] = {}
    result: list[Finding] = []
    for finding in findings:
        mapping = cache.get(finding.file)
        if mapping is None:
            path = root / finding.file
            try:
                mapping = ignored_lines(path.read_text(encoding="utf-8", errors="replace")) if path.is_file() else {}
            except OSError:
                mapping = {}
            cache[finding.file] = mapping
        rules = mapping.get(max(1, finding.line), set())
        if rules is None or finding.rule in rules:
            continue
        result.append(finding)
    return result
