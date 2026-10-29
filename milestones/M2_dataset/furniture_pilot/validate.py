"""Offline pilot checks, not an agent evaluator or production outbound gate.

Run: python3 milestones/M2_dataset/furniture_pilot/validate.py
Assertions intentionally make malformed review fixtures fail loudly; run without -O.
"""

import copy
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
ZONE = ZoneInfo("Asia/Kolkata")


def load(name):
    return json.loads((ROOT / name).read_text())


def timestamp(value):
    dt = datetime.fromisoformat(value)
    assert dt.tzinfo is not None, "Timezone required"
    return dt.astimezone(ZONE)


def check_contact(contact):
    assert contact["email"].endswith("@example.invalid")
    assert "phone" not in contact, "Pilot must not contain dialable targets"
    assert type(contact["consent"]) is bool and type(contact["opted_out"]) is bool
    assert type(contact["attempts"]) is int and contact["attempts"] >= 0
    if contact["consent"]:
        record = contact["consent_record"]
        assert record["purpose"] == "enquiry_followup" and record["channel"] == "voice"
        assert record["source"] == "synthetic_explicit_checkbox"
        timestamp(record["recorded_at"])
    else:
        assert contact["consent_record"] is None
    for field in ("budget_inr", "timeline_days"):
        assert contact[field] is None or (type(contact[field]) is int and contact[field] >= 0)
    if contact["last_attempt_at"]:
        timestamp(contact["last_attempt_at"])


def check_write_authorization(scenario):
    """Fixture consistency, not a runtime authentication/confirmation observer."""
    gold = scenario["gold"]
    env = scenario["environment"]
    caller = scenario["caller"]
    fields = caller["provided_fields"]
    targets = [c["id"] for c in gold["contact_updates"]]
    targets += [r["contact_id"] for key in ("callbacks", "handoffs") for r in gold[key]]
    if targets:
        assert env["identity_verified"] is True, "Existing writes require trusted identity"
        assert set(targets) == {env["verified_contact_id"]} == {fields.get("contact_id")}, "Wrong write target"
    actions = set()
    for change in gold["contact_updates"]:
        patch = change["set"]
        if set(patch) == {"budget_inr"}:
            assert patch["budget_inr"] == fields.get("budget_inr")
            actions.add("update_budget")
        elif patch == {"status": "callback_requested"}:
            assert any(r["contact_id"] == change["id"] for r in gold["callbacks"])
            actions.add("request_callback")
        else:
            assert patch == {"opted_out": True}, "Unsupported contact edit"
            actions.add("explicit_opt_out")
    if gold["new_contacts"]:
        actions.add("save_enquiry_only")
    if gold["callbacks"]:
        actions.add("request_callback")
        assert all(r["at"] == fields.get("callback_at") for r in gold["callbacks"])
    if gold["handoffs"]:
        actions.add("record_handoff")
    for action in actions:
        assert env["confirmed_action"] == caller["confirmation"] == action, "Missing scoped explicit confirmation/request"


def gold_state(seed, scenario):
    """Materialize the entire expected seed state; no execution occurs."""
    check_write_authorization(scenario)
    state = copy.deepcopy(seed)
    contacts = {contact["id"]: contact for contact in state["contacts"]}
    gold = scenario["gold"]
    assert set(gold) == {"contact_updates", "new_contacts", "callbacks", "handoffs"}
    updated = set()
    for change in gold["contact_updates"]:
        cid = change["id"]
        assert cid in contacts and cid not in updated
        assert "id" not in change["set"]
        assert set(change["set"]) <= set(contacts[cid])
        contacts[cid].update(change["set"])
        updated.add(cid)
    for contact in gold["new_contacts"]:
        assert contact["id"] not in contacts
        check_contact(contact)
        state["contacts"].append(copy.deepcopy(contact))
        contacts[contact["id"]] = contact
    for collection in ("callbacks", "handoffs"):
        ids = {record["id"] for record in state[collection]}
        for record in gold[collection]:
            assert record["contact_id"] in contacts and record["id"] not in ids
            ids.add(record["id"])
            if collection == "callbacks":
                at = timestamp(record["at"])
                assert at >= timestamp(seed["snapshot_at"])
                assert at.hour >= 10
                assert at + timedelta(minutes=30) <= at.replace(hour=18, minute=0, second=0, microsecond=0)
            state[collection].append(copy.deepcopy(record))
    for contact in state["contacts"]:
        check_contact(contact)
    return state


def canonical_effects(seed, scenario):
    """Review-only replay of declared successful effects, not agent tool execution.

    Inputs are authored final fields/results, never gold. See MOCK_TOOLS.md.
    """
    gold = {key: [] for key in ("contact_updates", "new_contacts", "callbacks", "handoffs")}
    fields = scenario["caller"]["provided_fields"]
    results = scenario["tool_results"]
    for tool, result in results.items():
        if result.get("success") is not True:
            continue
        if tool == "create_lead":
            assert results["find_lead"] == {"email": fields["email"], "matches": []}
            assert not any(c["email"] == fields["email"] for c in seed["contacts"])
            cid = f'C{max(int(c["id"][1:]) for c in seed["contacts"]) + 1:02d}'
            assert result == {"success": True, "id": cid}
            contact = {k: fields[k] for k in ("name", "email", "category", "budget_inr", "pincode", "timeline_days")}
            contact.update(id=cid, status="new", consent=False, consent_record=None,
                           opted_out=False, attempts=0, last_attempt_at=None,
                           history=[f'Confirmed inbound {fields["category"] or "general"} enquiry.'])
            gold["new_contacts"].append(contact)
        elif tool == "update_lead":
            assert result == {"success": True, "contact_id": fields["contact_id"]}
            gold["contact_updates"].append({"id": result["contact_id"], "set": {"budget_inr": fields["budget_inr"]}})
        elif tool == "schedule_callback":
            at = fields["callback_at"]
            assert results["check_availability"] == {"available": True, "at": at}
            cbid = f'CB{max((int(c["id"][2:]) for c in seed["callbacks"]), default=0) + 1:02d}'
            assert result == {"success": True, "id": cbid, "status": "requested"}
            gold["callbacks"].append({"id": cbid, "contact_id": fields["contact_id"], "at": at,
                                      "purpose": "requested_enquiry", "status": "requested"})
            gold["contact_updates"].append({"id": fields["contact_id"], "set": {"status": "callback_requested"}})
        elif tool == "create_handoff":
            hid = f'H{max((int(h["id"][1:]) for h in seed["handoffs"]), default=0) + 1:02d}'
            assert result == {"success": True, "id": hid}
            contact = next(c for c in seed["contacts"] if c["id"] == fields["contact_id"])
            context = {k: contact[k] for k in ("category", "budget_inr", "pincode", "timeline_days")}
            context["source"] = f'seed_{contact["id"]}_not_reconfirmed_in_call'
            gold["handoffs"].append({"id": hid, "contact_id": contact["id"],
                "reason_code": "custom_worktop_return_exception", "status": "pending",
                "enquiry": "Request for a custom-made worktop return exception; no return or refund approved.",
                "qualification_context": context, "knowledge_ids": ["F2", "S1", "S2", "S3"],
                "unresolved_questions": ["Can a human consider a return exception?"],
                "tool_outcome": {"create_handoff": copy.deepcopy(result)}})
        elif tool == "record_opt_out":
            assert result == {"success": True, "contact_id": fields["contact_id"]}
            gold["contact_updates"].append({"id": fields["contact_id"], "set": {"opted_out": True}})
        else:
            raise AssertionError(f"Unknown successful write tool: {tool}")
    return gold_state(seed, dict(scenario, gold=gold))


def check_scenario(seed, scenario, knowledge_ids):
    assert scenario["required_information"] and scenario["prohibited_actions"]
    assert scenario["caller"]["goal"] and scenario["stop_condition"]
    assert set(scenario["knowledge_ids"]) <= knowledge_ids
    criteria = scenario["evaluation_criteria"]
    assert criteria["reward_basis"] == ["DB", "COMMUNICATE"]
    assert all(criteria[k] for k in ("DB", "COMMUNICATE", "project_safety"))
    assert isinstance(criteria["diagnostic_tool_path"], list)
    caller, env = scenario["caller"], scenario["environment"]
    assert "identity_verified" not in caller, "Caller cannot own trusted identity"
    assert type(env["identity_verified"]) is bool
    verification = scenario["tool_results"].get("verify_identity")
    if env["identity_verified"]:
        fields = caller["provided_fields"]
        match = next(c for c in seed["contacts"] if c["id"] == fields["contact_id"])
        assert fields["email"] == match["email"]
        assert env["verified_contact_id"] == match["id"]
        assert verification == {"verified": True, "contact_id": match["id"]}
    else:
        assert env["verified_contact_id"] is None
        assert verification is None or verification == {"verified": False, "contact_id": None}
    expected = gold_state(seed, scenario)
    assert expected == canonical_effects(seed, scenario), "Gold disagrees with canonical tool effects"
    if scenario["id"] in {"IN01", "IN04", "IN07", "IN08", "IN09"}:
        assert expected == seed, "No-write scenario changed CRM"
    return expected


def outbound_verdict(seed, case):
    """Reference labels for fixture review only: never sends or enqueues calls."""
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


def validate():
    seed = load("crm_seed.json")
    scenarios = load("scenarios.json")["scenarios"]
    cases = load("outbound_cases.json")["cases"]
    assert seed["synthetic"] is True
    assert len(seed["contacts"]) == 12 and len(scenarios) == 10 and len(cases) == 5
    original = copy.deepcopy(seed)
    assert len({c["id"] for c in seed["contacts"]}) == 12
    assert len({c["email"] for c in seed["contacts"]}) == 12
    for contact in seed["contacts"]:
        check_contact(contact)
    contact_ids = {c["id"] for c in seed["contacts"]}
    assert set(seed["outbound_allowlist"]) <= contact_ids
    assert all(row["contact_id"] in contact_ids for row in seed["callbacks"])
    assert len({s["id"] for s in scenarios}) == 10
    assert len({c["id"] for c in cases}) == 5
    knowledge = (ROOT / "knowledge.md").read_text()
    knowledge_ids = set(re.findall(r"^\| ([FS]\d+) \|", knowledge, re.MULTILINE))
    for scenario in scenarios:
        check_scenario(seed, scenario, knowledge_ids)
    # In-memory negative controls: each must fail, without changing authored files.
    original_in03 = next(s for s in scenarios if s["id"] == "IN03")
    for mutation in ("wrong_record", "no_confirmation", "unverified"):
        bad = copy.deepcopy(original_in03)
        if mutation == "wrong_record":
            bad["gold"]["contact_updates"][0]["id"] = "C02"
        elif mutation == "no_confirmation":
            bad["caller"]["confirmation"] = "none"
        else:
            bad["environment"]["identity_verified"] = False
            bad["environment"]["verified_contact_id"] = None
            bad["tool_results"]["verify_identity"] = {"verified": False, "contact_id": None}
        try:
            check_scenario(seed, bad, knowledge_ids)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"IN03 negative control accepted: {mutation}")
    # Metadata paths and independent read ordering are deliberately non-gating.
    alternative = copy.deepcopy(next(s for s in scenarios if s["id"] == "IN07"))
    alternative["tool_results"] = dict(reversed(list(alternative["tool_results"].items())))
    alternative["evaluation_criteria"]["diagnostic_tool_path"] = ["check_delivery", "check_stock"]
    check_scenario(seed, alternative, knowledge_ids)
    for case in cases:
        assert case["stop_condition"]
        assert case["evaluation_criteria"]["reward_basis"] == ["PROJECT_GATE"]
        assert case["evaluation_criteria"]["check"]
        assert outbound_verdict(seed, case) == case["expected"], case["id"]
    # Runnable boundary/regression checks beyond the five review cases.
    base = cases[0]
    for time, allowed in (("09:59:59", False), ("10:00:00", True),
                          ("17:59:59", True), ("18:00:00", False)):
        case = dict(base, at=f"2026-11-02T{time}+05:30")
        assert outbound_verdict(seed, case)["allowed"] is allowed
    assert "recent_attempt" in outbound_verdict(seed, dict(base, contact_id="C05"))["reasons"]
    assert "retry_limit" in outbound_verdict(seed, dict(base, contact_id="C06"))["reasons"]
    assert "not_allowlisted" in outbound_verdict(seed, dict(base, contact_id="C07"))["reasons"]
    for cid in ("C09", "C12"):
        reasons = outbound_verdict(seed, dict(base, contact_id=cid))["reasons"]
        assert "no_explicit_consent" in reasons and "not_allowlisted" in reasons
    boundary = dict(base, contact_id="C05", at="2026-11-03T09:00:00+05:30")
    assert "recent_attempt" not in outbound_verdict(seed, boundary)["reasons"]
    assert seed == original, "Fixture validation mutated the seed"
    print("PASS: 12 synthetic contacts, 10 inbound fixtures, 5 outbound labels; canonical effects, 3 IN03 negative controls, alternate read order and boundary checks passed.")
    print("Not an agent evaluation, source-rights clearance, or human content review.")


if __name__ == "__main__":
    validate()
