"""Provider-neutral LLM client with tool calling (standard library HTTP only).

Two wire formats cover every provider the team considered:

* ``OpenAICompatibleClient``: OpenAI, Groq and Ollama all expose the same
  ``/chat/completions`` API with tool calls, so one adapter serves all three.
* ``AnthropicClient``: Anthropic's ``/v1/messages`` API.

Internally every message uses one neutral format::

    {"role": "system" | "user" | "assistant" | "tool", "content": str,
     "tool_calls": [{"id": str, "name": str, "arguments": dict}],   # assistant only
     "tool_call_id": str}                                          # tool only

so the agent, simulator and judge never depend on a provider. The provider is
picked with environment variables (see .env.example), which keeps API keys out
of code and lets the paid provider replace the free local one without edits.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

PROVIDERS = {
    # name: (wire format, default base URL, API key variable)
    "openai": ("openai", "https://api.openai.com/v1", "OPENAI_API_KEY"),
    "groq": ("openai", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "ollama": ("openai", "http://localhost:11434/v1", None),
    "anthropic": ("anthropic", "https://api.anthropic.com/v1", "ANTHROPIC_API_KEY"),
}


@dataclass
class Completion:
    content: str
    tool_calls: list = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    latency_s: float = 0.0


class LLMError(RuntimeError):
    pass


def _post(url: str, payload: dict, headers: dict, timeout: float, retries: int = 4) -> dict:
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, data=body, method="POST",
                                         headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")[:500]
            if err.code in (429, 500, 502, 503, 529) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise LLMError(f"HTTP {err.code} from {url}: {detail}") from None
        except (urllib.error.URLError, TimeoutError) as err:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise LLMError(f"Cannot reach {url}: {err}") from None
    raise LLMError("unreachable")


class OpenAICompatibleClient:
    def __init__(self, model: str, base_url: str, api_key: str | None = None,
                 timeout: float = 180.0, extra: dict | None = None):
        self.model, self.base_url, self.api_key = model, base_url.rstrip("/"), api_key
        self.timeout, self.extra = timeout, extra or {}

    @staticmethod
    def to_wire(messages: list[dict]) -> list[dict]:
        wire = []
        for m in messages:
            if m["role"] == "assistant" and m.get("tool_calls"):
                wire.append({"role": "assistant", "content": m.get("content") or None,
                             "tool_calls": [{"id": c["id"], "type": "function",
                                             "function": {"name": c["name"],
                                                          "arguments": json.dumps(c["arguments"])}}
                                            for c in m["tool_calls"]]})
            elif m["role"] == "tool":
                wire.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
            else:
                wire.append({"role": m["role"], "content": m["content"]})
        return wire

    @staticmethod
    def from_wire(data: dict) -> Completion:
        message = data["choices"][0]["message"]
        calls = []
        for i, c in enumerate(message.get("tool_calls") or []):
            raw = c["function"].get("arguments") or "{}"
            try:
                args = json.loads(raw) if isinstance(raw, str) else raw
            except json.JSONDecodeError:
                args = {"_unparsed": raw}
            calls.append({"id": c.get("id") or f"call_{i}", "name": c["function"]["name"], "arguments": args})
        usage = data.get("usage") or {}
        return Completion(content=message.get("content") or "", tool_calls=calls,
                          usage={"input_tokens": usage.get("prompt_tokens", 0),
                                 "output_tokens": usage.get("completion_tokens", 0)})

    def complete(self, messages, tools=None, temperature=0.0, max_tokens=800, json_mode=False) -> Completion:
        payload = {"model": self.model, "messages": self.to_wire(messages),
                   "temperature": temperature, "max_tokens": max_tokens, **self.extra}
        if tools:
            payload["tools"] = [{"type": "function", "function": t} for t in tools]
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        start = time.perf_counter()
        result = self.from_wire(_post(f"{self.base_url}/chat/completions", payload, headers, self.timeout))
        result.latency_s = time.perf_counter() - start
        return result


class AnthropicClient:
    def __init__(self, model: str, api_key: str, base_url: str = "https://api.anthropic.com/v1",
                 timeout: float = 180.0):
        self.model, self.api_key, self.base_url, self.timeout = model, api_key, base_url.rstrip("/"), timeout

    @staticmethod
    def to_wire(messages: list[dict]) -> tuple[str, list[dict]]:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        wire: list[dict] = []
        for m in messages:
            if m["role"] == "system":
                continue
            if m["role"] == "assistant":
                blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                blocks += [{"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["arguments"]}
                           for c in m.get("tool_calls") or []]
                wire.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "..."}]})
            elif m["role"] == "tool":
                block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
                if wire and wire[-1]["role"] == "user" and isinstance(wire[-1]["content"], list) \
                        and wire[-1]["content"] and wire[-1]["content"][0].get("type") == "tool_result":
                    wire[-1]["content"].append(block)  # results of parallel calls share one turn
                else:
                    wire.append({"role": "user", "content": [block]})
            else:
                wire.append({"role": "user", "content": m["content"]})
        return system, wire

    @staticmethod
    def from_wire(data: dict) -> Completion:
        text = "".join(b.get("text", "") for b in data.get("content", []) if b["type"] == "text")
        calls = [{"id": b["id"], "name": b["name"], "arguments": b.get("input") or {}}
                 for b in data.get("content", []) if b["type"] == "tool_use"]
        usage = data.get("usage") or {}
        return Completion(content=text, tool_calls=calls,
                          usage={"input_tokens": usage.get("input_tokens", 0),
                                 "output_tokens": usage.get("output_tokens", 0)})

    def complete(self, messages, tools=None, temperature=0.0, max_tokens=800, json_mode=False) -> Completion:
        system, wire = self.to_wire(messages)
        payload = {"model": self.model, "system": system, "messages": wire,
                   "temperature": temperature, "max_tokens": max_tokens}
        if tools:
            payload["tools"] = [{"name": t["name"], "description": t["description"],
                                 "input_schema": t["parameters"]} for t in tools]
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        start = time.perf_counter()
        result = self.from_wire(_post(f"{self.base_url}/messages", payload, headers, self.timeout))
        result.latency_s = time.perf_counter() - start
        return result


def make_client(role: str = "AGENT"):
    """Build a client from env vars, e.g. AGENT_PROVIDER / AGENT_MODEL.

    Falls back to LLM_PROVIDER / LLM_MODEL so one setting can drive the agent,
    simulator and judge. Roles: AGENT, SIMULATOR, JUDGE.
    """
    provider = (os.getenv(f"{role}_PROVIDER") or os.getenv("LLM_PROVIDER") or "").lower()
    model = os.getenv(f"{role}_MODEL") or os.getenv("LLM_MODEL")
    if provider not in PROVIDERS or not model:
        raise LLMError(f"Set LLM_PROVIDER ({'/'.join(PROVIDERS)}) and LLM_MODEL (or {role}_*) in .env")
    wire, default_url, key_var = PROVIDERS[provider]
    api_key = os.getenv(key_var) if key_var else None
    if key_var and not api_key:
        raise LLMError(f"{key_var} is not set")
    base_url = os.getenv(f"{provider.upper()}_BASE_URL") or default_url
    if provider == "ollama" and not base_url.rstrip("/").endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"
    if wire == "anthropic":
        return AnthropicClient(model, api_key, base_url)
    extra = {"reasoning_effort": "none"} if provider == "ollama" else {}
    return OpenAICompatibleClient(model, base_url, api_key, extra=extra)
