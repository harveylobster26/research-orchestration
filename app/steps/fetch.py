from __future__ import annotations

from pathlib import Path

from app.config import FetchSettings
from app.providers.page_fetcher import PageFetcher
from app.schemas import FetchedDocument, SearchBatch


def fetch_documents(
    search_batches: list[SearchBatch],
    fetcher: PageFetcher,
    cache_dir: Path,
    settings: FetchSettings,
    max_documents: int | None = None,
) -> list[FetchedDocument]:
    documents: list[FetchedDocument] = []
    seen_urls: set[str] = set()
    limit = settings.max_documents if max_documents is None else max_documents

    for batch in search_batches:
        for result in batch.results:
            if result.url in seen_urls:
                continue
            seen_urls.add(result.url)
            try:
                documents.append(fetcher.fetch(result, cache_dir))
            except Exception:
                continue
            if len(documents) >= limit:
                return documents

    return documents
