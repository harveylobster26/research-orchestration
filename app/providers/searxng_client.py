from __future__ import annotations

import json
from urllib.parse import urlencode, urlparse
from urllib.request import urlopen
from urllib.parse import urlparse as parse_url, urlunparse

from app.config import SearxngSettings
from app.schemas import SearchBatch, SearchResult


class SearxngClient:
    def __init__(self, settings: SearxngSettings) -> None:
        self.settings = settings

    def search(self, query: str, limit: int | None = None) -> SearchBatch:
        params = {
            "q": query,
            "format": "json",
            "language": self.settings.language,
            "safesearch": self.settings.safe_search,
        }
        if self.settings.default_engines:
            params["engines"] = ",".join(self.settings.default_engines)

        url = f"{self.settings.base_url.rstrip('/')}/search?{urlencode(params)}"
        try:
            payload = _get_json_with_local_fallback(url, timeout=self.settings.timeout_seconds)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to reach SearXNG at {self.settings.base_url}. "
                "Update config/settings.yaml if your SearXNG endpoint uses a different host or port."
            ) from exc

        candidates: list[SearchResult] = []
        seen_urls: set[str] = set()
        for item in payload.get("results", []):
            raw_url = str(item.get("url", "")).strip()
            if not raw_url or raw_url in seen_urls:
                continue
            seen_urls.add(raw_url)
            result = SearchResult(
                title=str(item.get("title", "")).strip() or raw_url,
                url=raw_url,
                snippet=str(item.get("content", "")).strip(),
                source_domain=urlparse(raw_url).netloc.lower(),
            )
            if self._blocked(result.source_domain):
                continue
            candidates.append(result)

        candidates.sort(key=lambda item: self._score_result(item), reverse=True)
        max_results = limit or self.settings.results_per_query
        return SearchBatch(query=query, results=candidates[:max_results])

    def healthcheck(self) -> dict:
        params = {
            "q": "test",
            "format": "json",
            "language": self.settings.language,
            "safesearch": self.settings.safe_search,
        }
        if self.settings.default_engines:
            params["engines"] = ",".join(self.settings.default_engines)

        url = f"{self.settings.base_url.rstrip('/')}/search?{urlencode(params)}"
        try:
            return _get_json_with_local_fallback(url, timeout=min(self.settings.timeout_seconds, 10))
        except Exception as exc:
            raise RuntimeError(
                f"Unable to reach SearXNG at {self.settings.base_url}. "
                "Update config/settings.yaml if your SearXNG endpoint uses a different host or port."
            ) from exc

    def _blocked(self, domain: str) -> bool:
        return any(token in domain for token in self.settings.blocked_domains)

    def _score_result(self, result: SearchResult) -> int:
        domain = result.source_domain
        title = result.title.lower()
        snippet = result.snippet.lower()
        score = 0

        if any(token in domain for token in self.settings.preferred_domains):
            score += 8
        if any(token in domain for token in ["investor", "ir.", "sec.gov"]):
            score += 6
        if any(token in title for token in ["earnings", "transcript", "investor", "conference", "presentation", "backlog", "orders"]):
            score += 5
        if any(token in snippet for token in ["backlog", "lead time", "orders", "liquid cooling", "switchgear", "transformer", "optical", "transceiver"]):
            score += 3
        if any(token in domain for token in ["arxiv.org", "nature.com", "mdpi.com", "science.gov", "sciencedirect.com", "springer.com"]):
            score -= 4
        if any(token in title for token in ["topics by", "abstract book", "issue", "market report"]):
            score -= 5

        return score


def _get_json_with_local_fallback(url: str, timeout: int) -> dict:
    last_exc: Exception | None = None
    for candidate in _candidate_local_urls(url):
        try:
            with urlopen(candidate, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def _candidate_local_urls(url: str) -> list[str]:
    parsed = parse_url(url)
    host = parsed.hostname
    if host not in {"localhost", "127.0.0.1"}:
        return [url]

    candidates = [url]
    alternate_host = "127.0.0.1" if host == "localhost" else "localhost"
    if parsed.netloc:
        alternate_netloc = parsed.netloc.replace(host, alternate_host, 1)
        alternate = urlunparse(parsed._replace(netloc=alternate_netloc))
        if alternate not in candidates:
            candidates.append(alternate)
    return candidates
