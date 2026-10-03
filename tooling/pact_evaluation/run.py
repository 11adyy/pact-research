"""Run: python -m tooling.pact_evaluation.run --out experiments/pact_evaluation/results

Default mode is entirely offline. No runtime code is patched by the experiment.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import logging
import os
import platform
import random
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from .fixtures import cases, ground_truth, hash_json, materialize
from .runner import ARMS, TrialRunner
from .statistics import paired_comparisons, summarize

REPO = Path(__file__).resolve().parents[2]


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def emit(path, obj):
    with path.open("a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def provenance(seed, live):
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        head = None
    files = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((REPO / "runtime").rglob("*.py"))
    }
    harness = {
        str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(Path(__file__).parent.glob("*.py"))
    }
    clock = time.get_clock_info("perf_counter")
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "git_head": head,
        "python": sys.version,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "clock_resolution_s": clock.resolution,
        "seed": seed,
        "mode": "live_llm" if live else "offline_deterministic",
        "runtime_sha256": files,
        "harness_sha256": harness,
        "timing_scope": "warm process; real YAML loading, engine, scheduler, binding/transport and gates; initialization separately recorded; audit off; logs disabled",
        "parallel_experiments": "one trial at a time; concurrency only inside its declared fan-out",
        "historical_results": "not imported into this run",
        "live_credentials_present": bool(os.environ.get("OPENAI_API_KEY")),
    }


def fault_scenarios():
    return [
        {
            "name": "service_exception",
            "fault": "exception",
            "fault_op": "solve",
            "expect": "contain",
        },
        {
            "name": "missing_output",
            "fault": "missing_output",
            "fault_op": "solve",
            "expect": "contain",
        },
        {
            "name": "wrong_intermediate_type",
            "fault": "wrong_type",
            "fault_op": "verify",
            "expect": "contain",
        },
        {
            "name": "null_intermediate",
            "fault": "null_output",
            "fault_op": "verify",
            "expect": "contain",
        },
        {
            "name": "negative_semantic_result",
            "fault": "semantic_negative",
            "fault_op": "solve",
            "expect": "contain",
        },
        {
            "name": "plausible_wrong_result",
            "fault": "semantic_positive",
            "fault_op": "solve",
            "expect": "contain",
        },
        {
            "name": "terminal_output_type",
            "fault": "terminal_wrong_type",
            "fault_op": "commit",
            "expect": "reject",
        },
        {"name": "low_trust", "trust": "sandbox", "expect": "contain"},
        {"name": "unconfirmed_effect", "confirmed": False, "expect": "contain"},
        {"name": "cross_tenant", "target_tenant_id": "tenant-b", "expect": "contain"},
        {"name": "missing_tenant", "tenant": None, "expect": "contain"},
        {
            "name": "missing_target_tenant",
            "target_tenant_id": None,
            "expect": "contain",
        },
        {
            "name": "transient_recovered",
            "fault": "transient",
            "fault_op": "solve",
            "skill": "evaluation.retry",
            "expect": "recover",
        },
        {
            "name": "transient_no_retry",
            "fault": "transient",
            "fault_op": "solve",
            "expect": "contain",
        },
        {
            "name": "step_timeout",
            "fault": "slow",
            "fault_op": "solve",
            "fault_delay_ms": 30,
            "skill": "evaluation.timeout",
            "expect": "contain",
        },
        {
            "name": "late_effect_after_timeout",
            "fault": "slow",
            "fault_op": "commit",
            "fault_delay_ms": 30,
            "skill": "evaluation.effect_timeout",
            "expect": "contain",
        },
    ]


def robustness(runners, dataset, out, n=25, seed=20261002):
    rows = []
    rng = random.Random(seed + 1)
    tasks = sorted({c["task"] for c in dataset})
    groups = {task: [c for c in dataset if c["task"] == task] for task in tasks}
    selected = [
        groups[tasks[i % len(tasks)]][i // len(tasks)]
        for i in range(min(n, min(map(len, groups.values())) * len(tasks)))
    ]
    for scenario in fault_scenarios():
        jobs = [(arm, c) for c in selected for arm in ARMS]
        rng.shuffle(jobs)
        for arm, c in jobs:
            case = copy.deepcopy(c)
            case["case_id"] = scenario["name"] + ":" + case["case_id"]
            for k in ["fault", "fault_op", "fault_delay_ms", "target_tenant_id"]:
                if k in scenario:
                    case[k] = scenario[k]
            r = runners[arm].run(
                case,
                skill=scenario.get("skill"),
                trust=scenario.get("trust", "elevated"),
                confirmed=scenario.get("confirmed", True),
                tenant=scenario.get("tenant", "tenant-a"),
            )
            r["scenario"] = scenario["name"]
            r["expected_behavior"] = scenario["expect"]
            r["task"] = scenario["name"]  # Summaries stratified by scenario.
            r["containment"] = r["status"] == "failed" and not r["effects"]
            r["detected"] = r["status"] == "failed"
            r["oracle_violation"] = not r["correct"]
            r["false_success"] = r["status"] == "completed" and not r["correct"]
            r["expectation_met"] = (
                r["correct"]
                if scenario["expect"] == "recover"
                else r["detected"]
                if scenario["expect"] == "reject"
                else r["containment"]
            )
            fault = case.get("fault_op")
            calls = [call["operation"] for call in r["calls"]]
            first = calls.index(fault) if fault in calls else None
            r["downstream_calls_after_fault"] = (
                len([op for op in calls[first + 1 :] if op != "integrity"])
                if first is not None
                else 0
            )
            rows.append(r)
            emit(out / "robustness.jsonl", r)
        print("robustness:", scenario["name"], flush=True)
    return rows


def structural(runners, dataset, out):
    rows = []
    for variant in ["bad_dependency", "cycle", "read_only"]:
        for c in dataset[:10]:
            r = runners["pact"].run(c, skill=f"evaluation.{variant}")
            r.update(
                scenario=variant,
                expectation_met=r["status"] == "failed"
                and not r["calls"]
                and not r["effects"],
            )
            rows.append(r)
    write_json(out / "structural.json", rows)
    return rows


def substitution(root, dataset, out):
    before = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("skills/**/skill.yaml")
    }
    rows = []
    for arm in ["pact", "pact_static_binding"]:
        runner = TrialRunner(root, arm)
        for c in dataset[:: max(1, len(dataset) // 40)]:
            runner.original_resolver.active_binding_map._cache = {}
            runner.binding_executor.invalidate_plan_cache()
            initial = runner.run(c)
            runner.activate_alternate()
            alternate = runner.run(c, repetition=1)
            observed = alternate["bindings"].get("s1")
            rows.append(
                {
                    "arm": arm,
                    "case_id": c["case_id"],
                    "correct_before": initial["correct"],
                    "correct_after": alternate["correct"],
                    "selected_binding_before": initial["bindings"].get("s1"),
                    "selected_binding": observed,
                    "substitution_observed": observed == "eval_solve_zalternate",
                }
            )
    after = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("skills/**/skill.yaml")
    }
    result = {
        "skill_files_changed": sum(before[k] != after[k] for k in before),
        "reused_workflows": 4,
        "shared_capabilities": 4,
        "selection_override_entries": 1,
        "runs": rows,
        "scope": "mechanical edit count and interface portability; not human developer productivity",
    }
    write_json(out / "substitution.json", result)
    return result


def scaling(runners, dataset, out, reps=20, seed=20261002):
    rows = []
    rng = random.Random(seed + 2)
    jobs = [
        (length, delay, rep, arm)
        for length in [1, 2, 8, 16, 32]
        for delay in [0, 1]
        for rep in range(reps)
        for arm in ["transport", "pact", "pact_static_binding"]
    ]
    rng.shuffle(jobs)
    for length, delay, rep, arm in jobs:
        c = copy.deepcopy(dataset[rep % len(dataset)])
        c["task"] = "sum"
        c["service_delay_ms"] = delay
        # Identity workloads test execution equivalence, not solver accuracy.
        c["value"] = ground_truth(c)["value"]
        c["label"] = "sum"
        c["case_id"] = f"chain{length}-delay{delay}-input{rep % len(dataset)}"
        r = runners[arm].run(c, rep, skill=f"evaluation.chain{length}", length=length)
        r["task"] = f"chain{length}-delay{delay}"
        r["length"] = length
        r["service_delay_ms"] = delay
        rows.append(r)
        emit(out / "scaling.jsonl", r)
    return rows


def fanout(root, dataset, out, reps=12):
    rows = []
    runners = {a: TrialRunner(root, a) for a in ["transport", "pact"]}
    for width in [1, 2, 4, 8]:
        for workers in [1, 4]:
            for rep in range(reps):
                c = copy.deepcopy(dataset[rep % len(dataset)])
                c.update(width=width, service_delay_ms=5)
                c["case_id"] = f"fanout{width}-worker{workers}-input{rep}"
                for arm in (
                    ["transport", "pact"] if rep % 2 == 0 else ["pact", "transport"]
                ):
                    r = runners[arm].run(
                        c, rep, skill=f"evaluation.fanout{width}", workers=workers
                    )
                    r["width"] = width
                    r["workers"] = workers
                    r["task"] = f"fanout{width}-workers{workers}"
                    r["expectation_met"] = (
                        r["status"] == "completed" and len(r["calls"]) == width + 1
                    )
                    rows.append(r)
    write_json(out / "fanout.json", rows)
    return rows


def report(summary, out):
    healthy = summary["healthy"]
    robust = summary["robustness"]
    lines = [
        "# PACT runtime evaluation",
        "",
        "**Measured mode: offline deterministic systems evaluation. No live model run was performed.**",
        "",
        "The supplied runtime is evaluated unchanged. Baselines use identical workload functions. `transport` uses the same real PythonCallInvoker, including per-call threads. `manual_guarded` adds independent checks and the same domain invariant; it also validates output types more strictly. Full PACT and manual_guarded have four workload calls plus one post gate; direct/transport omit the gate. Primary paired latency comparisons use manual_guarded; transport comparisons also appear separately. All arms have equal instrumentation. No synthetic timing is reported as inference latency.",
        "",
        "## Healthy workloads",
        "",
        "| Arm | Task | Cases | Runs | All-repeat success | Mean ms | 95% case-bootstrap CI | p95 ms |",
        "|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for s in healthy:
        lines.append(
            f"| {s['arm']} | {s['task']} | {s['independent_cases']} | {s['runs']} | {s['success_rate']:.1%} | {s['mean_latency_ms']:.3f} | [{s['mean_latency_bootstrap_95'][0]:.3f}, {s['mean_latency_bootstrap_95'][1]:.3f}] | {s['p95_ms']:.3f} |"
        )
    lines += [
        "",
        "## Fault and policy scenarios",
        "",
        "| Scenario | Arm | Cases | Expected behavior met | 95% Wilson CI |",
        "|---|---|---:|---:|---|",
    ]
    for s in robust:
        if s["arm"] in [
            "transport",
            "manual_guarded",
            "pact",
            "pact_no_policy",
            "pact_no_validation",
        ]:
            lo, hi = s["success_wilson_95"]
            lines.append(
                f"| {s['task']} | {s['arm']} | {s['independent_cases']} | {s['success_rate']:.1%} | [{lo:.3f}, {hi:.3f}] |"
            )
    lines += [
        "",
        "## Concrete limitations observed",
        "",
        "Full raw trials retain failures, exceptions, operation order, side-effect ledger, structured traces, and token counters. A detected error is distinct from containment (no ledger write), and correct task output is distinct from mere completion. Terminal-output failures can be detected after an effect, so they are not scored as containment successes.",
        "",
        f"Structural invalidity was rejected before a service call in {summary['structural_successes']}/{summary['structural_trials']} trials.",
        f"Live-model experiment: {summary['live_status']}.",
        "",
        "## Reuse and substitution",
        "",
        f"Four workflows reuse four capability contracts. Swapping the solver requires one selection override and changed {summary['substitution']['skill_files_changed']} skill files. The static-binding ablation cannot follow a subsequent active-map change without rebuilding its frozen selection. This is a mechanical change-footprint measurement, not a developer-time experiment.",
        "",
        "## Interpretation",
        "",
        "These results characterize a runtime over controlled deterministic services. They do not establish better LLM reasoning, robustness to prompt injection, statistical generalization to real deployments, or safety of arbitrary tools. Domain gates detect the declared invariant only; a plausible but wrong positive output is deliberately included to expose this limit. Trace-off tests use the actual public option and report actual trace content, rather than assuming the option suppresses every trace.",
        "",
        "Timing comparisons use paired per-case averages and seeded bootstrap confidence intervals. Repeated deterministic runs are not counted as independent cases. Wilson intervals describe finite test-case coverage, not real-world failure probabilities. Audit persistence is disabled in all arms and therefore excluded from cost claims. Logging is disabled before timing. Runtime cold construction is reported separately. Order is randomized and each trial clears the circuit breaker to prevent injected failures contaminating later trials.",
        "",
        "## Reproduction",
        "",
        "```bash",
        "python -m tooling.pact_evaluation.run --out experiments/pact_evaluation/results-reproduction --cases-per-task 100 --repetitions 3 --fault-cases 100 --scaling-reps 20 --seed 20261002",
        'python -m pytest tooling/pact_evaluation/test_evaluation.py -o addopts="" -q',
        "```",
        "",
        "For a live LLM run, use the separate command in README.md. It uses new results and never silently falls back to deterministic functions. Historical benchmark files are not counted as evidence in this evaluation.",
        "",
        "See `summary.json`, `manifest.json`, `dataset.json`, scenario definitions, generated YAML fixtures, and JSONL records for exact denominators and hashes.",
    ]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path, default=REPO / "experiments/pact_evaluation/results"
    )
    parser.add_argument("--cases-per-task", type=int, default=100)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--fault-cases", type=int, default=100)
    parser.add_argument("--scaling-reps", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261002)
    args = parser.parse_args()
    for value in [
        args.cases_per_task,
        args.repetitions,
        args.fault_cases,
        args.scaling_reps,
    ]:
        if value < 1:
            parser.error("counts must be positive")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ["healthy.jsonl", "robustness.jsonl", "scaling.jsonl"]:
        if (out / name).exists():
            parser.error(f"{out / name} exists; choose a new output directory")
    # Use explicit deterministic offline mode even when a host has credentials.
    os.environ["PACT_RUNTIME_LOG_LEVEL"] = "CRITICAL"
    logging.getLogger("pact_runtime").setLevel(logging.CRITICAL)
    logging.getLogger("runtime").setLevel(logging.CRITICAL)
    fixture_root = out / "fixtures"
    fixture_hashes = materialize(fixture_root)
    dataset = cases(args.cases_per_task, args.seed)
    write_json(out / "dataset.json", dataset)
    write_json(out / "scenarios.json", fault_scenarios())
    manifest = provenance(args.seed, False)
    manifest.update(
        config=vars(args) | {"out": str(out)},
        dataset_sha256=hash_json(dataset),
        fixture_sha256=fixture_hashes,
    )
    write_json(out / "manifest.json", manifest)
    runners = {arm: TrialRunner(fixture_root, arm) for arm in ARMS}
    # Warm the shared code paths. No warmup trial enters a reported denominator.
    for runner in runners.values():
        runner.run(dataset[0])
    jobs = [
        (c, rep, arm)
        for c in dataset
        for rep in range(args.repetitions)
        for arm in ARMS
    ]
    random.Random(args.seed).shuffle(jobs)
    healthy = []
    start = time.perf_counter()
    for i, (c, rep, arm) in enumerate(jobs):
        r = runners[arm].run(c, rep)
        healthy.append(r)
        emit(out / "healthy.jsonl", r)
        if i % 500 == 0:
            print(f"healthy: {i}/{len(jobs)}", flush=True)
    robust = robustness(
        runners, dataset, out, min(args.fault_cases, len(dataset)), args.seed
    )
    structural_rows = structural(runners, dataset, out)
    sub = substitution(fixture_root, dataset, out)
    scales = scaling(runners, dataset, out, args.scaling_reps, args.seed)
    fan = fanout(fixture_root, dataset, out)
    summary = {
        "healthy": summarize(healthy),
        "paired_latency": paired_comparisons(healthy, reference="manual_guarded"),
        "paired_latency_transport": paired_comparisons(healthy),
        "robustness": summarize(robust, "expectation_met"),
        "scaling": summarize(scales),
        "scaling_paired_latency": paired_comparisons(scales),
        "fanout": summarize(fan, "expectation_met"),
        "structural_successes": sum(r["expectation_met"] for r in structural_rows),
        "structural_trials": len(structural_rows),
        "substitution": sub,
        "initialization_ms": {a: r.initialization_ms for a, r in runners.items()},
        "trace_off_structured_steps": sorted(
            {len(r["trace"]) for r in healthy if r["arm"] == "pact_trace_off"}
        ),
        "total_trials": len(healthy)
        + len(robust)
        + len(structural_rows)
        + len(sub["runs"]) * 2
        + len(scales)
        + len(fan),
        "elapsed_seconds": time.perf_counter() - start,
        "live_status": "not run; OPENAI_API_KEY absent"
        if not os.environ.get("OPENAI_API_KEY")
        else "not run; offline mode explicitly selected",
    }
    write_json(out / "summary.json", summary)
    with (out / "healthy_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary["healthy"][0]))
        writer.writeheader()
        writer.writerows(summary["healthy"])
    report(summary, out)
    print(
        json.dumps(
            {
                "out": str(out),
                "trials": summary["total_trials"],
                "elapsed_seconds": summary["elapsed_seconds"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
