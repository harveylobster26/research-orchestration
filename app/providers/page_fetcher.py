from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from app.config import FetchSettings
from app.schemas import FetchedDocument, SearchResult
from app.utils import ensure_dir, hash_text, slugify


class PageFetcher:
    def __init__(self, settings: FetchSettings) -> None:
        self.settings = settings

    def fetch(self, result: SearchResult, cache_dir: Path) -> FetchedDocument:
        req = Request(result.url, headers={"User-Agent": self.settings.user_agent})
        with urlopen(req, timeout=self.settings.timeout_seconds) as response:
            content_type = response.headers.get_content_type()
            html = response.read().decode("utf-8", errors="replace")

        clean_text = clean_html_text(html)[: self.settings.max_chars_per_document]
        doc_key = f"{slugify(result.title, 40)}-{hash_text(result.url)}"
        raw_path = ensure_dir(cache_dir / "raw") / f"{doc_key}.html"
        clean_path = ensure_dir(cache_dir / "clean") / f"{doc_key}.txt"
        raw_path.write_text(html)
        clean_path.write_text(clean_text)

        return FetchedDocument(
            url=result.url,
            title=result.title,
            raw_html_path=str(raw_path),
            clean_text_path=str(clean_path),
            clean_text=clean_text,
            content_type=content_type,
        )


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self.parts.append(data.strip())


def clean_html_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = " ".join(parser.parts)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
