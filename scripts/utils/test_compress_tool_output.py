#!/usr/bin/env python3
"""Tests for compress_tool_output.py."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from compress_tool_output import compress_tool_output, MIN_COMPRESS_CHARS


# ---------------------------------------------------------------------------
# Passthrough / threshold tests
# ---------------------------------------------------------------------------

class TestPassthrough:
    def test_empty_string(self):
        assert compress_tool_output("", "pytest") == ""

    def test_short_output_unchanged(self):
        text = "PASSED test_foo.py::test_bar\n1 passed in 0.5s"
        assert compress_tool_output(text, "pytest") == text

    def test_below_threshold_unchanged(self):
        text = "x" * (MIN_COMPRESS_CHARS - 1)
        assert compress_tool_output(text, "pytest") == text

    def test_unknown_command_passthrough(self):
        text = "x" * 1000
        assert compress_tool_output(text, "curl https://example.com") == text

    def test_no_shorter_means_passthrough(self):
        """If compression produces equal or longer output, return original."""
        # A git status with very few files — compressed form may not be shorter
        text = " M file.py\n" * 100  # 1100 chars, but compression might not help
        result = compress_tool_output(text, "git status")
        assert len(result) <= len(text)


# ---------------------------------------------------------------------------
# Pytest compression
# ---------------------------------------------------------------------------

PYTEST_ALL_PASS = """collecting ... collected 50 items

test_foo.py::test_one PASSED                                          [  2%]
test_foo.py::test_two PASSED                                          [  4%]
test_foo.py::test_three PASSED                                        [  6%]
""" + "\n".join(f"test_foo.py::test_{i} PASSED                                          [{i*2}%]" for i in range(4, 51)) + """

============================== 50 passed in 3.21s ==============================
"""

PYTEST_WITH_FAILURES = """collecting ... collected 102 items

test_foo.py::test_one PASSED                                          [  1%]
test_foo.py::test_two PASSED                                          [  2%]
""" + "\n".join(f"test_foo.py::test_{i} PASSED" for i in range(3, 101)) + """
test_foo.py::test_bad FAILED                                          [ 99%]
test_foo.py::test_worse FAILED                                        [100%]

=================================== FAILURES ===================================
_________________________________ test_bad _________________________________

    def test_bad():
>       assert 1 == 2
E       assert 1 == 2

test_foo.py:42: AssertionError
_________________________________ test_worse _________________________________

    def test_worse():
>       raise ValueError("oops")
E       ValueError: oops

test_foo.py:50: ValueError
=========================== short test summary info ============================
FAILED test_foo.py::test_bad - assert 1 == 2
FAILED test_foo.py::test_worse - ValueError: oops
============================== 100 passed, 2 failed in 5.67s ==============================
"""


class TestPytest:
    def test_all_pass_compressed(self):
        result = compress_tool_output(PYTEST_ALL_PASS, "pytest tests/")
        assert "[compressed pytest output" in result
        assert "50 passed" in result
        assert len(result) < len(PYTEST_ALL_PASS)

    def test_failures_preserved(self):
        result = compress_tool_output(PYTEST_WITH_FAILURES, "python -m pytest")
        assert "test_bad" in result
        assert "test_worse" in result
        assert "assert 1 == 2" in result
        assert "ValueError: oops" in result
        assert "2 failed" in result
        assert len(result) < len(PYTEST_WITH_FAILURES)

    def test_individual_pass_lines_stripped(self):
        result = compress_tool_output(PYTEST_WITH_FAILURES, "pytest")
        # Individual PASSED lines should not appear
        assert "test_3 PASSED" not in result
        assert "test_50 PASSED" not in result


# ---------------------------------------------------------------------------
# Cargo test compression
# ---------------------------------------------------------------------------

CARGO_TEST_MIXED = """running 30 tests
test tests::test_a ... ok
test tests::test_b ... ok
""" + "\n".join(f"test tests::test_{i} ... ok" for i in range(3, 29)) + """
test tests::test_fail ... FAILED
test tests::test_another_fail ... FAILED

failures:

---- tests::test_fail stdout ----
thread 'tests::test_fail' panicked at 'assertion failed: false'

---- tests::test_another_fail stdout ----
thread 'tests::test_another_fail' panicked at 'not yet implemented'

failures:
    tests::test_fail
    tests::test_another_fail

test result: FAILED. 28 passed; 2 failed; 0 ignored; 0 measured; 0 filtered out
"""


class TestCargoTest:
    def test_failures_preserved(self):
        result = compress_tool_output(CARGO_TEST_MIXED, "cargo test")
        assert "test_fail" in result
        assert "assertion failed: false" in result
        assert "2 failed" in result
        assert len(result) < len(CARGO_TEST_MIXED)

    def test_ok_lines_stripped(self):
        result = compress_tool_output(CARGO_TEST_MIXED, "cargo test")
        assert "test_a ... ok" not in result


# ---------------------------------------------------------------------------
# git status compression
# ---------------------------------------------------------------------------

GIT_STATUS_PORCELAIN = """ M src/api/router.py
 M src/api/handler.py
 M tests/test_router.py
?? new_file.py
?? another_new.py
 D old_file.py
""" + "\n".join(f" M src/module_{i}.py" for i in range(20))

GIT_STATUS_HUMAN = """On branch main
Your branch is up to date with 'origin/main'.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
\tmodified:   src/api/router.py
\tmodified:   src/api/handler.py
\tmodified:   tests/test_router.py

Untracked files:
  (use "git add <file>..." to include in what will be committed)
\tnew_file.py
\tanother_new.py

no changes added to commit (use "git add" and/or "git commit -a" to add)
""" + "\n" * 30  # pad to exceed threshold


class TestGitStatus:
    def test_porcelain_compressed(self):
        result = compress_tool_output(GIT_STATUS_PORCELAIN, "git status")
        assert "modified" in result
        assert "untracked" in result
        assert len(result) < len(GIT_STATUS_PORCELAIN)

    def test_human_readable_compressed(self):
        result = compress_tool_output(GIT_STATUS_HUMAN, "git status")
        assert "modified" in result or "git status:" in result


# ---------------------------------------------------------------------------
# git diff compression
# ---------------------------------------------------------------------------

GIT_DIFF_LARGE = """diff --git a/src/router.py b/src/router.py
index abc1234..def5678 100644
--- a/src/router.py
+++ b/src/router.py
@@ -10,7 +10,8 @@ class Router:
     def route(self, request):
-        return self.default_handler(request)
+        handler = self.find_handler(request)
+        return handler(request)

     def find_handler(self, request):
         pass
diff --git a/src/handler.py b/src/handler.py
index 111222..333444 100644
--- a/src/handler.py
+++ b/src/handler.py
@@ -5,6 +5,10 @@ class Handler:
     def process(self):
-        pass
+        result = self.validate()
+        if result.ok:
+            return self.execute()
+        return result.error
""" + "\n".join(f"+    line_{i} = {i}" for i in range(100))  # pad to exceed threshold


class TestGitDiff:
    def test_keeps_changed_lines(self):
        result = compress_tool_output(GIT_DIFF_LARGE, "git diff")
        assert "+        handler = self.find_handler(request)" in result
        assert "-        return self.default_handler(request)" in result

    def test_strips_boilerplate(self):
        result = compress_tool_output(GIT_DIFF_LARGE, "git diff")
        assert "index abc1234" not in result
        assert "--- a/src/router.py" not in result

    def test_file_count_in_header(self):
        result = compress_tool_output(GIT_DIFF_LARGE, "git diff")
        assert "2 files" in result


# ---------------------------------------------------------------------------
# git log compression
# ---------------------------------------------------------------------------

GIT_LOG_VERBOSE = """commit a1b2c3d4e5f6789012345678901234567890abcd
Author: User Name <user@example.com>
Date:   Mon Apr 5 10:30:00 2026 +0000

    Fix routing bug in escalation handler

commit b2c3d4e5f678901234567890123456789012bcde
Author: User Name <user@example.com>
Date:   Sun Apr 4 15:00:00 2026 +0000

    Add context folding Phase 1 implementation

commit c3d4e5f6789012345678901234567890123cdef0
Author: User Name <user@example.com>
Date:   Sat Apr 3 12:00:00 2026 +0000

    Update model registry with new baselines
""" + "\n".join(f"""commit {"a" * 10}{i:030d}
Author: User <u@e.com>
Date:   Fri Apr 2 10:00:00 2026 +0000

    Commit message number {i}
""" for i in range(20))


class TestGitLog:
    def test_compact_format(self):
        result = compress_tool_output(GIT_LOG_VERBOSE, "git log")
        assert "a1b2c3d4" in result
        assert "Fix routing bug" in result
        assert "Author:" not in result
        assert "Date:" not in result

    def test_commit_count(self):
        result = compress_tool_output(GIT_LOG_VERBOSE, "git log")
        assert "23 commits" in result

    def test_already_compact_passthrough(self):
        compact = "a1b2c3d Fix bug\nb2c3d4e Add feature\nc3d4e5f Update docs\n" * 50
        result = compress_tool_output(compact, "git log")
        # Should pass through since lines are already short
        assert result == compact


# ---------------------------------------------------------------------------
# ls compression
# ---------------------------------------------------------------------------

LS_LARGE = "total 248\n" + "\n".join(
    f"drwxr-xr-x 2 user group 4096 Apr  5 10:00 dir_{i}" for i in range(5)
) + "\n" + "\n".join(
    f"-rw-r--r-- 1 user group  {1024 + i} Apr  5 10:00 file_{i}.py" for i in range(30)
) + "\n" + "\n".join(
    f"-rw-r--r-- 1 user group  {512 + i} Apr  5 10:00 module_{i}.ts" for i in range(15)
) + "\n" + "\n".join(
    f"-rw-r--r-- 1 user group  {256 + i} Apr  5 10:00 doc_{i}.md" for i in range(10)
)


class TestLs:
    def test_aggregated(self):
        result = compress_tool_output(LS_LARGE, "ls -la /workspace/src/")
        assert "[ls:" in result
        assert ".py" in result
        assert "dirs" in result
        assert len(result) < len(LS_LARGE)

    def test_file_count(self):
        result = compress_tool_output(LS_LARGE, "ls -la")
        assert "55 files" in result

    def test_plain_ls(self):
        plain = "\n".join(f"file_{i}.py" for i in range(60))
        result = compress_tool_output(plain, "ls")
        assert "[ls:" in result


# ---------------------------------------------------------------------------
# Build output compression
# ---------------------------------------------------------------------------

BUILD_OUTPUT_WITH_ERRORS = """   Compiling mylib v0.1.0
   Compiling myapp v0.1.0
""" + "\n".join(f"   Compiling dep_{i} v0.{i}.0" for i in range(30)) + """
error[E0308]: mismatched types
  --> src/main.rs:42:5
   |
42 |     let x: u32 = "hello";
   |                   ^^^^^^^ expected `u32`, found `&str`

error[E0599]: no method named `foo` found for struct `Bar`
  --> src/lib.rs:10:5

warning: unused variable `y`
  --> src/main.rs:50:9

Finished `dev` profile [unoptimized + debuginfo] target(s) in 12.34s
"""


class TestBuildOutput:
    def test_errors_preserved(self):
        result = compress_tool_output(BUILD_OUTPUT_WITH_ERRORS, "cargo build")
        assert "mismatched types" in result
        assert "no method named" in result
        assert "2 errors" in result

    def test_compiling_lines_stripped(self):
        result = compress_tool_output(BUILD_OUTPUT_WITH_ERRORS, "cargo build")
        assert "Compiling dep_" not in result

    def test_summary_preserved(self):
        result = compress_tool_output(BUILD_OUTPUT_WITH_ERRORS, "cargo build")
        assert "Finished" in result


# ---------------------------------------------------------------------------
# Dispatcher matching tests
# ---------------------------------------------------------------------------

class TestDispatcher:
    def test_pytest_variants(self):
        text = PYTEST_ALL_PASS
        # All should trigger pytest handler
        for cmd in ["pytest", "pytest tests/", "python -m pytest", "python -m pytest -v tests/"]:
            result = compress_tool_output(text, cmd)
            assert "[compressed pytest" in result, f"Failed for command: {cmd}"

    def test_git_status_variants(self):
        text = GIT_STATUS_PORCELAIN
        for cmd in ["git status", "git -c color.status=always status"]:
            result = compress_tool_output(text, cmd)
            assert "git status:" in result or len(result) <= len(text), f"Failed for: {cmd}"

    def test_build_variants(self):
        text = BUILD_OUTPUT_WITH_ERRORS
        for cmd in ["cargo build", "make -j8", "cmake --build build"]:
            result = compress_tool_output(text, cmd)
            assert "[build output:" in result, f"Failed for command: {cmd}"
