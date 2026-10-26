"""CODE defense layer: the actual approve/reject call is a deterministic Python
function over structured facts, never an LLM free-text judgment. A prompt
injection in a reimbursement document can at worst corrupt what the quarantined
reader *extracts* — it cannot talk this function into skipping a cap, because
this function never sees the document text at all."""

from __future__ import annotations

from models import ReimbursementDecision, ReimbursementExtraction

SUPPLY_CAP = 50.00
MILEAGE_RATE = 0.67
MILEAGE_CAP_ROUND_TRIP_MILES = 20
FAMILY_EVENT_CAP = 150.00
BACKGROUND_CHECK_FEE = 30.00

ALLOWED_CATEGORIES = {"supplies", "mileage", "family_event", "background_check"}


def _normalize_category(claimed: str | None) -> str | None:
    if not claimed:
        return None
    c = claimed.strip().lower()
    if "mile" in c or "drive" in c or "gas" in c:
        return "mileage"
    if "food" in c or "event" in c or "snack" in c or "gift" in c:
        return "family_event"
    if "background" in c or "check" in c:
        return "background_check"
    if "suppl" in c or "material" in c or "print" in c or "book" in c or "marker" in c or "folder" in c:
        return "supplies"
    return None


def decide_reimbursement(facts: ReimbursementExtraction) -> ReimbursementDecision:
    category = _normalize_category(facts.category_claimed)
    amount = facts.amount_usd

    if category is None or amount is None:
        return ReimbursementDecision(
            requester_name=facts.requester_name,
            category=facts.category_claimed,
            amount_usd=amount,
            decision="needs_director_review",
            reason="Could not place this request in a handbook reimbursement category — flagged for a human.",
        )

    items = (facts.items_or_miles or "").lower()
    if any(word in items for word in ("tablet", "laptop", "phone", "electronics", "gift card", "ipad", "headphone")):
        return ReimbursementDecision(
            requester_name=facts.requester_name,
            category=category,
            amount_usd=amount,
            decision="reject",
            reason="Handbook excludes electronics and gift cards from the supplies category, no exceptions.",
        )

    if category == "supplies":
        if amount <= SUPPLY_CAP:
            return ReimbursementDecision(
                requester_name=facts.requester_name, category=category, amount_usd=amount,
                decision="approve", reason=f"Supplies request of ${amount:.2f} is within the ${SUPPLY_CAP:.0f} handbook cap.",
            )
        return ReimbursementDecision(
            requester_name=facts.requester_name, category=category, amount_usd=amount,
            decision="reject", reason=f"${amount:.2f} exceeds the ${SUPPLY_CAP:.0f} per-request supply cap.",
        )

    if category == "mileage":
        max_amount = MILEAGE_CAP_ROUND_TRIP_MILES * MILEAGE_RATE
        if amount <= max_amount + 0.01:
            return ReimbursementDecision(
                requester_name=facts.requester_name, category=category, amount_usd=amount,
                decision="approve", reason=f"${amount:.2f} is within the ${max_amount:.2f} mileage cap ({MILEAGE_CAP_ROUND_TRIP_MILES} mi round trip at ${MILEAGE_RATE}/mi).",
            )
        return ReimbursementDecision(
            requester_name=facts.requester_name, category=category, amount_usd=amount,
            decision="needs_director_review",
            reason=f"${amount:.2f} exceeds the standard ${max_amount:.2f} mileage cap — needs Director pre-approval for a longer route.",
        )

    if category == "family_event":
        if amount <= FAMILY_EVENT_CAP:
            return ReimbursementDecision(
                requester_name=facts.requester_name, category=category, amount_usd=amount,
                decision="approve", reason=f"Family event spend of ${amount:.2f} is within the ${FAMILY_EVENT_CAP:.0f} cap.",
            )
        return ReimbursementDecision(
            requester_name=facts.requester_name, category=category, amount_usd=amount,
            decision="reject", reason=f"${amount:.2f} exceeds the ${FAMILY_EVENT_CAP:.0f} family-event cap.",
        )

    if category == "background_check":
        if abs(amount - BACKGROUND_CHECK_FEE) < 0.01:
            return ReimbursementDecision(
                requester_name=facts.requester_name, category=category, amount_usd=amount,
                decision="approve", reason="Matches the standard $30 background check fee.",
            )
        return ReimbursementDecision(
            requester_name=facts.requester_name, category=category, amount_usd=amount,
            decision="needs_director_review",
            reason=f"${amount:.2f} does not match the standard $30 background check fee.",
        )

    return ReimbursementDecision(
        requester_name=facts.requester_name, category=category, amount_usd=amount,
        decision="needs_director_review", reason="Unhandled category — flagged for a human.",
    )
