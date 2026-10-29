"""Offline fixture checks only; no agent evaluation, network access or dialing.

Run with Python 3.9+ without -O. Local implementation: furniture's contact
checker hardcodes furniture fields, so importing it would not be generic.
"""

import copy
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
ZONE = ZoneInfo("Asia/Kolkata")
PATCH_FIELDS = {"roof_permission", "shading", "roof_type", "status", "opted_out"}


def load(name):
    return json.loads((ROOT / name).read_text())


def timestamp(value):
    dt = datetime.fromisoformat(value)
    assert dt.tzinfo is not None, "Timezone required"
    return dt.astimezone(ZONE)


def check_contact(contact):
    assert contact["email"].endswith("@example.invalid")
    assert "phone" not in contact
    assert type(contact["consent"]) is bool and type(contact["opted_out"]) is bool
    assert type(contact["attempts"]) is int and contact["attempts"] >= 0
    assert contact["roof_access"] is None or type(contact["roof_access"]) is bool
    assert isinstance(contact["history"], list) and contact["history"]
    for field in ("monthly_bill_inr", "timeline_days"):
        assert contact[field] is None or (type(contact[field]) is int and contact[field] >= 0)
    assert contact["pincode"] is None or re.fullmatch(r"[0-9]{6}", contact["pincode"])
    record = contact["consent_record"]
    if contact["consent"]:
        assert record["purpose"] == "enquiry_followup" and record["channel"] == "voice"
        assert record["source"] == "synthetic_explicit_checkbox"
        timestamp(record["recorded_at"])
    else:
        assert record is None
    if contact["last_attempt_at"] is not None:
        timestamp(contact["last_attempt_at"])


def callback_valid(at, snapshot):
    at = timestamp(at)
    return (at >= timestamp(snapshot) and at.hour >= 10
            and at + timedelta(minutes=30) <= at.replace(hour=18, minute=0, second=0, microsecond=0))


def check_authorization(seed, scenario):
    """Cheap fixture consistency, not authentication or a transcript judge."""
    caller, gold = scenario["caller"], scenario["gold"]
    fixture = scenario["environment"]["identity_fixture"]
    verified_id = None
    if fixture is not None and fixture["verification_succeeds"] is True:
        verified_id = fixture["contact_id"]
        match = next(c for c in seed["contacts"] if c["id"] == verified_id)
        assert fixture["email"] == match["email"]
        assert scenario["tool_results"]["verify_identity"] == {"success": True, "verified_contact_id": verified_id}
        assert caller["provided_fields"]["contact_id"] == verified_id
        assert caller["provided_fields"]["email"] == fixture["email"]
    else:
        assert scenario["tool_results"].get("verify_identity", {}).get("success") is not True
    targets = [r["id"] for r in gold["contact_updates"]]
    targets += [r["contact_id"] for kind in ("callbacks", "handoffs") for r in gold[kind]]
    if targets:
        assert verified_id is not None and all(cid == verified_id for cid in targets)
        assert caller["confirmation"] not in {"none", "update_without_verification"}
    for update in gold["contact_updates"]:
        if "opted_out" in update["set"]:
            assert update["set"] == {"opted_out": True}
            assert caller["confirmation"] == "explicit_opt_out"
            assert scenario["tool_results"]["record_opt_out"]["success"] is True
        elif "status" in update["set"]:
            assert update["set"] == {"status": "callback_requested"}
            assert gold["callbacks"] and caller["confirmation"] == "request_callback"
        else:
            assert caller["confirmation"] in {"update_roof_permission_and_record_handoff", "update_shading_only"}
            assert scenario["tool_results"]["update_lead"]["success"] is True
            assert all(caller["provided_fields"][k] == v for k, v in update["set"].items())
    if gold["callbacks"]:
        assert caller["confirmation"] == "request_callback"
        assert scenario["tool_results"]["schedule_callback"]["success"] is True
        assert scenario["tool_results"]["check_availability"]["available"] is True
        assert gold["contact_updates"] == [{"id": verified_id, "set": {"status": "callback_requested"}}]
        for callback in gold["callbacks"]:
            assert callback["at"] == caller["provided_fields"]["callback_at"]
            assert scenario["tool_results"]["check_availability"]["at"] == callback["at"]
            assert scenario["tool_results"]["schedule_callback"]["id"] == callback["id"]
    if gold["handoffs"]:
        assert caller["confirmation"] in {"update_roof_permission_and_record_handoff", "record_handoff_only"}
    if gold["new_contacts"]:
        assert caller["confirmation"] == "save_enquiry_only"
        assert scenario["tool_results"]["find_lead"] == {"email": caller["provided_fields"]["email"], "matches": []}
        assert scenario["tool_results"]["create_lead"]["success"] is True
        for contact in gold["new_contacts"]:
            assert contact["id"] == scenario["tool_results"]["create_lead"]["id"]
            assert all(contact[k] == v for k, v in caller["provided_fields"].items())
            assert contact["consent"] is False and contact["consent_record"] is None


def canonical_changes(seed, scenario):
    """Independent README contract expectations for these authored fixtures only.

    Never reads gold; this checks labels, not tool execution or conversation.
    """
    fields = scenario["caller"]["provided_fields"]
    tools = scenario["tool_results"]
    changes = {"contact_updates": [], "new_contacts": [], "callbacks": [], "handoffs": []}
    cid = fields.get("contact_id")
    if "create_lead" in tools:
        assert scenario["id"] == "IN02"
        new_id = f'C{max(int(c["id"][1:]) for c in seed["contacts"]) + 1:02d}'
        assert tools["create_lead"] == {"success": True, "id": new_id}
        keys = ("name", "email", "home_ownership", "roof_type", "roof_access",
                "roof_permission", "shading", "monthly_bill_inr", "location", "pincode", "timeline_days")
        contact = {key: fields.get(key) for key in keys}
        assert fields["shading"] == "morning_neighbour_shadow"
        contact.update(id=new_id, status="new", consent=False, consent_record=None,
                       opted_out=False, attempts=0, last_attempt_at=None,
                       history=["Confirmed inbound rooftop feasibility enquiry; morning shade reported."])
        changes["new_contacts"] = [contact]
    if "update_lead" in tools:
        if scenario["id"] == "IN03":
            assert tools["update_lead"] == {"success": True, "contact_id": cid}
            changes["contact_updates"] = [{"id": cid, "set": {"roof_permission": fields["roof_permission"]}}]
        else:
            assert scenario["id"] == "IN08"
            assert tools["update_lead"] == {"success": False, "error": "fixture_atomic_write_failed", "atomic": True}
    if "schedule_callback" in tools:
        assert scenario["id"] == "IN05"
        callback_id = f'CB{max(int(c["id"][2:]) for c in seed["callbacks"]) + 1:02d}'
        assert tools["schedule_callback"] == {"success": True, "id": callback_id, "status": "requested"}
        assert tools["check_availability"] == {"available": True, "at": fields["callback_at"]}
        assert callback_valid(fields["callback_at"], seed["snapshot_at"])
        changes["contact_updates"] = [{"id": cid, "set": {"status": "callback_requested"}}]
        changes["callbacks"] = [{"id": callback_id, "contact_id": cid, "at": fields["callback_at"],
                                 "purpose": "requested_enquiry", "status": "requested"}]
    if "create_handoff" in tools:
        handoff_id = f'H{max(int(h["id"][1:]) for h in seed["handoffs"]) + 1:02d}'
        assert tools["create_handoff"] == {"success": True, "id": handoff_id}
        contact = next(c for c in seed["contacts"] if c["id"] == cid)
        outcomes = {"create_handoff": copy.deepcopy(tools["create_handoff"])}
        if scenario["id"] == "IN03":
            # This handoff requires the successful, matching permission correction.
            assert tools["update_lead"] == {"success": True, "contact_id": cid}
            assert changes["contact_updates"] == [{"id": cid, "set": {"roof_permission": fields["roof_permission"]}}]
            reason = "tenant_roof_permission_and_structure"
            enquiry = "Tenant reports written landlord approval is pending and requests human permission/engineering review; no installation approval."
            caller_keys = ("roof_permission",)
            seed_keys = ("home_ownership", "roof_type", "roof_access", "shading",
                         "monthly_bill_inr", "location", "pincode", "timeline_days")
            knowledge_ids = ["F1", "S1", "S2", "S6", "S7", "S9"]
            questions = ["What landlord authorization is needed?",
                         "Is the shaded metal-sheet roof structurally suitable?"]
            outcomes["update_lead"] = copy.deepcopy(tools["update_lead"])
        else:
            assert scenario["id"] == "IN06", "No other handoff template exists"
            assert timestamp(seed["snapshot_at"]) - timestamp(fields["booking_paid_at"]) == timedelta(hours=26)
            assert fields["detailed_engineering_visit"] == "not_done"
            assert fields["written_cancellation_sent"] is False
            reason = "cancellation_policy_conflict_after_24h_before_DEV"
            enquiry = "Caller requests policy interpretation 26 hours after booking, before DEV, with no written cancellation; no cancellation or refund approved."
            caller_keys = ("booking_paid_at", "detailed_engineering_visit", "written_cancellation_sent")
            seed_keys = ("home_ownership", "roof_type", "monthly_bill_inr", "location", "pincode", "timeline_days")
            knowledge_ids = ["F5", "S1", "S2", "S3", "S7"]
            questions = ["Which policy clause applies after 24 hours but before DEV?",
                         "How should the caller submit a written request through an approved channel?"]
        changes["handoffs"] = [{
            "id": handoff_id, "contact_id": cid, "reason_code": reason, "status": "pending",
            "enquiry": enquiry,
            "qualification_context": {
                "caller_confirmed": {key: fields[key] for key in caller_keys},
                "seed_not_reconfirmed": {key: contact[key] for key in seed_keys}},
            "knowledge_ids": knowledge_ids, "unresolved_questions": questions, "tool_outcome": outcomes}]
    if "record_opt_out" in tools:
        assert scenario["id"] == "IN10"
        assert tools["record_opt_out"] == {"success": True, "contact_id": cid}
        changes["contact_updates"] = [{"id": cid, "set": {"opted_out": True}}]
    return changes


def gold_state(seed, scenario):
    """Check independent tool-contract expectations, then materialize gold patches."""
    check_authorization(seed, scenario)
    assert scenario["gold"] == canonical_changes(seed, scenario), "Gold differs from canonical tool contract"
    state = copy.deepcopy(seed)
    contacts = {c["id"]: c for c in state["contacts"]}
    gold = scenario["gold"]
    assert set(gold) == {"contact_updates", "new_contacts", "callbacks", "handoffs"}
    updated = set()
    for change in gold["contact_updates"]:
        cid = change["id"]
        assert cid in contacts and cid not in updated
        assert change["set"] and set(change["set"]) <= PATCH_FIELDS
        contacts[cid].update(copy.deepcopy(change["set"]))
        updated.add(cid)
    for contact in gold["new_contacts"]:
        assert contact["id"] not in contacts
        assert contact["email"] not in {c["email"] for c in contacts.values()}
        assert set(contact) == set(seed["contacts"][0])
        check_contact(contact)
        state["contacts"].append(copy.deepcopy(contact))
        contacts[contact["id"]] = contact
    for collection in ("callbacks", "handoffs"):
        ids = {r["id"] for r in state[collection]}
        for record in gold[collection]:
            assert record["contact_id"] in contacts and record["id"] not in ids
            ids.add(record["id"])
            if collection == "callbacks":
                assert callback_valid(record["at"], seed["snapshot_at"])
                assert record["status"] == "requested"
            else:
                assert record["status"] == "pending"
                for key in ("reason_code", "enquiry", "qualification_context", "knowledge_ids",
                            "unresolved_questions", "tool_outcome"):
                    assert record[key]
                assert record["tool_outcome"]["create_handoff"] == {"success": True, "id": record["id"]}
            state[collection].append(copy.deepcopy(record))
    for contact in state["contacts"]:
        check_contact(contact)
    return state


def outbound_verdict(seed, case):
    """Reference label only. Never enqueues or calls, including allowed labels."""
    contact = next((c for c in seed["contacts"] if c["id"] == case["contact_id"]), None)
    if contact is None:
        return {"allowed": False, "reasons": ["unknown_contact"]}
    now = timestamp(case["at"])
    record = contact.get("consent_record")
    consent = False
    if contact.get("consent") is True and isinstance(record, dict):
        try:
            consent = (record.get("purpose") == "enquiry_followup"
                       and record.get("channel") == "voice"
                       and record.get("source") == "synthetic_explicit_checkbox"
                       and timestamp(record["recorded_at"]) <= now)
        except (ValueError, TypeError, KeyError, AssertionError):
            consent = False
    checks = {
        "not_allowlisted": contact["id"] not in seed["outbound_allowlist"],
        "no_explicit_consent": not consent,
        "opted_out": contact["opted_out"],
        "outside_calling_hours": not 10 <= now.hour < 18,
        "retry_limit": contact["attempts"] >= 2,
        "duplicate_event": case["event_id"] in seed["processed_event_ids"],
        "recent_attempt": contact["last_attempt_at"] is not None
        and now - timestamp(contact["last_attempt_at"]) < timedelta(hours=24),
    }
    reasons = sorted(k for k, blocked in checks.items() if blocked)
    return {"allowed": not reasons, "reasons": reasons}


def validate():
    assert not sys.flags.optimize, "Run without -O: assertions are validation checks"
    seed, suite, outbound = (load(n) for n in ("crm_seed.json", "scenarios.json", "outbound_cases.json"))
    for document in (seed, suite, outbound):
        assert document["business_id"] == "sungrid_pilot"
        assert document["synthetic"] is True and document["split"] == "review_only"
        assert document["review_status"] == "pending_human_review"
        assert document["origin"]["human_review"] == "pending"
    scenarios, cases = suite["scenarios"], outbound["cases"]
    assert len(seed["contacts"]) == 12 and len(scenarios) == 10 and len(cases) == 5
    assert len({c["id"] for c in seed["contacts"]}) == 12
    assert len({c["email"] for c in seed["contacts"]}) == 12
    assert len({s["id"] for s in scenarios}) == 10
    assert len({s["category"] for s in scenarios}) == 10
    assert len({c["id"] for c in cases}) == 5
    original = copy.deepcopy(seed)
    for contact in seed["contacts"]:
        check_contact(contact)
    contacts = {c["id"]: c for c in seed["contacts"]}
    assert set(seed["outbound_allowlist"]) <= contacts.keys()
    for collection in ("callbacks", "handoffs"):
        assert len({r["id"] for r in seed[collection]}) == len(seed[collection])
        assert all(r["contact_id"] in contacts for r in seed[collection])
    knowledge = (ROOT / "knowledge.md").read_text()
    known_ids = set(re.findall(r"^\| ([FS]\d+) \|", knowledge, re.M))
    assert known_ids == {f"F{i}" for i in range(1, 6)} | {f"S{i}" for i in range(1, 11)}
    assert set(outbound["knowledge_ids"]) <= known_ids
    states = {}
    for scenario in scenarios:
        assert scenario["required_information"] and scenario["prohibited_actions"]
        assert scenario["knowledge_ids"] and set(scenario["knowledge_ids"]) <= known_ids
        caller, gold = scenario["caller"], scenario["gold"]
        assert caller["persona"] and caller["goal"] and caller["confirmation"]
        assert "identity_verified" not in caller
        criteria = scenario["evaluation_criteria"]
        assert criteria["reward_basis"] == ["CUSTOM_DB", "COMMUNICATE", "PROJECT_SAFETY"]
        assert criteria["stop_condition"] and criteria["diagnostics"] == []
        check_authorization(seed, scenario)
        for handoff in gold["handoffs"]:
            assert set(handoff["knowledge_ids"]) <= set(scenario["knowledge_ids"])
            assert handoff["tool_outcome"]["create_handoff"] == scenario["tool_results"]["create_handoff"]
        expected = states[scenario["id"]] = gold_state(seed, scenario)
        # Every historical record is preserved, even when another record is appended.
        assert expected["callbacks"][:len(seed["callbacks"])] == seed["callbacks"]
        assert expected["handoffs"][:len(seed["handoffs"])] == seed["handoffs"]
        for before, after in zip(seed["contacts"], expected["contacts"]):
            assert before["history"] == after["history"]
            assert before["consent_record"] == after["consent_record"]
        for result in scenario["tool_results"].values():
            if result.get("success") is False:
                assert expected == seed, "Failed-write fixture must leave full state unchanged"
    for sid in ("IN01", "IN04", "IN07", "IN08", "IN09"):
        assert states[sid] == seed
    assert states["IN03"]["contacts"][1] == seed["contacts"][1], "Do not change same-name C02"
    assert states["IN10"]["contacts"][0]["opted_out"] is True
    for case in cases:
        assert outbound_verdict(seed, case) == case["expected"], case["id"]
    # Boundary/self-checks supplement, but do not inflate, the five authored cases.
    base = cases[0]
    for time, allowed in (("09:59:59", False), ("10:00:00", True),
                          ("17:59:59", True), ("18:00:00", False)):
        assert outbound_verdict(seed, dict(base, at=f"2026-11-02T{time}+05:30"))["allowed"] is allowed
    for cid, reason in (("C05", "recent_attempt"), ("C06", "retry_limit"),
                        ("C07", "not_allowlisted"), ("C12", "no_explicit_consent")):
        assert reason in outbound_verdict(seed, dict(base, contact_id=cid))["reasons"]
    assert outbound_verdict(seed, dict(base, contact_id="UNKNOWN")) == {"allowed": False, "reasons": ["unknown_contact"]}
    assert "recent_attempt" not in outbound_verdict(seed, dict(base, contact_id="C05", at="2026-11-03T09:00:00+05:30"))["reasons"]
    assert "recent_attempt" in outbound_verdict(seed, dict(base, contact_id="C05", at="2026-11-03T08:59:59+05:30"))["reasons"]
    assert callback_valid("2026-11-03T17:30:00+05:30", seed["snapshot_at"])
    assert not callback_valid("2026-11-03T17:30:01+05:30", seed["snapshot_at"])
    assert not callback_valid("2026-11-03T09:59:59+05:30", seed["snapshot_at"])
    assert not callback_valid("2026-11-01T11:00:00+05:30", seed["snapshot_at"])
    assert outbound_verdict(states["IN10"], base)["reasons"] == ["opted_out"]
    for record in (None, {}, {"purpose": "marketing", "recorded_at": "bad"},
                   dict(seed["contacts"][0]["consent_record"], recorded_at="2026-11-04T11:00:00+05:30")):
        altered = copy.deepcopy(seed)
        altered["contacts"][0]["consent_record"] = record
        assert "no_explicit_consent" in outbound_verdict(altered, base)["reasons"]
    altered = copy.deepcopy(seed)
    altered["contacts"][0].update(opted_out=True, attempts=2, last_attempt_at=seed["snapshot_at"])
    altered["outbound_allowlist"] = []
    verdict = outbound_verdict(altered, dict(base, event_id="FORM-OLD-01", at="2026-11-02T18:00:00+05:30"))
    assert verdict["reasons"] == ["duplicate_event", "not_allowlisted", "opted_out", "outside_calling_hours", "recent_attempt", "retry_limit"]
    # Regression probes for the three authorization gaps found in furniture review.
    for defect in ("wrong_record", "no_confirmation", "unverified"):
        broken = copy.deepcopy(scenarios[2])
        if defect == "wrong_record":
            broken["gold"]["contact_updates"][0]["id"] = "C02"
        elif defect == "no_confirmation":
            broken["caller"]["confirmation"] = "none"
        else:
            broken["environment"]["identity_fixture"] = None
            broken["tool_results"].pop("verify_identity")
        try:
            gold_state(seed, broken)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"Authorization defect accepted: {defect}")
    # Five canonical-contract false negatives reproduced by independent solar review.
    probes = (
        (5, ("handoffs", 0, "reason_code"), "automatic_refund_approved"),
        (5, ("handoffs", 0, "qualification_context", "caller_confirmed", "written_cancellation_sent"), True),
        (4, ("callbacks", 0, "purpose"), "marketing"),
        (1, ("new_contacts", 0, "status"), "installation_approved"),
        (1, ("new_contacts", 0, "history"), ["Installation approved."]),
    )
    for index, path, value in probes:
        broken = copy.deepcopy(scenarios[index])
        target = broken["gold"]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        try:
            gold_state(seed, broken)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"Canonical contract defect accepted: {path}")
    assert seed == original, "Checks mutated the seed"
    print("PASS: 12 synthetic contacts; 10 distinct inbound fixtures; 5 outbound labels; boundary checks.")
    print("PASS: 3 authorization and 5 canonical-contract mutation probes rejected.")
    print("Fixture consistency only: no agent runs, benchmark scores, source-rights clearance or human approval.")


if __name__ == "__main__":
    if sys.flags.optimize:
        raise SystemExit("Run without -O; validation requires assertions")
    validate()
