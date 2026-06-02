# Deployment Guide

> From development install to a hardened production instance.

See also: `docs/DEPLOYMENT_PRODUCT_FLOW.md` for bundle-based preview, promotion,
and rollback operations.

---

## Prerequisites

- Python ≥ 3.11
- `pact-registry` cloned alongside `pact-runtime` (sibling directories)

---

## 1. Development install

```bash
cd pact-runtime
python -m pip install -e ".[all]"
```

Copy and fill `.env.example`:

```bash
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY for LLM-backed capabilities
```

Verify:

```bash
pact-runtime doctor
```

---

## 2. Production install

### 2a. Locked dependencies

```bash
pip install ".[all]" --no-deps   # after resolving versions in a lockfile
```

Or use a container:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir ".[all]"
CMD ["pact-runtime", "serve"]
```

### 2b. Environment variables

| Variable | Required | Default | Purpose |
|----------|:--------:|---------|---------|
| `OPENAI_API_KEY` | For LLM caps | — | OpenAI API key |
| `PACT_RUNTIME_FS_ROOT` | No | `cwd` | Sandbox root for `fs.file.read` |
| `PACT_RUNTIME_AUDIT_DEFAULT_MODE` | No | `standard` | `off` / `standard` / `full` |
| `PACT_RUNTIME_MAX_WORKERS` | No | CPU+4 | Concurrent step threads |
| `PACT_RUNTIME_API_KEY` | For HTTP | — | Server API key for `x-api-key` auth |
| `PACT_RUNTIME_HOST` | No | `127.0.0.1` | Bind address |
| `PACT_RUNTIME_PORT` | No | `8080` | Bind port |
| `PACT_RUNTIME_DEBUG` | No | unset | Enable debug logging |

### 2c. Reverse proxy (**REQUIRED** for network-exposed deployments)

> **⚠️ The built-in HTTP server does not terminate TLS.** You **MUST** place a
> TLS-terminating reverse proxy in front of any instance accessible beyond
> `localhost`. Running without TLS exposes credentials and payloads in plaintext.

```
Client  →  nginx / Caddy (TLS termination)  →  pact-runtime serve (:8080)
```

Nginx example:

```nginx
server {
    listen 443 ssl;
    server_name skills.example.com;

    ssl_certificate     /etc/ssl/certs/skills.pem;
    ssl_certificate_key /etc/ssl/private/skills.key;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # Body limit (should match PACT_RUNTIME max_request_body_bytes)
        client_max_body_size 2m;
    }
}
```

---

## 3. Scaling

### Single instance

---

## 4. CLI `serve` Command

Start the HTTP API server directly:

```bash
pact-runtime serve
```

| Flag              | Env Variable                | Default     | Description                      |
|-------------------|-----------------------------|-------------|----------------------------------|
| `--host`          | `PACT_RUNTIME_HOST`         | `127.0.0.1` | Bind address                     |
| `--port`          | `PACT_RUNTIME_PORT`         | `8080`      | Bind port                        |
| `--api-key`       | `PACT_RUNTIME_API_KEY`      | *(none)*    | API key for `x-api-key` auth     |
| `--cors-origins`  | `PACT_RUNTIME_CORS_ORIGINS` | *(none)*    | Comma-separated allowed origins  |

Example:

```bash
pact-runtime serve --host 0.0.0.0 --port 9090 --api-key my-secret
```

---

## 5. Docker

### Build

```bash
docker build -t pact-runtime .
```

### Run

```bash
docker run -p 8080:8080 \
  -e PACT_RUNTIME_API_KEY=my-secret \
  -e OPENAI_API_KEY=sk-... \
  pact-runtime
```

### docker-compose

Create a `.env` file in the project root:

```dotenv
PACT_RUNTIME_API_KEY=my-secret
OPENAI_API_KEY=sk-...
```

Then:

```bash
docker compose up -d
```

The compose file exposes port `${PACT_RUNTIME_PORT:-8080}`, mounts `./bindings` read-write, and creates a `skills-data` named volume for artifacts.  A health check hits `GET /v1/health` every 30 s.

### Environment Variables Reference

| Variable                       | Default    | Purpose                          |
|--------------------------------|------------|----------------------------------|
| `PACT_RUNTIME_HOST`            | `0.0.0.0`  | Bind address inside container   |
| `PACT_RUNTIME_PORT`            | `8080`     | Server port                      |
| `PACT_RUNTIME_API_KEY`         |            | Auth for protected routes        |
| `PACT_RUNTIME_CORS_ORIGINS`    |            | Comma-separated origins          |
| `PACT_RUNTIME_MAX_WORKERS`     | CPU+4      | DAG scheduler thread pool        |
| `PACT_RUNTIME_ASYNC_WORKERS`   | `4`        | Async execution thread pool      |
| `PACT_RUNTIME_MAX_RUNS`        | `100`      | Max tracked async runs           |
| `OPENAI_API_KEY`               |            | For LLM-backed skills            |
| `OTEL_EXPORTER_OTLP_ENDPOINT` |            | OTel collector endpoint          |
| `OTEL_SERVICE_NAME`            | `pact-runtime` | OTel service name           |

Each pact-runtime instance is stateless (aside from the audit JSONL file).
Scale horizontally by running multiple instances behind a load balancer.

### Audit at scale

- With multiple instances, each writes to its own audit file.
- Use `PACT_RUNTIME_AUDIT_DEFAULT_MODE=off` to disable audit when you have
  external observability (e.g., OpenTelemetry).
- Periodically purge old records: `pact-runtime purge --older-than-days 30`.

### Worker tuning

```bash
# For IO-heavy workloads (many OpenAPI calls)
export PACT_RUNTIME_MAX_WORKERS=16

# For CPU-heavy workloads (large text baselines)
export PACT_RUNTIME_MAX_WORKERS=4
```

---

## 4. Health check

```bash
curl http://127.0.0.1:8080/health
# → {"status": "ok"}
```

---

## 5. Security checklist

Before exposing to a network:

- [ ] **[REQUIRED]** Place a TLS-terminating reverse proxy (nginx/Caddy) in front — the server does **not** support HTTPS natively.
- [ ] **[REQUIRED]** Set `PACT_RUNTIME_API_KEY` to a strong random value (≥ 32 chars).
- [ ] Set `PACT_RUNTIME_AUTH_MODE=enforced` (default since v0.2.0).
- [ ] Set `PACT_RUNTIME_FS_ROOT` to a dedicated read-only directory.
- [ ] Review `docs/SECURITY.md` for SSRF, LFI, rate limiting details.
- [ ] Set `PACT_RUNTIME_AUDIT_DEFAULT_MODE=full` for regulated environments.
- [ ] Restrict `allow_private_networks` to `False` (default) unless on-prem.
- [ ] Review the [OpenAPI spec](specs/consumer_facing_v1_openapi.json) for API contract reference.
