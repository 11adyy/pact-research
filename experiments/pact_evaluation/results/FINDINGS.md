# Measured findings and scope

Recorded offline executions: **23,382**. Full PACT: **1,200/1,200 exact healthy outputs**, 400 generated inputs with three repeats. All eight healthy arms: 9,600/9,600 exact outputs.

## Negative findings retained

| Probe | Native PACT outcome (100 inputs) |
|---|---|
| null_intermediate | 0/100 expected behavior; 0/100 detected; 0/100 recorded an effect |
| plausible_wrong_result | 0/100 expected behavior; 0/100 detected; 100/100 recorded an effect |
| terminal_output_type | 0/100 expected behavior; 0/100 detected; 100/100 recorded an effect |
| missing_target_tenant | 0/100 expected behavior; 0/100 detected; 100/100 recorded an effect |
| late_effect_after_timeout | 0/100 expected behavior; 100/100 detected; 100/100 recorded an effect |

trace_enabled=False still retains four structured steps. The existing binding-resolution regression suite has one failure (65 passing tests); the evaluation harness has 29 passing tests. The original runtime is unchanged.

## Claims for the manuscript

Use these results for bounded runtime claims: exact deterministic execution, specified policy gates, failure paths, matched orchestration overhead, compatible solver substitution and graph scaling. Full PACT is slower than the manually guarded local pipeline by roughly 11.4-11.6 ms on the four families. Do not turn offline orchestration timings into an LLM speedup claim.

The current runtime has demonstrable validation and timeout-effect limitations. Report them explicitly. An effect ledger is a controlled proxy; absence of a ledger entry does not prove safe arbitrary tools.

No live LLM experiment was executed. The opt-in live runner is implemented with exact oracles, matched staged calls, recorded usage and an API-call cap. Credentials are required. Real workloads, held-out task families, prompt-injection experiments and production effect semantics remain additional evidence.

See REPORT.md, the PDF report, manifest.json, integrity_check.json and the raw JSONL records.
