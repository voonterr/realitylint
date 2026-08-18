from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from .models import Finding, Severity

VALID_SEVERITIES = {"error", "warning", "notice", "off"}


@dataclass(frozen=True)
class Config:
    docs: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    severity: dict[str, str] = field(default_factory=dict)


def load_config(root: Path, path: str | None = None) -> Config:
    try:
        root = root.resolve(strict=False)
        config_path = (root / (path or ".realitylint.toml")).resolve(strict=False)
        config_path.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return Config()
    try:
        if not config_path.is_file():
            return Config()
        data = tomllib.loads(config_path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, tomllib.TOMLDecodeError):
        return Config()
    section = data.get("realitylint") if isinstance(data, dict) else None
    docs: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    if isinstance(section, dict) and isinstance(section.get("docs"), list):
        docs = tuple(str(item) for item in section["docs"] if isinstance(item, str))
    if isinstance(section, dict) and isinstance(section.get("exclude"), list):
        exclude = tuple(str(item) for item in section["exclude"] if isinstance(item, str))
    severity_section = data.get("severity") if isinstance(data, dict) else None
    severity: dict[str, str] = {}
    if isinstance(severity_section, dict):
        for rule, value in severity_section.items():
            normalized = str(value).lower()
            if normalized in VALID_SEVERITIES:
                severity[str(rule).upper()] = normalized
    return Config(docs=docs, exclude=exclude, severity=severity)


def apply_config(findings: list[Finding], config: Config) -> list[Finding]:
    result: list[Finding] = []
    for finding in findings:
        override = config.severity.get(finding.rule)
        if override == "off":
            continue
        if override in {"error", "warning", "notice"} and override != finding.severity:
            finding = Finding(
                finding.rule, override, finding.message, finding.file, finding.line,
                finding.evidence, finding.suggestion,
            )
        result.append(finding)
    return result
