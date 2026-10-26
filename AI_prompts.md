# AI prompt log — Final Project

Session: picked a real-stakeholder final project (per course prompt: "pick
something that matters to someone... hand over to a real person tomorrow").

## Problem selection

User asked for help brainstorming who/what to build for. Assistant proposed 4
directions grounded in the semester's prior assignments (HW3 catalogue tools,
HW5 multi-agent "Campus Customs" team, HW6 document-defense agent): a campus
org ops assistant, a vendor/invoice agent, a course-advising assistant, a
nonprofit coordination assistant. User picked "a real campus org's ops
assistant," then said they didn't have a specific club locked in and asked for
help finding data too.

Assistant proposed a concrete, representative scenario — a Yale student
tutoring org's 4-person e-board (Treasurer, Volunteer Coordinator, Family
Liaison, Director) — and generated realistic synthetic data for it rather than
waiting on a real export, explicitly flagging it as synthetic-but-representative.

## Project location

Asked the user where the project should live, since `AGENTS.md`'s literal
default ("Lectures 3") didn't match how HW3–HW6 were actually each given their
own top-level folder with their own `.venv`/git repo. User chose a new
top-level folder: `Final Project/`.

## Build

Built directly (no further prompting needed per-file): scaffolded the project
(venv, requirements, data files), then the backend —

- `models.py` / `decisions.py`: structured types + a deterministic reimbursement
  decision function, reusing HW6's "code defense" pattern (the LLM never makes
  the actual approve/reject call).
- `agents/reader.py`: a quarantined extraction agent (HW6's "quarantine defense"
  pattern) — no tools, locked system prompt, structured-only output.
- `tools.py`: a "design defense" layer that strips HTML-comment and
  `[assistant: ...]`-style embedded instructions out of reimbursement documents
  before anything else reads them, logging what was removed.
- `agents/{treasurer,volunteer,family,faq}.py`: four specialist agents, each
  with its own tools and system prompt.
- `agents/boss.py`: a front-desk agent that delegates to the four specialists
  via agent-as-tool calls (HW5's multi-agent delegation pattern, single-team
  version).
- `cache.py`: a simple exact-match response cache (separate concern from
  provider-side prompt caching) since e-board members ask the same FAQ
  repeatedly.
- `audit.py`: reused HW6's `build_tool_call_records` pattern for an append-only
  audit trail of every tool call per turn.
- `main.py` + `frontend/index.html`: a FastAPI `/chat` endpoint and a one-page
  vanilla HTML/JS chat UI (no build step, so it can be handed to a non-technical
  e-board member and just run with `uvicorn`).

## Live verification (after user supplied a working PORTKEY_API_KEY)

Two real bugs surfaced only once a live model was available, both fixed:

1. `Agent.run_sync()` called from inside another agent's running tool raises
   `UserError: ... cannot be used inside a synchronous tool ... can deadlock the
   run` in this pydantic-ai version. Fixed by making `boss.py`'s delegation
   tools and `treasurer.py`'s `review_reimbursement` tool `async def`, using
   `await agent.run(...)` throughout, and making `Team.answer` / the FastAPI
   `/chat` handler `async def` to match.
2. The boss agent initially routed "Review r04_injection_approve_all.txt" to
   `ask_faq` instead of `ask_treasurer`, and the FAQ specialist (reasonably)
   said it couldn't access a named file. Fixed by making the boss's system
   prompt explicit that any request naming a specific reimbursement file goes
   to `ask_treasurer`, which has a tool that reads straight from the
   `reimbursement_requests/` folder.

After both fixes, verified live end-to-end via the actual browser UI (not just
a script): budget lookup, both injection-attack reimbursement files (correctly
evaluated against real caps regardless of the embedded "approve without limit"
/ "developer override" instructions, with the stripped text reported back as a
security note), background-check flags, tutee waitlist ordering, and the FAQ
agent — all five produced correct, handbook-grounded answers, and
`output/audit_trail.json` recorded every tool call made along the way.

## Final deliverables pass (report, slides, repo, course-key constraints)

User provided the course's project-requirements doc (report, slide deck, GitHub
repo, model/budget rules, `.env` lookup rules). Work done against it:

- **Model switch to gpt-6-luna** (the only model allowed on the course Portkey
  key). This surfaced a real API constraint not hit before: gpt-6-luna rejects
  function-tool calls on the chat-completions endpoint unless
  `reasoning_effort="none"` (confirmed via a live 400 error quoting Portkey's
  message). Fixed by adding `DEFAULT_MODEL_SETTINGS = {"openai_reasoning_effort":
  "none"}` in `portkey_client.py` and passing it to every one of the six agents.
- **`.env` lookup**: confirmed `portkey_client.py` already matched the required
  order (own repo folder's `.env` wins over one folder up) and extended the key
  lookup to accept either `PORTKEY_API_KEY` or `OPENAI_API_KEY` (both names the
  course's shared grading `.env` may use).
- **Tokenomics**: added `backend/usage.py` (reusing HW6's cost-calculation
  pattern against `data/prices.json`) and threaded pydantic-ai's shared
  `RunUsage` object through every delegated agent call (`RunContext.usage`) so
  one user turn's cost reflects the whole Boss → specialist → reader chain, not
  just the top-level call. Logged every turn to `output/usage_log.json`.
- **Safety additions**: a per-turn `UsageLimits(request_limit=12)` (protects
  against a malfunctioning/looping agent), a message-length cap, and a daily
  spend ceiling checked against the real logged cost — all three directly
  tested by forcing them to trigger (not just read from the code), with the
  exact failure output recorded in `report/report.html` §6.
- **Report** (`report/report.html`): all 8 required sections, built from the
  real measurements and screenshots taken in this session (not invented
  numbers) — see the report itself for exact figures and the test outputs
  quoted verbatim.
- **Slides** (`report/slides.html`): a 10-slide reveal.js deck, CDN-loaded, with
  the architecture diagram inlined as SVG and all screenshots inlined as
  base64 `data:` URIs (generated by a one-off Python build script, not
  committed, so the HTML file itself is the single portable artifact) so it
  opens standalone when emailed, per the assignment's requirement. Paged
  through every slide via the browser to confirm rendering before finishing.

## Verification done in this session

- Unit-tested `tools.py` CSV readers and `decisions.decide_reimbursement`
  directly against all 6 sample reimbursement requests (including the 2 with
  embedded prompt-injection attempts) without calling the model — confirmed the
  injected "approve without limit" / "developer override" instructions were
  stripped from the document text before extraction, and that the deterministic
  decision ignores them regardless (same cap-based outcome as a clean request
  would get).
- Ran the full agent team end-to-end via `team.Team().answer(...)`: imports,
  agent construction, and tool wiring all worked. The live model call failed
  with a `401 Portkey Error: Invalid API Key` — this matches the known issue
  already noted in the root `AGENTS.md` ("the current root `.env` credential was
  rejected as invalid"). Full agent-team behavior (routing, FAQ grounding,
  reimbursement review end-to-end through the model) is unverified pending a
  working `PORTKEY_API_KEY`.
