"""Shared structured types for the ECTC e-board assistant."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ReimbursementExtraction(BaseModel):
    """What the quarantined reader copies out of a reimbursement request. No decision, no free text beyond fields."""

    requester_name: str | None = Field(description="Name of the person asking to be reimbursed, or null.")
    category_claimed: str | None = Field(
        description="The expense category as the document describes it (e.g. supplies, mileage, food), or null."
    )
    amount_usd: float | None = Field(description="Dollar amount requested, or null if not stated.")
    items_or_miles: str | None = Field(description="Items purchased, or miles driven, as literally stated.")


class ReimbursementDecision(BaseModel):
    """The Treasurer agent's final recommendation for one reimbursement request."""

    requester_name: str | None = None
    category: str | None = None
    amount_usd: float | None = None
    decision: Literal["approve", "reject", "needs_director_review"]
    reason: str = Field(description="One sentence citing the specific handbook rule that decided it.")


class ToolCallRecord(BaseModel):
    name: str
    args: str
    result: str


class AuditEntry(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: str
    user_message: str
    tool_calls: list[ToolCallRecord] = []
    final_answer: str
    hidden_text_removed: list[str] = []


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    agent: str
    session_id: str
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hit: bool = False
