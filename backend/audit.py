"""Shared helpers for turning a pydantic-ai run into an append-only audit entry."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart

from models import AuditEntry, ToolCallRecord

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
AUDIT_PATH = OUTPUT_DIR / "audit_trail.json"
TEXT_LIMIT = 300


def _shorten(value: object) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = " ".join(text.split())
    return text if len(text) <= TEXT_LIMIT else text[: TEXT_LIMIT - 3] + "..."


def build_tool_call_records(messages: list) -> list[ToolCallRecord]:
    results_by_call_id: dict[str, str] = {}
    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, ToolReturnPart):
                    results_by_call_id[part.tool_call_id] = _shorten(part.content)

    records = []
    for message in messages:
        if isinstance(message, ModelResponse):
            for part in message.parts:
                if isinstance(part, ToolCallPart) and part.tool_name != "final_result":
                    records.append(
                        ToolCallRecord(
                            name=part.tool_name,
                            args=_shorten(part.args),
                            result=results_by_call_id.get(part.tool_call_id, ""),
                        )
                    )
    return records


def append_audit(entry: AuditEntry) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    existing = []
    if AUDIT_PATH.exists():
        existing = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    existing.append(json.loads(entry.model_dump_json()))
    AUDIT_PATH.write_text(json.dumps(existing, indent=2), encoding="utf-8")
