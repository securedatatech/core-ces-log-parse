# core-ces-log-parse

Extract Cisco ESA mail log threads by sender email address and message ID (MID).

## Local data layout

Operational Cisco ESA logs and generated thread extracts are kept locally and are
not committed to Git. Put raw log inputs and sender lists in `input/`; write
combined or per-sender results to `output/`.

## Install

```bash
uv sync --locked
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

Run the comprehensive local checks before handing off a change:

```bash
uv sync --locked
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked mypy src
uv run --locked pytest --cov=core_ces_log_parse --cov-report=term-missing --cov-fail-under=80
python3 -B .github/scripts/ci_safeguards.py
uv run --locked pytest .github/tests/test_smoke_integration.py
uv run --locked pip-audit
uv run --locked pre-commit run --all-files
```

If a machine-wide uv configuration forces re-resolution of the committed lock
(for example, a rolling `exclude-newer`), prefix local uv commands with
`UV_NO_CONFIG=1`. This uses the repository lock without editing the machine-wide
settings. Do not regenerate the lock merely to bypass that configuration.

### PR smoke validation

[CI](.github/workflows/ci.yml) runs one Ubuntu job named `validate` on Python
3.14, with a five-minute timeout and a target of one to two rounded runner
minutes including setup. Draft PRs allocate no runner; ready PR updates cancel
superseded validation. There are no automatic main-push or scheduled test runs.

The job compares the whole PR from its merge base. An exact reviewed prose
allowlist in `.github/scripts/ci_scope.py` permits text-only validation for those
files; new or unknown paths, fixtures, source, dependencies, CI changes, mixed
changes, and empty diffs run smoke. Git errors or invalid routing outputs fail.
Prose must be regular UTF-8 files without NUL bytes or symlink traversal. Routing
and result safeguards run on both paths, so prose-only PRs still report success
through the same `validate` check.

To reproduce the code-change path locally:

```bash
uv sync --locked --python 3.14
python3 -B .github/scripts/ci_safeguards.py
uv run --locked --python 3.14 ruff format --check .
uv run --locked --python 3.14 ruff check .
uv run --locked --python 3.14 python -m compileall -q src tests .github/scripts .github/tests
uv run --locked --python 3.14 python .github/scripts/ci_smoke.py
```

The fixed pytest manifest selects these existing methods from `tests/test_main.py`:

| Class | Method | Behavior |
| --- | --- | --- |
| `TestSmoke` | `test_cli_smoke` | Combined thread extracts for matched addresses and MIDs |
| `TestSmoke` | `test_cli_outdir` | Per-address files and their contents |
| `TestSmoke` | `test_cli_missing_log` | Missing log input fails |
| `TestSmoke` | `test_cli_mutually_exclusive_outputs` | Conflicting output modes fail |
| `TestSmoke` | `test_cli_no_matches_found` | An unmatched address fails explicitly |
| `TestParsing` | `test_scan_requires_a_mid_on_the_sender_line` | Address–MID association requires the same log entry |

All six cases must collect exactly and pass setup, call, and teardown. Missing,
duplicate, skipped, xfail/xpass, and failed cases fail the gate. Smoke disables
coverage and clears injected pytest options, while retaining strict configuration
and marker checks. It installs the complete locked development environment.

### Full and release checkpoints

[Full validation](.github/workflows/full-validation.yml) is manually dispatched
and always runs the complete suite on Python 3.11, 3.12, 3.13, and 3.14 on Ubuntu,
with the existing 80% coverage floor. Separate full jobs retain formatting,
Ruff, mypy, pre-commit, dependency audit, and wheel build/installation checks.
No route can reduce an explicit full run to smoke. Dependabot remains enabled.

```bash
gh workflow run full-validation.yml --ref <candidate-ref>
gh run list --workflow full-validation.yml --event workflow_dispatch --limit 5 \
  --json databaseId,headSha,conclusion
gh run watch <run-id> --exit-status
gh run view <run-id> --json headSha,conclusion
git rev-parse <candidate-ref>
```

Before releasing, require a successful full run and verify its `headSha` equals
the exact commit being released. A changed branch needs a checkpoint for its new
SHA. This is an operator gate: there is no publisher or enforced release
permission in this repository, and dispatching full validation never publishes.

The local equivalent of the installed-wheel checkpoint is:

```bash
ces_checkpoint_dir=$(mktemp -d)
uv build --out-dir "$ces_checkpoint_dir/dist"
uv venv --python 3.14 "$ces_checkpoint_dir/wheel-venv"
uv pip install --python "$ces_checkpoint_dir/wheel-venv/bin/python" \
  --no-deps "$ces_checkpoint_dir/dist/"*.whl
"$ces_checkpoint_dir/wheel-venv/bin/python" -m core_ces_log_parse.main --help
"$ces_checkpoint_dir/wheel-venv/bin/python" -m core_ces_log_parse.main \
  --logs tests/fixtures/sample.log --senders tests/fixtures/senders.txt \
  --out "$ces_checkpoint_dir/sample-output.txt"
```

A green smoke check permits regressions outside those six cases to reach main.
Comprehensive assurance comes from the full checkpoint; typing, audits, packaging,
coverage, and cross-version regressions are deferred from automatic PR validation.
Linux checks do not establish native Windows/macOS behavior such as filesystem
case sensitivity, permissions, or path handling. Validate those platforms locally
when a change depends on them.
