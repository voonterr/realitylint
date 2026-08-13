from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal

Severity = Literal["error", "warning", "notice"]


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    message: str
    file: str = "README.md"
    line: int = 1
    evidence: str | None = None
    suggestion: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
