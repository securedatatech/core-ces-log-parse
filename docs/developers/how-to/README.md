# Developer how-to index

- [Install the locked environment](../../../README.md#install) uses the
  repository's `uv.lock` resolution.
- [Run development checks](../../../README.md#development) lists the
  formatter, linter, type checker, tests, audit, and pre-commit commands.
- [`tests/test_main.py`](../../../tests/test_main.py) is the canonical
  regression-test entry point for CLI and parsing behavior.

Keep new procedures linked to their source of truth. Do not copy tool
configuration from `pyproject.toml` into this index.
