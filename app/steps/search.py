from __future__ import annotations

from app.providers.searxng_client import SearxngClient
from app.schemas import Plan, SearchBatch


def run_search(plan: Plan, searxng: SearxngClient) -> list[SearchBatch]:
    return [searxng.search(query) for query in plan.queries]
