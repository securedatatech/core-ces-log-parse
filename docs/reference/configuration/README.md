# Configuration reference

There is no separate application configuration file. Runtime selection is
made through the CLI arguments documented in the [root usage
section](../../../README.md#usage), while packaging and development-tool
configuration is authoritative in [`pyproject.toml`](../../../pyproject.toml).

Operational log and sender-list files are supplied by path. The ignored
`input/` and `output/` directories are local data locations, not committed
configuration.
