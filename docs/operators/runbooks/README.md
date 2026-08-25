# Operator runbook index

The CLI is a local batch utility, so there are no service restart, deployment,
or remote-recovery runbooks. Current operational handling is limited to:

- use the CLI's validation messages for missing log or sender-list inputs;
- keep raw inputs unchanged and write a new output path for each extraction;
- use the tracked smoke-test fixtures when checking the installation boundary.

The root [README](../../../README.md) and the implementation in
[`main.py`](../../../src/core_ces_log_parse/main.py) remain canonical for
behavior and error handling. Add a focused runbook here only when a recurring
operational procedure exists.
