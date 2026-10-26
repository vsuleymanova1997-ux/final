"""A small exact-match response cache so the same question asked twice (very
common for e-board FAQs like "how do I get reimbursed") doesn't cost a fresh model
call. Keyed on the normalized message text — separate from the provider-side
prompt cache pydantic-ai/Portkey already gives you for repeated system prompts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent.parent / "output" / "response_cache.json"


def _key(message: str) -> str:
    normalized = " ".join(message.strip().lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _load() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def get(message: str) -> str | None:
    return _load().get(_key(message))


def set(message: str, reply: str) -> None:
    CACHE_PATH.parent.mkdir(exist_ok=True)
    cache = _load()
    cache[_key(message)] = reply
    CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
