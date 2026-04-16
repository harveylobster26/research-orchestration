from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class OllamaSettings:
    base_url: str = "http://127.0.0.1:11434"
    planning_model: str = "gemma4:latest"
    main_model: str = "gemma4:26b"
    utility_model: str = "gemma4:latest"
    main_timeout_seconds: int = 1800
    utility_timeout_seconds: int = 600
    temperature: float = 0.1


@dataclass
class SearxngSettings:
    base_url: str = "http://127.0.0.1:8081"
    default_engines: list[str] = field(default_factory=list)
    language: str = "en-US"
    results_per_query: int = 12
    safe_search: int = 0
    timeout_seconds: int = 30
    preferred_domains: list[str] = field(
        default_factory=lambda: [
            "sec.gov",
            "reuters.com",
            "investor",
            "ir.",
            "seekingalpha.com",
            "fool.com",
            "zacks.com",
            "marketbeat.com",
            "powermag.com",
            "semiengineering.com",
            "eetimes.com",
            "tomshardware.com",
            "networkworld.com",
            "datacenterdynamics.com",
            "manufacturingdive.com",
            "dwarkesh.com",
            "lexfridman.com",
            "a16z.com",
        ]
    )
    blocked_domains: list[str] = field(
        default_factory=lambda: [
            "facebook.com",
            "instagram.com",
            "tiktok.com",
            "reddit.com",
            "x.com",
            "twitter.com",
            "linkedin.com",
            "academia.edu",
            "issuu.com",
        ]
    )


@dataclass
class FetchSettings:
    user_agent: str = "local-research-orchestrator/0.1"
    timeout_seconds: int = 30
    max_documents: int = 36
    podcast_max_documents: int = 12
    max_chars_per_document: int = 20000


@dataclass
class PipelineSettings:
    objective: str = (
        "Find underfollowed public companies that benefit from AI infrastructure "
        "bottlenecks, gather evidence, rank candidates, reject weak ideas, and "
        "produce a markdown brief."
    )
    min_queries: int = 18
    max_queries: int = 18
    critique_enabled: bool = False
    profile: str = "early_discovery_ai_infra"


@dataclass
class AppSettings:
    ollama: OllamaSettings = field(default_factory=OllamaSettings)
    searxng: SearxngSettings = field(default_factory=SearxngSettings)
    fetch: FetchSettings = field(default_factory=FetchSettings)
    pipeline: PipelineSettings = field(default_factory=PipelineSettings)
    data_dir: str = "data"
    prompts_dir: str = "prompts"

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir)

    @property
    def prompts_path(self) -> Path:
        return Path(self.prompts_dir)


def load_settings(path: str | Path = "config/settings.yaml") -> AppSettings:
    config_path = Path(path)
    if not config_path.exists():
        return AppSettings()

    raw = _load_mapping(config_path)
    return AppSettings(
        ollama=OllamaSettings(**raw.get("ollama", {})),
        searxng=SearxngSettings(**raw.get("searxng", {})),
        fetch=FetchSettings(**raw.get("fetch", {})),
        pipeline=PipelineSettings(**raw.get("pipeline", {})),
        data_dir=raw.get("data_dir", "data"),
        prompts_dir=raw.get("prompts_dir", "prompts"),
    )


def _load_mapping(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text())
    return _parse_simple_yaml(path.read_text())


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            continue

        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        current = stack[-1][1]

        if raw_value == "":
            child: dict[str, Any] = {}
            current[key] = child
            stack.append((indent, child))
            continue

        current[key] = _parse_scalar(raw_value)

    return root


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"[]", "{}"}:
        return ast.literal_eval(lowered)
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value
