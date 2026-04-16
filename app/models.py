from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas import Evidence


@dataclass
class ExtractionResult:
    evidence: list[Evidence] = field(default_factory=list)
    rejected: list[Evidence] = field(default_factory=list)
