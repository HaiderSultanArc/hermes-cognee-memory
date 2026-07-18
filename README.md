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
ENABLE_BACKEND_ACCESS_CONTROL=true
REQUIRE_AUTHENTICATION=true

# Start the API at http://localhost:8000
docker compose up
```

Backend access control is recommended when multiple Cognee users or datasets need authorization
boundaries. The plugin uses one configured dataset across conversations; authentication protects
that persistent graph, while hashed session IDs separate Cognee's session cache without exposing
raw gateway identifiers. See Cognee's deployment documentation for production databases,
authentication, and API-key creation. Do not expose an auth-disabled Cognee service to an
untrusted network.

## Install

Install the published standalone repository into the active Hermes profile:

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

The entry type is `qa`, with a session ID and the configured persistent Cognee dataset. The provider creates the dataset before the first capture. For gateways, the effective gateway scope and Hermes session ID are deterministically hashed into the Cognee session ID; raw user/chat identifiers are not sent as identifiers. All conversations for the configured agent/profile contribute improved knowledge to the same dataset, while Cognee's session cache remains separated by session. Primary non-CLI initialization without a stable gateway scope fails closed. Local CLI sessions use their Hermes session ID directly. Cron/delegated/non-primary contexts do not auto-write.

At a real Hermes session boundary (exit, reset, or gateway expiry), the provider queues:

```text
POST /api/v1/improve
```

The provider sends that session ID with `run_in_background: false`. This bridges acknowledged cached Q&A into the permanent knowledge graph with confirmed completion. Turn writes and the improve request share one bounded FIFO worker, so persistence cannot overtake pending captures. Transient writes use bounded exponential retry; an unacknowledged capture blocks improvement rather than falsely marking the session persisted. A prolonged outage can still exceed the in-memory retry and shutdown windows, so this is best-effort unless the operator provides external process supervision and recovery. Set `auto_improve` to `false` if graph processing cost should be triggered manually.

Built-in Hermes `MEMORY.md` and `USER.md` remain the curated source of truth and are not mirrored into Cognee. Use `cognee_remember` for information that should also enter episodic/graph memory.

### Recall

The `cognee_recall` tool is the secure default. The provider tells Hermes to use it proactively when a request may benefit from prior context. Tool results are bounded, deduplicated, flattened, and labeled as untrusted evidence so stored prompt-injection text is not presented as an instruction.

Automatic prefetch is available by setting `auto_recall` to `true`, but is disabled by default. Hermes 0.18.2 wraps all provider-prefetched content in a generic system note that calls it "authoritative reference data"; until Hermes exposes provider-level trust metadata, enabling automatic recall explicitly opts into that trust model. When enabled, Hermes queues background recall through:

```text
POST /api/v1/recall
```

Default scope is `session + graph`, with automatic Cognee search routing (`search_type: null`). The two sources are queried independently so a missing first-run graph dataset does not discard valid session hits, and a cache outage does not discard graph hits. Background prefetch concurrency is bounded; excess speculative requests are skipped rather than creating unbounded threads.

### Tools

The provider exposes:

- `cognee_recall` — explicit memory lookup with scope and result limit
- `cognee_remember` — explicit session capture, persisted to the graph after a successful session-end improvement

The plugin does not define memory deletion, decay, reinforcement, or retention policy. Those semantics remain owned by the configured upstream Cognee service.

## Advanced configuration

Edit `$HERMES_HOME/cognee/config.json`:

```json
{
  "service_url": "http://localhost:8000",
  "dataset_name": "hermes-{identity}",
  "auto_capture": true,
  "auto_improve": true,
  "auto_recall": false,
  "recall_scope": ["session", "graph"],
  "top_k": 8,
  "request_timeout_seconds": 15,
  "graph_recall_timeout_seconds": 45,
  "improve_timeout_seconds": 300,
  "prefetch_timeout_seconds": 3,
  "prefetch_max_concurrency": 2,
  "max_prefetch_chars": 6000,
  "recall_circuit_failure_threshold": 3,
  "recall_circuit_cooldown_seconds": 30,
  "writer_queue_size": 256,
  "write_retry_attempts": 3,
  "write_retry_base_seconds": 0.25,
  "shutdown_flush_seconds": 310
}
```

`request_timeout_seconds` bounds health, capture, dataset, and session-only recall requests.
`graph_recall_timeout_seconds` applies when recall can query the graph, and
`improve_timeout_seconds` applies to synchronous session improvement. `prefetch_timeout_seconds`
only bounds how long Hermes waits for a queued background result; it does not cancel the underlying
network call. After `recall_circuit_failure_threshold` consecutive all-source recall failures,
automatic and explicit recall pause for `recall_circuit_cooldown_seconds`. After cooldown, exactly
one request probes the service; a failed probe immediately reopens the circuit, while a successful
probe closes it.

Keep `shutdown_flush_seconds` longer than `improve_timeout_seconds`. A shorter flush window can
terminate the provider while a valid session-end graph improvement is still running.

## Verify

```bash
hermes memory status
curl -fsS http://localhost:8000/health
```

Development checks:

```bash
uv sync --locked --extra dev
uv run pytest -q
uv run pytest --cov=src/hermes_cognee_memory --cov-branch --cov-fail-under=85
uv run ruff check .
uv build
```

The suite includes a real Hermes discovery/load test and an end-to-end local HTTP transport test.

## Repository layout

The implementation, module documentation, and tests use matching paths:

```text
src/hermes_cognee_memory/
docs/hermes_cognee_memory/
tests/hermes_cognee_memory/
```

The root `__init__.py` is intentionally a thin exception to the `src` layout. Hermes loads that
file directly when it discovers a standalone plugin; the file only re-exports the provider from
`src/hermes_cognee_memory`.

## Security notes

- API keys are sent only in the `X-Api-Key` header and are never written to provider JSON.
- The configured dataset is persistent across conversations; use separate configured datasets or
  Cognee identities only for deliberate agent, tenant, or trust boundaries.
- Service URLs reject embedded credentials, query strings, fragments, and unexpected paths; HTTP redirects are not followed, so auth headers cannot be redirected to another origin.
- Success responses are capped at 2 MiB. Remote error bodies are never exposed to the model.
- Plain HTTP is accepted only for loopback services; remote and link-local Cognee services must use HTTPS.
- Gateway scope and the Hermes session ID are hashed into deterministic Cognee session IDs. Missing gateway scope fails closed, and raw gateway identifiers are not sent as identifiers. Persistent graph memory is intentionally shared within the configured dataset.
- Automatic capture sends completed user/assistant turns, and automatic recall sends the current query, to the configured Cognee service. Set both `auto_capture` and `auto_recall` to `false` when conversation data must stay inside Hermes.
- Explicitly recalled content is probabilistic, untrusted evidence. It is flattened to one line per field and labeled as non-authoritative data; it cannot authorize actions or override current user instructions or curated Hermes memory. Automatic recall is opt-in because Hermes 0.18.2 applies its generic authoritative-memory wrapper to provider-prefetched content.
- Cognee is a network memory service. Its availability, retention, backups, access control, and deletion policy remain operator responsibilities.

## License

MIT
