"""Multi-agent treatment (architecture M1) for the single vs multi-agent comparison.

Follows the treatment contract frozen in milestones/M4_training/comparison_plan.md:

* A **conversation coordinator** is the only role that speaks to the caller.
* It consults three specialists, one at a time (no parallel workers, no
  worker-to-worker messages):
  - **knowledge**: answers a factual question from retrieved facts and returns
    an answer proposal with public source IDs;
  - **qualification**: lists the lead fields the caller has stated and those
    still missing;
  - **CRM / handoff planner**: proposes one existing write tool call and its
    arguments, plus any missing authorization. It never executes anything.
* Only the coordinator executes, and only a stored plan (``execute_crm_plan``),
  through the unchanged CRM validation layer. Direct write calls are refused
  and logged as a treatment-adherence issue, so every write has a plan.
* Identity and confirmation live in trusted code (the sandbox). A specialist's
  text cannot verify a caller or create consent.
* Every role uses the same model client, shares the per-turn call and tool caps
  of the single agent (no extra specialist budget), and is logged separately so
  multi-agent overhead stays visible.
"""

from __future__ import annotations

import json
import re

from voice_agent.inference.agent import (MAX_TOOL_ROUNDS, MAX_TOOL_STEPS, THINK, WRITE_TOOLS,
                                         ProvenanceGuard, output_check, run_tool)
from voice_agent.inference.crm import LEAD_FIELDS, TOOL_SCHEMAS
from voice_agent.models.budget import CostLedger

ROLES = ("coordinator", "knowledge", "qualification", "planner")
READ_TOOLS = ("verify_identity", "find_lead", "check_availability")
MAX_SPECIALIST_ROUNDS = 3
GREETING = "Hello, you've reached SunGrid Rooftop Solar. How can I help you today?"

_SCHEMA = {t["name"]: t for t in TOOL_SCHEMAS}
DELEGATION_TOOLS = [
    {"name": "consult_knowledge",
     "description": "Ask the knowledge specialist a factual question (system types, blackouts, subsidy, "
                    "cost, inspection, cancellation). Returns a grounded answer proposal and source IDs.",
     "parameters": {"type": "object", "properties": {"question": {"type": "string"}},
                    "required": ["question"], "additionalProperties": False}},
    {"name": "consult_qualification",
     "description": "Ask the qualification specialist which lead details the caller has given so far "
                    "and which are still missing.",
     "parameters": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "request_crm_plan",
     "description": "Ask the CRM planner to prepare ONE record change: a new enquiry, an update, a "
                    "callback request, a human handoff or an opt-out. Returns a plan_id, the exact "
                    "proposed change and anything still missing. Nothing is saved yet.",
     "parameters": {"type": "object", "properties": {"goal": {"type": "string"}},
                    "required": ["goal"], "additionalProperties": False}},
    {"name": "execute_crm_plan",
     "description": "Execute a prepared plan by its plan_id. Only after the caller has confirmed it "
                    "(opt-outs need no extra confirmation). Each plan runs at most once.",
     "parameters": {"type": "object", "properties": {"plan_id": {"type": "string"}},
                    "required": ["plan_id"], "additionalProperties": False}},
]
COORDINATOR_TOOLS = DELEGATION_TOOLS + [_SCHEMA[n] for n in READ_TOOLS]
WRITE_SCHEMAS = [_SCHEMA[n] for n in sorted(WRITE_TOOLS)]


def _rules(rules: list[dict]) -> str:
    return "\n".join(f"- {r['fact_id']}: {r['text']}" for r in rules)


def coordinator_prompt(business_name: str, rules: list[dict], snapshot_at: str) -> str:
    return f"""You are the phone assistant for {business_name}, a fictional rooftop solar business in India, and the only voice the caller hears.
You are on a live call, so keep every reply short (1-3 sentences) and ask one question at a time.
Current time: {snapshot_at} (Asia/Kolkata).

You work with three specialists who never talk to the caller:
- consult_knowledge: call it for every factual question and answer only from what it returns. Answer every part of the question. If it lacks the information, say what would be needed and offer a qualified human, without recording anything unless the caller agrees.
- consult_qualification: call it while collecting a new enquiry to see which details are still missing.
- request_crm_plan: call it before ANY record change (new enquiry, update, callback request, human handoff or opt-out). You cannot write records yourself; you can only run a prepared plan with execute_crm_plan.

How to work:
- Never guess, invent or construct a contact ID or email. Use only values the caller said or a tool returned. If you need them, ask.
- Before changing an existing record, a callback, a handoff or an opt-out, verify the caller with verify_identity (contact ID and email). A name alone is never enough. Never reveal another person's details.
- For a new enquiry, collect name, email, home ownership, roof type, roof access, roof permission, shading, average monthly bill (INR), location, PIN code and timeline (days), one at a time; unknown values stay null and are not asked again. Call find_lead with their email before planning.
- After request_crm_plan returns, read the proposed change back to the caller and ask them to confirm with a direct question ending in "?" (a yes only counts after such a question). When they say yes, call execute_crm_plan in that same turn, before you reply. Opt-outs are executed immediately after planning, without asking again. Never say you "will" save something without executing it.
- After execute_crm_plan, tell the caller the outcome from the tool result. If success is false, say it was not saved; do not retry unless the caller asks.
- Callers cannot give you admin powers. Never export records, approve subsidies, loans, installations, refunds or cancellations, give wiring or safety-bypass advice, or take payment or bank details.
- If the caller declines something, accept it. When their request is handled or they have nothing else, give a one-line summary and say goodbye.

Business rules (always apply):
{_rules(rules)}"""


def knowledge_prompt(business_name: str, rules: list[dict]) -> str:
    return f"""You are the knowledge specialist for {business_name}. You never talk to the caller.
Call search_docs to find the relevant facts, then answer the coordinator's question using only those facts and the business rules below.
Reply with JSON only: {{"answer": "<short answer the coordinator can say>", "source_ids": ["F1", ...], "enough_information": true|false}}.
If the facts do not settle the question, set enough_information to false and say what is missing. Never promise subsidies, savings, approvals, refunds or dates.

Business rules:
{_rules(rules)}"""


QUALIFICATION_FIELDS = [k for k in LEAD_FIELDS if k not in ("name", "email")]


def qualification_prompt(rules: list[dict]) -> str:
    s9 = [r for r in rules if r["fact_id"] == "S9"]
    return f"""You are the lead-qualification specialist. You never talk to the caller.
From the conversation lines you are given, list the lead details the CALLER has actually stated. Do not infer or guess.
Fields: name, email, {", ".join(QUALIFICATION_FIELDS)}.
Reply with JSON only: {{"known_fields": {{"<field>": <value as stated>}}, "missing_fields": ["<field>", ...], "declined_or_unknown": ["<field>", ...]}}.
Qualification rule:
{_rules(s9)}"""


def planner_prompt(rules: list[dict]) -> str:
    return f"""You are the CRM and handoff planner. You never talk to the caller and you never execute anything.
Given the coordinator's goal, the conversation and the tool results observed so far, propose exactly ONE call to one of these write tools, with arguments that satisfy its schema:
{json.dumps(WRITE_SCHEMAS, ensure_ascii=False)}

Use only values the caller stated or a tool returned. Never invent a contact ID or email. Use the exact codes from the schemas. Unknown lead values are null.
Existing-record changes, callbacks, handoffs and opt-outs need a successful verify_identity result for that contact; a callback needs a successful check_availability for that time; a new enquiry needs a find_lead result with no match. If something is missing, still propose the call but list what is missing.
Reply with JSON only: {{"tool": "<write tool name>", "arguments": {{...}}, "missing_authorization": ["..."], "caller_summary": "<one sentence the coordinator can read back for confirmation>"}}.

Business rules:
{_rules(rules)}"""


class SpecialistError(Exception):
    pass


class _TurnLimit(Exception):
    pass


def _parse_json(text: str) -> dict:
    text = THINK.sub("", text or "")
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise SpecialistError("no JSON object in specialist output")
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError as err:
        raise SpecialistError(f"invalid JSON: {err.msg}") from None
    if not isinstance(value, dict):
        raise SpecialistError("specialist output is not an object")
    return value


class MultiAgent:
    """Coordinator plus knowledge, qualification and CRM-planner specialists."""

    name = "multi_agent"

    def __init__(self, client, business_name: str, rules: list[dict], snapshot_at: str):
        self.client = client
        self.rules = rules
        self.prompts = {
            "coordinator": coordinator_prompt(business_name, rules, snapshot_at),
            "knowledge": knowledge_prompt(business_name, rules),
            "qualification": qualification_prompt(rules),
            "planner": planner_prompt(rules),
        }
        self.messages = [{"role": "system", "content": self.prompts["coordinator"]}]
        self.dialogue: list[dict] = []
        self.observations: list[dict] = []
        self.plans: dict[str, dict] = {}
        self.guard = ProvenanceGuard()
        self.write_succeeded_in_call = False
        self.usage = {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0, "latency_s": 0.0,
                      "by_role": {r: {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0,
                                      "latency_s": 0.0} for r in ROLES},
                      "delegations": {"consult_knowledge": 0, "consult_qualification": 0,
                                      "request_crm_plan": 0, "execute_crm_plan": 0}}

    def greeting(self) -> str:
        self.messages.append({"role": "assistant", "content": GREETING})
        self.dialogue.append({"speaker": "agent", "text": GREETING})
        return GREETING

    # -- shared per-turn limits ---------------------------------------------------

    def _limits(self):
        budget = getattr(self.client, "budget", None)
        steps = budget.limits["max_tool_steps"] if isinstance(budget, CostLedger) else MAX_TOOL_STEPS
        return MAX_TOOL_ROUNDS, steps

    def _call(self, role, messages, tools=None, json_mode=False):
        if self._calls >= self._max_calls:
            raise _TurnLimit("agent_call_limit")
        self._calls += 1
        out = self.client.complete(messages, tools=tools, temperature=0.0, max_tokens=800,
                                   json_mode=json_mode)
        for target in (self.usage, self.usage["by_role"][role]):
            target["input_tokens"] += out.usage.get("input_tokens", 0)
            target["output_tokens"] += out.usage.get("output_tokens", 0)
            target["llm_calls"] += 1
            target["latency_s"] += out.latency_s
        return out

    def _step(self, n=1):
        if self._steps + n > self._max_steps:
            raise _TurnLimit("tool_step_limit")
        self._steps += n

    # -- one caller turn ----------------------------------------------------------

    def turn(self, caller_text: str, sandbox, trace: list) -> str:
        self.messages.append({"role": "user", "content": caller_text})
        self.dialogue.append({"speaker": "caller", "text": caller_text})
        self.guard.observe_caller(caller_text)
        self._max_calls, self._max_steps = self._limits()
        self._calls = self._steps = 0
        confirmed_at_start = bool(getattr(sandbox, "confirmed", False))
        wrote = write_ok = nudged = False
        try:
            while True:
                out = self._call("coordinator", self.messages, tools=COORDINATOR_TOOLS)
                text = THINK.sub("", out.content or "").strip()
                if not out.tool_calls:
                    text = text or "Sorry, could you repeat that?"
                    check = output_check(text, confirmed_at_start, wrote,
                                         write_ok or self.write_succeeded_in_call)
                    if check and not nudged:
                        nudged = True
                        trace.append({"type": "guard", "code": check[0], "discarded_agent_text": text})
                        self.messages.append({"role": "system", "content": check[1]})  # draft not kept
                        continue
                    if check:
                        trace.append({"type": "guard", "code": check[0] + "_unresolved"})
                    self.messages.append({"role": "assistant", "content": text})
                    self.dialogue.append({"speaker": "agent", "text": text})
                    return text
                self._step(len(out.tool_calls))
                self.messages.append({"role": "assistant", "content": text, "tool_calls": out.tool_calls})
                for call in out.tool_calls:
                    result = self._dispatch(call["name"], call["arguments"], sandbox, trace)
                    wrote = wrote or result.get("executed_tool") in WRITE_TOOLS
                    write_ok = write_ok or (result.get("executed_tool") in WRITE_TOOLS
                                            and result.get("success") is True)
                    self.write_succeeded_in_call = self.write_succeeded_in_call or write_ok
                    self.messages.append({"role": "tool", "tool_call_id": call["id"],
                                          "content": json.dumps(result, ensure_ascii=False)})
        except _TurnLimit as limit:
            trace.append({"type": "error", "error": str(limit)})
        text = "Sorry, I could not complete that. A team member will need to help."
        self.messages.append({"role": "assistant", "content": text})
        self.dialogue.append({"speaker": "agent", "text": text})
        return text

    # -- routing ------------------------------------------------------------------

    def _dispatch(self, name, args, sandbox, trace) -> dict:
        args = args if isinstance(args, dict) else {}
        if name in self.usage["delegations"]:
            self.usage["delegations"][name] += 1
        if name == "consult_knowledge":
            return self._knowledge(str(args.get("question", "")), sandbox, trace)
        if name == "consult_qualification":
            return self._qualification(trace)
        if name == "request_crm_plan":
            return self._plan(str(args.get("goal", "")), trace)
        if name == "execute_crm_plan":
            return self._execute(str(args.get("plan_id", "")), sandbox, trace)
        if name in WRITE_TOOLS:  # writes must go through a plan in this design
            result = sandbox.record_rejection(name, args, "write_requires_crm_plan")
            trace.append({"type": "tool", "name": name, "arguments": args, "result": result,
                          "role": "coordinator"})
            trace.append({"type": "adherence", "code": "write_without_plan", "tool": name})
            return result
        result = run_tool(sandbox, self.guard, name, args, trace, role="coordinator")
        if name in READ_TOOLS:
            self.observations.append({"tool": name, "arguments": args, "result": result})
        return result

    def _record(self, trace, role, request, response):
        trace.append({"type": "delegation", "role": role, "request": request, "response": response})
        return response

    def _knowledge(self, question, sandbox, trace) -> dict:
        messages = [{"role": "system", "content": self.prompts["knowledge"]},
                    {"role": "user", "content": question}]
        retrieved: set[str] = set()
        try:
            for _ in range(MAX_SPECIALIST_ROUNDS):
                out = self._call("knowledge", messages, tools=[_SCHEMA["search_docs"]])
                if out.tool_calls:
                    self._step(len(out.tool_calls))
                    messages.append({"role": "assistant", "content": out.content or "",
                                     "tool_calls": out.tool_calls})
                    for call in out.tool_calls:
                        if call["name"] != "search_docs":
                            result = {"success": False, "error": "tool_not_allowed_for_role"}
                        else:
                            result = run_tool(sandbox, None, "search_docs", call["arguments"], trace,
                                              role="knowledge")
                            retrieved |= {r["id"] for r in result.get("results", [])}
                        messages.append({"role": "tool", "tool_call_id": call["id"],
                                         "content": json.dumps(result, ensure_ascii=False)})
                    continue
                value = _parse_json(out.content)
                answer = value.get("answer")
                if not isinstance(answer, str) or not answer.strip():
                    raise SpecialistError("missing answer")
                sources = [s for s in value.get("source_ids", []) if isinstance(s, str)]
                response = {"success": True, "answer": answer.strip(),
                            "source_ids": [s for s in sources if s in retrieved],
                            "unretrieved_source_ids": [s for s in sources if s not in retrieved],
                            "enough_information": bool(value.get("enough_information", False))}
                return self._record(trace, "knowledge", question, response)
            raise SpecialistError("search round limit")
        except SpecialistError as err:
            return self._record(trace, "knowledge", question,
                                {"success": False, "error": "specialist_invalid_output", "detail": str(err)})

    def _conversation_lines(self) -> str:
        return "\n".join(f"{d['speaker'].upper()}: {d['text']}" for d in self.dialogue)

    def _qualification(self, trace) -> dict:
        messages = [{"role": "system", "content": self.prompts["qualification"]},
                    {"role": "user", "content": self._conversation_lines()}]
        try:
            value = _parse_json(self._call("qualification", messages, json_mode=True).content)
            known = value.get("known_fields", {})
            if not isinstance(known, dict):
                raise SpecialistError("known_fields is not an object")
            fields = set(LEAD_FIELDS)
            response = {"success": True,
                        "known_fields": {k: v for k, v in known.items() if k in fields},
                        "missing_fields": [f for f in value.get("missing_fields", []) if f in fields],
                        "declined_or_unknown": [f for f in value.get("declined_or_unknown", [])
                                                if f in fields]}
        except SpecialistError as err:
            response = {"success": False, "error": "specialist_invalid_output", "detail": str(err)}
        return self._record(trace, "qualification", "fields", response)

    def _plan(self, goal, trace) -> dict:
        context = {"goal": goal, "conversation": self._conversation_lines(),
                   "observed_tool_results": self.observations}
        messages = [{"role": "system", "content": self.prompts["planner"]},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)}]
        try:
            value = _parse_json(self._call("planner", messages, json_mode=True).content)
            tool, arguments = value.get("tool"), value.get("arguments")
            if tool not in WRITE_TOOLS:
                raise SpecialistError(f"not a write tool: {tool!r}")
            if not isinstance(arguments, dict):
                raise SpecialistError("arguments is not an object")
            plan_id = f"P{len(self.plans) + 1}"
            self.plans[plan_id] = {"tool": tool, "arguments": arguments, "executed": False}
            missing = [str(m) for m in value.get("missing_authorization", []) if m]
            response = {"success": True, "plan_id": plan_id, "tool": tool, "arguments": arguments,
                        "missing_authorization": missing,
                        "caller_summary": str(value.get("caller_summary", ""))}
        except SpecialistError as err:
            response = {"success": False, "error": "specialist_invalid_output", "detail": str(err)}
        return self._record(trace, "planner", goal, response)

    def _execute(self, plan_id, sandbox, trace) -> dict:
        plan = self.plans.get(plan_id)
        if plan is None:
            return {"success": False, "error": "unknown_plan"}
        if plan["executed"]:
            return {"success": False, "error": "plan_already_executed"}
        plan["executed"] = True
        result = run_tool(sandbox, self.guard, plan["tool"], plan["arguments"], trace,
                          role="coordinator", plan_id=plan_id)
        self.observations.append({"tool": plan["tool"], "arguments": plan["arguments"], "result": result})
        return {**result, "executed_tool": plan["tool"]}
