"""Run dependency-free CI safeguards, including an explicit nonempty-suite guard."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / ".github" / "tests"), pattern="test_ci*.py")
    count = suite.countTestCases()
    if loader.errors or not count:
        raise SystemExit("CI safeguard tests must collect successfully and be nonempty")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if (
        result.testsRun != count
        or not result.wasSuccessful()
        or result.skipped
        or result.expectedFailures
    ):
        raise SystemExit("Every CI safeguard test must run and pass")


if __name__ == "__main__":
    main()
