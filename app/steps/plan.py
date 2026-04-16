from __future__ import annotations

from app.config import AppSettings
from app.providers.ollama_client import OllamaClient
from app.schemas import Plan
from app.utils import read_profile_prompt


def build_plan(settings: AppSettings, ollama: OllamaClient, objective: str) -> Plan:
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
    plan = Plan.from_dict(raw)
    if settings.pipeline.max_queries:
        plan.queries = plan.queries[: settings.pipeline.max_queries]
    return plan
