# Cognee Curated-Memory Bootstrap — 2026-07-16

> Historical record: this import used an earlier ArcCognee fork. Frequency-reinforcement and
> exact-entry-deletion claims below are not capabilities of the current upstream-aligned service.

## Result

Eleven compact records from the current curated Codex memory were copied into Cognee and
persisted to the graph.

- Dataset: `arc-function`
- Session: `codex-memory-bootstrap-20260716`
- Captured Q&A records: 11
- Improvement result: `PipelineRunCompleted`
- Improvement duration: 61.93 seconds
- Cognee version after import: `1.3.0-local`
- Service health after import: healthy

This was a copy, not a migration. The curated memory files remain authoritative and were
not edited or deleted.

## Imported Topics

1. User working preferences and repository conventions.
2. ArcHermes Codex sandbox regression attribution and safe migration behavior.
3. ArcFunction development-to-live deployment workflow.
4. Local Cognee configuration, isolation, and credential separation.
5. Verified Cognee request, recall, improvement, and shutdown timeouts.
6. Historical Ladybug frequency-reinforcement experiment, since removed from ArcCognee.
7. ArcCodex sandbox triage and important implementation files.
8. Hermes runtime selection through `HERMES_CODEX_BIN` and host-aware restarts.
9. Common Codex resume commands.
10. ArcHermes merge-conflict integration practices.
11. The hybrid memory policy: Cognee supplements curated memory rather than replacing it.

## Exclusions

- Raw rollout transcripts and complete chat histories.
- API keys, `.env` contents, authentication headers, and other credentials.
- Generated logs, build output, and unrelated repository state.
- Claims that were only transient diagnostics and had no reusable value.

Each record includes a bounded context label identifying it as a curated Codex memory
snapshot dated 2026-07-16. The labels are provenance hints, not a live synchronization
mechanism.

## Retrieval Validation

### Development fix versus stale live runtime

- Paraphrased query: a fix is committed in development but the live ArcHermes runtime
  still acts old; what workflow should be used?
- Duration: 11.12 seconds.
- Result: useful graph completion recommending provenance checks, exact-commit
  verification, and deployment through the updater.
- Assessment: pass.

### Exact corrections versus associative memory

- Paraphrased query: where should exact corrections and durable workflow rules live?
- Duration: 3.20 seconds.
- Result: retrieved the relevant bootstrap chunk, but the chunk combined multiple Q&A
  topics and another result contained an irrelevant historical canary.
- Assessment: partial; relevant evidence was present but retrieval granularity was poor.

### Long graph-improvement budget

- Paraphrased query: why can Cognee graph improvement run for several minutes?
- Duration: 37.85 seconds.
- Result: useful graph completion recovered the 15-second ordinary, 45-second graph
  recall, and 300-second improvement budgets and explained the distinction.
- Assessment: pass, but close to the plugin default 45-second graph-recall timeout.

## Consistency Rules

- Do not automatically re-import the full snapshot after every curated-memory change.
  That would create duplicate or contradictory graph facts.
- When a seeded fact is corrected, curated memory wins. The plugin does not provide a custom
  replacement or exact-delete workflow.
- Future bulk imports should use one session per coherent topic instead of grouping all
  topics in one session.
- Use explicit `cognee_recall` and treat returned content as untrusted evidence.

The 11 records in this snapshot form a grouped historical graph representation. The current plugin
does not maintain a local provenance ledger or provide per-entry deletion. Any cleanup or rebuild
must use supported upstream Cognee lifecycle operations and separate operator approval.

## Newly Observed Operational Issue

Before the import, a fresh Cognee container remained unhealthy while attempting repeated
Hugging Face tokenizer metadata requests. It recovered after falling back to TikToken.
No bootstrap write was attempted until `/health` returned ready. This is tracked as
`COG-OPS-008` in `operational-evaluation.md`.
