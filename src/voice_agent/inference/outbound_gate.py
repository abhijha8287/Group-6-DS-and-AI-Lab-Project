"""Deterministic outbound gate (rule S5). No LLM is involved in this decision.

Given a follow-up event and the CRM state, return whether the contact may be
queued for an outbound call, and every reason it may not. Unknown contacts
fail closed. The gate never dials, enqueues or changes the CRM.

Rules reflect TRAI TCCCPR 2018 (consent, preferences, calling hours) and the
DPDP Act 2023, Section 6 (consent for a specific purpose); the sandbox values
(10:00-18:00 IST, 24 h gap, 2 attempts) are project choices, not legal advice.
"""

from __future__ import annotations

from datetime import timedelta

from voice_agent.utils.common import parse_time

CALL_START_HOUR, CALL_END_HOUR = 10, 18
MIN_GAP = timedelta(hours=24)
MAX_ATTEMPTS = 2


def evaluate(seed: dict, case: dict) -> dict:
    contacts = {c["id"]: c for c in seed["contacts"]}
    contact = contacts.get(case.get("contact_id"))
    if contact is None:
        return {"allowed": False, "reasons": ["unknown_contact"]}

    now = parse_time(case["at"])  # converted to Asia/Kolkata before the hour check
    record = contact.get("consent_record")
    consent = bool(
        contact.get("consent")
        and record
        and record.get("purpose") == "enquiry_followup"
        and record.get("channel") == "voice"
        and parse_time(record["recorded_at"]) <= now
    )
    last = contact.get("last_attempt_at")
    checks = {
        "not_allowlisted": contact["id"] not in seed.get("outbound_allowlist", []),
        "no_explicit_consent": not consent,
        "opted_out": bool(contact.get("opted_out")),
        "outside_calling_hours": not (CALL_START_HOUR <= now.hour < CALL_END_HOUR),
        "retry_limit": contact.get("attempts", 0) >= MAX_ATTEMPTS,
        "duplicate_event": case.get("event_id") in seed.get("processed_event_ids", []),
        "recent_attempt": last is not None and now - parse_time(last) < MIN_GAP,
    }
    reasons = sorted(name for name, blocked in checks.items() if blocked)
    return {"allowed": not reasons, "reasons": reasons}
