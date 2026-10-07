"""Exercise the smoke entry point with real pytest in full checkpoints only."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
RUNNER = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import ci_smoke
ci_smoke.ROOT = Path(sys.argv[2])
ci_smoke.SMOKE_TESTS = tuple(sys.argv[3:])
ci_smoke.main()
"""


class TestSmokeIntegration(unittest.TestCase):
    def run_candidate(self, source: str, nodes: tuple[str, ...] | None = None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "test_candidate.py").write_text(textwrap.dedent(source), encoding="utf-8")
            (root / "pytest.ini").write_text(
                "[pytest]\naddopts = --cov=anything --cov-fail-under=100\n", encoding="utf-8"
            )
            (root / "stale.xml").write_text(
                '<testsuite tests="1" failures="0"><testcase name="test_candidate"/></testsuite>',
                encoding="utf-8",
            )
            environment = os.environ.copy()
            environment["PYTEST_ADDOPTS"] = "--cov=anything -k never_matches"
            environment["COVERAGE_PROCESS_START"] = str(root / "missing-coveragerc")
            selected = ("test_candidate.py::test_candidate",) if nodes is None else nodes
            result = subprocess.run(
                [sys.executable, "-c", RUNNER, str(SCRIPTS), str(root), *selected],
                env=environment,
                capture_output=True,
                text=True,
                cwd=root,
            )
            self.assertFalse(list(root.glob(".coverage*")), result.stdout + result.stderr)
            self.assertFalse((root / "htmlcov").exists())
            return result

    def test_real_pass_ignores_injected_coverage_and_filters(self) -> None:
        result = self.run_candidate("def test_candidate():\n    assert True\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("All 1 selected smoke cases executed and passed", result.stdout)

    def test_bad_outcomes_fail_despite_a_stale_green_report(self) -> None:
        sources = {
            "assertion": "def test_candidate():\n    assert False\n",
            "import": "import nonexistent_ci_guard_dependency\ndef test_candidate(): pass\n",
            "skip": "import pytest\n@pytest.mark.skip\ndef test_candidate(): pass\n",
            "xfail": "import pytest\n@pytest.mark.xfail\ndef test_candidate(): assert False\n",
            "xpass": "import pytest\n@pytest.mark.xfail\ndef test_candidate(): pass\n",
            "setup": """
                import pytest
                @pytest.fixture(autouse=True)
                def broken_setup():
                    raise RuntimeError('setup failed')
                def test_candidate(): pass
            """,
            "teardown": """
                import pytest
                @pytest.fixture(autouse=True)
                def broken_teardown():
                    yield
                    raise RuntimeError('teardown failed')
                def test_candidate(): pass
            """,
        }
        for name, source in sources.items():
            with self.subTest(name=name):
                result = self.run_candidate(source)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_empty_duplicate_and_missing_selections_fail(self) -> None:
        for nodes in (
            (),
            ("test_candidate.py::test_candidate",) * 2,
            ("test_candidate.py::test_missing",),
        ):
            with self.subTest(nodes=nodes):
                result = self.run_candidate("def test_candidate(): pass\n", nodes)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
