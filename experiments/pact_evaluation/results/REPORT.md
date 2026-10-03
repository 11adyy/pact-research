# PACT runtime evaluation

**Measured mode: offline deterministic systems evaluation. No live model run was performed.**

The supplied runtime is evaluated unchanged. Baselines use identical workload functions. `transport` uses the same real PythonCallInvoker, including per-call threads. `manual_guarded` adds independent checks and the same domain invariant; it also validates output types more strictly. Full PACT and manual_guarded have four workload calls plus one post gate; direct/transport omit the gate. Primary paired latency comparisons use manual_guarded; transport comparisons also appear separately. All arms have equal instrumentation. No synthetic timing is reported as inference latency.

## Healthy workloads

| Arm | Task | Cases | Runs | All-repeat success | Mean ms | 95% case-bootstrap CI | p95 ms |
|---|---|---:|---:|---:|---:|---|---:|
| direct | decision | 100 | 300 | 100.0% | 0.154 | [0.151, 0.157] | 0.187 |
| direct | max | 100 | 300 | 100.0% | 0.051 | [0.050, 0.053] | 0.076 |
| direct | sum | 100 | 300 | 100.0% | 0.052 | [0.051, 0.054] | 0.079 |
| direct | text | 100 | 300 | 100.0% | 0.076 | [0.073, 0.079] | 0.110 |
| manual_guarded | decision | 100 | 300 | 100.0% | 0.729 | [0.712, 0.745] | 0.916 |
| manual_guarded | max | 100 | 300 | 100.0% | 0.601 | [0.566, 0.661] | 0.790 |
| manual_guarded | sum | 100 | 300 | 100.0% | 0.586 | [0.567, 0.610] | 0.754 |
| manual_guarded | text | 100 | 300 | 100.0% | 0.611 | [0.595, 0.626] | 0.819 |
| pact | decision | 100 | 300 | 100.0% | 12.139 | [12.068, 12.216] | 13.211 |
| pact | max | 100 | 300 | 100.0% | 12.096 | [11.993, 12.205] | 13.887 |
| pact | sum | 100 | 300 | 100.0% | 12.081 | [11.951, 12.242] | 13.504 |
| pact | text | 100 | 300 | 100.0% | 12.250 | [11.989, 12.684] | 13.250 |
| pact_no_policy | decision | 100 | 300 | 100.0% | 11.405 | [11.305, 11.519] | 13.037 |
| pact_no_policy | max | 100 | 300 | 100.0% | 11.119 | [11.022, 11.229] | 12.241 |
| pact_no_policy | sum | 100 | 300 | 100.0% | 11.201 | [11.053, 11.409] | 12.321 |
| pact_no_policy | text | 100 | 300 | 100.0% | 11.131 | [11.045, 11.226] | 12.404 |
| pact_no_validation | decision | 100 | 300 | 100.0% | 11.869 | [11.772, 11.974] | 12.953 |
| pact_no_validation | max | 100 | 300 | 100.0% | 11.880 | [11.760, 12.005] | 13.750 |
| pact_no_validation | sum | 100 | 300 | 100.0% | 12.269 | [11.751, 13.146] | 13.429 |
| pact_no_validation | text | 100 | 300 | 100.0% | 11.884 | [11.757, 12.033] | 12.998 |
| pact_static_binding | decision | 100 | 300 | 100.0% | 12.501 | [12.174, 13.042] | 13.745 |
| pact_static_binding | max | 100 | 300 | 100.0% | 12.250 | [12.028, 12.555] | 14.099 |
| pact_static_binding | sum | 100 | 300 | 100.0% | 12.126 | [12.019, 12.233] | 14.138 |
| pact_static_binding | text | 100 | 300 | 100.0% | 12.395 | [11.996, 13.128] | 13.644 |
| pact_trace_off | decision | 100 | 300 | 100.0% | 12.309 | [12.185, 12.477] | 13.886 |
| pact_trace_off | max | 100 | 300 | 100.0% | 12.094 | [11.993, 12.197] | 13.462 |
| pact_trace_off | sum | 100 | 300 | 100.0% | 12.263 | [12.043, 12.547] | 13.729 |
| pact_trace_off | text | 100 | 300 | 100.0% | 12.226 | [12.072, 12.403] | 13.598 |
| transport | decision | 100 | 300 | 100.0% | 0.724 | [0.709, 0.740] | 0.947 |
| transport | max | 100 | 300 | 100.0% | 0.560 | [0.547, 0.573] | 0.766 |
| transport | sum | 100 | 300 | 100.0% | 0.556 | [0.541, 0.570] | 0.747 |
| transport | text | 100 | 300 | 100.0% | 0.602 | [0.584, 0.621] | 0.807 |

## Fault and policy scenarios

| Scenario | Arm | Cases | Expected behavior met | 95% Wilson CI |
|---|---|---:|---:|---|
| cross_tenant | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| late_effect_after_timeout | manual_guarded | 100 | 0.0% | [0.000, 0.037] |
| low_trust | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| missing_output | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| missing_target_tenant | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| missing_tenant | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| negative_semantic_result | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| null_intermediate | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| plausible_wrong_result | manual_guarded | 100 | 0.0% | [0.000, 0.037] |
| service_exception | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| step_timeout | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| terminal_output_type | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| transient_no_retry | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| transient_recovered | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| unconfirmed_effect | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| wrong_intermediate_type | manual_guarded | 100 | 100.0% | [0.963, 1.000] |
| cross_tenant | pact | 100 | 100.0% | [0.963, 1.000] |
| late_effect_after_timeout | pact | 100 | 0.0% | [0.000, 0.037] |
| low_trust | pact | 100 | 100.0% | [0.963, 1.000] |
| missing_output | pact | 100 | 100.0% | [0.963, 1.000] |
| missing_target_tenant | pact | 100 | 0.0% | [0.000, 0.037] |
| missing_tenant | pact | 100 | 100.0% | [0.963, 1.000] |
| negative_semantic_result | pact | 100 | 100.0% | [0.963, 1.000] |
| null_intermediate | pact | 100 | 0.0% | [0.000, 0.037] |
| plausible_wrong_result | pact | 100 | 0.0% | [0.000, 0.037] |
| service_exception | pact | 100 | 100.0% | [0.963, 1.000] |
| step_timeout | pact | 100 | 100.0% | [0.963, 1.000] |
| terminal_output_type | pact | 100 | 0.0% | [0.000, 0.037] |
| transient_no_retry | pact | 100 | 100.0% | [0.963, 1.000] |
| transient_recovered | pact | 100 | 100.0% | [0.963, 1.000] |
| unconfirmed_effect | pact | 100 | 100.0% | [0.963, 1.000] |
| wrong_intermediate_type | pact | 100 | 100.0% | [0.963, 1.000] |
| cross_tenant | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| late_effect_after_timeout | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| low_trust | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| missing_output | pact_no_policy | 100 | 100.0% | [0.963, 1.000] |
| missing_target_tenant | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| missing_tenant | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| negative_semantic_result | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| null_intermediate | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| plausible_wrong_result | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| service_exception | pact_no_policy | 100 | 100.0% | [0.963, 1.000] |
| step_timeout | pact_no_policy | 100 | 100.0% | [0.963, 1.000] |
| terminal_output_type | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| transient_no_retry | pact_no_policy | 100 | 100.0% | [0.963, 1.000] |
| transient_recovered | pact_no_policy | 100 | 100.0% | [0.963, 1.000] |
| unconfirmed_effect | pact_no_policy | 100 | 0.0% | [0.000, 0.037] |
| wrong_intermediate_type | pact_no_policy | 100 | 100.0% | [0.963, 1.000] |
| cross_tenant | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| late_effect_after_timeout | pact_no_validation | 100 | 0.0% | [0.000, 0.037] |
| low_trust | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| missing_output | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| missing_target_tenant | pact_no_validation | 100 | 0.0% | [0.000, 0.037] |
| missing_tenant | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| negative_semantic_result | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| null_intermediate | pact_no_validation | 100 | 0.0% | [0.000, 0.037] |
| plausible_wrong_result | pact_no_validation | 100 | 0.0% | [0.000, 0.037] |
| service_exception | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| step_timeout | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| terminal_output_type | pact_no_validation | 100 | 0.0% | [0.000, 0.037] |
| transient_no_retry | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| transient_recovered | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| unconfirmed_effect | pact_no_validation | 100 | 100.0% | [0.963, 1.000] |
| wrong_intermediate_type | pact_no_validation | 100 | 0.0% | [0.000, 0.037] |
| cross_tenant | transport | 100 | 0.0% | [0.000, 0.037] |
| late_effect_after_timeout | transport | 100 | 0.0% | [0.000, 0.037] |
| low_trust | transport | 100 | 0.0% | [0.000, 0.037] |
| missing_output | transport | 100 | 100.0% | [0.963, 1.000] |
| missing_target_tenant | transport | 100 | 0.0% | [0.000, 0.037] |
| missing_tenant | transport | 100 | 0.0% | [0.000, 0.037] |
| negative_semantic_result | transport | 100 | 0.0% | [0.000, 0.037] |
| null_intermediate | transport | 100 | 0.0% | [0.000, 0.037] |
| plausible_wrong_result | transport | 100 | 0.0% | [0.000, 0.037] |
| service_exception | transport | 100 | 100.0% | [0.963, 1.000] |
| step_timeout | transport | 100 | 0.0% | [0.000, 0.037] |
| terminal_output_type | transport | 100 | 0.0% | [0.000, 0.037] |
| transient_no_retry | transport | 100 | 100.0% | [0.963, 1.000] |
| transient_recovered | transport | 100 | 100.0% | [0.963, 1.000] |
| unconfirmed_effect | transport | 100 | 0.0% | [0.000, 0.037] |
| wrong_intermediate_type | transport | 100 | 0.0% | [0.000, 0.037] |

## Concrete limitations observed

Full raw trials retain failures, exceptions, operation order, side-effect ledger, structured traces, and token counters. A detected error is distinct from containment (no ledger write), and correct task output is distinct from mere completion. Terminal-output failures can be detected after an effect, so they are not scored as containment successes.

Structural invalidity was rejected before a service call in 30/30 trials.
Live-model experiment: not run; OPENAI_API_KEY absent.

## Reuse and substitution

Four workflows reuse four capability contracts. Swapping the solver requires one selection override and changed 0 skill files. The static-binding ablation cannot follow a subsequent active-map change without rebuilding its frozen selection. This is a mechanical change-footprint measurement, not a developer-time experiment.

## Interpretation

These results characterize a runtime over controlled deterministic services. They do not establish better LLM reasoning, robustness to prompt injection, statistical generalization to real deployments, or safety of arbitrary tools. Domain gates detect the declared invariant only; a plausible but wrong positive output is deliberately included to expose this limit. Trace-off tests use the actual public option and report actual trace content, rather than assuming the option suppresses every trace.

Timing comparisons use paired per-case averages and seeded bootstrap confidence intervals. Repeated deterministic runs are not counted as independent cases. Wilson intervals describe finite test-case coverage, not real-world failure probabilities. Audit persistence is disabled in all arms and therefore excluded from cost claims. Logging is disabled before timing. Runtime cold construction is reported separately. Order is randomized and each trial clears the circuit breaker to prevent injected failures contaminating later trials.

## Reproduction

```bash
python -m tooling.pact_evaluation.run --out experiments/pact_evaluation/results-reproduction --cases-per-task 100 --repetitions 3 --fault-cases 100 --scaling-reps 20 --seed 20261002
python -m pytest tooling/pact_evaluation/test_evaluation.py -o addopts="" -q
```

For a live LLM run, use the separate command in README.md. It uses new results and never silently falls back to deterministic functions. Historical benchmark files are not counted as evidence in this evaluation.

See `summary.json`, `manifest.json`, `dataset.json`, scenario definitions, generated YAML fixtures, and JSONL records for exact denominators and hashes.
