# Architecture index

The current implementation is intentionally small and is centered on
[`src/core_ces_log_parse/main.py`](../../../src/core_ces_log_parse/main.py).
That module owns CLI parsing, sender/MID discovery, log indexing, and output
rendering; the tracked tests exercise the behavior at the CLI and helper
boundaries.

The domain vocabulary is maintained in the root [`CONTEXT.md`](../../../CONTEXT.md).
There are no additional architecture records today. Add a focused design
document or ADR only when a lasting architectural decision needs a separate
canonical source.
