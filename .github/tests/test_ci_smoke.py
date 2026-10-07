"""Dependency-free tests of exact collection and report safeguards."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_smoke  # noqa: E402

NODE = "tests/test_example.py::test_success"


def session(nodes: tuple[str, ...]) -> SimpleNamespace:
    return SimpleNamespace(items=[SimpleNamespace(nodeid=node) for node in nodes])


def report(phase: str, outcome: str = "passed", **attributes) -> SimpleNamespace:
    return SimpleNamespace(
        nodeid=NODE,
        when=phase,
        outcome=outcome,
        passed=outcome == "passed",
        skipped=outcome == "skipped",
        failed=outcome == "failed",
        **attributes,
    )


class TestSmokeGuard(unittest.TestCase):
    def passing_gate(self) -> ci_smoke.SmokeGate:
        gate = ci_smoke.SmokeGate((NODE,))
        gate.pytest_collection_finish(session((NODE,)))
        for phase in ("setup", "call", "teardown"):
            gate.pytest_runtest_logreport(report(phase))
        return gate

    def test_valid_manifest_and_complete_pass(self) -> None:
        ci_smoke.validate_manifest(ci_smoke.SMOKE_TESTS)
        self.assertEqual(len(ci_smoke.SMOKE_TESTS), 6)
        self.passing_gate().verify(0)

    def test_empty_duplicate_and_nonconcrete_selections_fail(self) -> None:
        for nodes in ((), (NODE, NODE), ("tests/test_example.py",)):
            with self.subTest(nodes=nodes):
                with self.assertRaises(ValueError):
                    ci_smoke.SmokeGate(nodes)

    def test_collection_drift_fails(self) -> None:
        for nodes in ((), (NODE, NODE), (NODE, "other.py::test_other")):
            with self.subTest(nodes=nodes):
                with self.assertRaisesRegex(ValueError, "collection"):
                    ci_smoke.SmokeGate((NODE,)).pytest_collection_finish(session(nodes))

    def test_setup_call_and_teardown_failures_are_rejected(self) -> None:
        for phase in ("setup", "call", "teardown"):
            with self.subTest(phase=phase):
                gate = self.passing_gate()
                gate.pytest_runtest_logreport(report(phase, "failed"))
                with self.assertRaises(ValueError):
                    gate.verify(0)

    def test_skip_xfail_and_xpass_are_rejected(self) -> None:
        outcomes = (
            report("call", "skipped"),
            report("call", "skipped", wasxfail="expected"),
            report("call", "passed", wasxfail="unexpected success"),
        )
        for outcome in outcomes:
            with self.subTest(outcome=outcome):
                gate = self.passing_gate()
                gate.pytest_runtest_logreport(outcome)
                with self.assertRaises(ValueError):
                    gate.verify(0)

    def test_missing_or_duplicate_phase_and_abnormal_exit_fail(self) -> None:
        gate = self.passing_gate()
        gate.passed.pop()
        with self.assertRaises(ValueError):
            gate.verify(0)
        gate = self.passing_gate()
        gate.pytest_runtest_logreport(report("call"))
        with self.assertRaises(ValueError):
            gate.verify(0)
        with self.assertRaises(ValueError):
            self.passing_gate().verify(2)

    def test_main_clears_injected_options_and_disables_coverage(self) -> None:
        def pytest_main(arguments, plugins):
            self.assertNotIn("PYTEST_ADDOPTS", os.environ)
            self.assertNotIn("COVERAGE_PROCESS_START", os.environ)
            self.assertIn("addopts=", arguments)
            self.assertIn("no:pytest_cov", arguments)
            self.assertIn("no:cov", arguments)
            self.assertIn("--strict-config", arguments)
            self.assertIn("--strict-markers", arguments)
            self.assertEqual(arguments[-1:], [NODE])
            gate = plugins[0]
            gate.pytest_collection_finish(session((NODE,)))
            for phase in ("setup", "call", "teardown"):
                gate.pytest_runtest_logreport(report(phase))
            return 0

        fake_pytest = SimpleNamespace(main=pytest_main)
        with (
            patch.dict(sys.modules, {"pytest": fake_pytest}),
            patch.dict(
                os.environ, {"PYTEST_ADDOPTS": "--cov=anything", "COVERAGE_PROCESS_START": "bad"}
            ),
            patch.object(ci_smoke, "SMOKE_TESTS", (NODE,)),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            ci_smoke.main()

    def test_stale_report_cannot_satisfy_an_empty_current_run(self) -> None:
        with self.assertRaises(ValueError):
            ci_smoke.SmokeGate((NODE,)).verify(0)
