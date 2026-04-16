from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from app.providers.searxng_client import SearxngClient
from app.schemas import SearchBatch, SearchResult


@dataclass(frozen=True)
class PodcastSource:
    label: str
    queries: list[str]
    seed_urls: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    required_url_tokens: list[str] = field(default_factory=list)
    title_hints: list[str] = field(default_factory=list)
    exclude_url_tokens: list[str] = field(default_factory=list)


_PODCAST_SOURCES = [
    PodcastSource(
        label="Dwarkesh Podcast",
        queries=[
            'site:dwarkesh.com/p transcript',
            'site:dwarkesh.com/p podcast',
            'site:dwarkesh.com/p "Dwarkesh Patel"',
            '"Dwarkesh Podcast" transcript',
        ],
        seed_urls=[
            "https://www.dwarkesh.com/archive",
            "https://www.dwarkesh.com/",
        ],
        allowed_domains=["dwarkesh.com"],
        required_url_tokens=["/p/"],
        title_hints=["dwarkesh", "podcast", "jensen", "episode"],
        exclude_url_tokens=["/t/", "/about", "/archive", "/comments"],
    ),
    PodcastSource(
        label="AI + a16z",
        queries=[
            'site:a16z.com/podcast "AI + a16z"',
            'site:a16z.com/podcast "AI + a16z" transcript',
            'site:a16z.com/podcast a16z ai',
            '"AI + a16z" transcript',
        ],
        seed_urls=[
            "https://a16z.com/ai/",
            "https://a16z.com/podcasts/ai-a16z/",
        ],
        allowed_domains=["a16z.com"],
        required_url_tokens=["/podcast/"],
        title_hints=["ai + a16z", "a16z", "podcast", "ai"],
        exclude_url_tokens=["/tag/", "/author/", "/category/"],
    ),
    PodcastSource(
        label="a16z Show",
        queries=[
            'site:a16z.com/podcast "a16z"',
            'site:a16z.com/podcast transcript a16z',
            'site:a16z.com/podcast AI infrastructure a16z',
            '"a16z Show" transcript',
        ],
        seed_urls=[
            "https://a16z.com/podcasts/",
        ],
        allowed_domains=["a16z.com"],
        required_url_tokens=["/podcast/"],
        title_hints=["a16z", "podcast", "show"],
        exclude_url_tokens=["/tag/", "/author/", "/category/"],
    ),
    PodcastSource(
        label="Latent Space",
        queries=[
            '"Latent Space" transcript',
            '"Latent Space" podcast transcript',
            '"Latent Space" AI podcast',
            '"Latent Space" full transcript',
        ],
        seed_urls=[
            "https://www.latent.space/",
        ],
        allowed_domains=["latent.space"],
        required_url_tokens=["/p/"],
        title_hints=["latent space", "podcast", "transcript", "episode"],
        exclude_url_tokens=["/about", "/archive", "/tag/"],
    ),
    PodcastSource(
        label="Lex Fridman",
        queries=[
            'site:lexfridman.com transcript',
            'site:lexfridman.com podcast transcript',
            'site:lexfridman.com AI transcript',
            '"Lex Fridman Podcast" transcript',
        ],
        seed_urls=[
            "https://lexfridman.com/category/transcripts/",
        ],
        allowed_domains=["lexfridman.com"],
        required_url_tokens=["transcript"],
        title_hints=["transcript", "lex fridman", "podcast"],
        exclude_url_tokens=["/category/", "/about", "/sponsors"],
    ),
    PodcastSource(
        label="The Cognitive Revolution",
        queries=[
            '"The Cognitive Revolution" transcript',
            '"The Cognitive Revolution" podcast transcript',
            '"The Cognitive Revolution" AI podcast',
            '"The Cognitive Revolution" full transcript',
        ],
        seed_urls=[
            "https://www.cognitiverevolution.ai/",
        ],
        allowed_domains=["cognitiverevolution.ai"],
        required_url_tokens=["/"],
        title_hints=["cognitive revolution", "podcast", "episode", "transcript"],
        exclude_url_tokens=["/about", "/subscribe", "/privacy", "/terms"],
    ),
    PodcastSource(
        label="No Priors",
        queries=[
            '"No Priors" transcript',
            '"No Priors" podcast transcript',
            '"No Priors" AI podcast',
            '"No Priors" full transcript',
        ],
        seed_urls=[
            "https://www.nopriors.com/",
        ],
        allowed_domains=["nopriors.com"],
        required_url_tokens=["/"],
        title_hints=["no priors", "podcast", "episode", "transcript"],
        exclude_url_tokens=["/about", "/subscribe", "/privacy", "/terms"],
    ),
    PodcastSource(
        label="Anthony Pompliano",
        queries=[
            '"Anthony Pompliano" podcast transcript',
            '"The Pomp Podcast" transcript',
            '"Anthony Pompliano" AI podcast',
            '"Pomp Podcast" full transcript',
        ],
        seed_urls=[
            "https://anthonypompliano.com/podcast",
            "https://anthonypompliano.com/",
        ],
        allowed_domains=["anthonypompliano.com"],
        required_url_tokens=["podcast"],
        title_hints=["pomp", "podcast", "anthony pompliano", "episode"],
        exclude_url_tokens=["/about", "/contact", "/privacy", "/terms"],
    ),
    PodcastSource(
        label="Moonshots",
        queries=[
            '"Moonshots with Peter Diamandis" transcript',
            '"Moonshots" "Peter Diamandis" transcript',
            '"Moonshots" podcast Peter Diamandis',
            '"Moonshots with Peter Diamandis" full transcript',
        ],
        seed_urls=[
            "https://www.diamandis.com/podcast",
            "https://www.diamandis.com/",
        ],
        allowed_domains=["diamandis.com"],
        required_url_tokens=["podcast"],
        title_hints=["moonshots", "diamandis", "podcast", "episode"],
        exclude_url_tokens=["/about", "/contact", "/privacy", "/terms"],
    ),
]

_TRANSCRIPT_HINTS = (
    "transcript",
    "podcast",
    "episode",
    "show notes",
    "full text",
)


def discover_podcast_transcripts(searxng: SearxngClient) -> list[SearchBatch]:
    batches: list[SearchBatch] = []
    now = datetime.now(timezone.utc)
    month_name = now.strftime("%B")
    year = now.strftime("%Y")

    for source in _PODCAST_SOURCES:
        results: list[SearchResult] = []
        seen_urls: set[str] = set()
        discovery_notes: list[str] = []

        seed_results = _discover_from_seed_pages(source)
        if seed_results:
            discovery_notes.append(f"seed:{len(seed_results)}")
        _merge_results(results, seen_urls, seed_results)

        search_results, queries_run = _discover_from_search(source, searxng, month_name, year)
        discovery_notes.extend(queries_run)
        _merge_results(results, seen_urls, search_results)

        batches.append(
            SearchBatch(
                query=f"[podcast] {source.label}: {' || '.join(discovery_notes)}",
                results=results[:12],
            )
        )

    return batches


def _discover_from_search(
    source: PodcastSource,
    searxng: SearxngClient,
    month_name: str,
    year: str,
) -> tuple[list[SearchResult], list[str]]:
    results: list[SearchResult] = []
    seen_urls: set[str] = set()
    queries_run: list[str] = []

    for base_query in source.queries:
        for query, time_range in _query_variants(base_query, month_name, year):
            rendered = query if time_range else f"{query} [no-time-filter]"
            if rendered in queries_run:
                continue
            queries_run.append(rendered)
            try:
                batch = searxng.search(query, limit=8, time_range=time_range)
            except Exception:
                continue
            ranked = _prioritize_transcript_results(batch.results, source)
            for item in ranked:
                if item.url in seen_urls:
                    continue
                seen_urls.add(item.url)
                results.append(item)

    return results[:12], queries_run


def _query_variants(base_query: str, month_name: str, year: str) -> list[tuple[str, str | None]]:
    return [
        (f"{base_query} {month_name} {year}", "week"),
        (base_query, "week"),
        (f"{base_query} latest episode transcript", "week"),
        (f"{base_query} {year}", None),
        (f"{base_query} full transcript", None),
    ]


def _discover_from_seed_pages(source: PodcastSource) -> list[SearchResult]:
    results: list[SearchResult] = []
    seen_urls: set[str] = set()

    for seed_url in source.seed_urls:
        try:
            html = _fetch_html(seed_url)
        except Exception:
            continue
        parser = _LinkParser()
        parser.feed(html)
        for href, text in parser.links:
            absolute_url = urljoin(seed_url, href)
            if not _candidate_allowed(absolute_url, text, source):
                continue
            if absolute_url in seen_urls:
                continue
            seen_urls.add(absolute_url)
            title = _clean_anchor_text(text) or absolute_url
            results.append(
                SearchResult(
                    title=title,
                    url=absolute_url,
                    snippet=f"discovered from {seed_url}",
                    source_domain=urlparse(absolute_url).netloc.lower(),
                )
            )

    return _prioritize_transcript_results(results, source)[:12]


def _merge_results(
    destination: list[SearchResult],
    seen_urls: set[str],
    new_results: list[SearchResult],
) -> None:
    for item in new_results:
        if item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        destination.append(item)


def _candidate_allowed(url: str, text: str, source: PodcastSource) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False

    domain = parsed.netloc.lower()
    if source.allowed_domains and not any(token in domain for token in source.allowed_domains):
        return False

    normalized_url = url.lower()
    if any(token in normalized_url for token in source.exclude_url_tokens):
        return False

    if source.required_url_tokens and not any(token in normalized_url for token in source.required_url_tokens):
        return False

    clean_text = _clean_anchor_text(text).lower()
    if not clean_text:
        return False

    low_signal = {
        "about",
        "contact",
        "privacy",
        "terms",
        "subscribe",
        "sign in",
        "sign up",
        "home",
        "archive",
    }
    if clean_text in low_signal:
        return False

    return True


def _prioritize_transcript_results(results: list[SearchResult], source: PodcastSource) -> list[SearchResult]:
    ranked = sorted(results, key=lambda item: _result_priority(item, source), reverse=True)
    return [item for item in ranked if _result_priority(item, source)[0] > 0]


def _result_priority(result: SearchResult, source: PodcastSource) -> tuple[int, int, int, int]:
    title = result.title.lower()
    snippet = result.snippet.lower()
    url = result.url.lower()
    haystack = " ".join([title, snippet, result.source_domain.lower(), url])

    transcript_score = sum(1 for hint in _TRANSCRIPT_HINTS if hint in haystack)
    title_hint_score = sum(1 for hint in source.title_hints if hint in haystack)
    required_token_score = sum(1 for token in source.required_url_tokens if token in url)
    direct_transcript_bonus = 2 if "transcript" in title or "transcript" in url else 0
    discovered_from_seed_bonus = 1 if "discovered from" in snippet else 0

    return (
        transcript_score + title_hint_score + required_token_score + direct_transcript_bonus + discovered_from_seed_bonus,
        title_hint_score,
        direct_transcript_bonus,
        len(snippet),
    )


def _fetch_html(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "local-research-orchestrator/0.1",
        },
    )
    with urlopen(req, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _clean_anchor_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self._current_href = href
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None and data.strip():
            self._current_text.append(data.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or self._current_href is None:
            return
        text = " ".join(self._current_text).strip()
        self.links.append((self._current_href, text))
        self._current_href = None
        self._current_text = []
