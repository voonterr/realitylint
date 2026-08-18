from __future__ import annotations

import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from ..models import Finding
from .common import display_path, extract_commands

BIN_RE = re.compile(r"\bcargo\s+run\b[^\n]*?(?:--bin(?:=|\s+))([A-Za-z0-9_.-]+)")
FEATURE_RE = re.compile(r"(?:--features|-F)(?:=|\s+)([^\s]+)")
RUST_CLAIM_RE = re.compile(r"\bRust\s+(?:version\s+)?v?(\d+\.\d+(?:\.\d+)?)\+?", re.I)


def _manifest(root: Path, base: Path) -> tuple[dict | None, str | None]:
    path = base / "Cargo.toml"
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root.resolve(strict=False))
        path = resolved
        if not path.is_file():
            return None, "Cargo.toml not found"
        if path.stat().st_size > 2 * 1024 * 1024:
            return None, "Cargo.toml is larger than 2 MiB"
        data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, RuntimeError, ValueError, tomllib.TOMLDecodeError) as exc:
        return None, f"cannot parse Cargo.toml: {exc.__class__.__name__}"
    return data if isinstance(data, dict) else {}, None


def _bins(base: Path, data: dict) -> set[str]:
    result: set[str] = set()
    raw_bins = data.get("bin")
    if isinstance(raw_bins, list):
        for item in raw_bins:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                result.add(item["name"])
    package = data.get("package")
    if isinstance(package, dict) and isinstance(package.get("name"), str):
        try:
            if (base / "src/main.rs").is_file():
                result.add(package["name"])
        except OSError:
            pass
    return result


def _major_minor(version: str) -> tuple[int, int] | None:
    parts = version.split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None


def scan_rust_drift(root: Path, doc_path: Path) -> list[Finding]:
    try:
        text = doc_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    doc = display_path(root, doc_path)
    findings: list[Finding] = []
    commands = extract_commands(root, doc_path, text, (r"\bcargo\s+(?:run|build|test)\b",))
    manifests: list[tuple[Path, dict]] = []
    for command in commands:
        if command.source == "inline" and not re.search(r"--bin|--features|-F(?:=|\s)", command.text):
            continue
        data, error = _manifest(root, command.base)
        if error:
            findings.append(Finding(
                "RL016", "error", f"Documented Cargo command cannot be verified: {error}.",
                doc, command.line,
                suggestion="Add/fix Cargo.toml or document the correct working directory.",
            ))
            continue
        assert data is not None
        manifests.append((command.base, data))
        bin_match = BIN_RE.search(command.text)
        if bin_match:
            name = bin_match.group(1)
            available = _bins(command.base, data)
            if name not in available:
                findings.append(Finding(
                    "RL017", "error", f'Documented Cargo binary "{name}" is not defined.',
                    doc, command.line,
                    evidence=f"Available binaries: {', '.join(sorted(available)) or '(none)'}",
                    suggestion="Use a defined binary name or add [[bin]] metadata/source.",
                ))
        features = data.get("features") if isinstance(data.get("features"), dict) else {}
        for feature_match in FEATURE_RE.finditer(command.text):
            raw = feature_match.group(1)
            for feature in [part for part in raw.split(",") if part and part not in {"default", "all"}]:
                if feature not in features:
                    findings.append(Finding(
                        "RL018", "error", f'Documented Cargo feature "{feature}" is not defined in Cargo.toml.',
                        doc, command.line,
                        evidence=f"Available features: {', '.join(sorted(features)) or '(none)'}",
                        suggestion="Use an existing feature or add it to [features].",
                    ))

    # If there were no Cargo command examples, a Rust version claim can still be
    # verified against a root Cargo.toml when present.
    if not manifests:
        data, _error = _manifest(root, root)
        if data is not None:
            manifests.append((root, data))
    for match in RUST_CLAIM_RE.finditer(text):
        documented = match.group(1)
        actual: str | None = None
        for _base, data in manifests:
            package = data.get("package")
            if isinstance(package, dict) and isinstance(package.get("rust-version"), str):
                actual = package["rust-version"]
                break
        if actual and _major_minor(documented) != _major_minor(actual):
            findings.append(Finding(
                "RL022", "warning", f'Documented Rust version {documented} differs from Cargo rust-version {actual}.',
                doc, text.count("\n", 0, match.start()) + 1,
                suggestion="Confirm the intended MSRV and keep docs/Cargo.toml aligned.",
            ))
            break
    return findings
