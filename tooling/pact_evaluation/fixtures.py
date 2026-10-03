"""Seeded cases and YAML fixtures for the real loaders/binding/service stack."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import yaml

CAPS = ["normalize", "solve", "verify", "commit", "identity", "integrity", "merge"]
PIPELINE = ["normalize", "solve", "verify", "commit"]


def ground_truth(c):
    # Independent oracle, derived from generated latent values, never model output.
    if c["task"] == "decision":
        scores = []
        for i, option in enumerate(c["options"]):
            if option["eligible"]:
                total = 0
                for j in range(len(c["weights"])):
                    total += option["scores"][j] * c["weights"][j]
                scores.append((total, i, option["name"]))
        score, _, name = min(scores, key=lambda x: (-x[0], x[1]))
        return {"value": score, "label": name}
    values = c["oracle_values"] if c["task"] == "text" else c["values"]
    if c["task"] == "max":
        answer = values[0]
        for value in values[1:]:
            answer = max(answer, value)
    else:
        answer = 0
        for value in values:
            answer += value
    return {"value": answer, "label": c["task"]}


def cases(n=100, seed=20261002):
    rng = random.Random(seed)
    out = []
    for task in ["sum", "max", "decision", "text"]:
        for i in range(n):
            c = {
                "case_id": f"{task}-{i:04d}",
                "task": task,
                "target_tenant_id": "tenant-a",
                "values": [rng.randrange(100) for _ in range(rng.randint(2, 30))],
            }
            if task == "decision":
                c["weights"] = [rng.randint(1, 9) for _ in range(4)]
                c["options"] = [
                    {
                        "name": f"option-{j}",
                        "scores": [rng.randrange(20) for _ in range(4)],
                        "eligible": j == 0 or rng.random() > 0.3,
                    }
                    for j in range(8)
                ]
            if task == "text":
                c["oracle_values"] = c.pop("values")
                c["text"] = (
                    "; ".join(
                        f"item:node_{j}={v}" for j, v in enumerate(c["oracle_values"])
                    )
                    + "; unrelated 1234"
                )
            out.append(c)
    return out


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


def skill(sid, steps):
    return {
        "id": sid,
        "version": "1.0.0",
        "name": sid,
        "description": "Evaluation fixture",
        "inputs": {
            "data": {"type": "object", "required": True},
            "target_tenant_id": {"type": "string"},
        },
        "outputs": {"result": {"type": "object", "required": True}},
        "steps": steps,
    }


def chain(length=4, mode="normal"):
    ops = PIPELINE if length == 4 else ["identity"] * length
    steps = []
    for i, op in enumerate(ops):
        mapping = {"data": "inputs.data" if i == 0 else f"vars.s{i - 1}"}
        if op == "commit":
            mapping["target_tenant_id"] = "inputs.target_tenant_id"
        config = {}
        if mode == "retry" and op == "solve":
            config["retry"] = {"max_attempts": 2, "backoff_seconds": 0}
        if mode == "timeout" and op == "solve":
            config["timeout_seconds"] = 0.005
        if mode == "effect_timeout" and op == "commit":
            config["timeout_seconds"] = 0.005
        if mode == "bad_dependency" and i == 0:
            config["depends_on"] = ["absent"]
        if mode == "cycle":
            config["depends_on"] = [f"s{(i - 1) % length}"]
        if mode == "read_only" and i == 0:
            target = "frame.context"
        else:
            target = "outputs.result" if i == length - 1 else f"vars.s{i}"
        steps.append(
            {
                "id": f"s{i}",
                "uses": f"eval.{op}.run",
                "input": mapping,
                "output": {"data": target},
                "config": config,
            }
        )
    return steps


def materialize(root: Path):
    dump(
        root / "services/official/evaluation.yaml",
        {
            "id": "eval_service",
            "kind": "pythoncall",
            "module": "tooling.pact_evaluation.operations",
        },
    )
    defaults = {}
    for op in CAPS:
        cid = f"eval.{op}.run"
        fields = {"data": {"type": "object", "required": True}}
        if op == "commit":
            fields["target_tenant_id"] = {"type": "string", "required": True}
        if op == "merge":
            fields["branches"] = {"type": "array", "required": True}
        output = (
            {
                "allowed": {"type": "boolean", "required": True},
                "reason": {"type": "string"},
            }
            if op == "integrity"
            else {"data": {"type": "object", "required": True}}
        )
        cap = {
            "id": cid,
            "version": "1.0.0",
            "description": "Controlled systems evaluation operation",
            "inputs": fields,
            "outputs": output,
            "metadata": {},
            "properties": {"deterministic": True, "side_effects": op == "commit"},
        }
        if op == "solve":
            cap["safety"] = {
                "mandatory_post_gates": [
                    {"capability": "eval.integrity.run", "on_fail": "block"}
                ]
            }
        if op == "commit":
            cap["safety"] = {
                "trust_level": "elevated",
                "requires_confirmation": True,
                "allowed_targets": ["same_tenant"],
            }
        dump(root / f"capabilities/{cid}.yaml", cap)
        for suffix in ["default", "alternate"] if op == "solve" else ["default"]:
            bid = f"eval_{op}_{'zalternate' if suffix == 'alternate' else suffix}"
            mapping = (
                {"allowed": "response.allowed", "reason": "response.reason"}
                if op == "integrity"
                else {"data": "response.data"}
            )
            binding = {
                "id": bid,
                "capability": cid,
                "service": "eval_service",
                "protocol": "pythoncall",
                "operation": "solve_alternate" if suffix == "alternate" else op,
                "request": {f: f"input.{f}" for f in fields},
                "response": mapping,
                "metadata": {"status": "stable", "conformance_profile": "standard"},
            }
            dump(root / f"bindings/official/{cid}/{bid}.yaml", binding)
        defaults[cid] = f"eval_{op}_default"
    dump(root / "policies/official_default_selection.yaml", {"defaults": defaults})
    for task in ["sum", "max", "decision", "text"]:
        dump(
            root / f"skills/evaluation/pipeline/{task}/skill.yaml",
            skill(f"evaluation.{task}", chain()),
        )
    for mode in [
        "retry",
        "timeout",
        "effect_timeout",
        "bad_dependency",
        "cycle",
        "read_only",
    ]:
        dump(
            root / f"skills/evaluation/variants/{mode}/skill.yaml",
            skill(f"evaluation.{mode}", chain(mode=mode)),
        )
    for length in [1, 2, 8, 16, 32]:
        dump(
            root / f"skills/evaluation/scaling/n{length}/skill.yaml",
            skill(f"evaluation.chain{length}", chain(length)),
        )
    for width in [1, 2, 4, 8]:
        steps = [
            {
                "id": f"b{i}",
                "uses": "eval.identity.run",
                "input": {"data": "inputs.data"},
                "output": {"data": f"vars.b{i}"},
                "config": {"depends_on": []},
            }
            for i in range(width)
        ]
        steps.append(
            {
                "id": "join",
                "uses": "eval.merge.run",
                "input": {
                    "data": "inputs.data",
                    "branches": [f"vars.b{i}" for i in range(width)],
                },
                "output": {"data": "outputs.result"},
                "config": {"depends_on": [f"b{i}" for i in range(width)]},
            }
        )
        dump(
            root / f"skills/evaluation/fanout/w{width}/skill.yaml",
            skill(f"evaluation.fanout{width}", steps),
        )
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.yaml"))
    }


def public_input(case):
    # Ground truth fields are never sent to runtime or live model.
    return {k: v for k, v in case.items() if not k.startswith("oracle_")}


def hash_json(data):
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
