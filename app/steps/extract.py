from __future__ import annotations

from pathlib import Path

from app.config import AppSettings
from app.models import ExtractionResult
from app.providers.ollama_client import OllamaClient
from app.schemas import Evidence, FetchedDocument, Plan
from app.utils import domain_for_url, read_profile_prompt, slugify, write_json


def extract_evidence(
    settings: AppSettings,
    ollama: OllamaClient,
    plan: Plan,
    documents: list[FetchedDocument],
    run_dir: Path | None = None,
) -> ExtractionResult:
    prompt_template = read_profile_prompt(
        settings.prompts_path,
        settings.pipeline.profile,
        "extractor.md",
    )
    evidence: list[Evidence] = []
    rejected: list[Evidence] = []
    query_context = ", ".join(plan.queries)

    for index, document in enumerate(documents, start=1):
        print(f"[pipeline] extract document {index}/{len(documents)}: {document.title or document.url}", flush=True)
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
        artifact_name = f"{index:03d}-{slugify(document.title or document.url, 60)}"
        artifact_dir = run_dir / 'artifacts' / 'extract' if run_dir is not None else None
        try:
            raw = ollama.generate_json(
                prompt,
                model=settings.ollama.utility_model,
                temperature=0.0,
                timeout_seconds=settings.ollama.utility_timeout_seconds,
            )
            if artifact_dir is not None:
                write_json(artifact_dir / f'{artifact_name}.json', raw)
            items = raw.get("evidence") or [_fallback_rejection(document)]
        except Exception as exc:
            print(
                f"[pipeline] extract warning for document {index}/{len(documents)}: {exc}",
                flush=True,
            )
            failure_payload = {"error": str(exc), "url": document.url, "title": document.title}
            if artifact_dir is not None:
                write_json(artifact_dir / f'{artifact_name}.error.json', failure_payload)
            items = [_fallback_rejection(document, reason=str(exc))]

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


def _fallback_rejection(document: FetchedDocument, reason: str | None = None) -> dict[str, object]:
    rejection_reason = reason or "No useful evidence found in document."
    flags = ["model_extraction_failed_or_empty"]
    if reason:
        flags.append(f"parse_error: {reason[:200]}")
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
        "red_flags": flags,
        "is_relevant": False,
        "rejection_reason": rejection_reason,
    }
