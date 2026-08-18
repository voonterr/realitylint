from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SHELL_LANGS = {"", "bash", "sh", "shell", "shell-session", "console", "zsh", "fish", "powershell", "pwsh"}
FENCE_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)$")
INLINE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")


@dataclass(frozen=True)
class Command:
    text: str
    line: int
    base: Path
    source: str = "fence"


def display_path(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except (OSError, RuntimeError, ValueError):
        return path.name


def resolve_inside(root: Path, base: Path, token: str) -> Path | None:
    token = token.strip().strip('"\'(),;:')
    if not token or any(ch in token for ch in "*?{}[]"):
        return None
    if re.match(r"^[A-Za-z]:[\\/]", token) or token.startswith(("/", "\\\\")):
        return None
    try:
        path = (base / token.replace("\\", "/")).resolve(strict=False)
        path.relative_to(root.resolve(strict=False))
        return path
    except (OSError, RuntimeError, ValueError):
        return None


def _split_shell(command: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    escaped = False
    i = 0
    while i < len(command):
        ch = command[i]
        if escaped:
            buf.append(ch)
            escaped = False
            i += 1
            continue
        if ch == "\\" and quote != "'":
            buf.append(ch)
            escaped = True
            i += 1
            continue
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == ";" or command.startswith("&&", i) or command.startswith("||", i):
            value = "".join(buf).strip()
            if value:
                parts.append(value)
            buf = []
            i += 2 if command.startswith(("&&", "||"), i) else 1
            continue
        buf.append(ch)
        i += 1
    value = "".join(buf).strip()
    if value:
        parts.append(value)
    return parts


def _cd_target(segment: str) -> str | None:
    match = re.match(r"^(?:cd|pushd|set-location)\s+(?:/d\s+)?(.+?)\s*$", segment, re.I)
    if not match:
        return None
    value = match.group(1).strip().strip('"\'')
    return value if value and value != "-" else None


def extract_commands(root: Path, doc_path: Path, text: str, keywords: tuple[str, ...]) -> list[Command]:
    lines = text.splitlines()
    commands: list[Command] = []
    active_char: str | None = None
    active_len = 0
    active_shell = False
    base = root

    for line_no, content in enumerate(lines, 1):
        if active_char is None:
            match = FENCE_RE.match(content)
            if match:
                fence = match.group("fence")
                active_char = fence[0]
                active_len = len(fence)
                info = match.group("info").strip()
                lang = info.split(None, 1)[0].lower() if info else ""
                active_shell = lang in SHELL_LANGS
                base = root
                continue
        else:
            stripped = content.lstrip(" ")
            if len(content) - len(stripped) <= 3 and re.match(rf"^{re.escape(active_char)}{{{active_len},}}\s*$", stripped):
                active_char = None
                active_len = 0
                active_shell = False
                base = root
                continue
            if active_shell:
                raw = content.strip()
                if not raw or raw.startswith("#"):
                    continue
                raw = re.sub(r"^(?:\$|>)\s+", "", raw)
                raw = re.sub(r"^PS\s+[^>]*>\s*", "", raw, flags=re.I)
                raw = re.sub(r"^[A-Za-z]:[\\/][^>]*>\s*", "", raw)
                raw = re.sub(r"^[^@\s]+@[^:\s]+:[^$#]*[$#]\s*", "", raw)
                for segment in _split_shell(raw):
                    target = _cd_target(segment)
                    if target is not None:
                        candidate = resolve_inside(root, base, target)
                        if candidate is not None:
                            try:
                                if candidate.is_dir():
                                    base = candidate
                            except OSError:
                                pass
                        continue
                    if any(re.search(keyword, segment, re.I) for keyword in keywords):
                        commands.append(Command(segment, line_no, base, "fence"))

    # Inline code is useful for compact command examples. It always starts at repo root.
    for match in INLINE_RE.finditer(text):
        snippet = match.group(1).strip()
        # Inline documentation often describes command syntax with metavariables.
        # Treat those as syntax, not as a concrete repository claim.
        if re.search(r"<[^>]+>|\b(?:NAME|PATH|TARGET|FEATURE|SERVICE|COMMAND)\b", snippet):
            continue
        if snippet and any(re.search(keyword, snippet, re.I) for keyword in keywords):
            commands.append(Command(snippet, text.count("\n", 0, match.start()) + 1, root, "inline"))

    # Deduplicate fence + inline captures.
    seen: set[tuple[str, int, str]] = set()
    result: list[Command] = []
    for command in commands:
        key = (command.text, command.line, display_path(root, command.base))
        if key not in seen:
            seen.add(key)
            result.append(command)
    return result
