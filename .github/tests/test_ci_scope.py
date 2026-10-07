"""Routing regressions that run with the standard library on every PR."""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import ci_scope  # noqa: E402


class TestRouting(unittest.TestCase):
    def test_reviewed_prose_only(self) -> None:
        for path in ci_scope.PROSE_FILES:
            with self.subTest(path=path):
                self.assertEqual(ci_scope.classify([path]), {"smoke": False, "inputs": False})

    def test_unknown_and_executable_paths_select_smoke(self) -> None:
        for path in (
            "src/core_ces_log_parse/main.py",
            "tests/test_main.py",
            "tests/fixtures/sample.log",
            "tests/fixtures/example.md",
            "docs/new-executable-example.md",
            "uv.lock",
            "pyproject.toml",
            ".github/workflows/ci.yml",
            "unknown",
        ):
            with self.subTest(path=path):
                self.assertTrue(ci_scope.classify([path])["smoke"])

    def test_empty_and_mixed_changes_select_smoke(self) -> None:
        self.assertTrue(ci_scope.classify([])["smoke"])
        self.assertTrue(ci_scope.classify(["README.md", "uv.lock"])["smoke"])

    def test_prose_validation_accepts_utf8_and_deletions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("Matched address – MID\n", encoding="utf-8")
            ci_scope.validate_prose(["README.md", "CONTEXT.md"], root)

    def test_invalid_prose_fails_even_in_mixed_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for data in (b"bad\0text", b"bad\xfftext"):
                with self.subTest(data=data):
                    (root / "README.md").write_bytes(data)
                    with self.assertRaises((ValueError, UnicodeDecodeError)):
                        ci_scope.validate_prose(["README.md", "uv.lock"], root)

    def test_symlinks_in_file_or_parent_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").symlink_to(root / "missing")
            with self.assertRaisesRegex(ValueError, "symlink"):
                ci_scope.validate_prose(["README.md"], root)
            (root / "docs").symlink_to(root / "missing-docs", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                ci_scope.validate_prose(["docs/README.md"], root)

    def test_directory_instead_of_prose_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").mkdir()
            with self.assertRaisesRegex(ValueError, "regular file"):
                ci_scope.validate_prose(["README.md"], root)

    def test_read_and_stat_errors_propagate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("valid", encoding="utf-8")
            with patch.object(Path, "read_bytes", side_effect=PermissionError("read denied")):
                with self.assertRaises(PermissionError):
                    ci_scope.validate_prose(["README.md"], root)
            with patch.object(Path, "lstat", side_effect=PermissionError("stat denied")):
                with self.assertRaises(PermissionError):
                    ci_scope.validate_prose(["README.md"], root)

    def test_invalid_relative_paths_fail_if_added_to_allowlist(self) -> None:
        for name in ("../README.md", "/README.md"):
            with self.subTest(name=name), patch.object(ci_scope, "PROSE_FILES", {name}):
                with self.assertRaisesRegex(ValueError, "repository-relative"):
                    ci_scope.validate_prose([name])

    def test_invalid_shas_and_git_failures_do_not_become_empty_scope(self) -> None:
        for revision in ("", "main", "1234", "-bad", "a" * 39):
            with self.subTest(revision=revision):
                with self.assertRaises(ValueError):
                    ci_scope.changed_paths(revision, "b" * 40)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(subprocess.CalledProcessError):
                ci_scope.changed_paths("a" * 40, "b" * 40, Path(directory))

    def test_main_emits_explicit_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            environment = {
                "CI_BASE_SHA": "a" * 40,
                "CI_HEAD_SHA": "b" * 40,
                "GITHUB_OUTPUT": str(output),
            }
            with (
                patch.dict(os.environ, environment),
                patch.object(ci_scope, "changed_paths", return_value=["README.md"]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                ci_scope.main()
            self.assertEqual(output.read_text(), "smoke=false\ninputs=false\n")

    def test_missing_sha_and_failed_validation_emit_no_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "output"
            with patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}, clear=True):
                with self.assertRaises(KeyError):
                    ci_scope.main()
            environment = {
                "CI_BASE_SHA": "a" * 40,
                "CI_HEAD_SHA": "b" * 40,
                "GITHUB_OUTPUT": str(output),
            }
            with (
                patch.dict(os.environ, environment),
                patch.object(ci_scope, "changed_paths", return_value=["README.md"]),
                patch.object(ci_scope, "validate_prose", side_effect=OSError("read failed")),
            ):
                with self.assertRaises(OSError):
                    ci_scope.main()
            self.assertFalse(output.exists())


class TestGitDiff(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.git("-c", "init.defaultBranch=main", "init", "-q")
        (self.root / "README.md").write_text("initial\n", encoding="utf-8")
        self.base = self.commit()

    def git(self, *arguments: str) -> str:
        return subprocess.run(
            ["git", *arguments], cwd=self.root, check=True, capture_output=True, text=True
        ).stdout.strip()

    def commit(self) -> str:
        self.git("add", "--all")
        self.git(
            "-c",
            "user.name=CI tests",
            "-c",
            "user.email=ci-tests@example.com",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "fixture",
        )
        return self.git("rev-parse", "HEAD")

    def test_diff_covers_all_pr_commits_and_empty_diff(self) -> None:
        self.assertEqual(ci_scope.changed_paths(self.base, self.base, self.root), [])
        (self.root / "README.md").write_text("changed\n", encoding="utf-8")
        self.commit()
        (self.root / "code with spaces.py").write_text("pass\n", encoding="utf-8")
        head = self.commit()
        self.assertEqual(
            ci_scope.changed_paths(self.base, head, self.root),
            ["README.md", "code with spaces.py"],
        )
        with self.assertRaises(subprocess.CalledProcessError):
            ci_scope.changed_paths(self.base, "f" * 40, self.root)

    def test_both_rename_directions_select_smoke(self) -> None:
        (self.root / "README.md").rename(self.root / "unreviewed.md")
        head = self.commit()
        paths = ci_scope.changed_paths(self.base, head, self.root)
        self.assertEqual(paths, ["README.md", "unreviewed.md"])
        self.assertTrue(ci_scope.classify(paths)["smoke"])
        (self.root / "unreviewed.md").rename(self.root / "README.md")
        next_head = self.commit()
        paths = ci_scope.changed_paths(head, next_head, self.root)
        self.assertEqual(paths, ["README.md", "unreviewed.md"])
        self.assertTrue(ci_scope.classify(paths)["smoke"])
