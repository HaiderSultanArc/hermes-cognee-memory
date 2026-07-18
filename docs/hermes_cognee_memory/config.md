# Configuration

Source: `src/hermes_cognee_memory/config.py`

Configuration is stored at `$HERMES_HOME/cognee/config.json`. `load_config` starts from
`DEFAULT_CONFIG`, then applies values from a secure regular file owned by the current user.
Missing, malformed, insecure, or unreadable files fall back to defaults.

`save_config` writes atomically through a temporary file. The Cognee directory is mode `0700` and
the JSON file is mode `0600`. API keys do not belong in this file; the provider setup flow writes
`COGNEE_API_KEY` to the active Hermes `.env` instead.

The defaults keep automatic capture and improvement enabled, checkpoint acknowledged captures
into the graph every 10 turns, keep automatic recall disabled, bound network and queue sizes, and
protect recall failures with a small circuit breaker. Set `improve_every_n_turns` to `0` to retain
session-end improvement without periodic checkpoints; `auto_improve=false` disables both paths. Fast
health/session operations use `request_timeout_seconds` (15 seconds), graph-capable recall uses
`graph_recall_timeout_seconds` (45 seconds), and synchronous session improvement uses
`improve_timeout_seconds` (300 seconds). `shutdown_flush_seconds` defaults to 310 seconds so the
ordered writer can finish one in-flight improvement before teardown.
