# PACT: Procedural Agent Composition and Traceability

## 1. Introduction

Modern AI agents are predominantly built around **prompt-driven execution**: a model receives instructions, optionally calls tools, and produces outputs based on implicit reasoning hidden within the model.

While effective for simple tasks, this paradigm presents fundamental limitations:

- Opaque reasoning and lack of inspectability
- Fragile and non-deterministic behavior
- Unsafe interaction with external systems
- Limited composability and reuse
- Difficulty in testing, auditing, and governing execution

**PACT (Procedural Agent Composition and Traceability)** proposes a different approach.

> PACT defines a standard for building agents as **structured execution systems**, where reasoning, decisions, and actions are explicit, composable, and governable.

---

## 2. The Problem with Prompt-Driven Agents

Current agent systems rely heavily on:

- Implicit reasoning inside LLMs
- Ad-hoc tool calling
- Unstructured intermediate state
- Weak or externalized safety mechanisms

This leads to systems that are:

| Limitation | Impact |
|-----------|--------|
| Hidden reasoning | Impossible to debug or audit |
| Non-determinism | Hard to reproduce behavior |
| Tool misuse | Risk of unsafe actions |
| Tight coupling | Low reuse across systems |
| Prompt complexity | Hard to maintain and scale |

---

## 3. The PACT Model

PACT introduces a **Cognitive Execution Layer** between agents and external systems.

### 3.1 Cognitive State

- Frame — context, goals, constraints
- Working — intermediate reasoning artifacts
- Output — final results
- Trace — execution lineage

### 3.2 Capabilities (Contracts)

Atomic operations with explicit inputs/outputs, independent of execution backend.

### 3.3 Skills (Execution Graphs)

Declarative workflows (DAGs) composing capabilities.

### 3.4 Safety Layer

- Trust levels
- Validation gates
- Human confirmation
- Scope constraints

---

## 4. Core Principles

1. Execution over prompting  
2. Explicit state over implicit context  
3. Contracts over conventions  
4. Separation of intent and execution  
5. Safety as a first-class concern  

---

## 5. Architecture Overview

Agent → PACT Layer → Capabilities → Bindings → Services

---

## 6. Reference Implementation

PACT Runtime is a reference implementation of PACT.

---

## 7. Vision

PACT enables:

- Reproducible agents
- Safe execution
- Composable intelligence
- Interoperable ecosystems

---

## 8. Conclusion

PACT shifts agent design:

From prompt-driven → to execution-driven systems.

---

## 📄 Research Paper

The formal foundations of PACT are described in:

> Pelegrini, N. D. (2026). *From Agent Instructions to Executable Procedures: The PACT Architecture*. Zenodo. [docs/PAPER.md](docs/PAPER.md)

📥 [Download PDF](docs/papers/pact_paper_final_clean_v2.pdf) · 📖 [Full paper page](docs/PAPER.md)

