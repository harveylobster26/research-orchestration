from __future__ import annotations

import json
from typing import Any
from urllib import error, request
from urllib.parse import urlparse, urlunparse

from app.config import OllamaSettings


class OllamaClient:
    def __init__(self, settings: OllamaSettings) -> None:
        self.settings = settings

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        format_json: bool = False,
        temperature: float | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model or self.settings.main_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.settings.temperature if temperature is None else temperature,
            },
        }
        if format_json:
            payload["format"] = "json"

        try:
            raw = _post_json_with_local_fallback(
                f"{self.settings.base_url.rstrip('/')}/api/generate",
                payload,
                timeout=self.settings.timeout_seconds,
            )
        except Exception as exc:
            detail = str(exc) or exc.__class__.__name__
            raise RuntimeError(
                f"Unable to reach Ollama at {self.settings.base_url}. "
                f"Generation request failed: {detail}"
            ) from exc
        return str(raw.get("response", "")).strip()

    def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        raw = self.generate(
            prompt,
            model=model,
            format_json=True,
            temperature=temperature,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                return json.loads(raw[start : end + 1])
            raise

    def healthcheck(self) -> dict[str, Any]:
        try:
            return _get_json_with_local_fallback(
                f"{self.settings.base_url.rstrip('/')}/api/tags",
                timeout=min(self.settings.timeout_seconds, 10),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Unable to reach Ollama at {self.settings.base_url}. "
                "Update config/settings.yaml if your Ollama endpoint uses a different host or port."
            ) from exc


def _post_json(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def _get_json(url: str, timeout: int) -> dict[str, Any]:
    req = request.Request(url, method="GET")
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json_with_local_fallback(url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    last_exc: Exception | None = None
    for candidate in _candidate_local_urls(url):
        try:
            return _post_json(candidate, payload, timeout)
        except Exception as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def _get_json_with_local_fallback(url: str, timeout: int) -> dict[str, Any]:
    last_exc: Exception | None = None
    for candidate in _candidate_local_urls(url):
        try:
            return _get_json(candidate, timeout)
        except Exception as exc:
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def _candidate_local_urls(url: str) -> list[str]:
    parsed = urlparse(url)
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
