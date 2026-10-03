"""Shared workload implementations, used unchanged by every execution strategy.

Faults are intentional test stimuli. Effects are an in-memory ledger, never real
filesystem, network, payment, or production writes. The live adapter is opt-in.
"""

from __future__ import annotations

import copy
import json
import os
import re
import threading
import time
import urllib.request

LOCK = threading.Lock()
CALLS: list[dict] = []
EFFECTS: list[dict] = []
COUNTS: dict[tuple[str, str], int] = {}


def reset():
    with LOCK:
        CALLS.clear()
        EFFECTS.clear()
        COUNTS.clear()


def snapshot():
    with LOCK:
        return copy.deepcopy(CALLS), copy.deepcopy(EFFECTS)


def record(op, data):
    rid = data.get("run_id", "invalid") if isinstance(data, dict) else "invalid"
    with LOCK:
        key = (rid, op)
        COUNTS[key] = COUNTS.get(key, 0) + 1
        CALLS.append(
            {
                "operation": op,
                "run_id": rid,
                "attempt": COUNTS[key],
                "at_ns": time.perf_counter_ns(),
                "tokens_in": 0,
                "tokens_out": 0,
            }
        )
        return COUNTS[key], len(CALLS) - 1


def model_stage(op, data):
    """All staged live arms call the exact same prompt and parser here."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Live evaluation requires OPENAI_API_KEY")
    prompts = {
        "normalize": "Copy the JSON object. For task text, extract all item:<name>=<integer> pairs from text into values and names arrays. Return the object as JSON.",
        "solve": "Copy the object and add value and label. For sum/text, value=sum(values), label=task. For max, value=max(values), label=max. For decision, choose eligible=true option with maximum sum(weight[j]*scores[j]); ties go to lowest index. value=that score; label=that option name. Return JSON.",
        "verify": "Copy the object exactly. Do not change value or label. Return JSON.",
        "single": "Solve this task in one response. For sum/text, sum values (for text first extract item:<name>=<integer> pairs), label=task. For max, value=max(values), label=max. For decision, choose eligible=true option maximizing sum(weight[j]*scores[j]); ties go to lowest index. Return JSON with integer value and string label.",
    }
    body = json.dumps(
        {
            "model": data.get("model", "gpt-4o-mini"),
            "temperature": 0,
            "seed": data.get("model_seed", 42),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": prompts[op]},
                {"role": "user", "content": json.dumps(data)},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    # No API-level retries: failed requests remain visible experimental outcomes.
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.load(response)
    content = json.loads(result["choices"][0]["message"]["content"])
    usage = result.get("usage", {})
    return content, usage


def _operate(op, data, alternate=False):
    attempt, index = record(op, data)
    if not isinstance(data, dict):
        # Deliberately permissive service: the runtime must enforce its contract.
        return {"data": data}
    fault = data.get("fault") if data.get("fault_op") == op else None
    if fault == "exception" or (fault == "transient" and attempt == 1):
        raise RuntimeError("injected service failure")
    if fault == "slow":
        time.sleep(data.get("fault_delay_ms", 30) / 1000)
    delay = data.get("service_delay_ms", 0)
    if delay:
        time.sleep(delay / 1000)
    if fault == "missing_output":
        return {"unexpected": "missing data"}
    if fault == "wrong_type":
        return {"data": "not an object"}
    if fault == "null_output":
        return {"data": None}
    d = copy.deepcopy(data)
    if d.get("live") and op in {"normalize", "solve", "verify"}:
        original = d.copy()
        d, usage = model_stage(op, d)
        # Identity/control fields belong to the harness, not generated text.
        for field in ["run_id", "live", "model", "model_seed", "task"]:
            if field in original:
                d[field] = original[field]
        with LOCK:
            CALLS[index].update(
                tokens_in=usage.get("prompt_tokens", 0),
                tokens_out=usage.get("completion_tokens", 0),
            )
    elif op == "normalize" and d["task"] == "text":
        pairs = re.findall(r"item:([A-Za-z0-9_]+)=(\d+)", d["text"])
        d["values"] = [int(v) for _, v in pairs]
        d["names"] = [name for name, _ in pairs]
    elif op == "solve":
        if d["task"] in {"sum", "text"}:
            # Alternative implementation uses a loop, not built-in sum.
            value = 0
            if alternate:
                for v in d["values"]:
                    value += v
            else:
                value = sum(d["values"])
            d.update(value=value, label=d["task"])
        elif d["task"] == "max":
            d.update(
                value=sorted(d["values"])[-1] if alternate else max(d["values"]),  # noqa: FURB192 -- intentionally distinct alternate solver
                label="max",
            )
        elif d["task"] == "decision":
            candidates = [
                (sum(w * s for w, s in zip(d["weights"], o["scores"])), -i, o["name"])
                for i, o in enumerate(d["options"])
                if o["eligible"]
            ]
            score, _, label = max(candidates)
            d.update(value=score, label=label)
    elif op == "commit":
        with LOCK:
            EFFECTS.append(
                {
                    "run_id": d["run_id"],
                    "value": d.get("value"),
                    "label": d.get("label"),
                }
            )
    if fault == "semantic_negative":
        d["value"] = -999
    if fault == "semantic_positive":
        d["value"] = 999999  # Satisfies positivity, but violates the task oracle.
    if fault == "terminal_wrong_type":
        return {"data": ["not", "an", "object"]}
    return {"data": d}


def normalize(data):
    return _operate("normalize", data)


def solve(data):
    return _operate("solve", data)


def solve_alternate(data):
    return _operate("solve", data, alternate=True)


def verify(data):
    return _operate("verify", data)


def commit(data, target_tenant_id=None):
    return _operate("commit", data)


def identity(data):
    return _operate("identity", data)


def integrity(data):
    record("integrity", data)
    allowed = (
        isinstance(data, dict)
        and type(data.get("value")) is int
        and data["value"] >= 0
        and isinstance(data.get("label"), str)
    )
    return {
        "allowed": allowed,
        "reason": "nonnegative integer value and string label required",
    }


def merge(data, branches):
    record("merge", data)
    if len(branches) != data["width"]:
        raise ValueError("missing fan-out branch")
    return {"data": copy.deepcopy(data)}
