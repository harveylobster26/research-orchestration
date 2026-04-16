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
3. Fetch and cache page content
4. Extract structured evidence via a utility model
5. Score companies with deterministic rules
6. Synthesize a markdown brief

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
- cached HTML/text documents
- `evidence.json`
- `ranked_companies.json`
- `brief.md`

## Notes

- Open WebUI remains useful for prompt testing, but this app is the system of record.
- The default config expects Ollama at `http://127.0.0.1:11434` and SearXNG at `http://127.0.0.1:8081`. Open WebUI at `http://localhost:3000` is not used as the workflow engine.
- The default Ollama setup uses `gemma4:latest` for planning, `gemma4:26b` for final synthesis, and `gemma4:latest` for utility extraction.
- The pipeline now prints stage progress so you can see whether it is planning, searching, fetching, extracting, scoring, or synthesizing.
- The pipeline prefers deterministic fallbacks when model output is malformed so runs stay debuggable.
- Prompt/result examples from your attached files are now represented as profile-specific prompt templates under [`prompts`](/Users/commander/Documents/research_orchestration/prompts).
- If your local services are not on `http://127.0.0.1:11434` and `http://127.0.0.1:8081`, change them in [`config/settings.yaml`](/Users/commander/Documents/research_orchestration/config/settings.yaml).
