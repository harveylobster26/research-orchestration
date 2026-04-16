from __future__ import annotations

from pathlib import Path

from app.config import AppSettings
from app.models import ExtractionResult
from app.providers.ollama_client import OllamaClient
from app.providers.page_fetcher import PageFetcher
from app.providers.searxng_client import SearxngClient
from app.schemas import PipelineArtifacts, RunManifest
from app.steps.extract import extract_evidence
from app.steps.fetch import fetch_documents
from app.steps.plan import build_plan
from app.steps.score import rank_companies
from app.steps.search import run_search
from app.steps.synthesize import synthesize_brief
from app.utils import build_run_dir, write_json, write_text


class ResearchPipeline:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.ollama = OllamaClient(settings.ollama)
        self.searxng = SearxngClient(settings.searxng)
        self.fetcher = PageFetcher(settings.fetch)

    def run(self, objective: str) -> PipelineArtifacts:
        run_dir = build_run_dir(self.settings.data_path)
        manifest = RunManifest(
            run_id=Path(run_dir).name,
            objective=objective,
            run_dir=str(run_dir),
        )
        write_json(run_dir / "manifest.json", manifest.to_dict())

        plan = build_plan(self.settings, self.ollama, objective)
        write_json(run_dir / "plan.json", plan.to_dict())

        search_results = run_search(plan, self.searxng)
        write_json(run_dir / "search_results.json", [item.to_dict() for item in search_results])

        documents = fetch_documents(
            search_results,
            self.fetcher,
            run_dir / "cache",
            self.settings.fetch,
        )
        write_json(run_dir / "documents.json", [item.to_dict() for item in documents])

        extracted: ExtractionResult = extract_evidence(
            self.settings,
            self.ollama,
            plan,
            documents,
        )
        write_json(
            run_dir / "evidence.json",
            {
                "evidence": [item.to_dict() for item in extracted.evidence],
                "rejected": [item.to_dict() for item in extracted.rejected],
            },
        )

        ranked_companies = rank_companies(extracted.evidence)
        write_json(run_dir / "ranked_companies.json", [item.to_dict() for item in ranked_companies])

        brief = synthesize_brief(
            self.settings,
            self.ollama,
            plan,
            ranked_companies,
            extracted.evidence,
            extracted.rejected,
        )
        brief_path = run_dir / "brief.md"
        write_text(brief_path, brief)

        return PipelineArtifacts(
            manifest=manifest,
            plan=plan,
            search_results=search_results,
            documents=documents,
            evidence=extracted.evidence + extracted.rejected,
            ranked_companies=ranked_companies,
            brief_path=str(brief_path),
        )

    def healthcheck(self) -> list[tuple[str, str]]:
        statuses: list[tuple[str, str]] = []

        try:
            payload = self.ollama.healthcheck()
            models = payload.get("models", [])
            statuses.append(("ollama", f"ok ({len(models)} models visible)"))
        except Exception as exc:
            statuses.append(("ollama", f"error ({exc})"))

        try:
            payload = self.searxng.healthcheck()
            results = payload.get("results", [])
            statuses.append(("searxng", f"ok ({len(results)} sample results returned)"))
        except Exception as exc:
            statuses.append(("searxng", f"error ({exc})"))

        return statuses
