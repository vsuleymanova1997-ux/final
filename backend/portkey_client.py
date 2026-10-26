"""Shared Portkey-routed OpenAI-compatible model client, per project convention."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# override=True on both loads, in "furthest first" order, so these two .env files are
# always authoritative over whatever happened to already be in the shell's environment
# (e.g. an unrelated PORTKEY_API_KEY a grader's own shell profile exports) — the repo's
# own .env is loaded last, so it still wins over the one in the folder above it.
load_dotenv(PROJECT_ROOT.parent / ".env", override=True)
load_dotenv(PROJECT_ROOT / ".env", override=True)

PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY") or os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-6-luna")
BASE_URL = os.getenv("BASE_URL", "https://api.portkey.ai/v1")

if not PORTKEY_API_KEY:
    raise RuntimeError(
        "No PORTKEY_API_KEY or OPENAI_API_KEY found in this folder's .env or the folder above it."
    )


def get_model() -> OpenAIChatModel:
    return OpenAIChatModel(
        MODEL_NAME,
        provider=OpenAIProvider(base_url=BASE_URL, api_key=PORTKEY_API_KEY),
    )


# gpt-6-luna rejects function tools unless reasoning_effort is "none" (it has no
# separate /v1/responses reasoning path through Portkey here), so every agent in
# this project is built with this as its default model_settings.
DEFAULT_MODEL_SETTINGS = {"openai_reasoning_effort": "none"}
