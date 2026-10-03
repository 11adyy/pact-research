# PACT systems evaluation

This harness tests the **actual, unmodified runtime** through generated YAML
skills/capabilities, the real binding registry and resolver, real PythonCallInvoker,
the engine, scheduler, data mappings, policies, retries, and tracing. Services are
controlled deterministic implementations. Effects are an isolated in-memory ledger.
There are no production writes and no ML training.

## Reproduce offline

From the repository root, with Python >=3.11 and the ordinary package dependencies:

```bash
python -m tooling.pact_evaluation.run \
  --out experiments/pact_evaluation/results-reproduction \
  --cases-per-task 100 --repetitions 3 --fault-cases 100 \
  --scaling-reps 20 --seed 20261002
python -m pytest tooling/pact_evaluation/test_evaluation.py -o addopts="" -q
```

An existing trials file is never overwritten. Use a new output directory.
No credentials are needed, and historical experiment outputs are not included.

## Arms

| Arm | Configuration |
|---|---|
| direct | Same functions called directly; lower-bound orchestration baseline |
| transport | Same four-step chain and real PythonCallInvoker, including its threads |
| manual_guarded | Same transport plus manually implemented trust, confirmation, tenant, input/output checks and the same post gate |
| pact | Full native runtime with actual YAML and binding layers |
| pact_no_policy | Safety metadata removed via loader wrapper; native runtime code unchanged |
| pact_no_validation | Capability validation/enrichment adapter bypassed; real response mapper and transport remain |
| pact_trace_off | Public `trace_enabled=False` option; actual trace content is measured |
| pact_static_binding | Freeze real initial resolver selections; all other runtime layers retained |

Full PACT and manual_guarded both invoke four workload functions and one integrity
gate. Transport/direct have four calls and omit governance; they are not equivalent
in checks. The primary paired overhead comparison is therefore manual_guarded.
The validation ablation does **not** remove response mapping or planner checks.
The trace flag may not suppress every trace: negative findings are retained.

## Protocol and metrics

- Four task families: sum, maximum, constrained weighted selection, and tagged text
  extraction/aggregation. Exact oracles use generated latent values. Neither the
  service nor model receives oracle-only fields.
- Paired healthy inputs, three repetitions, randomized arm/input order, warmups
  excluded, initialization recorded separately, audit off, runtime logging off.
- Real elapsed times measured by perf_counter_ns; no fabricated inference latency.
- Correctness is exact equality of value and label; completion alone is not success.
- Faults: exceptions, missing output fields, wrong types, nulls, invariant violations,
  plausible wrong outputs, retries, timeout, and late effects after timeout.
- Policy probes: insufficient trust, missing confirmation, cross-tenant action,
  missing tenant context, and missing target tenant.
- Structural probes: unknown dependency, cyclic graph, and read-only state writes.
- Scaling: 1/2/8/16/32-step chains, 0/1ms declared service delay, matched transport;
  fan-out widths 1/2/4/8, workers 1/4, 5ms service delay, native and matched scripted
  thread-pool execution. Artificial delays are labeled and never called LLM latency.
- Reuse: four workflows share four capability interfaces; swap one implementation
  without modifying skills. This measures edit footprint, not human productivity.
- Confidence: case-cluster bootstrap (2000 draws), paired per-case latency difference,
  p50/p95, and Wilson intervals over cases passing **all** repetitions. Deterministic
  repeats do not enlarge the independent-case denominator.
- Raw records preserve errors, calls, effects, traces, binding choices, and counters.
  Circuit breakers reset before each trial so fault histories do not contaminate
  later cases. Trials execute serially except intentional internal fan-out.

## Live LLM arm (prepared, not run without credentials)

```bash
export OPENAI_API_KEY=...   # set securely; never commit it
python -m tooling.pact_evaluation.live \
  --out experiments/pact_evaluation/live-results \
  --model gpt-4o-mini --cases-per-task 25 --repetitions 3 \
  --seed 20261002 --max-api-calls 4000
```

This schedules 3000 API calls (100 cases x 3 repeats x [single + 3 staged arms]).
The cap is enforced before the run. Use fewer cases for a budget smoke test.
It compares single-call prompting, the shared three-model-call pipeline via matched
transport, the manually guarded pipeline, and full PACT. Staged arms share identical
prompts, parsing, model settings and functions. Seed changes by repetition. A seed
does not guarantee provider determinism. JSON parse errors and API errors are
reported; no offline fallback or invisible API retry is performed. Usage is collected
from provider responses; no fixed dollar-price assumptions are made. HTTP timeout
is 60 seconds. Provider/model version drift must be considered when reproducing.

These constrained oracle tasks support systems comparisons, not claims about general
agent reasoning or arbitrary prompt-injection resistance. A larger agent task suite
with held-out workloads and real operational policies remains future evidence.

## Evidence and findings

The recorded run includes a manifest with hashes of runtime/harness/fixtures/dataset,
environment, clock and random seed; raw JSONL/JSON, CSV, and a human-readable report.
Tests called `negative_evidence` intentionally confirm current weaknesses rather
than hiding them or counting them as safety guarantees. If the runtime is repaired,
change those regression expectations and run a fresh directory; preserve the old
evidence for a pre/post comparison.

## Recorded delivery

`results/` contains the measured 23,382-execution offline run, complete raw data,
manifest, integrity check, tables, negative findings and an eight-page PDF report.
Validation logs are in `validation/`. The runtime is unchanged.

The PDF can be rebuilt using optional report dependencies:

```bash
python -m pip install reportlab matplotlib
python experiments/pact_evaluation/build_report.py \
  --results experiments/pact_evaluation/results \
  --pdf /absolute/path/PACT_Evaluation_Report.pdf
```

The author-reported LLM appendix is stored in `author_reported_llm/`; its aggregate
values are unverified and are not added to the independently measured trial count.

The original architecture manuscript is now extended in `paper/`, with its
13-page PDF and editable Markdown/LaTeX sources. The evaluation report remains
a separate supplemental document.
