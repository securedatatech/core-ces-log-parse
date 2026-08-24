# core-ces-log-parse

Extract Cisco ESA mail log threads by sender email address and message ID (MID).

## Local data layout

Operational Cisco ESA logs and generated thread extracts are kept locally and are
not committed to Git. Put raw log inputs and sender lists in `input/`; write
combined or per-sender results to `output/`.

## Install

```bash
uv sync
```

## Dependency sources of truth

`pyproject.toml` is authoritative for project metadata and dependency
constraints. `uv.lock` is authoritative for reproducible dependency
resolution. Use `uv sync --locked` to create or update the development
environment. `requirements.txt` is intentionally not maintained.

## Usage

```bash
mkdir -p input output

uv run python -m core_ces_log_parse.main \
  --logs input/mail1_1021.txt input/mail2_1021.txt \
  --senders input/addresses.txt \
  --out output/combined_threads.txt
```

To write one output file per sender, use `--outdir output/threads` instead of
`--out`.

For a checked-in smoke test that does not require local operational data:

```bash
uv run python -m core_ces_log_parse.main \
  --logs tests/fixtures/sample.log \
  --senders tests/fixtures/senders.txt \
  --out /tmp/core-ces-log-parse-sample.txt
```

## Development

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest --cov=core_ces_log_parse --cov-report=term-missing
uv run pip-audit
uv run pre-commit run --all-files
```
