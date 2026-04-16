from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify(value: str, limit: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug[:limit] or "item"


def hash_text(value: str, length: int = 12) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def build_run_dir(data_dir: Path) -> Path:
    return ensure_dir(data_dir / "runs" / utc_timestamp())


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text)


def read_prompt(path: Path) -> str:
    return path.read_text().strip()


def read_profile_prompt(prompts_dir: Path, profile: str, name: str) -> str:
    candidate = prompts_dir / profile / name
    if candidate.exists():
        return read_prompt(candidate)
    return read_prompt(prompts_dir / name)


def domain_for_url(url: str) -> str:
    return urlparse(url).netloc.lower()
