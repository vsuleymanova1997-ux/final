from __future__ import annotations

from datetime import date

from pydantic_ai import Agent

import tools
from portkey_client import DEFAULT_MODEL_SETTINGS

FAMILY_SYSTEM_PROMPT = """\
You are the Family Liaison assistant for Elm City Tutoring Corps (ECTC). You \
answer questions about the tutee matching queue using get_tutee_queue.

- Families are matched in request order, prioritizing whoever has waited longest \
  when multiple tutors are free for the same slot (handbook policy).
- A family waiting more than 4 weeks (28 days) from requested_date should be \
  flagged for a personal follow-up call by you, not just left waiting — call this \
  out explicitly when it applies.
- Today's date is given in each user message if relevant; otherwise estimate from \
  the requested_date column.
"""


def build_family_agent(model) -> Agent:
    def get_tutee_queue(status: str | None = None) -> list[dict]:
        """Tutee matching queue, optionally filtered by status (matched/waiting)."""
        return tools.get_tutee_queue(status=status)

    def today() -> str:
        """Today's date, ISO format."""
        return date.today().isoformat()

    return Agent(
        model, system_prompt=FAMILY_SYSTEM_PROMPT, tools=[get_tutee_queue, today], model_settings=DEFAULT_MODEL_SETTINGS
    )
