"""Route a complete PR diff conservatively and validate known prose files."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]

# These files are prose, not executable documentation or application inputs.
# New paths must be reviewed before being added; a .md suffix alone is insufficient.
PROSE_FILES = frozenset(
    {
        "AGENTS.md",
        "CONTEXT.md",
        "README.md",
        "config/README.md",
        "deploy/README.md",
        "docs/README.md",
        "docs/adr/README.md",
        "docs/agents/README.md",
        "docs/agents/domain.md",
        "docs/agents/issue-tracker.md",
        "docs/agents/triage-labels.md",
        "docs/developers/README.md",
        "docs/developers/architecture/README.md",
        "docs/developers/how-to/README.md",
        "docs/operators/README.md",
        "docs/operators/how-to/README.md",
        "docs/operators/runbooks/README.md",
        "docs/reference/README.md",
        "docs/reference/api/README.md",
        "docs/reference/cli/README.md",
        "docs/reference/configuration/README.md",
        "examples/README.md",
        "scripts/README.md",
    }
)


def classify(paths: list[str]) -> dict[str, bool]:
    # There is no separate executable-doc or canonical-input validator.
    # Tracked sample fixtures are validated by the selected CLI smoke cases.
    return {"smoke": not paths or any(path not in PROSE_FILES for path in paths), "inputs": False}


def changed_paths(base: str, head: str, root: Path = ROOT) -> list[str]:
    for revision in (base, head):
        if not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", revision):
            raise ValueError("Expected full base and head commit SHAs")
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", base + "..." + head, "--"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [os.fsdecode(name) for name in result.stdout.split(b"\0") if name]


def validate_prose(paths: list[str], root: Path = ROOT) -> None:
    root = root.resolve()
    for name in paths:
        if name not in PROSE_FILES:
            continue
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Invalid repository-relative prose path")
        path = root.joinpath(*relative.parts)
        for candidate in (path, *path.parents):
            if candidate == root:
                break
            if candidate.is_symlink():
                raise ValueError("Prose must not traverse symlinks: " + repr(name))
        try:
            path.lstat()
        except FileNotFoundError:
            continue  # Deleted prose has no bytes to validate, but still affects routing.
        if not path.is_file():
            raise ValueError("Prose must be a regular file: " + repr(name))
        data = path.read_bytes()
        if b"\0" in data:
            raise ValueError("Prose contains NUL: " + repr(name))
        data.decode("utf-8")


def main() -> None:
    paths = changed_paths(os.environ["CI_BASE_SHA"], os.environ["CI_HEAD_SHA"])
    validate_prose(paths)
    scope = classify(paths)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        for key, value in scope.items():
            output.write(key + "=" + str(value).lower() + "\n")
    print(json.dumps(scope, sort_keys=True))


if __name__ == "__main__":
    main()
