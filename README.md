# Hermes Cognee Memory

A standalone [Hermes Agent](https://github.com/NousResearch/hermes-agent) memory provider backed by a separately managed [Cognee](https://github.com/topoteretes/cognee) API service.

This plugin captures completed Hermes turns as Cognee typed Q&A entries and recalls both current-session and persistent graph memory before later turns. It uses Cognee over HTTP and does **not** import the Cognee Python SDK into Hermes.

## Why a standalone repository?

Hermes's contribution policy keeps third-party product integrations out of the core `plugins/` tree. Exclusive memory providers are distributed as standalone repositories and installed under `$HERMES_HOME/plugins/<name>`.

## Requirements

- Python **3.11–3.13**
- Hermes Agent **0.18.2+** with the exclusive `MemoryProvider` plugin API
- Cognee API **1.3.0+** exposing `/health`, `/api/v1/datasets`, `/api/v1/remember/entry`, `/api/v1/recall`, and `/api/v1/improve`
- Cognee session memory enabled with `CACHING=true`
- An API key in `COGNEE_API_KEY` when Cognee authentication is enabled

The plugin itself has **no runtime Python dependencies** beyond Hermes and the standard library.

## Start Cognee

From a Cognee checkout, configure its required LLM/database environment and enable session caching:

```bash
# In Cognee's .env
CACHING=true

# Start the API at http://localhost:8000
docker compose up
```

See Cognee's own deployment documentation for production databases, authentication, and API-key creation. Do not expose an auth-disabled Cognee service to an untrusted network.

## Install

After the standalone repository is published, install it into the active Hermes profile:

```bash
hermes plugins install HaiderSultanArc/hermes-cognee-memory
hermes memory setup cognee
```

Do not use `pip install` to activate this provider. Hermes discovers exclusive memory
providers from the active profile's plugin directory; `hermes plugins install` places
the repository there and preserves the required `plugin.yaml` and root `__init__.py`.

For local development, link a checkout directly:

```bash
PLUGIN_DIR="${HERMES_HOME:-$HOME/.hermes}/plugins/cognee"
mkdir -p "$(dirname "$PLUGIN_DIR")"
ln -s /absolute/path/to/hermes-cognee-memory "$PLUGIN_DIR"
```

## Configure

Run the provider setup flow:

```bash
hermes memory setup cognee
```

It asks for:

- **Service URL** — default `http://localhost:8000`; both a server root and a trailing `/api/v1` are accepted. Plain HTTP is restricted to loopback hosts; remote services require HTTPS.
- **Dataset name** — default `hermes-{identity}`; `{identity}` expands to the active Hermes agent identity/profile.
- **API key** — optional for local auth-disabled Cognee; stored only in the active Hermes `.env` as `COGNEE_API_KEY`.

Non-secret settings are stored in `$HERMES_HOME/cognee/config.json` with mode `0600`.

The API key is the only environment setting:

```bash
COGNEE_API_KEY=...
```

## Behavior

### Automatic capture

After each completed primary-agent turn, the provider queues a non-blocking request to:

```text
POST /api/v1/remember/entry
```

The entry type is `qa`, with the Hermes session ID and configured Cognee dataset. Gateway memory receives a deterministic hashed suffix derived from Hermes's effective session key: DMs and per-user sessions stay isolated, while intentionally shared group/thread sessions share their conversation dataset. Primary non-CLI initialization without that scope fails closed; a user identifier alone is not accepted because it cannot prove whether the conversation is shared. Local CLI sessions retain the profile-wide dataset name. Cron/delegated/non-primary contexts do not auto-write.

At a real Hermes session boundary (exit, reset, or gateway expiry), the provider queues:

```text
POST /api/v1/improve
```

Before the first improvement, the provider idempotently creates the dataset and sends that session ID with `run_in_background: false`. This bridges acknowledged cached Q&A into the permanent knowledge graph with confirmed completion. Turn writes and the improve request share one bounded FIFO worker, so persistence cannot overtake pending captures. Transient writes use bounded exponential retry; an unacknowledged capture blocks improvement rather than falsely marking the session persisted. A prolonged outage can still exceed the in-memory retry and shutdown windows, so this is best-effort unless the operator provides external process supervision and recovery. Set `auto_improve` to `false` if graph processing cost should be triggered manually.

Built-in Hermes `memory` adds and replacements are mirrored. Removes are intentionally **not** translated to Cognee: Cognee's forget operations can have wider dataset/user scope and are not safely equivalent to deleting one Hermes text entry.

### Automatic recall

At the end of a turn, Hermes queues background recall for the next turn through:

```text
POST /api/v1/recall
```

Default scope is `session + graph`, with automatic Cognee search routing (`search_type: null`). The two sources are queried independently so a missing first-run graph dataset does not discard valid session hits, and a cache outage does not discard graph hits. Background prefetch concurrency is bounded; excess speculative requests are skipped rather than creating unbounded threads. Returned memory is bounded, deduplicated, flattened, and labeled as untrusted reference data. These controls reduce prompt-injection risk but cannot make arbitrary stored text inherently trustworthy.

### Tools

The provider exposes:

- `cognee_recall` — explicit memory lookup with scope and result limit
- `cognee_remember` — explicit session capture, persisted to the graph after a successful session-end improvement

No broad delete tool is exposed.

## Advanced configuration

Edit `$HERMES_HOME/cognee/config.json`:

```json
{
  "service_url": "http://localhost:8000",
  "dataset_name": "hermes-{identity}",
  "auto_capture": true,
  "auto_improve": true,
  "auto_recall": true,
  "recall_scope": ["session", "graph"],
  "top_k": 8,
  "request_timeout_seconds": 15,
  "prefetch_timeout_seconds": 3,
  "prefetch_max_concurrency": 2,
  "max_prefetch_chars": 6000,
  "writer_queue_size": 256,
  "write_retry_attempts": 3,
  "write_retry_base_seconds": 0.25,
  "shutdown_flush_seconds": 30
}
```

`prefetch_timeout_seconds` only bounds how long Hermes waits for a queued background result. Network calls themselves are bounded by `request_timeout_seconds`.

## Verify

```bash
hermes memory status
curl -fsS http://localhost:8000/health
```

Development checks:

```bash
uv sync --locked --extra dev
uv run pytest -q
uv run pytest --cov=hermes_cognee_memory --cov-branch --cov-fail-under=85
uv run ruff check .
uv build
```

The suite includes a real Hermes discovery/load test and an end-to-end local HTTP transport test.

## Security notes

- API keys are sent only in the `X-Api-Key` header and are never written to provider JSON.
- Service URLs reject embedded credentials, query strings, fragments, and unexpected paths; HTTP redirects are not followed, so auth headers cannot be redirected to another origin.
- Success responses are capped at 2 MiB. Remote error bodies are never exposed to the model.
- Plain HTTP is accepted only for loopback services; remote and link-local Cognee services must use HTTPS.
- Gateway datasets follow Hermes's effective session boundary using deterministic hashes. DMs and per-user sessions remain isolated; intentionally shared group/thread sessions share memory just as they share transcript context. Missing gateway scope fails closed, and raw identifiers are never placed in dataset names.
- Automatic capture sends completed user/assistant turns, and automatic recall sends the current query, to the configured Cognee service. Set both `auto_capture` and `auto_recall` to `false` when conversation data must stay inside Hermes.
- Recalled content is untrusted data. It is flattened to one line per field and explicitly labeled as reference data; it must not override the live system/user prompt.
- Cognee is a network memory service. Its availability, retention, backups, access control, and deletion policy remain operator responsibilities.

## License

MIT
