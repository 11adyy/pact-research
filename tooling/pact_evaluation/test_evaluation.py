"""Harness checks plus explicit negative-evidence regression tests.

Passing these tests does NOT mean the known negative findings are repaired.
"""

import copy
import logging

import pytest

from .fixtures import cases, ground_truth, materialize, public_input
from .runner import TrialRunner
from .statistics import paired_comparisons, summarize, wilson


@pytest.fixture
def root(tmp_path):
    logging.getLogger("pact_runtime").setLevel(logging.CRITICAL)
    materialize(tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    "arm",
    [
        "transport",
        "manual_guarded",
        "pact",
        "pact_no_policy",
        "pact_no_validation",
        "pact_static_binding",
    ],
)
def test_real_stack_agrees_with_independent_oracle(root, arm):
    runner = TrialRunner(root, arm)
    for c in cases(2):
        r = runner.run(c)
        assert r["correct"], r["error"]
        assert len(r["effects"]) == 1


@pytest.mark.parametrize("fault", ["exception", "missing_output", "semantic_negative"])
def test_fault_blocking_prevents_commit(root, fault):
    c = cases(1)[0] | {"fault": fault, "fault_op": "solve"}
    r = TrialRunner(root, "pact").run(c)
    assert r["status"] == "failed"
    assert not r["effects"]
    assert "commit" not in [call["operation"] for call in r["calls"]]


@pytest.mark.parametrize(
    "kwargs", [{"trust": "sandbox"}, {"confirmed": False}, {"tenant": None}]
)
def test_policy_denial_has_no_effect(root, kwargs):
    r = TrialRunner(root, "pact").run(cases(1)[0], **kwargs)
    assert r["status"] == "failed" and not r["effects"]


def test_cross_tenant_denied_with_explicit_target(root):
    r = TrialRunner(root, "pact").run(cases(1)[0] | {"target_tenant_id": "tenant-b"})
    assert r["status"] == "failed" and not r["effects"]


def test_retry_recovers_once_without_duplicating_effect(root):
    r = TrialRunner(root, "pact").run(
        cases(1)[0] | {"fault": "transient", "fault_op": "solve"},
        skill="evaluation.retry",
    )
    assert r["correct"] and len(r["effects"]) == 1
    assert len([c for c in r["calls"] if c["operation"] == "solve"]) == 2


@pytest.mark.parametrize("mode", ["cycle", "bad_dependency", "read_only"])
def test_invalid_graph_rejected_before_any_service(root, mode):
    r = TrialRunner(root, "pact").run(cases(1)[0], skill=f"evaluation.{mode}")
    assert r["status"] == "failed" and not r["calls"] and not r["effects"]


def test_negative_evidence_positive_but_wrong_result_passes_invariant(root):
    r = TrialRunner(root, "pact").run(
        cases(1)[0] | {"fault": "semantic_positive", "fault_op": "solve"}
    )
    assert r["status"] == "completed" and not r["correct"] and len(r["effects"]) == 1


def test_negative_evidence_terminal_output_type_not_checked(root):
    r = TrialRunner(root, "pact").run(
        cases(1)[0] | {"fault": "terminal_wrong_type", "fault_op": "commit"}
    )
    assert r["status"] == "completed" and not r["correct"]


def test_negative_evidence_trace_off_retains_structured_steps(root):
    r = TrialRunner(root, "pact_trace_off").run(cases(1)[0])
    assert len(r["trace"]) == 4


def test_negative_evidence_null_is_not_a_required_object(root):
    r = TrialRunner(root, "pact").run(
        cases(1)[0] | {"fault": "null_output", "fault_op": "verify"}
    )
    assert r["status"] == "completed" and not r["correct"]


def test_negative_evidence_target_tenant_absence_is_not_rejected(root):
    r = TrialRunner(root, "pact").run(cases(1)[0] | {"target_tenant_id": None})
    assert r["status"] == "completed" and len(r["effects"]) == 1


def test_negative_evidence_timed_out_operation_can_still_have_effect(root):
    r = TrialRunner(root, "pact").run(
        cases(1)[0] | {"fault": "slow", "fault_op": "commit", "fault_delay_ms": 30},
        skill="evaluation.effect_timeout",
    )
    assert r["status"] == "failed" and len(r["effects"]) == 1


def test_binding_substitution_and_static_ablation(root):
    c = cases(1)[0]
    for arm in ["pact", "pact_static_binding"]:
        runner = TrialRunner(root, arm)
        before = runner.run(c)
        assert before["bindings"]["s1"] == "eval_solve_default"
        runner.activate_alternate()
        after = runner.run(c)
        assert before["correct"] and after["correct"]
        assert after["bindings"]["s1"] == (
            "eval_solve_zalternate" if arm == "pact" else "eval_solve_default"
        )


def test_case_generation_and_oracle_are_reproducible():
    a = cases(10, 42)
    assert a == cases(10, 42)
    assert a != cases(10, 43)
    for c in a:
        before = copy.deepcopy(c)
        expected = ground_truth(c)
        assert c == before and type(expected["value"]) is int
        assert not any(k.startswith("oracle_") for k in public_input(c))


def test_repeated_runs_do_not_inflate_case_sample_size():
    rows = [
        {
            "arm": "pact",
            "task": "sum",
            "case_id": "same",
            "repetition": i,
            "correct": True,
            "latency_ms": float(i + 1),
        }
        for i in range(100)
    ]
    s = summarize(rows)[0]
    assert s["runs"] == 100 and s["independent_cases"] == 1
    assert s["success_wilson_95"] == wilson(1, 1)


def test_pairing_is_by_case_not_row_order():
    rows = [
        {"arm": a, "task": "sum", "case_id": c, "latency_ms": v}
        for a, c, v in [
            ("transport", "a", 1),
            ("pact", "b", 4),
            ("transport", "b", 2),
            ("pact", "a", 3),
        ]
    ]
    p = paired_comparisons(rows)[0]
    assert p["paired_cases"] == 2 and p["mean_difference_ms"] == 2


@pytest.mark.parametrize("arm", ["transport", "pact"])
def test_fanout_and_join_use_same_workload_count(root, arm):
    r = TrialRunner(root, arm).run(
        cases(1)[0] | {"width": 4, "service_delay_ms": 1},
        skill="evaluation.fanout4",
        workers=4,
    )
    assert r["status"] == "completed" and len(r["calls"]) == 5
