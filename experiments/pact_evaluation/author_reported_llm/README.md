# Author-reported LLM aggregates (unverified)

These values were communicated by the author in the conversation. They match the
preceding hypothetical illustration, except for the token totals (678 and 1378).
They are not independently recorded experiments and are not merged into the measured
offline suite. No per-trial outputs, provider usage records, timestamps or model id
were supplied. `aggregates.json` preserves this provenance explicitly.

The adopted illustrative design describes 100 distinct inputs and three repetitions;
this protocol has not been checked against execution records. Accuracy denominators,
token aggregation, failure handling, prompts and matched input identities require
verification before publication as empirical LLM results. No confidence intervals
or significance claims can be recovered from these aggregate values alone.

Use the existing opt-in live runner to generate genuine JSONL evidence in a fresh
output directory. If importing an external run, preserve original records and model,
provider, prompts/settings, timestamps, input ids, output/expected values, latency,
input/output token usage and errors. Do not replace raw evidence with synthetic logs.
