# Configuration

Source: `src/hermes_cognee_memory/config.py`

Configuration is stored at `$HERMES_HOME/cognee/config.json`. `load_config` starts from
`DEFAULT_CONFIG`, then applies values from a secure regular file owned by the current user.
Missing, malformed, insecure, or unreadable files fall back to defaults.

`save_config` writes atomically through a temporary file. The Cognee directory is mode `0700` and
the JSON file is mode `0600`. API keys do not belong in this file; the provider setup flow writes
`COGNEE_API_KEY` to the active Hermes `.env` instead.

The defaults keep automatic capture and improvement enabled, automatic recall disabled, network
and queue sizes bounded, and recall failures protected by a small circuit breaker. Fast
health/session operations use `request_timeout_seconds` (15 seconds), graph-capable recall uses
`graph_recall_timeout_seconds` (45 seconds), and synchronous session improvement uses
`improve_timeout_seconds` (300 seconds). `shutdown_flush_seconds` defaults to 310 seconds so the
ordered writer can finish one in-flight improvement before teardown.
