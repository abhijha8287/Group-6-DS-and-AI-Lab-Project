"""Simulated callers. They see only the ``caller`` part of a task.

``LLMCaller`` role-plays the caller with an LLM (as in tau-bench's user
simulator). ``ScriptedCaller`` always agrees and is used only with the
oracle harness check.
"""

from __future__ import annotations

import json
import re

STOP = "###STOP###"
THINK = re.compile(r"<think>.*?</think>", re.S)


def caller_prompt(caller: dict) -> str:
    return f"""You are role-playing a CALLER phoning a solar business. You are not an assistant.
Persona: {caller['persona']}
Your goal and limits: {caller['goal']}
Facts you know (give each one only when the agent asks for it; never invent other facts):
{json.dumps(caller['provided_fields'], ensure_ascii=False)}

Rules:
- Speak like a person on the phone: one or two short sentences per turn.
- Follow your goal exactly. Refuse anything your goal says to refuse.
- When the agent asks you to confirm something your goal allows, start your reply with "Yes, I confirm".
- When the agent asks to confirm something your goal does not allow, start your reply with "No".
- Do not repeat the same request more than twice. If the agent has answered as well as it can, accept it.
- When your goal is complete, when you have nothing more to ask, or when the agent says goodbye, reply with only {STOP}"""


class LLMCaller:
    def __init__(self, client, caller: dict):
        self.client = client
        self.messages = [{"role": "system", "content": caller_prompt(caller)}]
        self.usage = {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0}

    def reply(self, agent_text: str) -> str:
        # Roles are mirrored: the agent's words are the simulator's "user" input.
        self.messages.append({"role": "user", "content": agent_text})
        out = self.client.complete(self.messages, temperature=0.0, max_tokens=200)
        self.usage["input_tokens"] += out.usage.get("input_tokens", 0)
        self.usage["output_tokens"] += out.usage.get("output_tokens", 0)
        self.usage["llm_calls"] += 1
        text = THINK.sub("", out.content or "").strip() or STOP
        self.messages.append({"role": "assistant", "content": text})
        return text


class ScriptedCaller:
    def __init__(self, caller: dict):
        self.opened = False
        self.usage = {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0}

    def reply(self, agent_text: str) -> str:
        if not self.opened:
            self.opened = True
            return "Hello, I have a request about my enquiry."
        if "goodbye" in agent_text.lower():
            return STOP
        return "Yes, I confirm."
