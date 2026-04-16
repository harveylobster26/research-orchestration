from __future__ import annotations

from collections import defaultdict

from app.schemas import Evidence, RankedCompany


def rank_companies(evidence_items: list[Evidence]) -> list[RankedCompany]:
    by_ticker: dict[str, list[Evidence]] = defaultdict(list)
    for item in evidence_items:
        if item.ticker and item.ticker != "UNKNOWN":
            by_ticker[item.ticker].append(item)

    ranked: list[RankedCompany] = []
    for ticker, group in by_ticker.items():
        avg_relevance = _average([item.ai_infra_relevance for item in group])
        avg_underfollowed = _average([item.underfollowed_signal for item in group])
        avg_rerated = _average([item.rerated_risk for item in group])
        avg_confidence = _average([item.confidence for item in group])
        source_bonus = sum(_source_bonus(item.source_type) for item in group)

        total_score = 0
        total_score += round(avg_relevance * 3)
        total_score += round(avg_underfollowed * 2)
        total_score += round(avg_confidence * 2)
        total_score -= round(avg_rerated * 3)
        total_score += source_bonus

        lead = group[0]
        ranked.append(
            RankedCompany(
                company=lead.company,
                ticker=ticker,
                bottleneck_category=lead.bottleneck_category,
                total_score=total_score,
                evidence_count=len(group),
                evidence_quality=avg_relevance,
                average_confidence=avg_confidence,
                underfollowed_signal=avg_underfollowed,
                rerated_risk=avg_rerated,
                summary=" ".join(item.evidence_summary for item in group[:2]),
            )
        )

    ranked.sort(
        key=lambda item: (item.total_score, item.average_confidence, item.evidence_count),
        reverse=True,
    )
    return ranked


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _source_bonus(source_type: str) -> int:
    if source_type == "filing_or_ir":
        return 2
    if source_type == "market_media":
        return 0
    return 1
