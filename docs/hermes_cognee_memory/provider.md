# Cognee memory provider

Source: `src/hermes_cognee_memory/provider.py`

`CogneeMemoryProvider` implements Hermes's exclusive `MemoryProvider` contract. It owns the
provider lifecycle, persistent dataset and session scoping, background capture queue, recall prefetch workers,
session improvement, and the `cognee_recall`, `cognee_remember`, and `cognee_forget` tools.

Key boundaries:

- only completed primary-agent turns are captured automatically;
- the configured dataset remains stable across conversations so improved knowledge forms one
  persistent graph;
- gateway scope and the Hermes session ID are hashed into a deterministic Cognee session ID,
  keeping raw user/chat identifiers out of the service while separating session cache entries;
- writes and improvement share one bounded FIFO worker so improvement cannot pass pending writes;
- recall output is bounded and rendered as untrusted evidence;
- repeated recall failures open a circuit breaker and allow one recovery probe after cooldown;
- graph recall and synchronous improvement receive separate, bounded timeout budgets;
- acknowledged entry UUIDs are stored in a bounded, content-free local provenance ledger;
- exact forgetting is serialized with capture and improvement, and confirmed deletes become local
  tombstones;
- broad and query-based deletion are not exposed;
- built-in curated Hermes memory is not mirrored because it has no safe remote entry-ID mapping
  for replacement or deletion.

Call `shutdown` when the provider is no longer used. It stops new work, waits within configured
bounds for queued writes and prefetch threads, and preserves failed-write state so improvement is
not falsely reported as complete. The default flush window is deliberately longer than the
synchronous improvement timeout; reducing it can abandon graph persistence during teardown.

Before the first capture, the provider ensures that the active dataset exists. Each successful
remember response is recorded as an entry UUID, dataset, and session tuple. If that local write
fails, the provider attempts to roll back the untracked server entry and blocks improvement rather
than treating the capture as durable.

`cognee_forget` accepts only an exact UUID found in that ledger for the active dataset. It sends the
recorded tuple to `POST /api/v1/forget/entry`, requires confirmation for the same UUID and graph
deletion, then writes a tombstone. Unknown, legacy, malformed, or evicted entries fail closed.
