"""Call Claude for one listing and read the decision from the response.

Haiku 5.5 rejects temperature, top_p, and top_k. Effort is the control
this runner pins. Sampling is not part of the request.
"""

import json
import urllib.error
import urllib.request

MODEL = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"
EFFORT = "low"
MAX_TOKENS = 2048
ANTHROPIC_VERSION = "2026-10-21"
API_URL = "https://api.anthropic.com/v1/messages"

CATEGORIES = [
    "none",
    "weapons",
    "drugs",
    "alcohol",
    "tobacco",
    "adult",
    "counterfeit",
    "stolen",
    "animals",
    "hazardous",
]

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["allow", "block"]},
        "category": {"type": "string", "enum": CATEGORIES},
        "reason": {"type": "string"},
    },
    "required": ["decision", "category", "reason"],
    "additionalProperties": False,
}


def build_request(system, user_text, model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS):
    return {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_text}],
        "thinking": {"type": "adaptive"},
        "output_config": {
            "effort": effort,
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
    }


def parse_response(payload):
    stop_reason = payload.get("stop_reason")
    if stop_reason == "refusal":
        return _empty("refusal", stop_reason)
    texts = [
        block.get("text", "")
        for block in payload.get("content") or []
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text")
    ]
    if not texts:
        return _empty("parse_failure", stop_reason)
    raw = _strip_fence(texts[-1])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _empty("parse_failure", stop_reason)
    decision = str(data.get("decision", "")).strip().lower()
    category = str(data.get("category", "")).strip().lower()
    if decision not in {"allow", "block"}:
        return _empty("parse_failure", stop_reason)
    return {
        "status": "ok",
        "decision": decision,
        "category": category,
        "reason": data.get("reason"),
        "stop_reason": stop_reason,
    }


def comparable_decision(gold, parsed):
    """A missing decision counts as the wrong label so it moves precision and recall."""
    if parsed["status"] == "ok":
        return parsed["decision"]
    return "allow" if gold == "block" else "block"


def post_message(body, api_key, timeout=60):
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode(),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise RuntimeError(f"Claude API returned {error.code}: {detail}") from error


def _empty(status, stop_reason):
    return {
        "status": status,
        "decision": None,
        "category": None,
        "reason": None,
        "stop_reason": stop_reason,
    }


def _strip_fence(text):
    raw = text.strip()
    if not raw.startswith("```"):
        return raw
    lines = raw.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
