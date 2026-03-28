# Environment Variables Reference

All environment variables use the `PACT_RUNTIME_` prefix.

## Core Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `PACT_RUNTIME_REGISTRY_ROOT` | `../pact-registry` (sibling dir) | Path to the registry repo (capabilities, skills, vocabulary) |
| `PACT_RUNTIME_RUNTIME_ROOT` | Project root | Path to pact-runtime runtime root |
| `PACT_RUNTIME_HOST_ROOT` | Same as runtime root | Path to the host root (local overrides, `.pact-runtime/` dir) |

## Server Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PACT_RUNTIME_HOST` | `127.0.0.1` | Bind address for the HTTP server |
| `PACT_RUNTIME_PORT` | `8080` | Port for the HTTP server |
| `PACT_RUNTIME_CORS_ORIGINS` | _(empty — CORS disabled)_ | Comma-separated allowed origins (e.g. `http://localhost:3000,https://app.example.com`) |
| `PACT_RUNTIME_DRAIN_SECONDS` | `5` | Graceful shutdown drain period (seconds) |
| `PACT_RUNTIME_ASYNC_WORKERS` | `4` | Number of async execution workers for `/execute/async` |
| `PACT_RUNTIME_MAX_RUNS` | `100` | Maximum stored runs in the in-memory RunStore |

## Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `PACT_RUNTIME_AUTH_MODE` | `permissive` | Auth enforcement: `enforced` (reject unauthenticated), `permissive` (allow anonymous as reader), `disabled` |
| `PACT_RUNTIME_API_KEY` | _(none)_ | API key for `X-API-Key` header authentication |
| `PACT_RUNTIME_RBAC` | _(deprecated)_ | **Deprecated** — use `PACT_RUNTIME_AUTH_MODE=enforced` instead. Setting `1`/`true`/`yes` enables enforced mode. |
| `PACT_RUNTIME_TRUSTED_PROXIES` | _(empty)_ | Comma-separated trusted proxy CIDRs for `X-Forwarded-For` parsing |

## Webhooks

| Variable | Default | Description |
|----------|---------|-------------|
| `PACT_RUNTIME_WEBHOOKS_REQUIRE_SECRET` | _(empty)_ | When set to `1`/`true`, webhook registration requires an HMAC secret |

## Execution Safety

| Variable | Default | Description |
|----------|---------|-------------|
| `PACT_RUNTIME_PYTHONCALL_ALLOWED_MODULES` | _(empty — all allowed)_ | Comma-separated allowlist of Python modules for PythonCall bindings |
| `PACT_RUNTIME_PYTHONCALL_TIMEOUT` | `30` | Timeout in seconds for PythonCall binding execution |

## Scaffolder

| Variable | Default | Description |
|----------|---------|-------------|
| `PACT_RUNTIME_SCAFFOLDER_MODE` | `binding-first` | Scaffolding mode: `binding-first` or `contract-first` |
