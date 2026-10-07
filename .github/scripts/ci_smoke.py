"""Run exactly the supported smoke cases, without coverage or incomplete results."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SMOKE_TESTS = (
    "tests/test_main.py::TestSmoke::test_cli_smoke",
    "tests/test_main.py::TestSmoke::test_cli_outdir",
    "tests/test_main.py::TestSmoke::test_cli_missing_log",
    "tests/test_main.py::TestSmoke::test_cli_mutually_exclusive_outputs",
    "tests/test_main.py::TestSmoke::test_cli_no_matches_found",
    "tests/test_main.py::TestParsing::test_scan_requires_a_mid_on_the_sender_line",
)
SMOKE_OPTIONS = ("--strict-config", "--strict-markers")


def validate_manifest(nodes: tuple[str, ...]) -> None:
    if not nodes or len(set(nodes)) != len(nodes) or any(".py::" not in node for node in nodes):
        raise ValueError("Provide distinct concrete pytest test IDs")


class SmokeGate:
    def __init__(self, expected: tuple[str, ...]) -> None:
        validate_manifest(expected)
        self.expected = expected
        self.collected: list[str] = []
        self.passed: list[tuple[str, str]] = []
        self.bad: list[tuple[str, str, str]] = []

    def pytest_collection_finish(self, session) -> None:
        self.collected = [item.nodeid for item in session.items]
        if Counter(self.collected) != Counter(self.expected):
            raise ValueError("Smoke collection does not match the manifest")

    def pytest_runtest_logreport(self, report) -> None:
        if report.failed or report.skipped or hasattr(report, "wasxfail"):
            self.bad.append((report.nodeid, report.when, report.outcome))
        if report.passed:
            self.passed.append((report.nodeid, report.when))

    def verify(self, exit_code: int) -> None:
        expected_reports = Counter(
            (node, phase) for node in self.expected for phase in ("setup", "call", "teardown")
        )
        if (
            exit_code != 0
            or self.bad
            or Counter(self.collected) != Counter(self.expected)
            or Counter(self.passed) != expected_reports
        ):
            raise ValueError("Every selected smoke case must execute and pass all phases")


def main() -> None:
    validate_manifest(SMOKE_TESTS)
    os.environ.pop("PYTEST_ADDOPTS", None)
    os.environ.pop("COVERAGE_PROCESS_START", None)
    os.chdir(ROOT)

    # Keep this module importable by stdlib safeguards on prose-only PRs.
    import pytest

    gate = SmokeGate(SMOKE_TESTS)
    code = pytest.main(
        [
            "-q",
            "-o",
            "addopts=",
            "-p",
            "no:pytest_cov",
            "-p",
            "no:cov",
            *SMOKE_OPTIONS,
            *SMOKE_TESTS,
        ],
        plugins=[gate],
    )
    gate.verify(code)
    print(f"All {len(SMOKE_TESTS)} selected smoke cases executed and passed without coverage")


if __name__ == "__main__":
    main()
