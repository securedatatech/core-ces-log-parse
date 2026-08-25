## Agent skills

### Issue tracker

Issues and specs live in GitHub Issues for `securedatatech/core-ces-log-parse`; use the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository; read the root `CONTEXT.md` and `docs/adr/` when they exist. See `docs/agents/domain.md`.

## Repository scope

`core-ces-log-parse` is a local CLI for extracting focused Cisco ESA mail-log
records by matched address and MID. Preserve the existing module entry point,
input semantics, output formats, and regression coverage unless an issue
explicitly requests a behavior change.

## Boundaries

- Treat `src/` and tracked `tests/` fixtures as repository content.
- Treat `input/` as local operational evidence and `output/` as generated
  extracts; preserve both and keep them out of commits.
- Keep generated caches, virtual environments, coverage data, and build
  products ignored according to `.gitignore`.
- Use the vocabulary in `CONTEXT.md` for domain prose. Keep established CLI
  flags and Cisco ESA terminology stable when compatibility requires them.

## Validation

Use `uv sync --locked` before local checks. The root
[README development section](README.md#development) is the canonical command
list; CI is authoritative for the complete matrix. At minimum, validate
formatting, Ruff, mypy, pytest with coverage, pip-audit, and pre-commit before
handing off a change.

## Documentation map

Start with [`docs/README.md`](docs/README.md) for audience routing. Use
[`docs/agents/README.md`](docs/agents/README.md) for agent-specific pointers;
the existing issue-tracker, triage-label, and domain documents remain their
own canonical sources.
