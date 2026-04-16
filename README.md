# Local Research Orchestrator

Local-first, deterministic research pipeline for AI-infrastructure equity discovery using:

- Ollama for local inference
- SearXNG for search
- simple HTTP fetching for cached source collection
- Open WebUI as an optional manual prompt/testing console

## What it does

The v1 pipeline runs fixed stages:

1. Plan bottlenecks, queries, and target evidence types
2. Search via SearXNG
3. Add curated podcast transcript discovery for the past week
4. Fetch and cache page content in `data/documents/`
5. Extract structured evidence via a utility model
6. Score companies with deterministic rules
7. Synthesize a markdown brief

Artifacts are written under `data/runs/<timestamp>/` so each run is inspectable and reproducible.

## Quick start

1. Create a virtual environment and install requirements.
2. Update [`config/settings.yaml`](/Users/commander/Documents/research_orchestration/config/settings.yaml) if your local service URLs, model names, profile, or Ollama timeouts differ.
3. Run:

```bash
python -m app.main
```

You can also override the objective:

```bash
python -m app.main --objective "Find public suppliers of power distribution gear used in AI data center buildouts"
```

You can select a prompt/output profile:

```bash
python -m app.main --profile early_discovery_ai_infra
python -m app.main --profile weekly_scarcity_brief
```

You can run a preflight check for local services:

```bash
python -m app.main --healthcheck
```

## Output

Each run creates:

- `manifest.json`
- `plan.json`
- `search_results.json`
- `podcast_results.json`
- `documents.json`
- `evidence.json`
- `ranked_companies.json`
- `brief.md`
- `artifacts/planner_raw.json`
- `artifacts/extract/*.json`

Fetched documents are cached across runs under [`data/documents`](/Users/commander/Documents/research_orchestration/data/documents).

## Notes

- Open WebUI remains useful for prompt testing, but this app is the system of record.
- The default config expects Ollama at `http://127.0.0.1:11434` and SearXNG at `http://127.0.0.1:8081`. Open WebUI at `http://localhost:3000` is not used as the workflow engine.
- The default Ollama setup uses `gemma4:latest` for planning, `gemma4:26b` for final synthesis, and `gemma4:latest` for utility extraction.
- The pipeline now prints stage progress so you can see whether it is planning, searching, discovering podcast transcripts, fetching, extracting, scoring, or synthesizing.
- Search is biased toward better transcript, IR, filing, and trade-press domains while blocking weak social and aggregator sources.
- Deeper research defaults now use 18 planner queries, 12 search results per query, and up to 36 fetched documents.
- Prompt/result examples from your attached files are now represented as profile-specific prompt templates under [`prompts`](/Users/commander/Documents/research_orchestration/prompts).
- If your local services are not on `http://127.0.0.1:11434` and `http://127.0.0.1:8081`, change them in [`config/settings.yaml`](/Users/commander/Documents/research_orchestration/config/settings.yaml).
