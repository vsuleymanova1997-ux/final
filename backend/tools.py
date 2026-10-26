"""Data-access tools shared by the e-board agents. All reads are plain CSV/text —
no database — because that is what a real 4-person e-board actually has."""

from __future__ import annotations

import csv
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MEMBERS_PATH = DATA_DIR / "members.csv"
BUDGET_PATH = DATA_DIR / "budget.csv"
QUEUE_PATH = DATA_DIR / "tutee_queue.csv"
HANDBOOK_PATH = DATA_DIR / "handbook.md"
REQUESTS_DIR = DATA_DIR / "reimbursement_requests"


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def list_members(status: str | None = None, role: str | None = None) -> list[dict]:
    """List roster members, optionally filtered by status (active/inactive) or role."""
    rows = _read_csv(MEMBERS_PATH)
    if status:
        rows = [r for r in rows if r["status"].lower() == status.lower()]
    if role:
        rows = [r for r in rows if r["role"].lower() == role.lower()]
    return rows


def find_member(name_or_email: str) -> dict | None:
    """Look up one member by name (case-insensitive substring) or exact email."""
    needle = name_or_email.strip().lower()
    for row in _read_csv(MEMBERS_PATH):
        if row["email"].lower() == needle or needle in row["name"].lower():
            return row
    return None


def background_check_flags() -> list[dict]:
    """Members whose background check is pending or expired — cannot tutor solo."""
    return [r for r in _read_csv(MEMBERS_PATH) if r["background_check_status"] in ("pending", "expired") and r["status"] == "active"]


def get_budget() -> list[dict]:
    """Budget by category: allocated, spent, and remaining."""
    rows = _read_csv(BUDGET_PATH)
    for r in rows:
        r["remaining_usd"] = round(float(r["allocated_usd"]) - float(r["spent_usd"]), 2)
    return rows


def get_budget_category(category: str) -> dict | None:
    for row in get_budget():
        if row["category"].lower() == category.lower():
            return row
    return None


def get_tutee_queue(status: str | None = None) -> list[dict]:
    """Tutee matching queue, optionally filtered by status (matched/waiting)."""
    rows = _read_csv(QUEUE_PATH)
    if status:
        rows = [r for r in rows if r["status"].lower() == status.lower()]
    return rows


def read_handbook() -> str:
    """Full text of the e-board handbook (policies + FAQ)."""
    return HANDBOOK_PATH.read_text(encoding="utf-8")


def list_reimbursement_requests() -> list[str]:
    """Filenames of pending reimbursement requests waiting on the Treasurer."""
    return sorted(p.name for p in REQUESTS_DIR.glob("*.txt"))


_INJECTION_PATTERNS = [
    re.compile(r"<!--.*?-->", re.DOTALL),
    re.compile(r"\[(?:assistant|system)\s*:.*?\]", re.IGNORECASE | re.DOTALL),
    re.compile(r"SYSTEM NOTE.*", re.IGNORECASE),
]


def read_reimbursement_request(filename: str) -> dict:
    """Read one raw reimbursement request. Returns the cleaned text plus any
    embedded instruction-like content that was stripped out (for the audit log) —
    this is the DESIGN defense layer: untrusted content never reaches the decision
    logic with embedded instructions intact, and what was removed is always logged."""
    path = REQUESTS_DIR / filename
    raw = path.read_text(encoding="utf-8")
    removed: list[str] = []
    cleaned = raw
    for pattern in _INJECTION_PATTERNS:
        for match in pattern.finditer(cleaned):
            removed.append(match.group(0).strip())
        cleaned = pattern.sub("[removed: embedded instruction]", cleaned)
    return {"filename": filename, "text": cleaned, "removed": removed}
