#!/usr/bin/env python3
"""Model-free tests for the proposed filler_run15 patch (never runs a keeper/job)."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "scripts/coordination/rowflow/filler_run15.sh"
PATCH = Path(__file__).with_name("filler_run15-stop-completion.patch")


def extract_function(source: str, name: str) -> str:
    marker = f"{name}() {{"
    start = source.index(marker)
    depth = 0
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start : i + 1]
    raise AssertionError(f"unterminated function {name}")


def extract_startup_completion(source: str) -> str:
    start = source.index("if hard_stop_recorded; then", source.index('log "launcher up'))
    end = source.index("while :; do", start)
    return source[start:end]


class StopCompletionPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        target = cls.root / "scripts/coordination/rowflow/filler_run15.sh"
        target.parent.mkdir(parents=True)
        target.write_bytes(SOURCE.read_bytes())
        subprocess.run(["patch", "-s", "-p1", "-i", str(PATCH)], cwd=cls.root, check=True)
        cls.patched = target.read_text()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_shell(self, script: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", "-c", script], text=True, capture_output=True)

    def finish_case(self, reason: str, rc: int, complete: bool, cleanup_bad: int = 0):
        fn = extract_function(self.patched, "finish_job")
        script = f'''\n{fn}
is_complete() {{ [ "$COMPLETE_RESULT" = 1 ]; }}
mark_complete() {{ echo marked-complete; return 0; }}
write_ended() {{ echo "ended:$1:$2"; }}
log() {{ echo "log:$*"; }}
COMPLETE_RESULT={1 if complete else 0}
STARTED_ONE=0
finish_job {cleanup_bad} {reason} {rc}
jobrc=$?
printf 'state:%s\\n' "$STARTED_ONE"
exit $jobrc
'''
        return self.run_shell(script)

    def test_hard_end_preserved_even_when_native_predicate_is_true(self):
        result = self.finish_case("hard-end", 75, True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ended:75:hard-end", result.stdout)
        self.assertNotIn("marked-complete", result.stdout)

    def test_disk_floor_preserved_even_when_native_predicate_is_true(self):
        result = self.finish_case("disk-floor", 75, True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ended:75:disk-floor", result.stdout)
        self.assertNotIn("marked-complete", result.stdout)

    def test_normal_complete_marks_row_complete(self):
        result = self.finish_case("exited", 0, True)
        self.assertEqual(result.returncode, 20, result.stderr)
        self.assertIn("marked-complete", result.stdout)
        self.assertNotIn("ended:", result.stdout)

    def test_partial_native_output_without_completion_is_recorded_partial(self):
        result = self.finish_case("exited", 0, False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ended:75:partial-native-incomplete", result.stdout)
        self.assertNotIn("marked-complete", result.stdout)

    def test_restart_hard_stop_receipt_wins_over_true_native_marker(self):
        fn = extract_function(self.patched, "hard_stop_recorded")
        startup = extract_startup_completion(self.patched)
        with tempfile.TemporaryDirectory() as d:
            ended = Path(d) / "ended"
            ended.write_text("rc=75 time=2026-11-04T00:00:00Z reason=disk-floor\n")
            script = f'''\nENDED={ended}\n{fn}
is_complete() {{ return 0; }}
mark_complete() {{ echo marked-complete; }}
log() {{ echo "log:$*"; }}
{startup}
echo startup-fell-through
'''
            result = self.run_shell(script)
        self.assertEqual(result.returncode, 75, result.stderr)
        self.assertIn("completion cannot override stop evidence", result.stdout)
        self.assertNotIn("marked-complete", result.stdout)
        self.assertNotIn("startup-fell-through", result.stdout)

    def test_other_or_partial_ended_receipt_does_not_claim_hard_stop(self):
        fn = extract_function(self.patched, "hard_stop_recorded")
        with tempfile.TemporaryDirectory() as d:
            ended = Path(d) / "ended"
            ended.write_text("rc=75 time=2026-11-04T00:00:00Z reason=partial-native-incomplete\n")
            result = self.run_shell(f'ENDED={ended}\n{fn}\nhard_stop_recorded')
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
