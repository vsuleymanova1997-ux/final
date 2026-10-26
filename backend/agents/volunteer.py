from __future__ import annotations

from pydantic_ai import Agent

import tools
from portkey_client import DEFAULT_MODEL_SETTINGS

VOLUNTEER_SYSTEM_PROMPT = """\
You are the Volunteer Coordinator assistant for Elm City Tutoring Corps (ECTC). \
You answer questions about the tutor roster, logged hours, and background check \
status, using list_members and background_check_flags.

- A tutor with background_check_status "pending" or "expired" cannot tutor a \
  family solo (handbook policy) — say so plainly if asked whether someone can \
  tutor.
- 20+ hours_logged_ytd qualifies a tutor for a certificate of service.
"""


def build_volunteer_agent(model) -> Agent:
    def list_members(status: str | None = None, role: str | None = None) -> list[dict]:
        """List roster members, optionally filtered by status or role."""
        return tools.list_members(status=status, role=role)

    def find_member(name_or_email: str) -> dict | None:
        """Look up one member by name or email."""
        return tools.find_member(name_or_email)

    def background_check_flags() -> list[dict]:
        """Active members whose background check is pending or expired."""
        return tools.background_check_flags()

    return Agent(
        model,
        system_prompt=VOLUNTEER_SYSTEM_PROMPT,
        tools=[list_members, find_member, background_check_flags],
        model_settings=DEFAULT_MODEL_SETTINGS,
    )
