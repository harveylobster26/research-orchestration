from __future__ import annotations

from datetime import datetime, timezone

from app.providers.searxng_client import SearxngClient
from app.schemas import SearchBatch, SearchResult


_PODCAST_SOURCES = [
    {
        "label": "Dwarkesh Podcast",
        "queries": [
            'site:dwarkesh.com/p transcript',
            'site:dwarkesh.com/p podcast',
            'site:dwarkesh.com/p "Dwarkesh Patel"',
            '"Dwarkesh Podcast" transcript',
        ],
    },
    {
        "label": "AI + a16z",
        "queries": [
            'site:a16z.com/podcast "AI + a16z"',
            'site:a16z.com/podcast "AI + a16z" transcript',
            'site:a16z.com/podcast a16z ai',
            '"AI + a16z" transcript',
        ],
    },
    {
        "label": "a16z Show",
        "queries": [
            'site:a16z.com/podcast "a16z"',
            'site:a16z.com/podcast transcript a16z',
            'site:a16z.com/podcast AI infrastructure a16z',
            '"a16z Show" transcript',
        ],
    },
    {
        "label": "Latent Space",
        "queries": [
            '"Latent Space" transcript',
            '"Latent Space" podcast transcript',
            '"Latent Space" AI podcast',
            '"Latent Space" full transcript',
        ],
    },
    {
        "label": "Lex Fridman",
        "queries": [
            'site:lexfridman.com transcript',
            'site:lexfridman.com podcast transcript',
            'site:lexfridman.com AI transcript',
            '"Lex Fridman Podcast" transcript',
        ],
    },
    {
        "label": "The Cognitive Revolution",
        "queries": [
            '"The Cognitive Revolution" transcript',
            '"The Cognitive Revolution" podcast transcript',
            '"The Cognitive Revolution" AI podcast',
            '"The Cognitive Revolution" full transcript',
        ],
    },
    {
        "label": "No Priors",
        "queries": [
            '"No Priors" transcript',
            '"No Priors" podcast transcript',
            '"No Priors" AI podcast',
            '"No Priors" full transcript',
        ],
    },
    {
        "label": "Anthony Pompliano",
        "queries": [
            '"Anthony Pompliano" podcast transcript',
            '"The Pomp Podcast" transcript',
            '"Anthony Pompliano" AI podcast',
            '"Pomp Podcast" full transcript',
        ],
    },
    {
        "label": "Moonshots",
        "queries": [
            '"Moonshots with Peter Diamandis" transcript',
            '"Moonshots" "Peter Diamandis" transcript',
            '"Moonshots" podcast Peter Diamandis',
            '"Moonshots with Peter Diamandis" full transcript',
        ],
    },
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
        label = source["label"]
        results: list[SearchResult] = []
        seen_urls: set[str] = set()
        queries_run: list[str] = []

        for base_query in source["queries"]:
            for query, time_range in _query_variants(base_query, month_name, year):
                rendered = query if time_range else f"{query} [no-time-filter]"
                if rendered in queries_run:
                    continue
                queries_run.append(rendered)
                batch = searxng.search(query, limit=8, time_range=time_range)
                for item in _prioritize_transcript_results(batch.results):
                    if item.url in seen_urls:
                        continue
                    seen_urls.add(item.url)
                    results.append(item)

        batches.append(
            SearchBatch(
                query=f"[podcast] {label}: {' || '.join(queries_run)}",
                results=results[:12],
            )
        )

    return batches


def _query_variants(base_query: str, month_name: str, year: str) -> list[tuple[str, str | None]]:
    return [
        (f"{base_query} {month_name} {year}", "week"),
        (base_query, "week"),
        (f"{base_query} latest episode transcript", "week"),
        (f"{base_query} {year}", None),
        (f"{base_query} full transcript", None),
    ]


def _prioritize_transcript_results(results: list[SearchResult]) -> list[SearchResult]:
    return sorted(results, key=_result_priority, reverse=True)


def _result_priority(result: SearchResult) -> tuple[int, int, int]:
    haystack = " ".join(
        [
            result.title.lower(),
            result.snippet.lower(),
            result.source_domain.lower(),
        ]
    )
    transcript_score = sum(1 for hint in _TRANSCRIPT_HINTS if hint in haystack)
    direct_transcript_bonus = 1 if "transcript" in result.title.lower() or "transcript" in result.url.lower() else 0
    return (transcript_score, direct_transcript_bonus, len(result.snippet))
