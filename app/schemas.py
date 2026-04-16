from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


_NULL_MARKERS = {
    "",
    "none",
    "null",
    "n/a",
    "na",
    "unknown",
    "not applicable",
}


@dataclass
class Plan:
    research_goal: str
    bottlenecks: list[str] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    target_evidence_types: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict) -> "Plan":
        return cls(
            research_goal=payload.get("research_goal", ""),
            bottlenecks=list(payload.get("bottlenecks", [])),
            queries=list(payload.get("queries", [])),
            target_evidence_types=list(payload.get("target_evidence_types", [])),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    source_domain: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchBatch:
    query: str
    results: list[SearchResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "results": [item.to_dict() for item in self.results],
        }


@dataclass
class FetchedDocument:
    url: str
    title: str
    raw_html_path: str
    clean_text_path: str
    clean_text: str
    retrieved_at: str = field(default_factory=utc_now_iso)
    content_type: str = "text/html"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Evidence:
    company: str
    ticker: str
    bottleneck_category: str
    source_url: str
    source_type: str
    evidence_summary: str
    evidence_snippet: str
    ai_infra_relevance: float
    underfollowed_signal: float
    rerated_risk: float
    confidence: float
    red_flags: list[str] = field(default_factory=list)
    is_relevant: bool = True
    rejection_reason: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "Evidence":
        return cls(
            company=_normalize_company(payload.get("company", "Unknown")),
            ticker=_normalize_ticker(payload.get("ticker", "UNKNOWN")),
            bottleneck_category=str(payload.get("bottleneck_category", "unclassified")),
            source_url=str(payload.get("source_url", "")),
            source_type=str(payload.get("source_type", "web")),
            evidence_summary=str(payload.get("evidence_summary", "")),
            evidence_snippet=str(payload.get("evidence_snippet", "")),
            ai_infra_relevance=_bounded_float(payload.get("ai_infra_relevance", 0.0)),
            underfollowed_signal=_bounded_float(payload.get("underfollowed_signal", 0.0)),
            rerated_risk=_bounded_float(payload.get("rerated_risk", 0.0)),
            confidence=_bounded_float(payload.get("confidence", 0.0)),
            red_flags=[str(flag) for flag in payload.get("red_flags", [])],
            is_relevant=bool(payload.get("is_relevant", True)),
            rejection_reason=payload.get("rejection_reason"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RankedCompany:
    company: str
    ticker: str
    bottleneck_category: str
    total_score: int
    evidence_count: int
    evidence_quality: float
    average_confidence: float
    underfollowed_signal: float
    rerated_risk: float
    summary: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunManifest:
    run_id: str
    objective: str
    run_dir: str
    started_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineArtifacts:
    manifest: RunManifest
    plan: Plan
    search_results: list[SearchBatch]
    documents: list[FetchedDocument]
    evidence: list[Evidence]
    ranked_companies: list[RankedCompany]
    brief_path: str | None = None


def _bounded_float(value: object) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return max(0.0, min(1.0, numeric))


def _normalize_company(value: object) -> str:
    text = str(value).strip()
    if text.lower() in _NULL_MARKERS:
        return "Unknown"
    return text


def _normalize_ticker(value: object) -> str:
    text = str(value).strip()
    if text.lower() in _NULL_MARKERS:
        return "UNKNOWN"
    return text.upper()
