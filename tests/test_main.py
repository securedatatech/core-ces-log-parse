# tests/test_main.py

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures"
LOG_PATH = FIXTURES_DIR / "sample.log"
SENDERS_PATH = FIXTURES_DIR / "senders.txt"
SOURCE_DIR = ROOT_DIR / "src"
TEST_ENV = os.environ.copy()
TEST_ENV["PYTHONPATH"] = os.pathsep.join(
    path for path in (str(SOURCE_DIR), TEST_ENV.get("PYTHONPATH")) if path
)

if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from core_ces_log_parse.main import (  # noqa: E402
    extract_mid,
    extract_sender_candidates,
    index_logs_for_mids,
    load_senders,
    main,
    render_thread,
    scan_mids_for_senders,
)


class TestSmoke(unittest.TestCase):
    def test_cli_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "out.txt"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "core_ces_log_parse.main",
                    "--logs",
                    str(LOG_PATH),
                    "--senders",
                    str(SENDERS_PATH),
                    "--out",
                    str(out_path),
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                env=TEST_ENV,
            )

            msg = result.stderr.strip() or result.stdout.strip()
            self.assertEqual(result.returncode, 0, msg=msg)
            self.assertTrue(out_path.exists(), "Output file was not created")

            data = out_path.read_text(encoding="utf-8")
            self.assertIn("noreply@salesforce.com", data)
            self.assertIn("alerts@mail.salesforce.com", data)
            self.assertIn("MID 1001", data)
            self.assertIn("MID 2002", data)

    def test_cli_outdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "core_ces_log_parse.main",
                    "--logs",
                    str(LOG_PATH),
                    "--senders",
                    str(SENDERS_PATH),
                    "--outdir",
                    str(out_dir),
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                env=TEST_ENV,
            )

            msg = result.stderr.strip() or result.stdout.strip()
            self.assertEqual(result.returncode, 0, msg=msg)
            self.assertTrue(out_dir.exists(), "Output directory was not created")

            sender_files = sorted(p.name for p in out_dir.glob("*.txt"))
            self.assertIn("noreply_salesforce.com.txt", sender_files)
            self.assertIn("alerts_mail.salesforce.com.txt", sender_files)

            sample_path = out_dir / "noreply_salesforce.com.txt"
            data = sample_path.read_text(encoding="utf-8")
            self.assertIn("MID 1001", data)

    def test_cli_missing_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_log = Path(tmpdir) / "missing.log"
            out_path = Path(tmpdir) / "out.txt"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "core_ces_log_parse.main",
                    "--logs",
                    str(missing_log),
                    "--senders",
                    str(SENDERS_PATH),
                    "--out",
                    str(out_path),
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                env=TEST_ENV,
            )

            msg = result.stderr.strip() or result.stdout.strip()
            self.assertNotEqual(result.returncode, 0, msg=msg)
            self.assertIn("Error: log file not found", msg)

    def test_cli_missing_senders_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_senders = Path(tmpdir) / "missing.txt"
            out_path = Path(tmpdir) / "out.txt"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "core_ces_log_parse.main",
                    "--logs",
                    str(LOG_PATH),
                    "--senders",
                    str(missing_senders),
                    "--out",
                    str(out_path),
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                env=TEST_ENV,
            )

            msg = result.stderr.strip() or result.stdout.strip()
            self.assertNotEqual(result.returncode, 0, msg=msg)
            self.assertIn("Error: senders file not found", msg)

    def test_cli_missing_senders(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "out.txt"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "core_ces_log_parse.main",
                    "--logs",
                    str(LOG_PATH),
                    "--out",
                    str(out_path),
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                env=TEST_ENV,
            )

            msg = result.stderr.strip() or result.stdout.strip()
            self.assertNotEqual(result.returncode, 0, msg=msg)
            self.assertIn("Error: No senders provided", msg)

    def test_cli_mutually_exclusive_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "out.txt"
            out_dir = Path(tmpdir) / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "core_ces_log_parse.main",
                    "--logs",
                    str(LOG_PATH),
                    "--sender",
                    "noreply@salesforce.com",
                    "--out",
                    str(out_path),
                    "--outdir",
                    str(out_dir),
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                env=TEST_ENV,
            )

            msg = result.stderr.strip() or result.stdout.strip()
            self.assertNotEqual(result.returncode, 0, msg=msg)
            self.assertIn("Error: Specify exactly one of --out or --outdir.", msg)

    def test_cli_no_matches_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "out.txt"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "core_ces_log_parse.main",
                    "--logs",
                    str(LOG_PATH),
                    "--sender",
                    "missing@example.com",
                    "--out",
                    str(out_path),
                ],
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                env=TEST_ENV,
            )

            msg = result.stderr.strip() or result.stdout.strip()
            self.assertNotEqual(result.returncode, 0, msg=msg)
            self.assertIn(
                "No matches found: none of the senders were found with a MID on the same line.", msg
            )


class TestParsing(unittest.TestCase):
    def test_sender_candidates_are_normalized(self) -> None:
        line = "MID=42 From:<User@Example.com> mailfrom=<Other@Example.com>"

        self.assertEqual(
            extract_sender_candidates(line),
            {"user@example.com", "other@example.com"},
        )

    def test_supported_mid_syntaxes(self) -> None:
        self.assertEqual(extract_mid("MID=100"), "100")
        self.assertEqual(extract_mid("mid:200"), "200")
        self.assertEqual(extract_mid("mid 300"), "300")
        self.assertIsNone(extract_mid("message without an id"))

    def test_load_senders_ignores_comments_and_normalizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            senders_path = Path(tmpdir) / "senders.txt"
            senders_path.write_text(
                "# ignored\nUser@Example.com\n  alerts@example.com  \n",
                encoding="utf-8",
            )

            self.assertEqual(
                load_senders([str(senders_path)], ["INLINE@Example.com"]),
                {"user@example.com", "alerts@example.com", "inline@example.com"},
            )

    def test_missing_sender_file_reports_error(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            load_senders(["/does/not/exist/senders.txt"], [])

        self.assertIn("could not read senders file", str(raised.exception))

    def test_scan_requires_a_mid_on_the_sender_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "mail.log"
            log_path.write_text(
                "From:<user@example.com>\nMID 123 From:<user@example.com>\n",
                encoding="utf-8",
            )

            self.assertEqual(
                scan_mids_for_senders({"user@example.com"}, [str(log_path)]),
                {"user@example.com": {"123"}},
            )

    def test_scan_missing_log_reports_error(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            scan_mids_for_senders({"user@example.com"}, ["/does/not/exist/mail.log"])

        self.assertIn("could not read log file", str(raised.exception))

    def test_index_and_render_include_matching_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "mail.log"
            log_path.write_text("MID 123 From:<user@example.com>\n", encoding="utf-8")

            indexed = index_logs_for_mids([str(log_path)], {"123"})

        self.assertEqual(indexed["123"][0].lineno, 1)
        rendered = render_thread("user@example.com", ["123"], indexed)
        self.assertIn("[mail.log:1] MID 123 From:<user@example.com>", rendered)

    def test_empty_index_and_missing_rendered_mid_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "mail.log"
            log_path.write_text("MID 123 From:<user@example.com>\n", encoding="utf-8")

            self.assertEqual(index_logs_for_mids([str(log_path)], set()), {})

        rendered = render_thread("user@example.com", ["999"], {})
        self.assertIn("No lines found indexed by MID", rendered)


class TestMain(unittest.TestCase):
    def _run_main(self, *arguments: str) -> None:
        with patch.object(sys, "argv", ["core-ces-log-parse", *arguments]):
            main()

    def test_main_combined_output_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "nested" / "out.txt"
            self._run_main(
                "--logs",
                str(LOG_PATH),
                "--senders",
                str(SENDERS_PATH),
                "--out",
                str(out_path),
            )

            self.assertTrue(out_path.exists())
            self.assertIn("MID 1001", out_path.read_text(encoding="utf-8"))

    def test_main_outdir_creates_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "nested" / "out"
            self._run_main(
                "--logs",
                str(LOG_PATH),
                "--sender",
                "noreply@salesforce.com",
                "--outdir",
                str(out_dir),
            )

            self.assertTrue((out_dir / "noreply_salesforce.com.txt").exists())

    def test_main_validation_errors(self) -> None:
        cases = [
            (
                [
                    "--logs",
                    str(LOG_PATH),
                    "--sender",
                    "noreply@salesforce.com",
                    "--out",
                    "/tmp/out.txt",
                    "--outdir",
                    "/tmp/out",
                ],
                "Specify exactly one",
            ),
            (
                [
                    "--logs",
                    "/does/not/exist/mail.log",
                    "--sender",
                    "noreply@salesforce.com",
                    "--out",
                    "/tmp/out.txt",
                ],
                "log file not found",
            ),
            (
                [
                    "--logs",
                    str(LOG_PATH),
                    "--senders",
                    "/does/not/exist/senders.txt",
                    "--out",
                    "/tmp/out.txt",
                ],
                "senders file not found",
            ),
            (
                ["--logs", str(LOG_PATH), "--out", "/tmp/out.txt"],
                "No senders provided",
            ),
            (
                [
                    "--logs",
                    str(LOG_PATH),
                    "--sender",
                    "missing@example.com",
                    "--out",
                    "/tmp/out.txt",
                ],
                "No matches found",
            ),
        ]

        for arguments, expected in cases:
            with self.subTest(expected=expected):
                with self.assertRaises(SystemExit) as raised:
                    self._run_main(*arguments)
                self.assertIn(expected, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
