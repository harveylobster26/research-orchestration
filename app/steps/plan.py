from __future__ import annotations

from pathlib import Path

from app.config import AppSettings
from app.providers.ollama_client import OllamaClient
from app.schemas import Plan
from app.utils import read_profile_prompt, write_json


def build_plan(
    settings: AppSettings,
    ollama: OllamaClient,
    objective: str,
    run_dir: Path | None = None,
) -> Plan:
    prompt = read_profile_prompt(
        settings.prompts_path,
        settings.pipeline.profile,
        "planner.md",
    )
    raw = ollama.generate_json(
        f"{prompt}\n\nResearch objective:\n{objective}\n",
        model=settings.ollama.planning_model,
        temperature=0.1,
        timeout_seconds=settings.ollama.main_timeout_seconds,
    )
    if run_dir is not None:
        write_json(run_dir / 'artifacts' / 'planner_raw.json', raw)
    plan = Plan.from_dict(raw)
    plan.queries = _expand_queries(plan, settings.pipeline.min_queries, settings.pipeline.max_queries)
    return plan


def _expand_queries(plan: Plan, min_queries: int, max_queries: int) -> list[str]:
    queries = _dedupe(plan.queries)
    if len(queries) >= min_queries:
        return queries[:max_queries]

    default_bottlenecks = [
        "power delivery",
        "liquid cooling",
        "optical interconnects",
        "packaging",
        "site enablement",
    ]
    bottlenecks = _dedupe(plan.bottlenecks + default_bottlenecks)
    fallback_templates = [
        '{bottleneck} public company earnings transcript AI data center',
        '{bottleneck} investor presentation backlog AI data center public company',
        '{bottleneck} trade press lead times AI infrastructure public company',
        '{bottleneck} supplier public company conference transcript AI infrastructure',
    ]
    generic_queries = [
        "AI infrastructure bottleneck public company earnings transcript",
        "AI data center supplier backlog public company transcript",
        "AI infrastructure podcast transcript public company supply chain",
        "data center power cooling supplier public company investor presentation",
    ]

    for bottleneck in bottlenecks:
        for template in fallback_templates:
            queries.append(template.format(bottleneck=bottleneck))
            queries = _dedupe(queries)
            if len(queries) >= min_queries:
                return queries[:max_queries]

    for query in generic_queries:
        queries.append(query)
        queries = _dedupe(queries)
        if len(queries) >= min_queries:
            return queries[:max_queries]

    return queries[:max_queries]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        normalized = item.strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        output.append(normalized)
    return output
