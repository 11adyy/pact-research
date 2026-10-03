"""Opt-in paired LLM experiment. Never substitutes offline outputs for API results.

python -m tooling.pact_evaluation.live --out experiments/pact_evaluation/live-results
"""

from __future__ import annotations

import argparse
import copy
import logging
import os
import random
import time
from pathlib import Path

from tooling.pact_evaluation import operations as ops

from .fixtures import cases, ground_truth, hash_json, materialize, public_input
from .run import emit, provenance, write_json
from .runner import TrialRunner
from .statistics import paired_comparisons, summarize


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cases-per-task", type=int, default=25)
    p.add_argument("--repetitions", type=int, default=3)
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--seed", type=int, default=20261002)
    p.add_argument("--max-api-calls", type=int, default=4000)
    args = p.parse_args()
    if args.cases_per_task < 1 or args.repetitions < 1:
        p.error("counts must be positive")
    if not os.environ.get("OPENAI_API_KEY"):
        p.error("OPENAI_API_KEY is required; no fallback is performed")
    planned = (
        4 * args.cases_per_task * args.repetitions * 10
    )  # single + three staged arms x 3 calls
    if planned > args.max_api_calls:
        p.error(f"{planned} planned API calls exceed --max-api-calls")
    out = args.out.resolve()
    if (out / "trials.jsonl").exists():
        p.error("trials.jsonl exists; choose a new output directory")
    out.mkdir(parents=True, exist_ok=True)
    logging.getLogger("pact_runtime").setLevel(logging.CRITICAL)
    dataset = cases(args.cases_per_task, args.seed)
    write_json(out / "dataset.json", dataset)
    hashes = materialize(out / "fixtures")
    manifest = provenance(args.seed, True)
    manifest.update(
        model=args.model,
        planned_api_calls=planned,
        config=vars(args) | {"out": str(out)},
        dataset_sha256=hash_json(dataset),
        fixture_sha256=hashes,
        scope="exact-oracle controlled tasks; temperature 0; model seeds vary by repetition; no model-based judge; no seed determinism guarantee",
    )
    write_json(out / "manifest.json", manifest)
    runners = {
        arm: TrialRunner(out / "fixtures", arm)
        for arm in ["transport", "manual_guarded", "pact"]
    }
    jobs = [
        (c, r, a)
        for c in dataset
        for r in range(args.repetitions)
        for a in ["single", "transport", "manual_guarded", "pact"]
    ]
    random.Random(args.seed).shuffle(jobs)
    rows = []
    for i, (case, rep, arm) in enumerate(jobs):
        c = copy.deepcopy(case)
        c.update(live=True, model=args.model, model_seed=args.seed + rep)
        if arm == "single":
            data = public_input(c)
            data["run_id"] = f"{c['case_id']}:{rep}:single"
            start = time.perf_counter_ns()
            error = None
            actual = None
            usage = {}
            status = "completed"
            try:
                output, usage = ops.model_stage("single", data)
                actual = {k: output.get(k) for k in ["value", "label"]}
            except Exception as exc:  # noqa: BLE001 -- retain every experimental failure
                status = "failed"
                error = {"type": type(exc).__name__, "message": str(exc)}
            row = {
                "arm": arm,
                "task": c["task"],
                "case_id": c["case_id"],
                "repetition": rep,
                "status": status,
                "correct": status == "completed" and actual == ground_truth(c),
                "actual": actual,
                "expected": ground_truth(c),
                "latency_ms": (time.perf_counter_ns() - start) / 1e6,
                "error": error,
                "tokens_in": usage.get("prompt_tokens", 0),
                "tokens_out": usage.get("completion_tokens", 0),
            }
        else:
            row = runners[arm].run(c, rep)
        emit(out / "trials.jsonl", row)
        rows.append(row)
        print(
            f"live {i + 1}/{len(jobs)} {arm} {case['case_id']} {row['status']} correct={row['correct']}",
            flush=True,
        )
    summary = {
        "accuracy_latency": summarize(rows),
        "paired_overhead_ms": paired_comparisons(rows, reference="manual_guarded"),
        "tokens": {
            a: {
                "input": sum(r["tokens_in"] for r in rows if r["arm"] == a),
                "output": sum(r["tokens_out"] for r in rows if r["arm"] == a),
            }
            for a in ["single", "transport", "manual_guarded", "pact"]
        },
        "scope": "task-family proof of concept, not an open-ended agent benchmark or deployment safety claim",
    }
    write_json(out / "summary.json", summary)
    print(out)


if __name__ == "__main__":
    main()
