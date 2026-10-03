"""Real runtime adapters and independently implemented matched baselines."""

from __future__ import annotations

import copy
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from runtime.binding_models import InvocationRequest
from runtime.circuit_breaker import CircuitBreakerRegistry
from runtime.engine_factory import build_runtime_components
from runtime.execution_state import create_execution_state
from runtime.models import ExecutionOptions, ExecutionRequest
from runtime.pythoncall_invoker import PythonCallInvoker
from tooling.pact_evaluation import operations as ops

from .fixtures import PIPELINE, ground_truth, public_input

ARMS = [
    "direct",
    "transport",
    "manual_guarded",
    "pact",
    "pact_no_policy",
    "pact_no_validation",
    "pact_trace_off",
    "pact_static_binding",
]


class NoPolicyLoader:
    def __init__(self, loader):
        self.loader = loader

    def get_capability(self, cid):
        return replace(self.loader.get_capability(cid), safety=None)

    def __getattr__(self, name):
        return getattr(self.loader, name)


class BypassCapabilityValidation:
    """Ablation only. Keeps real binding, transport, and response mapping."""

    def __init__(self, executor):
        self.binding_executor = executor.binding_executor

    def execute(self, capability, step_input, **kwargs):
        kwargs.pop("trace_id", None)
        return self.binding_executor.execute(capability, step_input, **kwargs)


class StaticResolver:
    def __init__(self, mapping):
        self.mapping = mapping

    def resolve(self, cid):
        return self.mapping[cid]


class TrialRunner:
    def __init__(self, root, arm):
        self.arm = arm
        start = time.perf_counter_ns()
        self.components = build_runtime_components(root, root, root)
        self.engine = self.components.engine
        self.binding_executor = self.components.capability_executor.binding_executor
        self.registry = self.binding_executor.binding_registry
        self.invoker = PythonCallInvoker()
        self.original_resolver = self.binding_executor.binding_resolver
        if arm == "pact_no_policy":
            self.engine.capability_loader = NoPolicyLoader(
                self.engine.capability_loader
            )
        if arm == "pact_no_validation":
            self.engine.capability_executor = BypassCapabilityValidation(
                self.engine.capability_executor
            )
        if arm == "pact_static_binding":
            mapping = {
                b.capability_id: self.original_resolver.resolve(b.capability_id)
                for b in self.registry.list_bindings()
            }
            self.binding_executor.binding_resolver = StaticResolver(mapping)
        self.initialization_ms = (time.perf_counter_ns() - start) / 1e6

    def activate_alternate(self):
        # Exercise real active-map selection and documented cache invalidation.
        active = self.original_resolver.active_binding_map
        active._cache = {"eval.solve.run": "eval_solve_zalternate"}
        self.binding_executor.invalidate_plan_cache()

    def invoke(self, op, data, alternate=False, **extra):
        bid = f"eval_{op}_{'zalternate' if alternate and op == 'solve' else 'default'}"
        binding = self.registry.get_binding(bid)
        service = self.registry.get_service(binding.service_id)
        payload = {"data": data}
        payload.update(extra)
        if op == "commit":
            payload["target_tenant_id"] = (
                data.get("target_tenant_id") if isinstance(data, dict) else None
            )
        if self.arm == "direct":
            return getattr(ops, binding.operation_id)(**payload)
        request = InvocationRequest(
            protocol="pythoncall",
            service=service,
            binding=binding,
            operation_id=binding.operation_id,
            payload=payload,
        )
        return self.invoker.invoke(request).raw_response

    def run(
        self,
        case,
        repetition=0,
        skill=None,
        trust="elevated",
        confirmed=True,
        tenant="tenant-a",
        workers=1,
        alternate=False,
        length=None,
    ):
        ops.reset()
        # Faults must not contaminate later trials through shared circuit state.
        self.binding_executor.circuit_breaker = CircuitBreakerRegistry()
        data = public_input(copy.deepcopy(case))
        data["run_id"] = f"{case['case_id']}:{repetition}:{self.arm}"
        events = []
        error = None
        result = None
        trace = []
        failed_step = None
        status = "completed"
        state = None
        sid = skill or f"evaluation.{case['task']}"
        start = time.perf_counter_ns()
        try:
            if self.arm.startswith("pact"):
                options = ExecutionOptions(
                    trust_level=trust,
                    confirmed_capabilities=frozenset({"eval.commit.run"})
                    if confirmed
                    else frozenset(),
                    tenant_id=tenant,
                    trace_enabled=self.arm != "pact_trace_off",
                    max_workers=workers,
                    audit_mode="off",
                )
                inputs = {
                    "data": data,
                    "target_tenant_id": data.get("target_tenant_id"),
                }
                state = create_execution_state(sid, inputs, trace_id=data["run_id"])
                request = ExecutionRequest(
                    sid,
                    inputs,
                    options=options,
                    trace_id=data["run_id"],
                    channel="evaluation",
                    initial_state=state,
                )
                execution = self.engine.execute(request, trace_callback=events.append)
                status = execution.status
                result = execution.outputs.get("result")
                trace = [
                    {
                        "step_id": s.step_id,
                        "capability": s.capability_id,
                        "status": s.status,
                        "reads": list(s.reads),
                        "writes": list(s.writes),
                    }
                    for s in execution.state.trace.steps
                ]
            else:
                if sid.startswith("evaluation.fanout"):
                    with ThreadPoolExecutor(max_workers=workers) as pool:
                        futures = [
                            pool.submit(self.invoke, "identity", data)
                            for _ in range(data["width"])
                        ]
                        branches = [f.result()["data"] for f in futures]
                    result = self.invoke("merge", data, branches=branches)["data"]
                    pipeline = []
                else:
                    pipeline = PIPELINE if length is None else ["identity"] * length
                for i, op in enumerate(pipeline):
                    failed_step = f"s{i}"
                    guarded = self.arm == "manual_guarded"
                    if guarded and not isinstance(data, dict):
                        raise ValueError("manual input type check")
                    if guarded and op == "commit":
                        if trust not in {"elevated", "privileged"}:
                            raise PermissionError("trust")
                        if not confirmed:
                            raise PermissionError("confirmation")
                        if tenant is None or data.get("target_tenant_id") != tenant:
                            raise PermissionError("tenant")
                    attempts = 2 if sid == "evaluation.retry" and op == "solve" else 1
                    for attempt in range(attempts):
                        try:
                            timeout_op = (
                                "solve"
                                if sid == "evaluation.timeout"
                                else "commit"
                                if sid == "evaluation.effect_timeout"
                                else None
                            )
                            if guarded and op == timeout_op:
                                with ThreadPoolExecutor(max_workers=1) as pool:
                                    produced = pool.submit(
                                        self.invoke, op, data, alternate=alternate
                                    ).result(timeout=0.005)
                            else:
                                produced = self.invoke(op, data, alternate=alternate)
                            break
                        except Exception:
                            if attempt + 1 == attempts:
                                raise
                    if not isinstance(produced, dict) or "data" not in produced:
                        raise ValueError("missing output data")
                    data = produced["data"]
                    if guarded and not isinstance(data, dict):
                        raise ValueError("manual output type check")
                    if guarded and op == "solve" and not ops.integrity(data)["allowed"]:
                        raise ValueError("manual post gate")
                if pipeline:
                    result = data
                failed_step = None
        except Exception as exc:  # noqa: BLE001 -- retain every experimental failure
            status = "failed"
            error = {"type": type(exc).__name__, "message": str(exc)}
            failed_step = getattr(exc, "step_id", None) or failed_step
        elapsed = (time.perf_counter_ns() - start) / 1e6
        if state is not None:
            trace = [
                {
                    "step_id": s.step_id,
                    "capability": s.capability_id,
                    "status": s.status,
                    "reads": list(s.reads),
                    "writes": list(s.writes),
                }
                for s in state.trace.steps
            ]
        bindings = (
            {sid: step.binding_id for sid, step in state.step_results.items()}
            if state is not None
            else {}
        )
        if case.get("fault") == "slow":
            # Observe effects after timed-out Python threads can finish. This wait
            # is outside the latency measurement and prevents trial contamination.
            time.sleep(case.get("fault_delay_ms", 30) / 1000 + 0.015)
        calls, effects = ops.snapshot()
        canonical = (
            {k: result.get(k) for k in ["value", "label"]}
            if isinstance(result, dict)
            else None
        )
        expected = ground_truth(case)
        healthy_correct = status == "completed" and canonical == expected
        return {
            "case_id": case["case_id"],
            "task": case["task"],
            "arm": self.arm,
            "repetition": repetition,
            "skill": sid,
            "status": status,
            "correct": healthy_correct,
            "expected": expected,
            "actual": canonical,
            "latency_ms": elapsed,
            "calls": calls,
            "effects": effects,
            "trace": trace,
            "events": [{"type": e.type, "step_id": e.step_id} for e in events],
            "failed_step": failed_step,
            "error": error,
            "bindings": bindings,
            "tokens_in": sum(c["tokens_in"] for c in calls),
            "tokens_out": sum(c["tokens_out"] for c in calls),
        }
