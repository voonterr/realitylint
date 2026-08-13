from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

try:  # Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

from .models import Finding

MAX_README_BYTES = 5 * 1024 * 1024
MAX_METADATA_BYTES = 2 * 1024 * 1024

INLINE_CODE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
ENV_COPY_RE = re.compile(
    r"\b(?:cp|copy|copy-item)(?:\s+(?:-[A-Za-z]+|/[A-Za-z]+))*\s+"
    r"(?P<src>[\"']?[^\s\"']*\.env(?:\.(?:example|sample))?[\"']?)\s+"
    r"(?P<dst>[\"']?\.env[\"']?)(?:\s|$)",
    re.I,
)
PYTHON_FILE_RE = re.compile(
    r"\b(?:python(?:3(?:\.\d+)?)?|py)(?:\s+-[A-Za-z0-9_.-]+)*\s+"
    r"(?P<path>[\"']?[^\s\"']+\.py[\"']?)\b",
    re.I,
)
MAKE_RE = re.compile(r"\bmake\s+(?!-)([A-Za-z0-9_.-]+)")
PIP_COMMAND_RE = re.compile(r"\b(?:(?:python(?:3(?:\.\d+)?)?|py)\s+-m\s+)?pip(?:3)?\s+install\b", re.I)
PIN_RE = re.compile(r"\b([A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?)==([0-9][A-Za-z0-9_.+!-]*)")
MANAGER_COMMAND_RE = re.compile(r"\b(npm|pnpm|yarn|bun)\b", re.I)
LICENSE_CLAIM_RE = re.compile(r"\b(?:MIT|Apache(?:-2\.0)?|GPL(?:v?3)?|BSD)\s+licen[cs]e\b", re.I)
FENCE_START_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})(?P<info>[^\n]*)$")

SHELL_LANGS = {
    "",
    "bash",
    "sh",
    "shell",
    "shell-session",
    "console",
    "zsh",
    "fish",
    "powershell",
    "pwsh",
}

YARN_BUILTINS = {
    "add", "bin", "cache", "config", "create", "dlx", "exec", "help", "info", "init", "install",
    "link", "node", "npm", "pack", "plugin", "rebuild", "remove", "set", "stage", "unlink", "unplug",
    "up", "version", "why", "workspaces",
}
PNPM_BUILTINS = {
    "add", "audit", "bin", "config", "create", "deploy", "dlx", "env", "exec", "fetch", "help", "import",
    "init", "install", "link", "list", "outdated", "pack", "patch", "prune", "publish", "rebuild", "remove",
    "root", "server", "setup", "store", "test", "unlink", "update", "view", "why",
}
BUN_BUILTINS = {
    "add", "build", "create", "help", "init", "install", "link", "pm", "publish", "remove", "repl", "test",
    "unlink", "update", "upgrade", "x",
}

IGNORED_PATH_PREFIXES = ("http://", "https://", "mailto:", "#", "~", "${", "$", "<", "data:")

PATH_ARG_RE = r"(?:\"[^\"]+\"|\'[^\']+\'|[^\s]+)"
MANAGER_CWD_RE = {
    "npm": re.compile(rf"\bnpm\s+--prefix(?:=|\s+)(?P<path>{PATH_ARG_RE})", re.I),
    "yarn": re.compile(rf"\byarn\s+--cwd(?:=|\s+)(?P<path>{PATH_ARG_RE})", re.I),
    "pnpm": re.compile(rf"\bpnpm\s+(?:--dir(?:=|\s+)|-C\s+)(?P<path>{PATH_ARG_RE})", re.I),
    "bun": re.compile(rf"\bbun\s+--cwd(?:=|\s+)(?P<path>{PATH_ARG_RE})", re.I),
}
MAKE_CWD_RE = re.compile(rf"\bmake\s+(?:-C\s+|--directory(?:=|\s+))(?P<path>{PATH_ARG_RE})\s+(?P<target>[A-Za-z0-9_.-]+)", re.I)


@dataclass(frozen=True)
class Command:
    text: str
    line: int
    base: Path


def _line_for(text: str, start: int) -> int:
    return text.count("\n", 0, start) + 1


def _display_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name or "README.md"


def _escape_control(value: str, limit: int = 300) -> str:
    value = "".join(ch if ch >= " " and ch != "\x7f" else "?" for ch in value)
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _resolve_inside(root: Path, candidate: Path) -> Path | None:
    try:
        resolved = candidate.resolve(strict=False)
        resolved.relative_to(root)
        return resolved
    except (OSError, RuntimeError, ValueError):
        return None


def _safe_repo_path(root: Path, base: Path, token: str) -> Path | None:
    token = token.strip().strip('"\'(),;:')
    if not token or any(ord(ch) < 32 for ch in token):
        return None
    if token.startswith(IGNORED_PATH_PREFIXES):
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", token):
        return None
    if any(ch in token for ch in ("*", "?", "{", "}", "[", "]")):
        return None
    if re.match(r"^[A-Za-z]:[\\/]", token) or token.startswith(("/", "\\\\")):
        return None
    token = token.replace("\\", "/")
    try:
        return _resolve_inside(root, base / token)
    except (OSError, ValueError):
        return None


def _is_regular_file_inside(root: Path, path: Path) -> bool:
    resolved = _resolve_inside(root, path)
    if resolved is None:
        return False
    try:
        return resolved.is_file()
    except OSError:
        return False


def _read_small_text(root: Path, path: Path, max_bytes: int, encoding: str = "utf-8") -> tuple[str | None, str | None]:
    resolved = _resolve_inside(root, path)
    if resolved is None:
        return None, "path escapes the repository"
    try:
        if not resolved.is_file():
            return None, "not a regular file"
        size = resolved.stat().st_size
        if size > max_bytes:
            return None, f"file is too large ({size} bytes; limit {max_bytes})"
        return resolved.read_text(encoding=encoding, errors="replace"), None
    except OSError as exc:
        return None, f"cannot read file: {exc.__class__.__name__}"


def _mask_and_extract_fences(text: str) -> tuple[str, list[tuple[str, int, int]]]:
    """Return prose with fenced blocks masked and shell lines as (text, line, block_id)."""
    lines = text.splitlines(keepends=True)
    masked: list[str] = []
    commands: list[tuple[str, int, int]] = []
    active_char: str | None = None
    active_len = 0
    active_shell = False
    block_id = 0

    for line_no, raw in enumerate(lines, 1):
        content = raw.rstrip("\r\n")
        newline = raw[len(content):]
        if active_char is None:
            m = FENCE_START_RE.match(content)
            if not m:
                masked.append(raw)
                continue
            fence = m.group("fence")
            active_char = fence[0]
            active_len = len(fence)
            info = m.group("info").strip()
            lang = info.split(None, 1)[0].lower() if info else ""
            active_shell = lang in SHELL_LANGS
            block_id += 1
            masked.append(" " * len(content) + newline)
            continue

        stripped = content.lstrip(" ")
        leading = len(content) - len(stripped)
        close_re = rf"^{re.escape(active_char)}{{{active_len},}}\s*$"
        if leading <= 3 and re.match(close_re, stripped):
            active_char = None
            active_len = 0
            active_shell = False
            masked.append(" " * len(content) + newline)
            continue

        if active_shell:
            command = content.strip()
            if command and not command.startswith("#"):
                command = re.sub(r"^(?:\$|>)\s+", "", command)
                command = re.sub(r"^PS\s+[^>]*>\s*", "", command, flags=re.I)
                command = re.sub(r"^[A-Za-z]:[\\/][^>]*>\s*", "", command)
                command = re.sub(r"^[^@\s]+@[^:\s]+:[^$#]*[$#]\s*", "", command)
                if command:
                    commands.append((command, line_no, block_id))
        masked.append(" " * len(content) + newline)

    return "".join(masked), commands


def _split_shell_segments(command: str) -> list[str]:
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
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            i += 2 if command.startswith(("&&", "||"), i) else 1
            continue
        buf.append(ch)
        i += 1
    part = "".join(buf).strip()
    if part:
        parts.append(part)
    return parts


def _cd_target(segment: str) -> str | None:
    m = re.match(r"^(?:cd|pushd|set-location)\s+(?:/d\s+)?(.+?)\s*$", segment, re.I)
    if not m:
        return None
    value = m.group(1).strip().strip('"\'')
    return value if value and value != "-" else None


def _commands_with_bases(root: Path, prose: str, fence_commands: list[tuple[str, int, int]]) -> list[Command]:
    commands: list[Command] = []
    cwd_by_block: dict[int, Path] = {}

    for raw, line, block_id in fence_commands:
        base = cwd_by_block.get(block_id, root)
        for segment in _split_shell_segments(raw):
            target = _cd_target(segment)
            if target is not None:
                next_base = _safe_repo_path(root, base, target)
                if next_base is not None:
                    try:
                        if next_base.is_dir():
                            base = next_base
                        elif Path(target.replace("\\", "/")).name == root.name:
                            base = root
                    except OSError:
                        pass
                continue
            commands.append(Command(segment, line, base))
        cwd_by_block[block_id] = base

    for match in INLINE_CODE_RE.finditer(prose):
        snippet = match.group(1).strip()
        if not snippet:
            continue
        # Skip obvious metavariables used to explain syntax rather than claim a real command.
        lowered = snippet.lower()
        if "path/to/" in lowered or re.fullmatch(r"make\s+(?:target|<[^>]+>)", lowered):
            continue
        if re.search(r"\b(?:npm|pnpm|yarn|bun|pip|python|python3|py|make|cp|copy|copy-item)\b", snippet, re.I):
            commands.append(Command(snippet, _line_for(prose, match.start()), root))
    return commands


def _markdown_links(text: str) -> Iterable[tuple[str, int]]:
    """Extract common inline Markdown link/image destinations, including nested parentheses and optional titles."""
    i = 0
    while True:
        marker = text.find("](", i)
        if marker < 0:
            return
        pos = marker + 2
        while pos < len(text) and text[pos] in " \t":
            pos += 1
        start = pos
        if pos >= len(text):
            return
        if text[pos] == "<":
            end = text.find(">", pos + 1)
            if end >= 0:
                yield text[pos + 1:end], marker
                i = end + 1
                continue
        depth = 0
        escaped = False
        while pos < len(text):
            ch = text[pos]
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            elif ch in " \t\r\n" and depth == 0:
                break
            pos += 1
        if pos > start:
            yield text[start:pos].replace("\\(", "(").replace("\\)", ")"), marker
        i = max(marker + 2, pos + 1)


def _clean_link_target(target: str) -> str:
    target = target.strip()
    target = target.split("#", 1)[0].split("?", 1)[0]
    try:
        return unquote(target)
    except Exception:
        return target


def _load_package_json(root: Path, base: Path) -> tuple[bool, dict | None, str | None]:
    path = base / "package.json"
    if not _is_regular_file_inside(root, path):
        return False, None, None
    text, err = _read_small_text(root, path, MAX_METADATA_BYTES, "utf-8-sig")
    if err:
        return True, None, err
    try:
        data = json.loads(text or "")
    except json.JSONDecodeError as exc:
        return True, None, f"invalid JSON at line {exc.lineno}, column {exc.colno}"
    if not isinstance(data, dict):
        return True, None, "top-level JSON value is not an object"
    return True, data, None


def _load_pyproject(root: Path, base: Path) -> tuple[dict | None, str | None]:
    path = base / "pyproject.toml"
    if not _is_regular_file_inside(root, path):
        return None, None
    text, err = _read_small_text(root, path, MAX_METADATA_BYTES)
    if err:
        return None, err
    try:
        data = tomllib.loads(text or "")
    except tomllib.TOMLDecodeError as exc:
        return None, f"invalid TOML: {_escape_control(str(exc), 160)}"
    project = data.get("project")
    return (project if isinstance(project, dict) else {}), None


def _make_targets(root: Path, base: Path) -> tuple[bool, set[str], str | None]:
    path = next((base / name for name in ("GNUmakefile", "makefile", "Makefile") if _is_regular_file_inside(root, base / name)), None)
    if path is None:
        return False, set(), None
    text, err = _read_small_text(root, path, MAX_METADATA_BYTES)
    if err:
        return True, set(), err
    targets: set[str] = set()
    for line in (text or "").splitlines():
        if line.startswith(("\t", " ", ".")):
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*:(?![=])", line)
        if m:
            targets.add(m.group(1))
    return True, targets, None


def _manager_base(root: Path, default: Path, command: str, manager: str) -> Path:
    pattern = MANAGER_CWD_RE.get(manager)
    if pattern is None:
        return default
    match = pattern.search(command)
    if not match:
        return default
    raw = match.group("path").strip('"\'')
    resolved = _safe_repo_path(root, default, raw)
    return resolved if resolved is not None else default


def _documented_scripts(command: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    path_arg = PATH_ARG_RE
    npm_prefix = rf"(?:\s+--prefix(?:=|\s+){path_arg})?"
    yarn_cwd = rf"(?:\s+--cwd(?:=|\s+){path_arg})?"
    pnpm_cwd = rf"(?:\s+(?:--dir(?:=|\s+)|-C\s+){path_arg})?"
    bun_cwd = rf"(?:\s+--cwd(?:=|\s+){path_arg})?"

    for m in re.finditer(rf"\bnpm{npm_prefix}\s+run\s+([A-Za-z0-9_.:-]+)", command, re.I):
        found.append(("npm", m.group(1)))
    for m in re.finditer(rf"\bnpm{npm_prefix}\s+(start|stop|restart|test)\b", command, re.I):
        found.append(("npm", m.group(1).lower()))

    specs = (
        ("yarn", YARN_BUILTINS, yarn_cwd),
        ("pnpm", PNPM_BUILTINS, pnpm_cwd),
        ("bun", BUN_BUILTINS, bun_cwd),
    )
    for manager, builtins, cwd in specs:
        explicit_re = rf"\b{manager}{cwd}\s+run\s+((?!-)[A-Za-z0-9_.:-]+)"
        spans: list[tuple[int, int]] = []
        for m in re.finditer(explicit_re, command, re.I):
            found.append((manager, m.group(1)))
            spans.append(m.span())
        shorthand_re = rf"\b{manager}{cwd}\s+((?!-)[A-Za-z0-9_.:-]+)"
        for m in re.finditer(shorthand_re, command, re.I):
            if any(a <= m.start() < b for a, b in spans):
                continue
            script = m.group(1)
            if script == "run" or script.lower() in builtins:
                continue
            found.append((manager, script))
    return found


def _manager_used(command: str) -> str | None:
    m = MANAGER_COMMAND_RE.search(command)
    if not m:
        return None
    manager = m.group(1).lower()
    tail = command[m.end():].lstrip()
    if not tail or tail.startswith("--version"):
        return None
    return manager


def _lockfile_manager(root: Path, base: Path) -> tuple[str | None, list[str]]:
    candidates = {
        "npm": ("package-lock.json", "npm-shrinkwrap.json"),
        "pnpm": ("pnpm-lock.yaml",),
        "yarn": ("yarn.lock",),
        "bun": ("bun.lock", "bun.lockb"),
    }
    present: dict[str, list[str]] = {}
    for manager, names in candidates.items():
        hits = [name for name in names if _is_regular_file_inside(root, base / name)]
        if hits:
            present[manager] = hits
    if len(present) != 1:
        return None, [name for names in present.values() for name in names]
    manager = next(iter(present))
    return manager, present[manager]


def _normalize_project_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _pip_pins(command: str) -> list[tuple[str, str]]:
    m = PIP_COMMAND_RE.search(command)
    if not m:
        return []
    return [(pkg.split("[", 1)[0], version) for pkg, version in PIN_RE.findall(command[m.end():])]


def _looks_like_repo_path(token: str) -> bool:
    if not token or " " in token or token.startswith(("http", "./", "../", "~", "$")):
        return False
    if not ("/" in token or "\\" in token):
        return False
    if any(ch in token for ch in ("*", "?", "{", "}", "[", "]")):
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9_./\\-]+", token))


def scan(root: Path, readme: str = "README.md") -> list[Finding]:
    try:
        root = root.expanduser().resolve(strict=False)
    except (OSError, RuntimeError):
        return [Finding("RL000", "error", "Repository root could not be resolved.", file="README.md")]

    if not root.is_dir():
        return [Finding("RL000", "error", "Repository root is not a directory.", file="README.md")]

    readme_candidate = Path(readme)
    if readme_candidate.is_absolute():
        return [Finding("RL000", "error", "--readme must be a path inside the repository.", file=_escape_control(readme))]
    readme_path = _resolve_inside(root, root / readme_candidate)
    if readme_path is None:
        return [Finding("RL000", "error", "README path escapes the repository.", file=_escape_control(readme))]
    readme_display = _display_path(root, readme_path)

    if not readme_path.exists():
        return [Finding("RL000", "error", f"{readme_display} does not exist.", file=readme_display, suggestion="Add a README or pass --readme PATH.")]
    text, read_err = _read_small_text(root, readme_path, MAX_README_BYTES)
    if read_err:
        return [Finding("RL000", "error", f"Cannot scan {readme_display}: {read_err}.", file=readme_display)]
    text = text or ""

    prose, fence_commands = _mask_and_extract_fences(text)
    commands = _commands_with_bases(root, prose, fence_commands)
    findings: list[Finding] = []
    seen: set[tuple[str, int, str, str]] = set()
    package_cache: dict[Path, tuple[bool, dict | None, str | None]] = {}
    pyproject_cache: dict[Path, tuple[dict | None, str | None]] = {}
    make_cache: dict[Path, tuple[bool, set[str], str | None]] = {}

    def add(finding: Finding) -> None:
        finding = Finding(
            finding.rule,
            finding.severity,
            _escape_control(finding.message, 700),
            _escape_control(finding.file, 260),
            max(1, finding.line),
            _escape_control(finding.evidence, 500) if finding.evidence else None,
            _escape_control(finding.suggestion, 500) if finding.suggestion else None,
        )
        key = (finding.rule, finding.line, finding.message, finding.file)
        if key not in seen:
            seen.add(key)
            findings.append(finding)

    def package_for(base: Path) -> tuple[bool, dict | None, str | None]:
        if base not in package_cache:
            package_cache[base] = _load_package_json(root, base)
        return package_cache[base]

    def pyproject_for(base: Path) -> tuple[dict | None, str | None]:
        if base not in pyproject_cache:
            pyproject_cache[base] = _load_pyproject(root, base)
        return pyproject_cache[base]

    def make_for(base: Path) -> tuple[bool, set[str], str | None]:
        if base not in make_cache:
            make_cache[base] = _make_targets(root, base)
        return make_cache[base]

    # RL002: Markdown links/images must resolve relative to the README file.
    for target, offset in _markdown_links(prose):
        clean = _clean_link_target(target)
        if not clean:
            continue
        path = _safe_repo_path(root, readme_path.parent, clean)
        if path is not None and not path.exists():
            add(Finding("RL002", "error", f'Documented local link target "{clean}" does not exist.', readme_display, _line_for(text, offset), suggestion="Fix the link or add the referenced file."))

    # Command-based deterministic checks.
    for command in commands:
        base_display = _display_path(root, command.base)

        # RL001: package scripts must exist in the package.json for the command's working directory.
        for manager, script in _documented_scripts(command.text):
            package_base = _manager_base(root, command.base, command.text, manager)
            package_display = _display_path(root, package_base)
            package_exists, package, package_err = package_for(package_base)
            if package_err:
                add(Finding("RL010", "warning", f"Could not parse {package_display}/package.json: {package_err}.", readme_display, command.line, suggestion="Fix package.json so README claims can be verified."))
                continue
            if not package_exists:
                add(Finding("RL001", "error", f'Documented package script "{script}" has no package.json in working directory "{package_display}".', readme_display, command.line, suggestion="Correct the working directory/README command or add package.json."))
                continue
            scripts_obj = package.get("scripts") if package else None
            if scripts_obj is not None and not isinstance(scripts_obj, dict):
                add(Finding("RL010", "warning", f'{package_display}/package.json has a non-object "scripts" field.', readme_display, command.line, suggestion='Change "scripts" to a JSON object.'))
                scripts: set[str] = set()
            else:
                scripts = set((scripts_obj or {}).keys())
            if script not in scripts:
                evidence = ", ".join(sorted(scripts)[:20]) or "(none)"
                if len(scripts) > 20:
                    evidence += f", … (+{len(scripts) - 20} more)"
                add(Finding("RL001", "error", f'Documented package script "{script}" is not defined in {package_display}/package.json.', readme_display, command.line, evidence=f"Available scripts: {evidence}", suggestion=f'Add the "{script}" script or update the README command.'))

        # RL003: env templates copied during setup must be files.
        for match in ENV_COPY_RE.finditer(command.text):
            src = match.group("src").strip('"\'')
            path = _safe_repo_path(root, command.base, src)
            if path is not None and not _is_regular_file_inside(root, path):
                add(Finding("RL003", "error", f'Documented environment template "{src}" does not exist as a file.', readme_display, command.line, suggestion="Add the template or correct the setup command."))

        # RL005: Python entry files must exist as files.
        for match in PYTHON_FILE_RE.finditer(command.text):
            target = match.group("path").strip('"\'')
            path = _safe_repo_path(root, command.base, target)
            if path is not None and not _is_regular_file_inside(root, path):
                add(Finding("RL005", "error", f'Documented Python entry file "{target}" does not exist as a file.', readme_display, command.line, suggestion="Correct the command or add the entry file."))

        # RL006: Make targets require a Makefile and a matching target.
        make_invocations: list[tuple[Path, str]] = []
        make_cwd_spans: list[tuple[int, int]] = []
        for match in MAKE_CWD_RE.finditer(command.text):
            raw_dir = match.group("path").strip('"\'')
            make_base = _safe_repo_path(root, command.base, raw_dir) or command.base
            make_invocations.append((make_base, match.group("target")))
            make_cwd_spans.append(match.span())
        for match in MAKE_RE.finditer(command.text):
            if any(a <= match.start() < b for a, b in make_cwd_spans):
                continue
            make_invocations.append((command.base, match.group(1)))

        for make_base, target in make_invocations:
            make_display = _display_path(root, make_base)
            make_exists, targets, make_err = make_for(make_base)
            if make_err:
                add(Finding("RL010", "warning", f"Could not read {make_display}/Makefile: {make_err}.", readme_display, command.line, suggestion="Fix the Makefile so README claims can be verified."))
            elif not make_exists:
                add(Finding("RL006", "error", f'Documented Make target "{target}" has no Makefile in working directory "{make_display}".', readme_display, command.line, suggestion="Correct the working directory/README command or add a Makefile."))
            elif target not in targets:
                evidence = ", ".join(sorted(targets)[:30]) or "(none)"
                add(Finding("RL006", "error", f'Documented Make target "{target}" does not exist.', readme_display, command.line, evidence=f"Available targets: {evidence}", suggestion="Use an existing Make target or add it."))

        # RL004: package manager commands should agree with the sole lockfile family.
        used = _manager_used(command.text)
        if used:
            manager_base = _manager_base(root, command.base, command.text, used)
            manager_display = _display_path(root, manager_base)
            expected, lock_names = _lockfile_manager(root, manager_base)
            if expected and used != expected:
                add(Finding("RL004", "warning", f'README uses {used}, but working directory "{manager_display}" has only a {expected} lockfile family.', readme_display, command.line, evidence=f"Detected: {', '.join(lock_names)}", suggestion=f"Use {expected} in setup examples or commit the intended lockfile."))

        # RL007: pinned self-install version should match pyproject project.version.
        pins = _pip_pins(command.text)
        if pins:
            project, project_err = pyproject_for(command.base)
            if project_err:
                add(Finding("RL010", "warning", f"Could not parse {base_display}/pyproject.toml: {project_err}.", readme_display, command.line, suggestion="Fix pyproject.toml so README claims can be verified."))
            elif project:
                py_name = project.get("name")
                py_version = project.get("version")
                if isinstance(py_name, str) and isinstance(py_version, str):
                    normalized = _normalize_project_name(py_name)
                    for pkg, version in pins:
                        if _normalize_project_name(pkg) == normalized and version != py_version:
                            add(Finding("RL007", "error", f'README pins {pkg}=={version}, but pyproject.toml declares version {py_version}.', readme_display, command.line, suggestion="Update the README pin or the project version."))

    # RL008: common license claim requires a regular license file.
    license_match = LICENSE_CLAIM_RE.search(prose)
    if license_match:
        if not any(_is_regular_file_inside(root, root / name) for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")):
            add(Finding("RL008", "warning", "README claims a license, but no LICENSE/COPYING file was found.", readme_display, _line_for(text, license_match.start()), suggestion="Add the license file or remove the claim."))

    # RL009: obvious inline repository paths. Notice only to keep false-positive cost low.
    for match in INLINE_CODE_RE.finditer(prose):
        token = match.group(1).strip()
        if not _looks_like_repo_path(token):
            continue
        path = _safe_repo_path(root, root, token)
        if path is not None and not path.exists():
            add(Finding("RL009", "notice", f'Inline path "{token}" was not found in the repository.', readme_display, _line_for(text, match.start()), suggestion="Confirm the path is still current."))

    return sorted(findings, key=lambda f: (f.line, f.rule, f.message))
