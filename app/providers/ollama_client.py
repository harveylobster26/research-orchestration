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
        timeout_seconds: int | None = None,
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
                timeout=timeout_seconds or self.settings.utility_timeout_seconds,
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
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        attempts = [
            prompt,
            prompt
            + "\n\nIMPORTANT: Return exactly one valid JSON object. "
            + "Do not include markdown fences, commentary, or trailing text.",
        ]
        last_error: Exception | None = None
        last_raw = ""
        for attempt_prompt in attempts:
            raw = self.generate(
                attempt_prompt,
                model=model,
                format_json=True,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
            )
            last_raw = raw
            try:
                parsed = _parse_json_object(raw)
                if isinstance(parsed, dict):
                    return parsed
                raise RuntimeError("Model returned a JSON value that is not an object.")
            except Exception as exc:
                last_error = exc

        detail = str(last_error) if last_error else "unknown parse error"
        sample = last_raw[:400].replace("\n", " ")
        raise RuntimeError(f"Failed to parse JSON from Ollama response: {detail}. Response preview: {sample}")

    def healthcheck(self) -> dict[str, Any]:
        try:
            return _get_json_with_local_fallback(
                f"{self.settings.base_url.rstrip('/')}/api/tags",
                timeout=min(self.settings.utility_timeout_seconds, 10),
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


def _parse_json_object(raw: str) -> Any:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            text = "\n".join(lines[1:-1]).strip()

    for candidate in _json_candidates(text):
        normalized = _normalize_json(candidate)
        try:
            return json.loads(normalized)
        except json.JSONDecodeError:
            continue

    raise RuntimeError("No valid JSON object found in model response.")


def _json_candidates(text: str) -> list[str]:
    candidates: list[str] = [text]
    extracted = _extract_balanced_json(text)
    if extracted and extracted not in candidates:
        candidates.append(extracted)
    return candidates


def _extract_balanced_json(text: str) -> str | None:
    start = -1
    opening = ""
    for idx, char in enumerate(text):
        if char in "[{":
            start = idx
            opening = char
            break
    if start < 0:
        return None

    closing = "}" if opening == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        char = text[idx]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start : idx + 1]

    return None


def _normalize_json(text: str) -> str:
    replacements = {
        "“": '"',
        "”": '"',
        "’": "'",
        "‘": "'",
        " ": " ",
    }
    normalized = text
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized.strip()
