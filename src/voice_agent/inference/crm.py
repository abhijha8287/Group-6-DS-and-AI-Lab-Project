"""CRM sandbox, validation layer and agent tools for SunGrid Rooftop Solar.

Implements the mock-tool contract in milestones/M2_dataset/solar_pilot/README.md:

* Every task starts from a fresh deep copy of crm_seed.json.
* The validation layer, not the LLM, decides whether a write is allowed:
  existing-record writes need a verified contact (bound by ``verify_identity``)
  and a fresh caller confirmation; failures are atomic and change nothing.
* The agent never sees fixtures or gold. Fixture results (e.g. a forced
  failure in IN08) are applied inside the tool, as a real backend would fail.

Confirmation token: the contract asks for an opaque token issued only after a
real confirmation utterance. Here the harness issues it internally when the
agent's last message asked a question and the caller's reply starts with a
clear "yes"/"I confirm". Each write consumes it. This is a simple, auditable
rule; its limits are listed in the M3 report.
"""

from __future__ import annotations

import re
from datetime import timedelta

from voice_agent.utils.common import deep_copy, iso, parse_time

# ---- business schema (solar) -------------------------------------------------

PICKLISTS = {
    "home_ownership": ["owner", "co_owner", "tenant"],
    "roof_type": ["RCC", "metal_sheet"],
    "roof_permission": ["self_reported_owner", "society_approval_pending",
                        "landlord_approval_pending", "unknown"],
    "shading": ["unknown", "afternoon_tree_shadow", "morning_neighbour_shadow",
                "afternoon_water_tank_shadow"],
}
UPDATABLE = {"roof_permission", "roof_type", "shading"}
LEAD_FIELDS = {
    "name": str, "email": str, "home_ownership": str, "roof_type": str, "roof_access": bool,
    "roof_permission": str, "shading": str, "monthly_bill_inr": int, "location": str,
    "pincode": str, "timeline_days": int,
}
SHADING_PHRASE = {"morning_neighbour_shadow": "morning shade"}

HANDOFF_REGISTRY = {
    "tenant_roof_permission_and_structure": {
        "enquiry": "Tenant reports written landlord approval is pending and requests human "
                   "permission/engineering review; no installation approval.",
        "caller_keys": {"roof_permission": str},
        "seed_keys": ["home_ownership", "roof_type", "roof_access", "shading", "monthly_bill_inr",
                      "location", "pincode", "timeline_days"],
        "knowledge_ids": ["F1", "S1", "S2", "S6", "S7", "S9"],
        "unresolved_questions": ["What landlord authorization is needed?",
                                 "Is the shaded metal-sheet roof structurally suitable?"],
    },
    "cancellation_policy_conflict_after_24h_before_DEV": {
        "enquiry": "Caller requests policy interpretation 26 hours after booking, before DEV, "
                   "with no written cancellation; no cancellation or refund approved.",
        "caller_keys": {"booking_paid_at": str, "detailed_engineering_visit": str,
                        "written_cancellation_sent": bool},
        "seed_keys": ["home_ownership", "roof_type", "monthly_bill_inr", "location", "pincode",
                      "timeline_days"],
        "knowledge_ids": ["F5", "S1", "S2", "S3", "S7"],
        "unresolved_questions": ["Which policy clause applies after 24 hours but before DEV?",
                                 "How should the caller submit a written request through an "
                                 "approved channel?"],
    },
}

WRITE_TOOLS = {"create_lead", "update_lead", "schedule_callback", "create_handoff", "record_opt_out"}

AFFIRM = re.compile(r"^\W*(yes|yeah|yep|sure|ok|okay|correct|confirm(ed)?|go ahead|please do|"
                    r"that'?s right|that is right)\b", re.I)
I_CONFIRM = re.compile(r"\bi (do )?confirm\b", re.I)
NEGATE_START = re.compile(r"^\W*(no|nope|don'?t|do not|not)\b", re.I)


def is_confirmation(agent_text: str, caller_text: str) -> bool:
    asked = "?" in (agent_text or "")
    said_yes = bool(AFFIRM.match(caller_text) or I_CONFIRM.search(caller_text))
    return asked and said_yes and not NEGATE_START.match(caller_text)


# ---- tool schemas shown to the LLM --------------------------------------------

def _nullable(kind, enum=None):
    schema = {"type": [kind, "null"]}
    if enum:
        schema["enum"] = enum + [None]
    return schema


TOOL_SCHEMAS = [
    {"name": "search_docs",
     "description": "Search SunGrid's knowledge base. Returns facts with IDs (F1-F5). Use before "
                    "answering any question about solar systems, subsidies, costs or cancellation.",
     "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                    "required": ["query"], "additionalProperties": False}},
    {"name": "verify_identity",
     "description": "Verify an existing customer by contact ID and email. Required before any "
                    "change to an existing record, callback, handoff or opt-out.",
     "parameters": {"type": "object", "properties": {"contact_id": {"type": "string"},
                                                     "email": {"type": "string"}},
                    "required": ["contact_id", "email"], "additionalProperties": False}},
    {"name": "find_lead",
     "description": "Check whether an enquiry already exists for an email. Required before "
                    "create_lead. Does not reveal record details.",
     "parameters": {"type": "object", "properties": {"email": {"type": "string"}},
                    "required": ["email"], "additionalProperties": False}},
    {"name": "create_lead",
     "description": "Save a NEW enquiry after find_lead found no match and the caller confirmed "
                    "the details. Unknown fields must be null. Does not grant calling consent.",
     "parameters": {"type": "object", "properties": {
         "name": {"type": "string"}, "email": {"type": "string"},
         "home_ownership": _nullable("string", PICKLISTS["home_ownership"]),
         "roof_type": _nullable("string", PICKLISTS["roof_type"]),
         "roof_access": _nullable("boolean"),
         "roof_permission": _nullable("string", PICKLISTS["roof_permission"]),
         "shading": _nullable("string", PICKLISTS["shading"]),
         "monthly_bill_inr": _nullable("integer"), "location": _nullable("string"),
         "pincode": _nullable("string"), "timeline_days": _nullable("integer")},
         "required": ["name", "email"], "additionalProperties": False}},
    {"name": "update_lead",
     "description": "Change roof_permission, roof_type or shading on the verified contact, after "
                    "the caller confirmed the exact change.",
     "parameters": {"type": "object", "properties": {
         "contact_id": {"type": "string"},
         "set": {"type": "object", "properties": {k: {"type": "string", "enum": PICKLISTS[k]}
                                                  for k in sorted(UPDATABLE)},
                 "additionalProperties": False}},
         "required": ["contact_id", "set"], "additionalProperties": False}},
    {"name": "check_availability",
     "description": "Check a 30-minute callback slot (ISO time, Asia/Kolkata). Required before "
                    "schedule_callback.",
     "parameters": {"type": "object", "properties": {"at": {"type": "string"}},
                    "required": ["at"], "additionalProperties": False}},
    {"name": "schedule_callback",
     "description": "Save a callback REQUEST for the verified contact at a checked time, after "
                    "the caller confirmed it. Not a site visit and not calling consent.",
     "parameters": {"type": "object", "properties": {"contact_id": {"type": "string"},
                                                     "at": {"type": "string"}},
                    "required": ["contact_id", "at"], "additionalProperties": False}},
    {"name": "create_handoff",
     "description": "Record a human review request for the verified contact, after the caller "
                    "confirmed it. reason_code tenant_roof_permission_and_structure needs "
                    "caller_confirmed {roof_permission}. reason_code "
                    "cancellation_policy_conflict_after_24h_before_DEV needs caller_confirmed "
                    "{booking_paid_at (ISO time), detailed_engineering_visit ('done' or "
                    "'not_done'), written_cancellation_sent (boolean)}.",
     "parameters": {"type": "object", "properties": {
         "contact_id": {"type": "string"},
         "reason_code": {"type": "string", "enum": sorted(HANDOFF_REGISTRY)},
         "caller_confirmed": {"type": "object"}},
         "required": ["contact_id", "reason_code", "caller_confirmed"],
         "additionalProperties": False}},
    {"name": "record_opt_out",
     "description": "Immediately stop voice follow-up for the verified contact when they ask. "
                    "No extra confirmation needed.",
     "parameters": {"type": "object", "properties": {"contact_id": {"type": "string"}},
                    "required": ["contact_id"], "additionalProperties": False}},
]
TOOL_NAMES = {t["name"] for t in TOOL_SCHEMAS}


class ToolError(Exception):
    pass


class CRMSandbox:
    """One task's CRM state plus the session the validation layer checks against."""

    def __init__(self, seed: dict, harness: dict, index=None):
        self.state = deep_copy(seed)
        self.env = harness.get("environment") or {}
        self.fixtures = harness.get("tool_results") or {}
        self.index = index
        self.now = parse_time(seed["snapshot_at"])
        self.verified_id = None
        self.confirmed = False
        self.no_match_emails: set[str] = set()
        self.checked_slots: set[str] = set()
        self.observed: dict[str, dict] = {}
        self.log: list[dict] = []

    # -- conversation hooks ----------------------------------------------------

    def on_caller_turn(self, agent_text: str, caller_text: str) -> None:
        self.confirmed = is_confirmation(agent_text, caller_text)

    # -- dispatch --------------------------------------------------------------

    def execute(self, name: str, args: dict) -> dict:
        entry = {"tool": name, "args": args}
        try:
            if name not in TOOL_NAMES:
                raise ToolError("unknown_tool")
            if not isinstance(args, dict):
                raise ToolError("invalid_arguments")
            result = getattr(self, "_" + name)(**args)
        except ToolError as err:
            result = {"success": False, "error": str(err)}
            if name in WRITE_TOOLS:
                result["atomic"] = True
            entry["blocked"] = str(err)
        except TypeError:
            result = {"success": False, "error": "invalid_arguments"}
            entry["blocked"] = "invalid_arguments"
        entry["result"] = result
        self.log.append(entry)
        return result

    # -- validation helpers ----------------------------------------------------

    def _contact(self, cid):
        for c in self.state["contacts"]:
            if c["id"] == cid:
                return c
        raise ToolError("unknown_contact")

    def _require_verified(self, cid):
        if self.verified_id is None:
            raise ToolError("identity_not_verified")
        if cid != self.verified_id:
            raise ToolError("wrong_target_contact")

    def _consume_confirmation(self):
        if not self.confirmed:
            raise ToolError("caller_confirmation_missing")
        self.confirmed = False

    def _fixture_failure(self, name):
        fx = self.fixtures.get(name)
        if isinstance(fx, dict) and fx.get("success") is False:
            raise ToolError(fx.get("error", "backend_failure"))

    def _next_id(self, items, prefix):
        nums = [int(x["id"][len(prefix):]) for x in items if x["id"][len(prefix):].isdigit()]
        return f"{prefix}{(max(nums) + 1) if nums else 0:02d}"

    @staticmethod
    def _check_value(key, value, kind):
        if value is None:
            return
        if kind is int and (type(value) is not int or value < 0):
            raise ToolError(f"invalid_{key}")
        if kind is bool and type(value) is not bool:
            raise ToolError(f"invalid_{key}")
        if kind is str and not isinstance(value, str):
            raise ToolError(f"invalid_{key}")
        if key in PICKLISTS and value not in PICKLISTS[key]:
            raise ToolError(f"invalid_{key}")
        if key == "pincode" and not re.fullmatch(r"[0-9]{6}", value):
            raise ToolError("invalid_pincode")

    # -- tools -----------------------------------------------------------------

    def _search_docs(self, query: str):
        hits = self.index.search(query, k=3) if self.index else []
        return {"success": True, "results": [{"id": h["id"], "text": h["text"]} for h in hits]}

    def _verify_identity(self, contact_id: str, email: str):
        fixture = self.env.get("identity_fixture")
        ok = (fixture is not None and fixture.get("verification_succeeds")
              and fixture["contact_id"] == contact_id
              and fixture["email"].lower() == str(email).strip().lower())
        if not ok:
            self.verified_id = None
            return {"success": False, "verified_contact_id": None, "error": "verification_failed"}
        self.verified_id = contact_id
        return {"success": True, "verified_contact_id": contact_id}

    def _find_lead(self, email: str):
        email = str(email).strip().lower()
        matches = [c["id"] for c in self.state["contacts"] if c["email"].lower() == email]
        if not matches:
            self.no_match_emails.add(email)
            return {"success": True, "email": email, "match_found": False}
        result = {"success": True, "email": email, "match_found": True}
        if self.verified_id in matches:
            result["contact_id"] = self.verified_id
        return result

    def _create_lead(self, **fields):
        unknown = set(fields) - set(LEAD_FIELDS)
        if unknown:
            raise ToolError("unsupported_fields")
        email = str(fields.get("email", "")).strip().lower()
        if not fields.get("name") or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise ToolError("invalid_name_or_email")
        if email not in self.no_match_emails:
            raise ToolError("find_lead_no_match_required")
        for key, kind in LEAD_FIELDS.items():
            self._check_value(key, fields.get(key), kind)
        self._consume_confirmation()
        self._fixture_failure("create_lead")
        shading = fields.get("shading")
        phrase = SHADING_PHRASE.get(shading) or (shading.replace("_", " ") if shading and shading != "unknown" else None)
        history = ("Confirmed inbound rooftop feasibility enquiry; " + phrase + " reported."
                   if phrase else "Confirmed inbound rooftop feasibility enquiry.")
        contact = {"id": self._next_id(self.state["contacts"], "C")}
        for key in LEAD_FIELDS:
            contact[key] = fields.get(key)
        contact["email"] = email
        contact.update({"status": "new", "consent": False, "consent_record": None, "opted_out": False,
                        "attempts": 0, "last_attempt_at": None, "history": [history]})
        self.state["contacts"].append(contact)
        self.no_match_emails.discard(email)
        self.observed["create_lead"] = {"success": True, "id": contact["id"]}
        return {"success": True, "id": contact["id"], "contact": deep_copy(contact)}

    def _update_lead(self, contact_id: str, set: dict):  # noqa: A002 - contract name
        self._require_verified(contact_id)
        if not isinstance(set, dict) or not set or not (set.keys() <= UPDATABLE):
            raise ToolError("unsupported_fields")
        for key, value in set.items():
            if not isinstance(value, str):
                raise ToolError(f"invalid_{key}")
            self._check_value(key, value, str)
        self._consume_confirmation()
        self._fixture_failure("update_lead")
        contact = self._contact(contact_id)
        contact.update(set)
        self.observed["update_lead"] = {"success": True, "contact_id": contact_id}
        return {"success": True, "contact_id": contact_id, "contact": deep_copy(contact)}

    def _slot_ok(self, at):
        start = parse_time(at)
        end_limit = start.replace(hour=18, minute=0, second=0, microsecond=0)
        return start >= self.now and start.hour >= 10 and start + timedelta(minutes=30) <= end_limit

    def _check_availability(self, at: str):
        try:
            slot = iso(parse_time(at))
        except ValueError:
            raise ToolError("invalid_time")
        available = self._slot_ok(slot)
        fx = self.fixtures.get("check_availability")
        if available and isinstance(fx, dict) and iso(parse_time(fx["at"])) == slot:
            available = bool(fx.get("available"))
        if available:
            self.checked_slots.add(slot)
        return {"success": True, "available": available, "at": slot}

    def _schedule_callback(self, contact_id: str, at: str):
        self._require_verified(contact_id)
        try:
            slot = iso(parse_time(at))
        except ValueError:
            raise ToolError("invalid_time")
        if slot not in self.checked_slots:
            raise ToolError("availability_not_checked")
        self._consume_confirmation()
        self._fixture_failure("schedule_callback")
        contact = self._contact(contact_id)
        callback = {"id": self._next_id(self.state["callbacks"], "CB"), "contact_id": contact_id,
                    "at": slot, "purpose": "requested_enquiry", "status": "requested"}
        contact["status"] = "callback_requested"
        self.state["callbacks"].append(callback)
        return {"success": True, "id": callback["id"], "status": "requested",
                "callback": deep_copy(callback), "contact": deep_copy(contact)}

    def _create_handoff(self, contact_id: str, reason_code: str, caller_confirmed: dict):
        self._require_verified(contact_id)
        spec = HANDOFF_REGISTRY.get(reason_code)
        if spec is None:
            raise ToolError("unsupported_reason_code")
        if not isinstance(caller_confirmed, dict) or set(caller_confirmed) != set(spec["caller_keys"]):
            raise ToolError("invalid_caller_context")
        for key, kind in spec["caller_keys"].items():
            if type(caller_confirmed[key]) is not kind:
                raise ToolError(f"invalid_{key}")
        context = dict(caller_confirmed)
        if "booking_paid_at" in context:
            try:
                context["booking_paid_at"] = iso(parse_time(context["booking_paid_at"]))
            except ValueError:
                raise ToolError("invalid_booking_paid_at")
        self._consume_confirmation()
        self._fixture_failure("create_handoff")
        contact = self._contact(contact_id)
        new_id = self._next_id(self.state["handoffs"], "H")
        outcome = {}
        if "update_lead" in self.observed:
            outcome["update_lead"] = self.observed["update_lead"]
        outcome["create_handoff"] = {"success": True, "id": new_id}
        handoff = {
            "id": new_id, "contact_id": contact_id, "reason_code": reason_code, "status": "pending",
            "enquiry": spec["enquiry"],
            "qualification_context": {
                "caller_confirmed": context,
                "seed_not_reconfirmed": {k: contact[k] for k in spec["seed_keys"]},
            },
            "knowledge_ids": list(spec["knowledge_ids"]),
            "unresolved_questions": list(spec["unresolved_questions"]),
            "tool_outcome": outcome,
        }
        self.state["handoffs"].append(handoff)
        return {"success": True, "id": new_id, "handoff": deep_copy(handoff)}

    def _record_opt_out(self, contact_id: str):
        self._require_verified(contact_id)
        self._fixture_failure("record_opt_out")
        contact = self._contact(contact_id)
        contact["opted_out"] = True
        return {"success": True, "contact_id": contact_id, "contact": deep_copy(contact)}
