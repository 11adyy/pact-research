# Installation & Setup

## Prerequisites

- **Python 3.11+** (tested with 3.11 through 3.14)
- **git** (to clone the repositories)

## Quick Install

```bash
# 1. Clone both repositories side by side (required)
git clone https://example.invalid/pact-runtime.git
git clone https://example.invalid/pact-registry.git

# 2. Install the runtime (with all optional extras)
cd pact-runtime
pip install -e ".[all]"
```

That's it. The `pact-runtime` CLI is now available.

## Verify Installation

```bash
# Check CLI
pact-runtime --help

# Validate local setup first
pact-runtime doctor

# Run first skill (uses Python baselines, no API key needed)
echo '{"text":"PACT turns agent reasoning into reusable executable skills."}' > input_qs.json
pact-runtime run text.language-summary --input-file input_qs.json
rm input_qs.json
```

If `pact-runtime` is not available on your PATH, run the same commands via:

```bash
python -m cli.main doctor
python -m cli.main run text.language-summary --input-file input_qs.json
```

On Windows PowerShell, this module form is the most reliable in a fresh shell.

## Optional: LLM Provider

Some capabilities use OpenAI as a binding backend. To enable them:

```bash
# Copy the example env file
cp .env.example .env

# Edit .env and set your API key
# OPENAI_API_KEY=sk-...

# Then export it (Linux/Mac)
export OPENAI_API_KEY=sk-...

# Or on Windows PowerShell
$env:OPENAI_API_KEY = "sk-..."
```

Without an API key, the runtime falls back to deterministic Python baselines
for all capabilities. This is fully functional for development and testing.

## Install Options

```bash
# Minimal (only core dependencies: pyyaml, requests)
pip install -e .

# With PDF support
pip install -e ".[pdf]"

# With web scraping support
pip install -e ".[web]"

# With all extras (pdf + web)
pip install -e ".[all]"

# With development tools (extras + pytest)
pip install -e ".[dev]"
```

## Registry Tooling

The registry repo has its own lightweight dependencies:

```bash
cd ../pact-registry
pip install -r requirements.txt
```

Validate the registry:

```bash
python tools/validate_registry.py
python tools/generate_catalog.py
python tools/registry_stats.py
```

## Project Layout

```
your-workspace/
├── pact-runtime/           ← Runtime (this repo)
│   ├── cli/                  CLI entry point
│   ├── runtime/              Execution engine, scheduler, binding system
│   ├── gateway/              Skill discovery and attach
│   ├── customer_facing/      HTTP API and MCP bridge
│   ├── official_services/    Python baseline implementations
│   ├── bindings/official/    Binding definitions per capability
│   ├── services/official/    Service descriptors
│   ├── policies/             Default binding selection
│   └── docs/                 Architecture documentation
│
└── pact-registry/   ← Contracts (companion repo)
    ├── capabilities/         Capability YAML definitions
    ├── skills/               Skill YAML workflows
    ├── vocabulary/           Controlled naming vocabulary
    ├── catalog/              Generated machine-readable catalogs
    └── tools/                Validation and governance tooling
```

Both repos must be siblings in the same parent directory for the runtime
to locate registry definitions automatically.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(none)* | OpenAI API key for LLM-backed bindings |
| `PACT_RUNTIME_FS_ROOT` | `cwd()` | Root directory for `fs.file.read` sandbox |
| `PACT_RUNTIME_DEBUG` | *(unset)* | Enable verbose debug logging |
| `PACT_RUNTIME_AUDIT_DEFAULT_MODE` | `standard` | Audit mode: `off`, `standard`, `full` |

See `.env.example` for the full list.

## Next Steps

- [10-minute onboarding](ONBOARDING_10_MIN.md) — mental model and first skill run
- [Runner guide](RUNNER_GUIDE.md) — architecture deep dive
- [Project status](PROJECT_STATUS.md) — current milestone
