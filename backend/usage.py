"""Token/cost tracking ("tokenomics"). One entry per full boss-agent turn, with
usage summed across every delegated specialist call (see RunContext.usage
threaded through agents/boss.py and agents/treasurer.py)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai.usage import RunUsage

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRICES_PATH = PROJECT_ROOT / "data" / "prices.json"
USAGE_LOG_PATH = PROJECT_ROOT / "output" / "usage_log.json"
PRICE_KEY = "gpt-6-luna"


def compute_cost(usage: RunUsage) -> float:
    prices = json.loads(PRICES_PATH.read_text(encoding="utf-8"))[PRICE_KEY]
    uncached = usage.input_tokens - usage.cache_read_tokens - usage.cache_write_tokens
    total = (
        uncached * prices["input_per_1m"]
        + usage.cache_read_tokens * prices["cached_input_per_1m"]
        + usage.cache_write_tokens * prices["cache_write_per_1m"]
        + usage.output_tokens * prices["output_per_1m"]
    ) / 1_000_000
    return round(total, 6)


def log_usage(user_message: str, usage: RunUsage, cache_hit: bool = False) -> dict:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_message": user_message,
        "cache_hit": cache_hit,
        "requests": usage.requests,
        "input_tokens": usage.input_tokens,
        "cache_read_tokens": usage.cache_read_tokens,
        "cache_write_tokens": usage.cache_write_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": 0.0 if cache_hit else compute_cost(usage),
    }
    USAGE_LOG_PATH.parent.mkdir(exist_ok=True)
    existing = []
    if USAGE_LOG_PATH.exists():
        existing = json.loads(USAGE_LOG_PATH.read_text(encoding="utf-8"))
    existing.append(entry)
    USAGE_LOG_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return entry
