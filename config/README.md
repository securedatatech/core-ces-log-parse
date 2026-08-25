# Configuration directory

The CLI currently has no separate configuration files. Runtime inputs are
provided as command-line paths, and project/development configuration remains
in [`pyproject.toml`](../pyproject.toml).

This scoped index satisfies the repository navigation contract without
inventing a configuration format. Add a file here only when the application
gains a supported configuration artifact.
