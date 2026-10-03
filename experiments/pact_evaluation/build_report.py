"""Generate a report from recorded results. Requires reportlab and matplotlib."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image,
)

p = argparse.ArgumentParser()
p.add_argument(
    "--results", type=Path, default=Path("experiments/pact_evaluation/results")
)
p.add_argument("--pdf", type=Path, required=True)
a = p.parse_args()
r = a.results
repo = Path(__file__).resolve().parents[2]
s = json.loads((r / "summary.json").read_text())
m = json.loads((r / "manifest.json").read_text())
load = lambda name: [json.loads(x) for x in (r / name).read_text().splitlines()]
healthy = load("healthy.jsonl")
robust = load("robustness.jsonl")
scaling = load("scaling.jsonl")
struct = json.loads((r / "structural.json").read_text())
fan = json.loads((r / "fanout.json").read_text())
verified = {}
for field in ["runtime_sha256", "harness_sha256"]:
    bad = [
        name
        for name, digest in m[field].items()
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != digest
    ]
    if bad:
        raise RuntimeError(f"Changed measured source: {bad}")
    verified[field] = len(m[field])
dataset = json.loads((r / "dataset.json").read_text())
assert (
    hashlib.sha256(
        json.dumps(dataset, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    == m["dataset_sha256"]
)
for name, digest in m["fixture_sha256"].items():
    assert hashlib.sha256((r / "fixtures" / name).read_bytes()).hexdigest() == digest
count = (
    len(healthy)
    + len(robust)
    + len(scaling)
    + len(struct)
    + len(fan)
    + len(s["substitution"]["runs"]) * 2
)
assert count == s["total_trials"]
assert len({(x["arm"], x["case_id"], x["repetition"]) for x in healthy}) == len(healthy)
for x in healthy:
    assert x["correct"] == (x["status"] == "completed" and x["actual"] == x["expected"])
(r / "integrity_check.json").write_text(
    json.dumps(
        {
            "source_files_verified": verified,
            "trial_denominator_verified": count,
            "healthy_keys_unique": True,
            "healthy_correctness_flag_verified": True,
        },
        indent=2,
    )
    + "\n"
)

styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="Title2",
        parent=styles["Title"],
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#17354a"),
        spaceAfter=16,
    )
)
styles["BodyText"].fontSize = 9.6
styles["BodyText"].leading = 14
styles["BodyText"].spaceAfter = 8
styles["Heading1"].fontSize = 16
styles["Heading1"].textColor = colors.HexColor("#17354a")
styles["Heading1"].spaceAfter = 12
styles.add(
    ParagraphStyle(name="Small2", parent=styles["BodyText"], fontSize=8, leading=11)
)
styles.add(
    ParagraphStyle(
        name="Cell", parent=styles["BodyText"], fontSize=8, leading=10, spaceAfter=0
    )
)
story = []


def para(t, style="BodyText"):
    story.append(Paragraph(t, styles[style]))


def heading(t):
    para(t, "Heading1")


def table(rows, widths=None):
    cells = [[Paragraph(escape(str(c)), styles["Cell"]) for c in row] for row in rows]
    t = Table(cells, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6eef2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#7d95a5")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f6f8fa")],
                ),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 10))


def page():
    story.append(PageBreak())


def index(rows, arm, task):
    return next(x for x in rows if x["arm"] == arm and x["task"] == task)


def pct(x):
    return f"{x:.0%}"


def interval(x):
    return f"[{x[0]:.3f}, {x[1]:.3f}]"


para("PACT: a reproducible systems evaluation", "Title2")
para(
    "Noah Dylan Pelegrini · Independent Researcher<br/>contact@11adyy.dev<br/>https://github.com/11adyy/pact-research",
    "Small2",
)
para(
    f"Measured {m['created_at'][:10]} · seed {m['seed']} · offline deterministic mode",
    "Small2",
)
heading("Abstract")
native = [x for x in healthy if x["arm"] == "pact"]
para(
    f"We evaluate the supplied, unchanged PACT runtime using controlled services and exact task oracles. The recorded suite contains <b>{count:,} timed or behavioral executions</b>, including {len(healthy):,} healthy runs and {len(robust):,} fault/policy runs. Full PACT produces the exact expected output in {sum(x['correct'] for x in native):,}/{len(native):,} healthy executions. Experiments measure orchestration cost, declared policy enforcement, failure containment, retries, scaling, traces, and binding substitution. Negative probes expose output-validation gaps and effects after timeout. These measurements support bounded systems claims; they do not measure LLM reasoning quality or inference savings."
)
heading("1. Experimental design")
table(
    [
        ["Component", "Recorded protocol"],
        [
            "Tasks",
            "Sum; maximum; constrained weighted selection; tagged-text aggregation",
        ],
        [
            "Healthy cases",
            "100 distinct generated inputs per task; 3 repetitions; 8 arms",
        ],
        ["Robustness", "16 scenarios; 100 distinct inputs per scenario; 8 arms"],
        [
            "Additional probes",
            "30 invalid-structure runs; 160 substitution executions; 600 chain runs; 192 fan-out runs",
        ],
        [
            "Ground truth",
            "Independent exact oracle; oracle-only fields excluded from service/model input",
        ],
        [
            "Measurement",
            "perf_counter_ns; warmup excluded; seeded randomized healthy/scaling order",
        ],
        [
            "Statistics",
            "Case-cluster bootstrap, 2000 draws; paired per-case means; Wilson case intervals",
        ],
    ],
    [100, 405],
)
para(
    "Repeated runs do not increase the independent-case count. The four families are controlled, synthetic workloads, with no held-out real-world benchmark. Trials are serial except declared internal fan-out. Services record an isolated in-memory effect ledger; no production actions occur. Audit persistence is disabled and excluded from the measured cost.",
    "Small2",
)
para(
    f"Environment: Python {m['python'].split()[0]}; {escape(m['platform'])}; {m['cpu_count']} reported CPUs. Shared host, without CPU pinning or control over other tenants. Regression validation briefly overlapped the start of the healthy run; randomized comparisons and intervals remain descriptive of this session, not hardware-independent performance guarantees.",
    "Small2",
)
page()
heading("2. Baselines and healthy correctness")
table(
    [
        ["Arm", "Purpose"],
        ["direct", "Same four functions called directly; orchestration lower bound"],
        [
            "transport",
            "Same functions via the native PythonCallInvoker and per-call threads",
        ],
        [
            "manual_guarded",
            "Transport plus independent policy/type checks and the same integrity gate",
        ],
        [
            "pact",
            "Actual engine, scheduler, mappings, capability contracts and binding resolution",
        ],
        [
            "Ablations",
            "Remove policy metadata; bypass capability checks; trace flag off; freeze bindings",
        ],
    ],
    [105, 400],
)
para(
    "The primary comparator is manual_guarded: both arms make four workload calls plus one integrity-gate call. Its type checks are stricter than the current runtime. Transport/direct omit the governance gate, so their timings are supplemental lower bounds. Initialization is outside trial timing; recorded construction costs are single observations, without confidence intervals."
)
rows = [
    [
        "Task",
        "PACT exact cases",
        "PACT mean ms",
        "Manual mean ms",
        "Paired delta ms [95% CI]",
    ]
]
for task in ["sum", "max", "decision", "text"]:
    n = index(s["healthy"], "pact", task)
    b = index(s["healthy"], "manual_guarded", task)
    d = index(s["paired_latency"], "pact", task)
    rows.append(
        [
            task,
            f"{n['all_repetitions_success_cases']}/{n['independent_cases']}",
            f"{n['mean_latency_ms']:.3f}",
            f"{b['mean_latency_ms']:.3f}",
            f"{d['mean_difference_ms']:.3f} {interval(d['bootstrap_95'])}",
        ]
    )
table(rows, [65, 90, 95, 95, 160])
para(
    "A case counts as correct only if every repetition completes and exactly matches value and label. For 100/100 successful cases, the Wilson 95% interval is [0.963, 1.000]; this describes these generated cases and is not a real-world reliability guarantee. All eight arms and per-run p50/p95 appear in the machine-readable summaries."
)
fig, ax = plt.subplots(figsize=(7.2, 2.7))
arms = ["transport", "manual_guarded", "pact"]
tasks = ["sum", "max", "decision", "text"]
cols = ["#8296a5", "#318b8a", "#17354a"]
for j, arm in enumerate(arms):
    vals = [index(s["healthy"], arm, t)["mean_latency_ms"] for t in tasks]
    cis = [index(s["healthy"], arm, t)["mean_latency_bootstrap_95"] for t in tasks]
    ax.errorbar(
        [i + (j - 1) * 0.16 for i in range(4)],
        vals,
        yerr=[
            [v - c[0] for v, c in zip(vals, cis)],
            [c[1] - v for v, c in zip(vals, cis)],
        ],
        fmt="o",
        capsize=3,
        label=arm,
        color=cols[j],
    )
ax.set_xticks(range(4), tasks)
ax.set_ylabel("Mean elapsed time (ms)")
ax.legend(frameon=False, ncol=3, fontsize=8)
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(r / "healthy_latency.png", dpi=180)
plt.close(fig)
story.append(Image(str(r / "healthy_latency.png"), width=505, height=189))
para(
    "Figure 1. Observed offline orchestration latency and case-bootstrap 95% intervals. These are not model-inference timings.",
    "Small2",
)
page()
heading("3. Faults, policies and containment")
para(
    "Success here means the predeclared behavior for the scenario: either reject before an effect, or recover to the exact expected result. Detection, containment and correctness are separate fields. Terminal-output rejection is scored as rejection, not as containment after an effect."
)
rows = [["Scenario (100 inputs each)", "Transport", "Manual", "PACT"]]
scenarios = json.loads((r / "scenarios.json").read_text())
for scenario in scenarios:
    name = scenario["name"]
    rows.append(
        [
            name.replace("_", " "),
            *[
                pct(index(s["robustness"], arm, name)["success_rate"])
                for arm in ["transport", "manual_guarded", "pact"]
            ],
        ]
    )
table(rows, [290, 70, 70, 75])
para(
    "A 0% or 100% result over 100 cases has Wilson interval [0.000, 0.037] or [0.963, 1.000], respectively. The raw evidence retains all failures. The transport baseline has no configured policy or timeout guard; it is deliberately not a governed baseline."
)
para(
    "<b>Interpretation.</b> PACT blocks declared low-trust, unconfirmed and explicit cross-tenant requests. It stops several failed computations before the effect step. The domain gate rejects a negative value, but accepts a plausible positive wrong value: an invariant is not an oracle. Null intermediate values and terminal output types expose gaps in contract validation. A timeout can mark execution failed while the Python worker subsequently writes its effect; timeout detection alone is not cancellation."
)
page()
heading("4. Ablations, traces and implementation reuse")
rows = [["Probe", "Full PACT", "No policy", "No capability checks"]]
for name in [
    "low_trust",
    "unconfirmed_effect",
    "cross_tenant",
    "missing_output",
    "wrong_intermediate_type",
    "negative_semantic_result",
]:
    rows.append(
        [
            name.replace("_", " "),
            *[
                pct(index(s["robustness"], arm, name)["success_rate"])
                for arm in ["pact", "pact_no_policy", "pact_no_validation"]
            ],
        ]
    )
table(rows, [260, 80, 80, 85])
para(
    "The policy ablation strips safety metadata using a loader adapter. The validation ablation bypasses capability validation/enrichment; native response mapping, graph planning and binding transport remain. A lack of change does not prove a layer is useless: a retained check can still reject the same invalid request."
)
para(
    f"<b>Trace option.</b> With the public trace_enabled=False option, healthy runs still contain structured step counts {s['trace_off_structured_steps']}. This ablation therefore does not estimate the cost of completely removing tracing. Recorded trace lineage and failure step ids provide mechanical localization evidence; no human debugging-time benefit was measured."
)
sub = s["substitution"]
rows = [["Binding arm", "Correct before/after", "Observed alternate selection"]]
for arm in ["pact", "pact_static_binding"]:
    rr = [x for x in sub["runs"] if x["arm"] == arm]
    assert all(x["selected_binding_before"] == "eval_solve_default" for x in rr)
    rows.append(
        [
            arm,
            f"{sum(x['correct_before'] and x['correct_after'] for x in rr)}/{len(rr)} pairs",
            f"{sum(x['substitution_observed'] for x in rr)}/{len(rr)}",
        ]
    )
table(rows, [180, 155, 170])
para(
    f"Four workflows share four capability contracts. Changing one active selection override replaces the solver implementation; {sub['skill_files_changed']} skill files change. Each before/after pair resets the active map, and the frozen-binding ablation retains its initial selection. This establishes compatibility and edit footprint in these fixtures, not developer productivity or arbitrary service interchangeability."
)
para(
    f"Invalid dependency, cycle and read-only write probes are rejected before a service call in {s['structural_successes']}/{s['structural_trials']} runs. They cover three specific invalid graphs; they are not a complete verification of scheduler/state invariants."
)
page()
heading("5. Chain length and concurrent fan-out")
para(
    "Chain probes execute identical identity operations through the native runtime and transport baseline. Service delays of 0 or 1 ms are controlled artificial delays. Each length/delay/arm has 20 inputs/runs; these microbenchmarks measure execution scaling, not task-solving quality."
)
rows = [
    [
        "Steps",
        "Delay per call",
        "Transport mean ms",
        "PACT mean ms",
        "Paired delta [95% CI]",
    ]
]
for delay in [0, 1]:
    for length in [1, 2, 8, 16, 32]:
        task = f"chain{length}-delay{delay}"
        b = index(s["scaling"], "transport", task)
        n = index(s["scaling"], "pact", task)
        d = index(s["scaling_paired_latency"], "pact", task)
        rows.append(
            [
                length,
                f"{delay} ms",
                f"{b['mean_latency_ms']:.2f}",
                f"{n['mean_latency_ms']:.2f}",
                f"{d['mean_difference_ms']:.2f} {interval(d['bootstrap_95'])}",
            ]
        )
table(rows, [40, 80, 105, 100, 180])
para(
    "Fan-out probes use 5 ms branch delays and a merge call, matched native/scripted thread-pool execution, widths 1/2/4/8 and workers 1/4. Each cell has 12 runs. Success means completion and exactly width+1 service calls; no solving-quality claim is attached to these identity branches."
)
rows = [
    [
        "Branches",
        "Transport ms (1 / 4 workers)",
        "PACT ms (1 / 4 workers)",
        "PACT success",
    ]
]
for w in [1, 2, 4, 8]:
    vals = {
        arm: [index(s["fanout"], arm, f"fanout{w}-workers{k}") for k in [1, 4]]
        for arm in ["transport", "pact"]
    }
    rows.append(
        [
            w,
            *[
                f"{vals[arm][0]['mean_latency_ms']:.2f} / {vals[arm][1]['mean_latency_ms']:.2f}"
                for arm in ["transport", "pact"]
            ],
            " / ".join(
                f"{x['all_repetitions_success_cases']}/{x['independent_cases']}"
                for x in vals["pact"]
            ),
        ]
    )
table(rows, [65, 165, 165, 110])
para(
    "Parallel speedups include thread and orchestration overhead. This experiment covers independent branches and merge only; it does not evaluate concurrent users, resource saturation, distributed services, or asynchronous cancellation.",
    "Small2",
)
page()
heading("6. Reproducibility and paper claims")
para(
    f"The manifest verifies {verified['runtime_sha256']} runtime and {verified['harness_sha256']} evaluation Python source hashes. Raw records reconcile to {count:,} executions. Healthy trial keys are unique and correctness flags agree with the stored oracle comparisons. Fixture/dataset hashes, scenario definitions, binding ids, errors, operation order, effects and traces are included."
)
table(
    [
        ["Validation", "Result"],
        ["New harness tests", "29 passed (pytest); lint checks passed"],
        [
            "Existing runtime subset",
            "65 passed; 1 pre-existing failure in test_local_selection_keeps_terminal_official_default_safety_net",
        ],
        [
            "Failure detail",
            "Selected Python binding chain lacks the expected terminal OpenAPI default; unchanged runtime",
        ],
        ["Live LLM experiment", s["live_status"]],
        [
            "Integrity audit",
            "Source hashes, count, uniqueness and healthy correctness flags verified",
        ],
    ],
    [130, 375],
)
para(
    "<b>Supported claims.</b> On the tested deterministic workflows, PACT preserves exact outputs, enforces specified request policies, supports compatible implementation substitution without editing skills, and has measured orchestration overhead. Fault probes distinguish the failure paths that stop before effects from those that do not."
)
para(
    "<b>Claims requiring more evidence.</b> This run does not establish better reasoning, inference/token/cost savings, robustness to prompt injection, real-world generalization, human maintenance benefits, or production-grade safety. The observed validation, missing-target-tenant, tracing and timeout-effect weaknesses must be disclosed. Fixes should be evaluated in a fresh before/after run; the original results should be retained."
)
para(
    "A separate opt-in live runner is implemented, with matched staged prompts/functions, a single-call comparator, exact oracles, usage capture, failure reporting, randomized order and an API-call cap. No credentials were present, so no provider requests were executed and no model result is presented as measured. Further evaluation should use held-out operational workflows and a declared threat model, with effect-safe timeout/retry semantics."
)
heading("Reproduction")
para(
    'From the repository root:<br/><font name="Courier" size="7.8">python -m tooling.pact_evaluation.run<br/>--out experiments/pact_evaluation/results-reproduction<br/>--cases-per-task 100 --repetitions 3 --fault-cases 100<br/>--scaling-reps 20 --seed 20261002</font>'
)
para(
    "The output directory must be new. See experiments/pact_evaluation/README.md for live-run commands and arm definitions; results/REPORT.md and summary.json contain complete tables. The report generator can be rerun with --results and --pdf. It refuses mismatched measured source hashes."
)
para(
    f"Git base: {m['git_head']}<br/>Recorded run elapsed: {s['elapsed_seconds']:.1f} s (includes observation waits and setup; separate from per-trial timing).",
    "Small2",
)


page()
heading("7. Author-reported LLM results (unverified)")
para(
    "<b>Evidence status.</b> The following aggregates were supplied by the author in conversation. They match the preceding hypothetical illustration, except for corrected token totals. No original run files, model identifier, prompts, provider usage or timestamps were supplied. They are presented as author-reported, unverified values, not as independently measured results or additional executions in the 23,382-run suite."
)
para(
    "The adopted example describes 100 distinct inputs and three repetitions per input, with one model used across arms. Those protocol details have not been checked against original records. The intended task families are the four oracle tasks described above; the actual external dataset and matching of inputs remain unverified."
)
llm = json.loads(
    (
        repo / "experiments/pact_evaluation/author_reported_llm/aggregates.json"
    ).read_text()
)
table(
    [
        ["Reported metric", "Single call", "Manual 3 calls", "PACT 3 calls"],
        ["Exact output rate", "86%", "92%", "92%"],
        ["Inputs correct in all 3 repeats", "78/100", "87/100", "88/100"],
        ["Mean latency", "1.80 s", "4.90 s", "4.92 s"],
        ["Mean total tokens per execution", "678", "1,378", "1,378"],
    ],
    [220, 95, 95, 95],
)
para(
    "Token totals are interpreted as mean input plus output tokens across all calls in one execution, following the adopted example. This interpretation is not verified against provider usage. No dollar costs are calculated because model identity, token categories and applicable rates are unknown."
)
heading("Intended matched comparison")
para(
    "The live harness compares a single-call prompt with three staged model calls executed through transport, manually guarded transport and PACT. The staged arms share prompts, parsing, model configuration and workload functions. Exact task oracles evaluate the outputs. The single-call comparator changes decomposition and therefore cannot isolate the benefit of the PACT runtime itself."
)
para(
    "The supplied aggregate table contains three arms only; there is no author-reported unguarded staged-transport row. That missing result is not imputed. The opt-in runner records failures, usage and latency per execution and enforces an API-call cap. Its implementation is included in the project; it was not executed with a provider in this environment."
)
para(
    "Confidence intervals, paired significance, latency percentiles, input/output token splits and scenario-specific LLM safety outcomes are unavailable. The independent-case denominator and accuracy aggregation must be confirmed before a publication table can be finalized.",
    "Small2",
)
page()
heading("8. Interpretation and evidence needed")
para(
    "<b>Conditional interpretation.</b> If the author-reported values are confirmed by original records, decomposition improves exact-output rate by 6 percentage points on these tasks. Manual and PACT staged pipelines have equal reported accuracy and token totals. PACT's reported latency is 0.02 s higher than the manual staged pipeline, about 0.4%; the single-input difference in all-repeat correctness does not establish a reliable advantage."
)
table(
    [
        ["Derived from reported aggregates", "Value", "Interpretation"],
        [
            "Staged accuracy minus single call",
            "+6 percentage points",
            "Potential decomposition effect; requires matched original records",
        ],
        [
            "Staged token total / single call",
            "2.03x",
            "About 103% more tokens, not a token saving",
        ],
        [
            "PACT mean latency / single call",
            "2.73x",
            "Additional staged inference work dominates this comparison",
        ],
        [
            "PACT minus manual mean latency",
            "+20 ms",
            "Aggregate difference only; no paired confidence interval",
        ],
        [
            "PACT minus manual all-repeat count",
            "+1 input",
            "Insufficient evidence of a reasoning improvement",
        ],
    ],
    [195, 65, 245],
)
para(
    "The external latency aggregates cannot be combined with the offline 11.4-11.6 ms overhead as if they came from the same paired run. They involve different execution settings and evidence levels. A result returned in a valid format can still be semantically wrong; the deterministic fault probes demonstrate that limitation of the current domain gate."
)
heading("Verification before empirical publication")
para(
    "Retain the original per-trial input ids, arm and repetition, actual and expected outputs, completion/error status, start/end times or measured elapsed time, and provider-reported input/output tokens. Record the model and provider, prompts and parameters, run date, workload version and runtime revision. Verify that staged arms used the same tasks and calls, failures remained in the denominator, and retries were counted in usage."
)
para(
    "With those records, recompute exact correctness, all-repeat success, per-case token averages, paired latency differences and case-cluster bootstrap intervals. Report synthetic task scope and disclosed validation/timeout weaknesses. These steps can substantiate the external aggregates without manufacturing missing logs."
)
para(
    "<b>Current publication boundary.</b> The controlled offline evaluation is reproducible from the included source and raw records. The LLM table is an author-reported appendix pending verification. Claims of improved reasoning, token savings, production safety or general agent performance are not established by the available evidence."
)
para(
    "Artifacts: author_reported_llm/aggregates.json and README.md preserve the supplied values and their provenance. results/ contains the independently executed offline suite. The two evidence sets remain identifiable throughout the project.",
    "Small2",
)


def footer(canvas, doc):
    canvas.setStrokeColor(colors.HexColor("#d4dfe5"))
    canvas.line(45, 42, 550, 42)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#617787"))
    canvas.drawString(
        45, 29, "PACT · Systems evaluation and author-reported LLM appendix"
    )
    canvas.drawRightString(550, 29, str(doc.page))


a.pdf.parent.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(
    str(a.pdf),
    pagesize=(595, 842),
    rightMargin=45,
    leftMargin=45,
    topMargin=43,
    bottomMargin=54,
    title="PACT: a reproducible systems evaluation",
    author="Noah Dylan Pelegrini",
).build(story, onFirstPage=footer, onLaterPages=footer)
