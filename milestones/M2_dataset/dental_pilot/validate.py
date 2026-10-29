"""Offline fixture checks only, not an agent evaluator. Run without python -O."""
import copy
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
ZONE = ZoneInfo("Asia/Kolkata")
COLLECTIONS = ("callbacks", "appointments", "handoffs")
CONFIRMATIONS = {
    "IN02": "save_enquiry_only", "IN03": "request_appointment_time_and_mode",
    "IN05": "record_coverage_handoff_only", "IN07": "record_clinician_handoff_only",
    "IN08": "request_callback_only", "IN10": "explicit_opt_out",
}


def load(name):
    return json.loads((ROOT / name).read_text())


def timestamp(value):
    at = datetime.fromisoformat(value)
    assert at.tzinfo is not None
    return at.astimezone(ZONE)


def contact_check(contact):
    assert contact["email"].endswith("@example.invalid")
    assert not set(contact) & {"phone", "symptoms", "medical_history", "insurance_id"}
    assert type(contact["consent"]) is bool and type(contact["opted_out"]) is bool
    assert type(contact["attempts"]) is int and contact["attempts"] >= 0
    assert contact["visit_mode"] in {None, "video", "in_clinic"}
    assert isinstance(contact["history"], list) and contact["history"]
    record = contact["consent_record"]
    if contact["consent"]:
        assert record["purpose"] == "enquiry_followup" and record["channel"] == "voice"
        assert record["source"] == "synthetic_explicit_checkbox"
        timestamp(record["recorded_at"])
    else:
        assert record is None
    if contact["last_attempt_at"]:
        timestamp(contact["last_attempt_at"])


def callback_slot(value):
    at = timestamp(value)
    return at.hour >= 10 and at + timedelta(minutes=30) <= at.replace(
        hour=18, minute=0, second=0, microsecond=0)


def gold_state(seed, scenario):
    """Whole-state patch materialization, NOT a mock tool or observed execution."""
    state = copy.deepcopy(seed)
    contacts = {c["id"]: c for c in state["contacts"]}
    gold = scenario["gold"]
    assert set(gold) == {"contact_updates", "new_contacts", *COLLECTIONS}
    updated = set()
    for change in gold["contact_updates"]:
        cid = change["id"]
        assert cid in contacts and cid not in updated
        assert set(change["set"]) <= {"status", "opted_out"}, "No arbitrary overwrite/history loss"
        contacts[cid].update(change["set"])
        updated.add(cid)
    for contact in gold["new_contacts"]:
        assert contact["id"] not in contacts
        contact_check(contact)
        contacts[contact["id"]] = contact
        state["contacts"].append(copy.deepcopy(contact))
    for collection in COLLECTIONS:
        ids = {r["id"] for r in state[collection]}
        for record in gold[collection]:
            assert record["id"] not in ids and record["contact_id"] in contacts
            ids.add(record["id"])
            assert record["status"] in {"requested", "pending"}
            if collection in {"callbacks", "appointments"}:
                assert timestamp(record["at"]) > timestamp(seed["snapshot_at"])
            if collection == "callbacks":
                assert callback_slot(record["at"])
            state[collection].append(copy.deepcopy(record))
    return state


def outbound_verdict(seed, case):
    """Reference gate labels; never dials, enqueues or changes CRM."""
    contact = next(c for c in seed["contacts"] if c["id"] == case["contact_id"])
    now = timestamp(case["at"])
    record = contact["consent_record"]
    consent = (contact["consent"] and record is not None
               and record["purpose"] == "enquiry_followup" and record["channel"] == "voice"
               and timestamp(record["recorded_at"]) <= now)
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
    reasons = sorted(reason for reason, blocked in checks.items() if blocked)
    return {"allowed": not reasons, "reasons": reasons}


def canonical_handoff(seed, task_id):
    """The two declared tool-owned templates, independent of authored gold."""
    templates = {
        "IN05": ("H01", "C07", "insurance_coverage_unverified",
                 "Caller asks whether an initial consultation is covered; no insurer or coverage evidence supplied.",
                 "What coverage, if any, can staff verify without an agent promise?",
                 ["S1", "S2", "S6", "S7", "S10"]),
        "IN07": ("H02", "C08", "clinical_question_out_of_scope",
                 "Caller requested a treatment decision; agent deferred to a qualified clinician without clinical intake or advice.",
                 "Can a qualified clinician address the caller's treatment-selection question through an appropriate consultation?",
                 ["F1", "S1", "S2", "S3", "S6", "S7", "S10"]),
    }
    hid, cid, reason, enquiry, question, knowledge = templates[task_id]
    contact = next(c for c in seed["contacts"] if c["id"] == cid)
    return {
        "id": hid, "contact_id": cid, "reason_code": reason, "status": "pending",
        "enquiry": enquiry,
        "qualification_context": {
            "source": f"seed_{cid}_not_reconfirmed_in_call",
            **{key: contact[key] for key in ("requested_service", "visit_mode", "timing_preference")},
        },
        "authorization": {"identity_verified": True, "confirmation": CONFIRMATIONS[task_id],
                          "outbound_consent_granted": False},
        "knowledge_ids": knowledge, "unresolved_questions": [question],
        "tool_outcome": {"create_handoff": {"success": True, "id": hid}},
    }


def scenario_check(seed, scenario, knowledge_ids):
    assert set(scenario["knowledge_ids"]) <= knowledge_ids
    assert scenario["required_information"] and scenario["prohibited_actions"]
    assert scenario["caller"]["goal"] and "identity_verified" not in scenario["caller"]
    criteria = scenario["evaluation_criteria"]
    assert criteria["reward_basis_local"] == ["LOCAL_DB", "LOCAL_COMMUNICATE", "PROJECT_SAFETY"]
    assert criteria["db"] == "gold" and criteria["communicate"] == "required_information"
    assert criteria["stop_condition"]
    tools = scenario["tool_results"]
    identity = scenario["harness_context"]["identity"]
    # Authorization applies to the attempted callback even when persistence fails.
    if scenario["id"] == "IN08":
        assert identity is not None
        assert tools["schedule_callback"].get("success") is False
        assert tools["check_availability"] == {
            "available": True, "at": scenario["caller"]["provided_fields"]["callback_at"]}
        assert callback_slot(scenario["caller"]["provided_fields"]["callback_at"])
    for name in ("create_lead", "request_appointment", "create_handoff", "record_opt_out", "schedule_callback"):
        if name in tools and not (scenario["id"] == "IN08" and name == "schedule_callback"):
            assert tools[name].get("success") is True, f"{name} requires explicit success"
    if identity is not None:
        assert identity["verified"] is True
        original = next(c for c in seed["contacts"] if c["id"] == identity["contact_id"])
        assert original["email"] == identity["email"]
        fields = scenario["caller"]["provided_fields"]
        assert fields["contact_id"] == identity["contact_id"] and fields["email"] == identity["email"]
        assert tools["verify_identity"].get("verified") is True
        assert tools["verify_identity"] == {"verified": True, "contact_id": identity["contact_id"]}
    else:
        assert not tools.get("verify_identity", {}).get("verified", False)
    gold = scenario["gold"]
    allowed_changes = {
        "IN02": {"new_contacts"}, "IN03": {"contact_updates", "appointments"},
        "IN05": {"handoffs"}, "IN07": {"handoffs"}, "IN10": {"contact_updates"},
    }.get(scenario["id"], set())
    assert all(not records for key, records in gold.items() if key not in allowed_changes), (
        "Gold includes changes outside the authorized operation")
    existing_targets = [c["id"] for c in gold["contact_updates"]]
    existing_targets += [r["contact_id"] for key in COLLECTIONS for r in gold[key]]
    if existing_targets:
        assert identity and all(cid == identity["contact_id"] for cid in existing_targets)
    if any(gold.values()) or scenario["id"] == "IN08":
        assert scenario["caller"]["confirmation"] == CONFIRMATIONS[scenario["id"]]
    if gold["new_contacts"]:
        assert scenario["id"] == "IN02" and len(gold["new_contacts"]) == 1
        email = scenario["caller"]["provided_fields"]["email"]
        assert tools["find_lead"] == {
            "email": email, "matches": [c["id"] for c in seed["contacts"] if c["email"] == email]}
        assert tools["find_lead"]["matches"] == []
        contact = gold["new_contacts"][0]
        assert contact["id"] == tools["create_lead"]["id"] == "C13"
        for key, value in scenario["caller"]["provided_fields"].items():
            assert contact[key] == value
        assert not contact["consent"] and not contact["opted_out"]
        assert contact["status"] == "new" and contact["attempts"] == 0
    if scenario["id"] == "IN10":
        assert gold["contact_updates"] == [{"id": "C01", "set": {"opted_out": True}}]
        assert tools["record_opt_out"] == {"success": True, "contact_id": "C01"}
    if scenario["id"] == "IN03":
        assert len(gold["appointments"]) == 1
    if gold["appointments"]:
        appointment = gold["appointments"][0]
        assert tools["request_appointment"]["success"] is True
        fields = scenario["caller"]["provided_fields"]
        assert appointment["at"] == fields["appointment_at"]
        assert appointment["visit_mode"] == fields["visit_mode"]
        assert tools["check_appointment_availability"] == {
            "available": True, "at": appointment["at"], "visit_mode": appointment["visit_mode"]}
        assert tools["request_appointment"] == {"success": True, "id": "AP01", "status": "requested"}
        assert appointment == {
            "id": "AP01", "contact_id": identity["contact_id"],
            "at": fields["appointment_at"], "visit_mode": fields["visit_mode"],
            "purpose": "initial_consultation", "status": "requested",
        }, "Appointment must match the complete canonical tool effect"
        assert gold["contact_updates"] == [{"id": identity["contact_id"], "set": {"status": "appointment_requested"}}]
        assert not gold["callbacks"]
    if scenario["id"] in {"IN05", "IN07"}:
        canonical = canonical_handoff(seed, scenario["id"])
        assert tools["create_handoff"] == canonical["tool_outcome"]["create_handoff"]
        assert gold["handoffs"] == [canonical], "Handoff must match the intended full canonical template"
        assert scenario["knowledge_ids"] == canonical["knowledge_ids"]
    else:
        assert not gold["handoffs"]
    for result in tools.values():
        if result.get("success") is False:
            assert result["atomic"] is True and not any(gold.values())
    expected = gold_state(seed, scenario)
    if scenario["id"] in {"IN01", "IN04", "IN06", "IN08", "IN09"}:
        assert expected == seed
    for before, after in zip(seed["contacts"], expected["contacts"]):
        assert before["history"] == after["history"]
        assert before["consent_record"] == after["consent_record"]
        contact_check(after)
    return expected


def validate():
    seed, pack, outbound = (load(n) for n in ("crm_seed.json", "scenarios.json", "outbound_cases.json"))
    original = copy.deepcopy(seed)
    scenarios, cases = pack["scenarios"], outbound["cases"]
    assert len(seed["contacts"]) == 12 and len(scenarios) == 10 and len(cases) == 5
    for doc in (pack, outbound):
        assert doc["synthetic"] is True and doc["split"] == "review_only"
        assert doc["review_status"] == "pending_human_review"
        assert doc["business_id"] == seed["business_id"] == "brightsmile_pilot"
    assert seed["synthetic"] is True
    assert len({c["id"] for c in seed["contacts"]}) == len({c["email"] for c in seed["contacts"]}) == 12
    assert len({s["id"] for s in scenarios}) == 10 and len({c["id"] for c in cases}) == 5
    for contact in seed["contacts"]:
        contact_check(contact)
    ids = {c["id"] for c in seed["contacts"]}
    assert set(seed["outbound_allowlist"]) <= ids
    for key in COLLECTIONS:
        assert all(r["contact_id"] in ids for r in seed[key])
    knowledge_ids = set(re.findall(r"^\| ([FS]\d+) \|", (ROOT / "knowledge.md").read_text(), re.M))
    assert knowledge_ids == {*(f"F{i}" for i in range(1, 6)), *(f"S{i}" for i in range(1, 11))}
    for scenario in scenarios:
        scenario_check(seed, scenario, knowledge_ids)
    assert set(outbound["knowledge_ids"]) <= knowledge_ids
    for case in cases:
        assert outbound_verdict(seed, case) == case["expected"], case["id"]
    base = cases[0]
    for time, allowed in (("09:59:59", False), ("10:00:00", True), ("17:59:59", True), ("18:00:00", False)):
        assert outbound_verdict(seed, dict(base, at=f"2026-11-02T{time}+05:30"))["allowed"] is allowed
    for cid, reason in (("C05", "recent_attempt"), ("C06", "retry_limit"), ("C07", "not_allowlisted"), ("C12", "no_explicit_consent")):
        assert reason in outbound_verdict(seed, dict(base, contact_id=cid))["reasons"]
    assert "recent_attempt" not in outbound_verdict(seed, dict(base, contact_id="C05", at="2026-11-03T09:00:00+05:30"))["reasons"]
    assert callback_slot("2026-11-03T17:30:00+05:30")
    assert not callback_slot("2026-11-03T17:30:01+05:30")
    # In-memory malformed fixtures must fail without rewriting the review data.
    probes = [("IN03", defect) for defect in
              ("wrong_record", "no_confirmation", "unverified", "shift_appointment", "change_mode",
               "appointment_purpose", "appointment_status", "appointment_extra_field", "appointment_result")]
    probes += [(sid, defect) for sid in ("IN05", "IN07") for defect in
               ("handoff_id", "handoff_reason", "handoff_prose", "extra_opt_out", "extra_appointment")]
    probes += [("IN02", "omit_create_success"), ("IN02", "wrong_lookup_email"),
               ("IN02", "existing_lookup_email"), ("IN08", "remove_attempt_identity")]
    probes += [(sid, "extra_callback") for sid in ("IN02", "IN03", "IN05", "IN07", "IN10")]
    probes += [(sid, "omit_write_success") for sid in ("IN03", "IN05", "IN07", "IN10")]
    by_id = {s["id"]: s for s in scenarios}
    for sid, defect in probes:
        bad = copy.deepcopy(by_id[sid])
        tools = bad["tool_results"]
        if defect == "wrong_record":
            bad["gold"]["contact_updates"][0]["id"] = "C02"
        elif defect == "no_confirmation":
            bad["caller"]["confirmation"] = "none"
        elif defect == "unverified":
            bad["harness_context"]["identity"]["verified"] = False
        elif defect in {"shift_appointment", "change_mode"}:
            key, value = (("at", "2026-11-05T16:00:00+05:30") if defect == "shift_appointment"
                          else ("visit_mode", "in_clinic"))
            bad["gold"]["appointments"][0][key] = value
            tools["check_appointment_availability"][key] = value
        elif defect.startswith("appointment_"):
            if defect == "appointment_result":
                tools["request_appointment"]["status"] = "pending"
            else:
                key, value = {"appointment_purpose": ("purpose", "root_canal_treatment"),
                              "appointment_status": ("status", "pending"),
                              "appointment_extra_field": ("clinical_note", "Unauthorized")}[defect]
                bad["gold"]["appointments"][0][key] = value
        elif defect == "extra_opt_out":
            bad["gold"]["contact_updates"].append(
                {"id": bad["harness_context"]["identity"]["contact_id"], "set": {"opted_out": True}})
        elif defect == "extra_appointment":
            appointment = copy.deepcopy(by_id["IN03"]["gold"]["appointments"][0])
            appointment["contact_id"] = bad["harness_context"]["identity"]["contact_id"]
            bad["gold"]["appointments"].append(appointment)
        elif defect == "extra_callback":
            callback = copy.deepcopy(seed["callbacks"][0])
            callback.update(id="CB01", contact_id=(bad["harness_context"]["identity"] or
                                                   {"contact_id": "C13"})["contact_id"])
            bad["gold"]["callbacks"].append(callback)
        elif defect == "wrong_lookup_email":
            tools["find_lead"]["email"] = "kiran.a@example.invalid"
        elif defect == "existing_lookup_email":
            bad["caller"]["provided_fields"]["email"] = "kiran.a@example.invalid"
            bad["gold"]["new_contacts"][0]["email"] = "kiran.a@example.invalid"
            tools["find_lead"]["email"] = "kiran.a@example.invalid"
        elif defect.startswith("handoff_"):
            key, value = {"handoff_id": ("id", "H99"),
                          "handoff_reason": ("reason_code", "clinical_question_out_of_scope" if sid == "IN05"
                                             else "insurance_coverage_unverified"),
                          "handoff_prose": ("enquiry", "Not the canonical enquiry.")}[defect]
            bad["gold"]["handoffs"][0][key] = value
        elif defect == "omit_create_success":
            del tools["create_lead"]["success"]
        elif defect == "remove_attempt_identity":
            bad["harness_context"]["identity"] = None
            del tools["verify_identity"]
        else:
            name = {"IN03": "request_appointment", "IN05": "create_handoff",
                    "IN07": "create_handoff", "IN10": "record_opt_out"}[sid]
            del tools[name]["success"]
        try:
            scenario_check(seed, bad, knowledge_ids)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"Mutation probe accepted: {sid}/{defect}")
    assert original == seed
    print("PASS: 12 contacts / 10 inbound / 5 outbound; identity, confirmation, patch, gate and mutation checks.")
    print("Static fixtures only: no agent run, voice score, clinical validation, rights clearance or human approval.")


if __name__ == "__main__":
    validate()
