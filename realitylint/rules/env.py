from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ..models import Finding
from .common import display_path

TEMPLATE_NAMES = {".env.example", ".env.sample"}
EXCLUDED_DIRS = {".git", ".venv", "venv", "node_modules", "vendor", "dist", "build", "target", "__pycache__"}
INLINE_VAR_RE = re.compile(r"(?<!`)`([A-Z][A-Z0-9_]{2,})`(?!`)")
SHELL_VAR_RE = re.compile(r"\$\{([A-Z][A-Z0-9_]{2,})\}|\$([A-Z][A-Z0-9_]{2,})\b")
ASSIGN_RE = re.compile(r"(?m)^\s*(?:export\s+)?([A-Z][A-Z0-9_]{2,})\s*=")
SOURCE_PATTERNS = {
    ".py": (
        re.compile(r"os\.getenv\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']"),
        re.compile(r"os\.environ(?:\.get\()?\s*[\[\(]?\s*[\"']([A-Z][A-Z0-9_]*)[\"']"),
    ),
    ".js": (re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)"),),
    ".jsx": (re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)"),),
    ".ts": (re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)"),),
    ".tsx": (re.compile(r"process\.env\.([A-Z][A-Z0-9_]*)"),),
    ".go": (re.compile(r"os\.(?:Getenv|LookupEnv)\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']"),),
    ".rs": (re.compile(r"(?:std::)?env::var(?:_os)?\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']"),),
}


def _inside(root: Path, path: Path) -> Path | None:
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root.resolve(strict=False))
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


def _skip(path: Path, root: Path) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return True
    return any(part in EXCLUDED_DIRS for part in rel.parts)


def _template_vars(root: Path) -> tuple[set[str], list[Path]]:
    variables: set[str] = set()
    files: list[Path] = []
    try:
        for path in root.rglob("*"):
            if path.name not in TEMPLATE_NAMES or _skip(path, root):
                continue
            resolved = _inside(root, path)
            if resolved is None:
                continue
            try:
                if not resolved.is_file() or resolved.stat().st_size > 1024 * 1024:
                    continue
                text = resolved.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            files.append(resolved)
            variables.update(ASSIGN_RE.findall(text))
            if len(files) >= 100:
                break
    except OSError:
        pass
    return variables, files


def _documented_vars(root: Path, docs: Iterable[Path]) -> dict[str, tuple[str, int, bool]]:
    """Return NAME -> (doc, line, strong_env_syntax).

    `$NAME`, `${NAME}` and assignments are strong evidence. A bare inline
    `NAME` is only treated as an env claim when source code also uses NAME or
    the identifier contains an underscore, reducing false positives for inline
    acronyms such as `API` or `JSON`.
    """
    result: dict[str, tuple[str, int, bool]] = {}
    for doc in docs:
        resolved = _inside(root, doc)
        if resolved is None:
            continue
        try:
            if resolved.stat().st_size > 5 * 1024 * 1024:
                continue
            text = resolved.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        matches: list[tuple[int, str, bool]] = []
        for match in INLINE_VAR_RE.finditer(text):
            matches.append((match.start(), match.group(1), False))
        for match in SHELL_VAR_RE.finditer(text):
            matches.append((match.start(), match.group(1) or match.group(2), True))
        for match in ASSIGN_RE.finditer(text):
            matches.append((match.start(), match.group(1), True))
        for offset, name, strong in sorted(matches):
            current = result.get(name)
            item = (display_path(root, resolved), text.count("\n", 0, offset) + 1, strong)
            if current is None or (strong and not current[2]):
                result[name] = item
    return result


def _source_vars(root: Path) -> set[str]:
    result: set[str] = set()
    count = 0
    try:
        for path in root.rglob("*"):
            if count >= 1000 or _skip(path, root):
                continue
            patterns = SOURCE_PATTERNS.get(path.suffix.lower())
            if not patterns:
                continue
            resolved = _inside(root, path)
            if resolved is None:
                continue
            try:
                if not resolved.is_file() or resolved.stat().st_size > 1024 * 1024:
                    continue
                text = resolved.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            count += 1
            for pattern in patterns:
                result.update(pattern.findall(text))
    except OSError:
        pass
    return result


def scan_environment_drift(root: Path, docs: Iterable[Path]) -> list[Finding]:
    documented = _documented_vars(root, docs)
    if not documented:
        return []
    template_vars, templates = _template_vars(root)
    if not templates:
        # RL003 already handles explicit copy commands. Do not invent a global
        # env-template requirement for projects that configure env elsewhere.
        return []
    source_vars = _source_vars(root)
    findings: list[Finding] = []
    template_names = ", ".join(display_path(root, path) for path in templates[:8])
    for name, (doc, line, strong) in sorted(documented.items()):
        if name in template_vars:
            continue
        if not strong and "_" not in name and name not in source_vars:
            continue
        severity = "error" if name in source_vars else "warning"
        evidence = f"Checked environment templates: {template_names}"
        if name in source_vars:
            evidence += "; variable is also referenced by source code"
        findings.append(Finding(
            "RL014", severity, f'Documented environment variable "{name}" is missing from environment templates.',
            doc, line, evidence=evidence,
            suggestion=f"Add {name} to an .env.example/.env.sample file or update the documentation.",
        ))
    return findings
