# Hermes Cognee Memory Operational Evaluation

## Purpose

Track live behavior of the standalone ArcHermes plugin against an unmodified upstream-compatible
Cognee service. This document records integration evidence, not proposed Cognee memory semantics.

## Current Boundary

- ArcHermes loads `hermes-cognee-memory` as an exclusive `MemoryProvider`.
- The plugin captures completed primary turns, recalls bounded external context, and requests
  upstream session improvement.
- Cognee owns graph construction, retrieval, persistence, weighting, retention, and deletion.
- Curated `MEMORY.md` and `USER.md` remain the reviewed source of truth.
- Automatic recall remains disabled because current ArcHermes provider-prefetch wrapping describes
  memory too authoritatively for probabilistic external recall.

## Validated Baseline

| Scenario | Last known result | Revalidation needed after upstream reset |
|---|---|---|
| Plugin discovery and initialization | Passed | Yes |
| Session capture and recall | Passed | Yes |
| Persistent graph recall | Passed | Yes |
| Synchronous session improvement | Passed with long model-dependent latency | Yes |
| Operation-specific timeouts | Passed | Yes |
| Stable dataset across gateway sessions | Covered by tests | Yes, live |
| Authenticated dataset isolation | Configuration established | Yes, two-identity canary |
| Exact entry deletion | Removed from plugin scope | No |
| Frequency reinforcement customization | Removed from plugin scope | No |

Prior exact-deletion and custom-frequency results were produced by ArcCognee fork changes that have
been removed. They must not be treated as capabilities of the current plugin or upstream Cognee.

## Active Evaluation Items

### OPS-001: Attribute latency correctly

Current client budgets distinguish ordinary requests, graph recall, and improvement, but the plugin
does not yet emit enough structured timing to separate queue wait, transport, and upstream server
work. Add content-free operation metrics before changing timeout defaults.

### OPS-002: Validate the upstream API contract

Run the plugin against the reset ArcCognee service and verify dataset ensure, typed remember, scoped
recall, and synchronous improve. A health response alone does not prove endpoint compatibility.

### OPS-003: Revalidate authentication and isolation

Use real Cognee authentication and backend access control. Run synthetic cross-identity and
cross-dataset canaries. Dataset names and hashed session IDs are not authorization boundaries.

### OPS-004: Keep recall non-authoritative

Continue using explicit `cognee_recall` by default. If ArcHermes gains provider trust metadata,
validate that automatic recall is rendered as untrusted external evidence before enabling it.

### OPS-005: Bound shutdown and outage behavior

Test capture followed by immediate shutdown, an in-flight improve, service refusal, timeout, retry
exhaustion, and recovery after the recall circuit opens. Confirm that failed capture is never
reported as improved.

### OPS-006: Secret-safe diagnostics

Diagnostics must report endpoint reachability, authentication state, compatibility, and safe
configuration values without printing API keys, provider credentials, conversation content, raw
gateway IDs, or remote error bodies.

## Evaluation Method

Use synthetic canaries only. For each run record:

- plugin and Cognee commit/version;
- ArcHermes profile and plugin installation source;
- operation scope and bounded timing;
- success, skip, timeout, or error category;
- whether the result came from session or graph recall;
- whether isolation assertions passed.

Do not record prompts, answers, credentials, or raw identifiers in this file.
