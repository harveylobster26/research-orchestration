from __future__ import annotations

from app.config import AppSettings
from app.models import ExtractionResult
from app.providers.ollama_client import OllamaClient
from app.schemas import Evidence, FetchedDocument, Plan
from app.utils import domain_for_url, read_profile_prompt


def extract_evidence(
    settings: AppSettings,
    ollama: OllamaClient,
    plan: Plan,
    documents: list[FetchedDocument],
) -> ExtractionResult:
    prompt_template = read_profile_prompt(
        settings.prompts_path,
        settings.pipeline.profile,
        "extractor.md",
    )
    evidence: list[Evidence] = []
    rejected: list[Evidence] = []
    query_context = ", ".join(plan.queries)

    for document in documents:
        prompt = (
            f"{prompt_template}\n\n"
            f"Research goal: {plan.research_goal}\n"
            f"Bottlenecks: {', '.join(plan.bottlenecks)}\n"
            f"Target source types: {', '.join(plan.target_evidence_types)}\n"
            f"Search query context: {query_context}\n"
            f"Source URL: {document.url}\n"
            f"Document title: {document.title}\n"
            f"Document text:\n{document.clean_text}\n"
        )
        raw = ollama.generate_json(
            prompt,
            model=settings.ollama.utility_model,
            temperature=0.0,
        )
        items = raw.get("evidence") or [_fallback_rejection(document)]
        for item in items:
            merged = {
                "source_url": document.url,
                "source_type": _source_type_for_url(document.url),
                **item,
            }
            record = Evidence.from_dict(merged)
            if record.is_relevant:
                evidence.append(record)
            else:
                rejected.append(record)

    return ExtractionResult(evidence=evidence, rejected=rejected)


def _source_type_for_url(url: str) -> str:
    domain = domain_for_url(url)
    if any(token in domain for token in ["sec.gov", "investor", "ir."]):
        return "filing_or_ir"
    if any(token in domain for token in ["seekingalpha", "fool", "marketwatch"]):
        return "market_media"
    return "web"


def _fallback_rejection(document: FetchedDocument) -> dict[str, object]:
    return {
        "company": document.title or "Unknown",
        "ticker": "UNKNOWN",
        "bottleneck_category": "unclassified",
        "evidence_summary": "No structured evidence extracted.",
        "evidence_snippet": document.clean_text[:240],
        "ai_infra_relevance": 0.0,
        "underfollowed_signal": 0.0,
        "rerated_risk": 0.0,
        "confidence": 0.0,
        "red_flags": ["model_extraction_failed_or_empty"],
        "is_relevant": False,
        "rejection_reason": "No useful evidence found in document.",
    }
