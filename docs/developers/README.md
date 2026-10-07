# Developer documentation

The root [README development section](../../README.md#development) is the
canonical entry point for local validation commands.

- [How-to index](how-to/README.md): route environment and test workflows.
- [Architecture index](architecture/README.md): route the current source,
  test, and domain boundaries.
- [`pyproject.toml`](../../pyproject.toml): authoritative project metadata,
  dependency groups, and tool configuration.
- [PR CI workflow](../../.github/workflows/ci.yml): the single `validate`
  smoke/prose check on Ubuntu with Python 3.14.
- [Full checkpoint](../../.github/workflows/full-validation.yml): manually
  dispatched Python matrix, coverage, quality, audit, and installed-wheel checks.

The root [CI policy](../../README.md#pr-smoke-validation) documents fixed smoke
selection, deferred assurance, and the SHA-verified operator release checkpoint.

Existing source and tests stay at their current paths; this section adds
navigation only.
