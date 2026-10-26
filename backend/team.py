from __future__ import annotations

import json
from datetime import datetime, timezone

from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import UsageLimits

import cache
import usage as usage_log
from agents.boss import build_boss_agent
from agents.faq import build_faq_agent
from agents.family import build_family_agent
from agents.treasurer import build_treasurer_agent
from agents.volunteer import build_volunteer_agent
from audit import append_audit, build_tool_call_records
from models import AuditEntry
from portkey_client import get_model

MAX_MESSAGE_CHARS = 2000
# Normal turn: boss(1) + one specialist(1) [+ reader(1) for a reimbursement review] = 2-3
# model requests. 12 gives headroom for a multi-specialist question without letting a
# malfunctioning/looping agent burn unbounded requests on one user turn.
RUN_USAGE_LIMITS = UsageLimits(request_limit=12)
DAILY_BUDGET_USD = 2.00


class MessageTooLong(Exception):
    pass


class DailyBudgetExceeded(Exception):
    pass


def _spent_today() -> float:
    if not usage_log.USAGE_LOG_PATH.exists():
        return 0.0
    today = datetime.now(timezone.utc).date().isoformat()
    entries = json.loads(usage_log.USAGE_LOG_PATH.read_text(encoding="utf-8"))
    return sum(e["cost_usd"] for e in entries if e["timestamp"].startswith(today))


class Team:
    def __init__(self) -> None:
        model = get_model()
        specialists = {
            "treasurer": build_treasurer_agent(model),
            "volunteer": build_volunteer_agent(model),
            "family": build_family_agent(model),
            "faq": build_faq_agent(model),
        }
        self.boss = build_boss_agent(model, specialists)

    async def answer(self, message: str, use_cache: bool = True) -> str:
        # SAFETY: reject absurdly long input before it ever reaches the model —
        # cheap to check, closes off one obvious cost-flooding vector.
        if len(message) > MAX_MESSAGE_CHARS:
            raise MessageTooLong(f"Message is {len(message)} characters; the limit is {MAX_MESSAGE_CHARS}.")

        # SAFETY: a fixed daily spend ceiling for this deployment. A bug or a user
        # hammering the chat endpoint can't run the bill past this without a human
        # raising the limit.
        spent = _spent_today()
        if spent >= DAILY_BUDGET_USD:
            raise DailyBudgetExceeded(f"Today's ${DAILY_BUDGET_USD:.2f} model budget is used (${spent:.4f} spent).")

        if use_cache:
            cached = cache.get(message)
            if cached is not None:
                append_audit(
                    AuditEntry(agent="boss", user_message=message, final_answer=cached, tool_calls=[])
                )
                usage_log.log_usage(message, _EmptyUsage(), cache_hit=True)
                return cached

        try:
            # SAFETY: caps total model requests for this turn, so a malfunctioning
            # agent stuck calling tools in a loop fails loudly instead of running
            # forever / burning the budget.
            result = await self.boss.run(message, usage_limits=RUN_USAGE_LIMITS)
        except UsageLimitExceeded as exc:
            reply = (
                "I hit my per-turn safety limit before finishing this request (too many tool "
                "calls) — something may be wrong. Please try rephrasing, or flag this to a "
                f"human e-board member. ({exc})"
            )
            append_audit(AuditEntry(agent="boss", user_message=message, final_answer=reply, tool_calls=[]))
            return reply

        reply = result.output
        run_usage = result.usage

        append_audit(
            AuditEntry(
                agent="boss",
                user_message=message,
                final_answer=reply,
                tool_calls=build_tool_call_records(result.all_messages()),
            )
        )
        usage_log.log_usage(message, run_usage)
        if use_cache:
            cache.set(message, reply)
        return reply


class _EmptyUsage:
    requests = 0
    input_tokens = 0
    cache_read_tokens = 0
    cache_write_tokens = 0
    output_tokens = 0
