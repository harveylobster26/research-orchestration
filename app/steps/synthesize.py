from __future__ import annotations

import json

from app.config import AppSettings
from app.providers.ollama_client import OllamaClient
from app.schemas import Evidence, Plan, RankedCompany
from app.utils import read_profile_prompt


def synthesize_brief(
    settings: AppSettings,
    ollama: OllamaClient,
    plan: Plan,
    ranked_companies: list[RankedCompany],
    evidence: list[Evidence],
    rejected: list[Evidence],
) -> str:
    prompt = read_profile_prompt(
        settings.prompts_path,
        settings.pipeline.profile,
        "synthesizer.md",
    )
    payload = {
        "plan": plan.to_dict(),
        "ranked_companies": [item.to_dict() for item in ranked_companies],
        "evidence": [item.to_dict() for item in evidence],
        "rejected": [item.to_dict() for item in rejected],
    }
    return ollama.generate(
        f"{prompt}\n\nArtifacts:\n{json.dumps(payload, indent=2)}",
        model=settings.ollama.main_model,
        temperature=0.1,
    )
