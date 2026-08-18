from __future__ import annotations

from pathlib import Path
import fnmatch
from typing import Iterable

from .config import apply_config, load_config
from .directives import apply_directives
from .models import Finding
from .rules.docker import scan_docker_drift
from .rules.env import scan_environment_drift
from .rules.go import scan_go_drift
from .rules.rust import scan_rust_drift
from .scanner import scan as scan_document

DEFAULT_DOC_PATTERNS = ("README*.md", "docs/**/*.md", "CONTRIBUTING.md")


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def discover_docs(root: Path, readme: str = "README.md", *, all_docs: bool = False, patterns: Iterable[str] | None = None, exclude: Iterable[str] | None = None) -> list[Path]:
    root = root.expanduser().resolve(strict=False)
    found: dict[str, Path] = {}

    def add(path: Path) -> None:
        if not _inside(root, path):
            return
        try:
            if not path.is_file():
                return
            rel = path.resolve(strict=False).relative_to(root).as_posix()
        except (OSError, RuntimeError, ValueError):
            return
        if any(fnmatch.fnmatch(rel, pattern) for pattern in (exclude or ())):
            return
        found.setdefault(rel, path)

    add(root / readme)
    requested: list[str] = []
    if all_docs:
        requested.extend(DEFAULT_DOC_PATTERNS)
    if patterns:
        requested.extend(pattern for pattern in patterns if pattern)
    for pattern in requested:
        try:
            for path in root.glob(pattern):
                add(path)
        except (OSError, ValueError):
            continue
    return [found[key] for key in sorted(found)]


def _dedupe(findings: Iterable[Finding]) -> list[Finding]:
    seen: set[tuple[str, str, int, str, str]] = set()
    result: list[Finding] = []
    for finding in findings:
        key = (finding.rule, finding.file, finding.line, finding.severity, finding.message)
        if key in seen:
            continue
        seen.add(key)
        result.append(finding)
    result.sort(key=lambda f: (f.file.lower(), max(1, f.line), f.rule, f.message))
    return result


def scan_project(root: Path, readme: str = "README.md", *, all_docs: bool = False, patterns: Iterable[str] | None = None, config_path: str | None = None) -> list[Finding]:
    root = root.expanduser().resolve(strict=False)
    config = load_config(root, config_path)
    effective_patterns = list(patterns or ()) + list(config.docs)
    docs = discover_docs(root, readme, all_docs=all_docs, patterns=effective_patterns, exclude=config.exclude)
    if not docs:
        return scan_document(root, readme)

    findings: list[Finding] = []
    for doc in docs:
        rel = doc.relative_to(root).as_posix()
        findings.extend(scan_document(root, rel))
        findings.extend(scan_docker_drift(root, doc))
        findings.extend(scan_go_drift(root, doc))
        findings.extend(scan_rust_drift(root, doc))
    findings.extend(scan_environment_drift(root, docs))
    findings = _dedupe(findings)
    findings = apply_directives(root, findings)
    findings = apply_config(findings, config)
    return _dedupe(findings)
