# PACT: procedures an agent can execute and inspect

**Procedural Agent Composition and Traceability** gives recurring agent work an explicit representation. A model can still interpret a goal and perform individual operations, while the procedure records which operations cooperate, the information each consumes, and the constraints on their execution.

This repository contains the reference runtime. Its design starts with the composition model and derives the execution machinery from it.

## Representing the work

| Artifact | Responsibility |
| --- | --- |
| Skill | Define a procedure through steps and dependencies. |
| Capability | Name an operation and specify its input and output contract. |
| State | Keep inputs, intermediate artifacts and results addressable. |
| Binding | Choose an implementation independently of the procedure. |

A skill preserves the organization of a task across backend changes. A capability can be reused at multiple invocation sites. Bindings may connect an operation to a deterministic function, a model, or an external service; a typed contract alone cannot guarantee semantic correctness.

## Making the procedure executable

The runtime resolves implementations, schedules dependencies, maps state between steps, records execution evidence and applies configured policies. The relevant boundaries let a developer inspect an intermediate result, replace an implementation or enforce a constraint where it is needed.

Probabilistic implementations remain probabilistic. Traces expose what executed; they do not prove an answer correct. The value of the additional boundaries depends on the reuse, inspection and control requirements of the task.

## Research account

The accompanying manuscript, *From Agent Instructions to Executable Procedures: The PACT Architecture*, presents the composition model before the runtime. Its reported evaluation compares single-call prompting with structured execution using the same model on two small task families.

| Reported mean latency | Single call | Procedure |
| --- | ---: | ---: |
| Constrained decision | 4.79 s | 12.17 s |
| Text processing | 2.93 s | 7.86 s |

The structured configuration exposes intermediate traces and independently reusable operations. Reported text-output Jaccard variation rises from approximately 0.12 to 0.17. These observations describe the evaluated configurations; they do not establish better semantic accuracy, a stability guarantee or isolated scheduling overhead. The manuscript reports existing measurements rather than a new benchmark run.

## Run the local copy

Keep `pact-runtime/` and the supplied `pact-registry/` next to each other. Python 3.11 or later is required.

```bash
cd pact-runtime
python -m pip install -e .
python skills.py doctor
python skills.py run text.language-summary --input '{"text":"A procedure makes intermediate work inspectable."}'
```

Use `PACT_RUNTIME_REGISTRY_ROOT` to select another local catalog. Configure `PACT_RUNTIME_REGISTRY_URL` before requesting a remote clone. The ZIP provides the local catalog without its original Git history. Remote examples using `example.invalid` are placeholders to configure when publishing.

## Reference material

- [docs/INSTALLATION.md](docs/INSTALLATION.md)
- [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)
- [LICENSE](LICENSE)
