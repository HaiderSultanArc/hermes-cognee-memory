# Hermes Cognee Memory Operational Evaluation

## Purpose

This is the running soak-test record for using Cognee in ordinary Hermes work and
comparing it with Hermes's curated default memory. It records observed behavior, not
marketing expectations. Synthetic facts should be used for controlled tests; real
conversation data is recorded only through the configured Hermes capture policy.

## Scope And Runtime Boundary

- Cognee is attached to Hermes through `hermes-cognee-memory`.
- It does not transparently replace the separate Codex memory system used by a Codex
  session. Codex-side comparisons therefore require an explicit Cognee request or an
  equivalent Hermes run.
- Automatic capture and session-end improvement are enabled in the evaluated Hermes
  profile.
- Automatic recall remains disabled. Hermes 0.18.2 labels provider-prefetched memory as
  authoritative, which is too strong for probabilistic, externally stored recall.
- `cognee_recall` is the preferred evaluation path because its results are bounded and
  explicitly labeled as untrusted evidence.

## Operating Decision

Use both systems, for different jobs:

| Need | Preferred system | Reason |
|---|---|---|
| Exact durable preference or workflow rule | Curated default memory | Reviewed, deterministic, editable, and cheap to load. |
| Exact deletion of a newly recorded Cognee entry | Cognee `cognee_forget` | The live implementation requires a locally proven entry/session/dataset tuple and deletes only that UUID; an adjacent-entry canary passed without collateral deletion. |
| Correction of an authoritative durable rule | Curated default memory | Exact Cognee deletion does not turn probabilistic graph memory into an editable source of truth. |
| Prior episode recalled from a paraphrase | Cognee | Semantic recall does not require an exact keyword match. |
| Connections across sessions or related entities | Cognee | Graph retrieval can surface relationships not written as one curated rule. |
| Security-sensitive instruction or authorization | Neither recalled system alone | Recalled content is evidence, not authority; current user instructions and policy win. |
| Service outage or provider-budget failure | Curated default memory | It has no Cognee network, LLM, or graph-processing dependency. |

Cognee is therefore supplemental associative and episodic memory, not a replacement for
curated memory. A fact that must be exact, correctable, and durable should still be promoted
to curated memory after review.

## Baseline Results — 2026-07-16

| Scenario | Result | Evidence |
|---|---|---|
| Session capture and recall | Pass | A synthetic Q&A was stored and returned from session memory. |
| Persistent graph recall | Pass | A later graph recall returned the synthetic marker and graph evidence. |
| Frequency reinforcement | Pass | Three nodes and three edges changed from `0.0` to `1.0`. |
| Idempotent retry | Pass | A second run preserved `1.0`; session metadata retained `frequency_weights_applied: true`. |
| Full synchronous improvement | Pass | Installed plugin returned `PipelineRunCompleted` in 73.56 seconds. |
| Provider failure recovery | Pass after configuration fix | Reducing OpenRouter output budget from 8,192 to 6,000 stopped unaffordable-request retries. |
| Replacement for curated memory | Not recommended | Exact deletion now exists for newly provenance-backed entries, but curated memory remains deterministic, reviewed, and directly editable. |
| Exact entry deletion | Pass | Focused tests prove cache-before-graph deletion, provenance authorization, confirmation checks, and tombstones. A live two-entry canary completed in 24.7 seconds: the deleted entry disappeared while its adjacent entry remained recallable. |
| Transparent use from Codex | Not supported | The plugin is loaded by Hermes, not by the Codex memory runtime. |

## Issue And Improvement Log

### COG-OPS-001 — Improvement latency exceeds ordinary request budgets

- Status: mitigated
- Severity: high
- Observation: graph improvement can legitimately take longer than 120 seconds. A
  15-second catch-all made completed operations look like failures.
- Current mitigation: 15-second ordinary requests, 45-second graph recall, 300-second
  improvement, and 310-second shutdown flush.
- Improvement candidate: expose stage timings in the `/improve` response so timeout
  budgets can be based on measured work rather than container-log inspection.

### COG-OPS-002 — Provider token affordability caused wasteful retries

- Status: mitigated locally
- Severity: high
- Observation: Cognee requested 8,192 output tokens while the provider reported an
  affordability ceiling of 6,594. Retries consumed the entire 300-second client window.
- Current mitigation: both local LLM token controls are set to 6,000.
- Improvement candidate: treat deterministic provider errors such as insufficient
  credits or an impossible token budget as non-retryable. Validate duplicated token
  settings at startup and report disagreement clearly.

### COG-OPS-003 — High-level frequency logs are ambiguous

- Status: open
- Severity: medium
- Observation: the pipeline logs that frequency weights were applied for a session count
  even when all Q&A records are already marked processed. Actual `processed`, `applied`,
  and `skipped` totals are not included in the top-level `/improve` result.
- Improvement candidate: propagate those totals into structured stage results and log
  them at the `improve` boundary.

### COG-OPS-004 — Generic pipeline connection checks add avoidable latency

- Status: partially mitigated
- Severity: medium
- Observation: the original frequency path entered a generic LLM-backed pipeline even
  though frequency updates are graph/cache operations. Other improvement stages still
  perform repeated LLM and embedding connection checks.
- Current mitigation: frequency reinforcement now runs as bounded direct batches without
  the generic LLM connection test.
- Improvement candidate: perform one capability-aware connection check per improvement
  run, then share the result between stages that actually need that provider.

### COG-OPS-005 — Automatic recall has an unsafe trust label

- Status: open upstream limitation
- Severity: high
- Observation: Hermes 0.18.2 wraps provider-prefetched memory as authoritative even
  though Cognee recall is probabilistic and may contain stored prompt-injection text.
- Current mitigation: keep `auto_recall: false` and use explicit `cognee_recall`, whose
  output is bounded and labeled as untrusted evidence.
- Improvement candidate: add provider-level trust metadata to Hermes and render recalled
  memory as non-authoritative context.

### COG-OPS-006 — Exact deletion requires durable provenance

- Status: implemented and live-validated
- Severity: medium
- Observation: legacy grouped-session graph records cannot be mapped reliably back to
  individual Q&A IDs. New persistence now creates one Cognee `DataItem` per Q&A and uses
  the remember UUID as its `data_id`.
- Current implementation: the plugin stores only entry UUID, session, dataset,
  timestamps, and tombstone state in a bounded private ledger. `cognee_forget` rejects
  unknown or cross-dataset IDs and calls the exact server endpoint, which deletes the
  cache entry before graph/vector data. Broad dataset deletion remains unavailable.
- Live validation: Cognee commit `bab0e7ab6` and plugin commit `170626c` were deployed to
  Arc'ion. Two synthetic entries were stored and graphed; deleting the first UUID made it
  absent from session recall while the adjacent second entry remained present. The second
  entry was then deleted as cleanup. The full canary completed in 24.7 seconds.
- Remaining work: replacement remains deferred; it should be modeled as a confirmed
  delete plus a separately acknowledged write, not an in-place graph guess.

### COG-OPS-007 — Secret-safe diagnostics need a runbook

- Status: open documentation improvement
- Severity: high
- Observation: reading an entire `.env` during diagnosis can expose provider keys in
  terminal or agent output even when the goal is only to inspect token limits.
- Current mitigation: inspect named non-secret settings only, for example:

  ```bash
  rg -n '^LLM_(ARGS|MAX_COMPLETION_TOKENS)=' .env
  ```

- Improvement candidate: add a redacted configuration diagnostic command that emits
  setting presence and safe values while suppressing all credentials.

### COG-OPS-008 — Tokenizer discovery can delay service readiness

- Status: open
- Severity: medium
- Observation: after a container restart, Cognee remained unhealthy for roughly three
  minutes while the tokenizer resolver repeatedly requested metadata for
  `openai/text-embedding-3-small` from Hugging Face. It eventually fell back to TikToken
  and became healthy, but health requests blocked during the retry sequence.
- Current mitigation: wait for the bounded fallback and require a successful `/health`
  response before writes.
- Improvement candidate: configure a known compatible tokenizer explicitly or make the
  fallback decision without repeated network retries when the embedding provider is an
  OpenAI-compatible remote API.

### COG-OPS-009 — Multi-topic bootstrap sessions reduce retrieval granularity

- Status: open
- Severity: medium
- Observation: importing 11 curated Q&A records through one session produced a broad
  lexical result containing many unrelated Q&As. One query also returned an irrelevant
  historical canary alongside the useful bootstrap chunk.
- Current mitigation: treat graph completion as the useful answer and keep curated memory
  available for exact lookup. The existing bootstrap remains a legacy grouped graph
  snapshot and is not retroactively individually forgettable.
- Improvement candidate: import future snapshots as one session per coherent topic, add
  explicit topic/source metadata to graph entities, and evaluate a minimum relevance
  threshold before returning lexical fallback results. Do not duplicate the current
  snapshot until a safe replacement/delete mechanism exists.

### COG-OPS-010 — Cognee UI default port conflicts with the WhatsApp bridge

- Status: mitigated locally
- Severity: medium
- Observation: `http://localhost:3000` returned `Cannot GET /` with a restrictive CSP
  because port 3000 belonged to the ArcHermes WhatsApp bridge. The Cognee `frontend`
  profile was not running. The CSP console messages came from the bridge error response
  and were symptoms, not a Cognee frontend bug.
- Current mitigation: keep the WhatsApp bridge on port 3000 and run the Cognee frontend
  on loopback port 3001:

  ```bash
  docker compose --profile ui build frontend
  docker compose --profile ui run -d \
    --name cognee-frontend-ui \
    --no-deps \
    -p 127.0.0.1:3001:3000 \
    frontend
  docker update --restart always cognee-frontend-ui
  ```

  The verified UI URL is `http://localhost:3001`; `/` redirects to `/onboarding` and
  returns a Next.js page titled `Cognee`.
- Improvement candidate: make the frontend host port configurable in Compose, bind it to
  loopback by default, and document how to choose a non-conflicting port. A normal
  `docker compose --profile ui up` still attempts to claim host port 3000 in this checkout.

### COG-OPS-011 — Frontend dependency audit reports known vulnerabilities

- Status: open
- Severity: requires dependency-level review
- Observation: the frontend image build completed, but `npm ci` reported seven audit
  findings: four moderate and three high.
- Current mitigation: the UI is bound to loopback only. No automatic `npm audit fix` was
  applied because it can rewrite the dependency graph and introduce breaking changes.
- Improvement candidate: inspect `npm audit` details, update direct dependencies in the
  frontend repository, and run its test/build checks before accepting lockfile changes.

### COG-OPS-012 — Local UI and Hermes use different Cognee identities

- Status: mitigated with scoped dataset access
- Severity: high for operability
- Observation: the local UI login defaults to `default_user@example.com`, which currently
  sees datasets owned by or granted to that user. The Hermes plugin API key resolves to a
  separate generated agent user and owns the persistent `arc-function` dataset. Consequently,
  the UI default user does not list the memory dataset populated through Hermes.
- Related configuration trap: `.env` sets `ENABLE_BACKEND_ACCESS_CONTROL=true` and
  `REQUIRE_AUTHENTICATION=false`, but Cognee correctly forces authentication on because
  multi-tenant dataset isolation cannot safely run without an authenticated identity.
- Current mitigation: keep the identities separate and grant the default UI user scoped
  `read` and `write` permissions on the Hermes-owned `arc-function` dataset. The default
  user now lists the dataset, its schema inventory returns 18 types, and its graph
  visualization endpoint succeeds. Isolation-test datasets remain hidden. Do not copy
  credentials or disable backend access control merely to make datasets appear in the UI.
- Improvement candidates:
  1. Recommended for a single-user local installation: create a Cognee API key owned by
     the UI default user and configure Hermes to use it, then explicitly migrate or grant
     access to existing Hermes-owned datasets.
  2. Preserve the dedicated Hermes agent identity and grant the default UI user scoped
  read/manage permissions to the persistent dataset.
  3. Add a supported UI identity/API-key selector instead of requiring password login for
     agent-owned data.

Architecture note (2026-07-18): gateway conversations no longer create separate datasets. The
plugin keeps one configured persistent dataset and hashes gateway scope plus Hermes session ID into
Cognee's session identifier. Additional datasets now represent deliberate identity or trust
boundaries, not ordinary conversation lifecycle.

## Bootstrap Snapshot — 2026-07-16

The current curated Codex memory was copied, not moved, into Cognee dataset
`arc-function`. The import used session `codex-memory-bootstrap-20260716` and contains 11
compact Q&A records. Raw rollout transcripts, credentials, and private `.env` values were
not imported. See [`memory-bootstrap-2026-07-16.md`](memory-bootstrap-2026-07-16.md) for
the manifest and validation evidence.

The graph improvement completed in 61.93 seconds. Initial paraphrased graph queries took
11.12, 3.20, and 37.85 seconds. Two queries produced materially useful answers; the broad
curated-memory query found the relevant combined chunk but also returned an unrelated old
canary, so it is recorded as a noisy partial success rather than a clean pass.

This snapshot predates one-Q&A-per-`data_id` persistence. Its session entries may have
UUIDs in cache, but the permanent graph document was grouped, so the new exact-forget
tool must not claim those UUIDs or attempt partial graph deletion. A controlled rebuild
is required if individually deletable bootstrap records become necessary.

## Daily Evaluation Cases

Use real work when safe and synthetic canaries when control is needed. Record both useful
and failed recalls; logging only successes makes the comparison meaningless.

1. Exact preference: recall a stable user preference with a paraphrased question.
2. Prior decision: recover why a repository or architecture choice was made.
3. Cross-session association: connect a component, failure symptom, and earlier fix.
4. Sparse cue: retrieve a useful episode from one uncommon identifier.
5. Noise rejection: ask a common question and check that irrelevant sessions are absent.
6. Correction: introduce a replacement fact and check whether stale evidence still wins.
7. Frequency: reuse the same evidence and verify exactly one increment per recorded use.
8. Outage: stop or isolate Cognee and confirm Hermes remains usable with bounded failure.
9. Injection resistance: store synthetic instruction-like text and verify it is returned as
   quoted evidence, never followed as authority.
10. Latency: record session recall, graph recall, and improvement time separately.

## Observation Template

Append one block per meaningful use or failure:

```text
Date/time:
Hermes profile and plugin commit:
Task/query:
Expected useful memory:
Default-memory result:
Cognee result:
Session recall latency:
Graph recall latency:
Was Cognee materially helpful? yes/no, with reason:
False positives or omissions:
Security or privacy concern:
Follow-up issue/change:
```

## Promotion Criteria

Do not claim Cognee is better than the default memory system based on one synthetic
canary. A favorable conclusion requires repeated real-task evidence showing that Cognee
recovers useful context the curated system missed, without unacceptable false positives,
latency, stale contradictions, or operational failures. Curated memory remains the fallback
and source of truth throughout the evaluation.
