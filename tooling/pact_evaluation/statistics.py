"""Case-cluster summaries; repeated runs are not independent case samples."""

import math
import random
import statistics
from collections import defaultdict


def percentile(values, p):
    values = sorted(values)
    if not values:
        return None
    x = (len(values) - 1) * p
    i = int(x)
    return values[i] + (values[min(i + 1, len(values) - 1)] - values[i]) * (x - i)


def bootstrap_mean(values, seed=20261002, draws=2000):
    if not values:
        return [None, None]
    rng = random.Random(seed)
    n = len(values)
    means = [sum(rng.choices(values, k=n)) / n for _ in range(draws)]
    return [percentile(means, 0.025), percentile(means, 0.975)]


def wilson(k, n):
    if not n:
        return [None, None]
    z = 1.95996398454
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [max(0, center - half), min(1, center + half)]


def summarize(rows, flag="correct"):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["arm"], row["task"])].append(row)
    output = []
    for (arm, task), g in sorted(groups.items()):
        bycase = defaultdict(list)
        for r in g:
            bycase[r["case_id"]].append(r)
        means = [
            statistics.mean(r["latency_ms"] for r in group) for group in bycase.values()
        ]
        k = sum(all(r.get(flag, False) for r in group) for group in bycase.values())
        output.append(
            {
                "arm": arm,
                "task": task,
                "runs": len(g),
                "independent_cases": len(bycase),
                "all_repetitions_success_cases": k,
                "success_rate": k / len(bycase),
                "success_wilson_95": wilson(k, len(bycase)),
                "mean_latency_ms": statistics.mean(means),
                "mean_latency_bootstrap_95": bootstrap_mean(means),
                "p50_ms": percentile([r["latency_ms"] for r in g], 0.5),
                "p95_ms": percentile([r["latency_ms"] for r in g], 0.95),
            }
        )
    return output


def paired_comparisons(rows, reference="transport"):
    grouped = defaultdict(lambda: defaultdict(list))
    for r in rows:
        grouped[(r["task"], r["case_id"])][r["arm"]].append(r["latency_ms"])
    pairs = defaultdict(list)
    for (task, _), arms in grouped.items():
        if reference not in arms:
            continue
        baseline = statistics.mean(arms[reference])
        for arm, values in arms.items():
            if arm != reference:
                pairs[(task, arm)].append(statistics.mean(values) - baseline)
    return [
        {
            "task": task,
            "arm": arm,
            "reference": reference,
            "paired_cases": len(v),
            "mean_difference_ms": statistics.mean(v),
            "bootstrap_95": bootstrap_mean(v),
        }
        for (task, arm), v in sorted(pairs.items())
    ]
