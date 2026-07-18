# Hermes Cognee Memory Plugin Plan

## Purpose

Maintain `hermes-cognee-memory` as a small, standalone ArcHermes memory-provider plugin that
integrates with the current upstream Cognee HTTP API. The plugin adapts lifecycle, identity,
configuration, and transport concerns. It does not fork Cognee's memory model.

## Ownership Boundary

The plugin owns:

- ArcHermes `MemoryProvider` discovery and lifecycle integration;
- conversion of completed Hermes turns into typed Cognee Q&A entries;
- one configured persistent dataset per Hermes identity/profile;
- privacy-safe mapping from Hermes gateway/session scope to Cognee session IDs;
- ordered capture, periodic improvement checkpoints, and session-end catch-up requests;
- bounded recall formatting and untrusted-content labeling;
- authentication headers, URL validation, timeouts, retries, circuit breaking, and shutdown;
- plugin configuration, diagnostics, documentation, packaging, and tests.

Upstream Cognee owns:

- graph construction and retrieval algorithms;
- session persistence and improvement pipeline behavior;
- memory reinforcement, feedback, decay, retention, deletion, and consolidation;
- graph/vector/relational storage semantics;
- dataset authorization and backend access control;
- the HTTP request and response contract implemented by the Cognee service.

ArcHermes core should remain Cognee-agnostic. Generic improvements to memory-provider trust labels
or lifecycle hooks belong in ArcHermes only when they benefit every provider.

## Supported Architecture

```text
ArcHermes primary session
    -> standalone Cognee MemoryProvider
    -> validated HTTP(S) transport
    -> upstream Cognee API
    -> Cognee session cache and persistent graph
```

The plugin is installed under `$HERMES_HOME/plugins/cognee`. It uses no Cognee SDK dependency and
does not require Cognee-specific code in ArcHermes.

## Current API Contract

The supported Cognee service must provide:

| Operation | Endpoint | Plugin use |
|---|---|---|
| Health | `GET /health` | Operator and compatibility diagnostics |
| Dataset ensure | `POST /api/v1/datasets` | Create or reuse the configured persistent dataset |
| Capture | `POST /api/v1/remember/entry` | Store a typed Q&A in a scoped session |
| Recall | `POST /api/v1/recall` | Search session and/or persistent graph memory |
| Improve | `POST /api/v1/improve` | Ask Cognee to process a completed session synchronously |

The plugin exposes `cognee_recall` and `cognee_remember`. It deliberately exposes no custom
forgetting, weighting, or graph-mutation tools.

## ArcHermes Integration

### Initialization

- Expand `{identity}` in the configured dataset template.
- Use the Hermes session ID directly for CLI sessions.
- For gateways, hash platform, stable `gateway_session_key`, and Hermes session ID into a bounded
  Cognee session ID.
- Fail closed for primary non-CLI agents without stable gateway scope.
- Disable automatic writes for cron, delegated, and non-primary contexts.

### Capture

- Queue completed primary-agent turns without blocking the response path.
- Ensure the configured dataset before the first write.
- Send bounded question, answer, and context fields as a typed Q&A entry.
- Track in-memory write acknowledgement so improvement cannot pass a failed or pending capture.

### Improvement checkpoints and session completion

- Queue one synchronous `/improve` checkpoint after each configured number of captured turns.
- Keep the checkpoint independent of ArcHermes skill-review scheduling, which counts model/tool
  iterations and is best-effort rather than a memory lifecycle boundary.
- At session completion, queue a catch-up request when captures are newer than the last checkpoint.
- Use the same FIFO worker as capture to preserve ordering.
- Treat Cognee's returned result as the upstream pipeline outcome; do not reinterpret or extend its
  memory semantics.

### Recall

- Keep explicit `cognee_recall` available for scoped session and graph lookup.
- Query session and graph sources independently when both are requested so one unavailable source
  does not erase valid results from the other.
- Deduplicate, flatten, label, and cap recalled content before returning it to Hermes.
- Keep automatic prefetch disabled by default until ArcHermes can label provider memory as
  non-authoritative data.

## Configuration

Non-secret configuration lives in `$HERMES_HOME/cognee/config.json` with mode `0600`. The service
credential lives only in `COGNEE_API_KEY`.

| Setting | Default | Purpose |
|---|---:|---|
| `service_url` | `http://localhost:8000` | Cognee server root; plaintext is loopback-only |
| `dataset_name` | `hermes-{identity}` | Persistent graph dataset |
| `auto_capture` | `true` | Queue completed primary turns |
| `auto_improve` | `true` | Enable periodic and lifecycle-boundary improvement |
| `improve_every_n_turns` | `10` | Checkpoint acknowledged captures during active sessions; `0` disables periodic checkpoints |
| `auto_recall` | `false` | Enable background prefetch only by explicit operator choice |
| `recall_scope` | `session, graph` | Sources queried by automatic recall |
| `top_k` | `8` | Bounded result count |
| `request_timeout_seconds` | `15` | Health, dataset, capture, and session-only recall |
| `graph_recall_timeout_seconds` | `45` | Recall paths that may invoke graph/LLM work |
| `improve_timeout_seconds` | `300` | Synchronous upstream session improvement |
| `shutdown_flush_seconds` | `310` | Bound for queued writes and improvement during shutdown |
| `writer_queue_size` | `256` | Bound for pending mutations |
| `prefetch_max_concurrency` | `2` | Bound for speculative recall threads |
| `max_prefetch_chars` | `6000` | Prompt-injection and context-size boundary |

Validation must reject embedded URL credentials, unexpected paths, query strings, fragments,
remote plaintext HTTP, invalid numeric bounds, and secret persistence in JSON.

## Security And Isolation

- Send API keys only as `X-Api-Key` to the configured origin.
- Never follow HTTP redirects with authentication headers.
- Cap success responses and suppress remote error bodies.
- Treat recalled memory as untrusted evidence, never authorization or instructions.
- Keep one dataset across ordinary conversations; use separate authenticated Cognee identities or
  datasets only for deliberate trust or tenant boundaries.
- Require real Cognee authentication and backend access control when isolation matters. Hashed
  session IDs and dataset names are routing/privacy mechanisms, not authorization boundaries.
- Never store conversation text, credentials, or API responses in plugin metadata files.

## Reliability

- Preserve FIFO ordering between capture and improvement.
- Retry transient mutation failures with bounded exponential backoff.
- Do not mark a session improved when an earlier capture was not acknowledged.
- Treat an empty successful `/improve` response as lock contention, not confirmed persistence.
- Bound writer queues, prefetch concurrency, response sizes, retry attempts, and shutdown time.
- Use a recall circuit breaker so repeated outages do not add latency to every Hermes turn.
- Keep health/session timeouts short while giving graph recall and improvement independent budgets.
- Report availability honestly: configuration load is not proof that Cognee is reachable or ready.

## Performance Work

Performance changes must remain at the integration boundary and be measured before implementation.

### Priority 1: Instrument plugin latency

- Record bounded duration and outcome for dataset ensure, capture, each recall source, improve,
  queue wait, retry, and shutdown flush.
- Exclude prompts, recalled text, credentials, dataset names, raw session IDs, and gateway IDs.
- Distinguish plugin queue/transport latency from Cognee server processing time.

### Priority 2: Reduce avoidable requests

- Cache successful dataset readiness per provider instance.
- Coalesce duplicate pending improvements for the same session version.
- Skip empty captures and sessions with no acknowledged writes.
- Reuse completed prefetch results only for the matching session/query generation.

### Priority 3: Tune concurrency and budgets

- Benchmark explicit session recall, graph recall, one-turn capture, session-end improvement, and
  shutdown under ordinary ArcHermes workloads.
- Adjust queue size, prefetch concurrency, timeouts, and retry budgets from measurements.
- Do not add unbounded workers or parallelize ordered mutations.

### Performance targets

| Plugin-visible operation | Target |
|---|---:|
| Capture enqueue | under 10 ms |
| Session-only recall | under 1 s |
| Graph recall | under 5 s when Cognee is healthy |
| Queue wait excluding active improve | under 100 ms |
| Shutdown bookkeeping excluding upstream improve | under 1 s |

Upstream Cognee processing can exceed these targets. Metrics must make that distinction explicit
instead of hiding it behind a larger catch-all timeout.

## Compatibility Strategy

- Test against the current ArcCognee checkout while it is exactly aligned with `upstream/main`.
- Keep request payload fixtures matching upstream endpoint DTOs.
- Add a bounded compatibility diagnostic that checks health and reports missing required endpoints
  without mutating user data.
- Pin the documented minimum Cognee version only after verifying all required endpoints exist in
  that release.
- When upstream changes an endpoint, update the client adapter and tests; do not patch ArcCognee to
  preserve an obsolete plugin contract.

## Test And Documentation Contract

Every maintained source module has mirrored documentation and pytest coverage:

```text
src/hermes_cognee_memory/client.py
docs/hermes_cognee_memory/client.md
tests/hermes_cognee_memory/test_client.py
```

Required gates:

```bash
uv sync --locked --extra dev
uv run ruff check .
uv run pytest -q
uv run pytest --cov=src/hermes_cognee_memory --cov-branch --cov-fail-under=85
uv build
```

The suite must cover URL/auth safety, payload compatibility, response bounds, dataset/session
routing, lifecycle ordering, failed-capture behavior, timeout selection, circuit breaking,
concurrency bounds, shutdown, plugin discovery, and a local synthetic HTTP integration flow.

## Delivery Phases

### Phase 1: Upstream compatibility cleanup

- Remove fork-only Cognee endpoint assumptions and obsolete provenance state.
- Update source, tests, README, module docs, and operational notes.
- Pass all local quality gates against current upstream-compatible payloads.

Exit condition: the plugin contains no dependency on ArcCognee-only memory semantics.

### Phase 2: Compatibility diagnostics

- Define a read-only compatibility report for required endpoints and authentication failures.
- Make `hermes memory status` distinguish configured, reachable, authenticated, and compatible.
- Document actionable failures without exposing response bodies or credentials.

Exit condition: operators can identify a wrong Cognee version or auth configuration without log
archaeology.

### Phase 3: Plugin observability

- Add bounded per-operation timing and queue metrics.
- Add structured skip/failure reasons.
- Validate that metrics contain no conversation or identity data.

Exit condition: latency can be attributed to ArcHermes scheduling, plugin queueing, transport, or
upstream Cognee.

### Phase 4: Measured performance tuning

- Establish reproducible CLI and gateway benchmarks.
- Tune existing bounds and remove demonstrated redundant work.
- Preserve ordering, isolation, and failure semantics.

Exit condition: documented targets pass in the managed local deployment or deviations are clearly
attributed to upstream Cognee/model processing.

### Phase 5: Release validation

- Install through the normal ArcHermes plugin updater into a disposable profile.
- Validate setup, authenticated capture, session recall, graph recall, session-end improve,
  restart, and outage recovery with synthetic canaries.
- Validate the managed active-profile deployment separately before release.

Exit condition: source, installed plugin, documentation, and live behavior agree.

## Non-Goals

- Forking or extending Cognee's memory algorithms.
- Adding custom forgetting, decay, reinforcement, feedback, or graph mutation semantics.
- Importing the Cognee SDK into ArcHermes.
- Adding Cognee-specific code to ArcHermes core.
- Treating dataset names or hashes as security boundaries.
- Making automatic recall authoritative.
- Hiding slow upstream processing behind unbounded timeouts or workers.
