# Final Project — Elm City Tutoring Corps E-Board Assistant

**Report:** [`report/report.html`](report/report.html) (open in a browser, or Print →
Save as PDF) · **Slides:** [`report/slides.html`](report/slides.html) (reveal.js — open
and use arrow keys, press F for fullscreen)

A multi-agent e-board assistant for a Yale student tutoring org (synthetic data,
real workflow): a 4-person volunteer e-board's actual recurring work — budget /
reimbursement review, tutor roster & background-check tracking, tutee matching
waitlist, and volunteer FAQs — handled by a small PydanticAI agent team behind a
one-page chat UI, instead of a spreadsheet + email inbox.

This pulls together the semester's pieces: structured outputs, tool-using agents,
a multi-agent team with delegation (HW5), a FastAPI + web chat front end, a
response cache, and layered prompt-injection defenses on untrusted reimbursement
documents (HW6).

## Who this is for

A real ~40-person Yale service org e-board, run entirely by students with no paid
staff. The data here (`data/`) is invented, but the shape of it — a CSV roster, a
CSV budget, a folder of reimbursement emails, a markdown handbook — is exactly
what a real org's Treasurer/Coordinator/Liaison actually have, and swapping in
real CSVs/handbook text is the only change needed to hand this to a real e-board.

## Architecture

```
frontend/index.html        one-page chat UI (vanilla HTML/JS, no build step)
backend/
  main.py                  FastAPI: POST /chat, serves the frontend
  team.py                  wires the agent team together, caches, audits
  cache.py                 exact-match response cache (output/response_cache.json)
  audit.py                 append-only audit log of every tool call (output/audit_trail.json)
  decisions.py             CODE defense: deterministic reimbursement decision logic
  tools.py                 CSV/handbook/document readers shared by all agents
  usage.py                 tokenomics: per-turn cost from real usage, output/usage_log.json
  models.py                Pydantic structured types (ReimbursementDecision, etc.)
  portkey_client.py        shared Portkey-routed model client (gpt-6-luna)
  agents/
    boss.py                front-desk agent; delegates to the 4 specialists below
    treasurer.py            budget + reimbursement review
    volunteer.py             roster, hours, background checks
    family.py                 tutee matching queue
    faq.py                     handbook-grounded FAQ
    reader.py                QUARANTINE defense: extracts facts only, no tools, no decisions
data/
  org_profile.md, members.csv, budget.csv, tutee_queue.csv, handbook.md, prices.json
  reimbursement_requests/   6 sample requests, 2 of which embed prompt-injection attempts
report/
  report.html, slides.html, assets/   the written report, slide deck, screenshots, diagram
```

## Safety (see `report/report.html` §6 for the full writeup and tests)

Beyond the reimbursement defense below, `backend/team.py` enforces:
- **Message-length cap** (2,000 chars) — rejected before reaching the model (HTTP 413).
- **Daily spend ceiling** ($2.00/day, checked against real logged cost) — rejected before
  reaching the model once hit (HTTP 429).
- **Per-turn request limit** (`UsageLimits(request_limit=12)`) — a malfunctioning/looping
  agent fails with a clear message instead of hanging or running up cost.

### Prompt-injection defenses on reimbursement requests

Reimbursement requests are the one place untrusted text (an email someone wrote)
drives a money decision, so it gets three layers, mirroring HW6:

1. **Design** (`tools.read_reimbursement_request`): strips HTML comments and
   `[assistant: ...]`/`[system: ...]`-style embedded instructions out of the raw
   text before anything else sees it, and logs exactly what was removed.
2. **Quarantine** (`agents/reader.py`): a separate agent with no tools and a locked
   system prompt copies out only `requester_name`, `category_claimed`,
   `amount_usd`, `items_or_miles` into a structured type — it is explicitly told
   the document is data, never instructions.
3. **Code** (`decisions.py`): the actual approve/reject/needs-review call is a
   plain deterministic Python function over those four fields and the handbook's
   dollar caps — no LLM ever makes the real decision, so even a perfect injection
   can only corrupt what gets *extracted*, not talk the system into skipping a cap.

Try it in the UI: "Review r04_injection_approve_all.txt" and
"Review r05_injection_role_override.txt" — both embed an instruction telling the
assistant to approve without limit; both get evaluated against the real handbook
caps anyway, and the assistant reports what was stripped out as a security note.

## Setup

```bash
git clone <this-repo-url>
cd <this-repo-folder>
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### API key

This app needs **one** of `PORTKEY_API_KEY` or `OPENAI_API_KEY` (course key, model
`gpt-6-luna` only — see `.env.example`). It looks for a `.env` file in two places, in
this order, and a value in the closer one wins:

1. This repo's own root (`./.env`) — for your own local testing.
2. The folder **one level above** this repo (`../.env`) — this is where course
   graders' shared `.env` lives when every submission is cloned into one folder
   (`submissions/.env`, with `submissions/your-project/` being this repo).

For local testing:

```bash
cp .env.example .env    # then put your own key in it
```

No other environment variable names are read for the key — if you have a key under a
different name, rename it to one of the two above.

## Run it

```bash
.venv/bin/python -m uvicorn main:app --app-dir backend --port 8000
```

Open http://localhost:8000 — the page has a few example questions to click, or
type your own. Every answer shows its own real cost/token count right under it
(e.g. `$0.000264 · 1974 in / 134 out tokens`, or `served from cache · $0.00`).
Every turn is logged to `output/audit_trail.json` (tool calls + final answer)
and cached responses live in `output/response_cache.json`.

## Try these

- "How much is left in the tutoring_supplies budget?"
- "Review r04_injection_approve_all.txt" (prompt-injection attempt, should still
  be capped correctly)
- "Which tutors have an expired or pending background check?"
- "Which families have been waiting longest for a match?"
- "How do I get reimbursed for supplies?" (handbook FAQ)

## What's not done / next steps for a real handoff

- Swap `data/*.csv` and `data/handbook.md` for a real org's actual files.
- `review_reimbursement` currently reads from a fixed folder of `.txt` files —
  a real version would read incoming emails or a Google Form intake sheet.
- No auth on `/chat` — fine for a single e-board's shared laptop, not for a public
  deployment.
- `agents/family.py`'s "waited > 4 weeks" check uses the real current date against
  the synthetic 2025 `requested_date` values, so it will flag most of the sample
  queue as overdue — expected with this placeholder data, not a bug.

## Verified live

Confirmed working end-to-end on **gpt-6-luna** (the course key's only allowed model)
through the real browser UI (not just a script): budget lookup, both sample
prompt-injection reimbursement attacks (correctly capped regardless of the embedded
instructions, with the stripped text reported as a security note), background-check
flags, tutee waitlist ordering, and the handbook FAQ. Every turn's real token usage
and cost is logged to `output/usage_log.json`. See `AI_prompts.md` for implementation
issues this live pass caught and fixed, including a nested sync-agent-run deadlock
risk, a routing miss on the boss agent, and gpt-6-luna's `reasoning_effort="none"`
requirement for tool calls.
