# Support scripts

Development commands are documented in the root
[README](../README.md#development). CI routing, fixed smoke selection, and
safeguards live under `.github/scripts/`; the automatic
[PR workflow](../.github/workflows/ci.yml) and
[manual full checkpoint](../.github/workflows/full-validation.yml) define when
they run.

This scoped index prevents an empty or generic scripts directory from being
mistaken for an undocumented automation surface. Add a script here only when
it has a project-specific, repeatable purpose.
