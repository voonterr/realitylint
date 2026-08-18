from __future__ import annotations

import re
import shlex
from pathlib import Path

from ..models import Finding
from .common import display_path, extract_commands, resolve_inside

GO_CLAIM_RE = re.compile(r"\bGo\s+(?:version\s+)?v?(\d+\.\d+(?:\.\d+)?)\+?", re.I)
GO_DIRECTIVE_RE = re.compile(r"(?m)^go\s+(\d+\.\d+(?:\.\d+)?)\s*$")


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def _go_mod_version(root: Path, base: Path) -> str | None:
    path = resolve_inside(root, base, "go.mod")
    if path is None:
        return None
    try:
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            return None
        match = GO_DIRECTIVE_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    return match.group(1) if match else None


def _major_minor(version: str) -> tuple[int, int] | None:
    parts = version.split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None


def scan_go_drift(root: Path, doc_path: Path) -> list[Finding]:
    try:
        text = doc_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    doc = display_path(root, doc_path)
    findings: list[Finding] = []
    commands = extract_commands(root, doc_path, text, (r"\bgo\s+run\b",))
    bases: set[Path] = {command.base for command in commands} or {root}
    for command in commands:
        tokens = _tokens(command.text)
        try:
            idx = next(i for i, token in enumerate(tokens) if token == "go" and i + 1 < len(tokens) and tokens[i + 1] == "run")
        except StopIteration:
            continue
        for token in tokens[idx + 2:]:
            if token.startswith("-"):
                continue
            if token.endswith(".go") or token in {".", ".."} or token.startswith(("./", "../")):
                target = resolve_inside(root, command.base, token)
                if target is None:
                    continue
                try:
                    exists = target.is_file() if token.endswith(".go") else target.is_dir()
                    if target.is_dir():
                        exists = any(target.glob("*.go"))
                except OSError:
                    exists = False
                if not exists:
                    findings.append(Finding(
                        "RL015", "error", f'Documented go run target "{token}" does not exist or contains no Go files.',
                        doc, command.line,
                        suggestion="Correct the go run target or add the documented package/files.",
                    ))

    # A human-readable Go version claim is compared with the go.mod language
    # version only when a go.mod exists. This stays a warning because projects
    # may intentionally require a newer toolchain than the language directive.
    for match in GO_CLAIM_RE.finditer(text):
        documented = match.group(1)
        actual = next((value for base in bases if (value := _go_mod_version(root, base))), None)
        if actual and _major_minor(documented) != _major_minor(actual):
            findings.append(Finding(
                "RL021", "warning", f'Documented Go version {documented} differs from go.mod directive {actual}.',
                doc, text.count("\n", 0, match.start()) + 1,
                suggestion="Confirm the intended minimum Go version and keep docs/go.mod aligned.",
            ))
            break
    return findings
