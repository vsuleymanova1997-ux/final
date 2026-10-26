from __future__ import annotations

from pydantic_ai import Agent

import tools
from portkey_client import DEFAULT_MODEL_SETTINGS

FAQ_SYSTEM_PROMPT = """\
You are the general FAQ assistant for Elm City Tutoring Corps (ECTC) volunteers \
and e-board members. Answer using read_handbook — ground every answer in the \
handbook text and don't invent policy that isn't there. If the handbook doesn't \
cover something, say so and suggest who on the e-board to ask.
"""


def build_faq_agent(model) -> Agent:
    def read_handbook() -> str:
        """Full text of the ECTC e-board handbook (policies + FAQ)."""
        return tools.read_handbook()

    return Agent(model, system_prompt=FAQ_SYSTEM_PROMPT, tools=[read_handbook], model_settings=DEFAULT_MODEL_SETTINGS)
