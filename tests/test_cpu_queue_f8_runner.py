"""Deterministic controls for the tracked f8 queue runner's UTC admission rule."""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/system/cpu_queue_f8_runner.sh"
LEGACY_SHA256 = "d7f27ad46b5f6388cea53b04ed7b340ba8399faf2e6fade8d209998cd14250fd"
LEGACY_FIXTURE = ROOT / "tests/fixtures/cpu_queue_f8_v1_guard.sh.txt"
LEGACY_FIXTURE_SHA256 = "5fe47cb1e12fa36775ac2b6f13a2451206a284bf66fec414bd71c884aa85c460"
LEGACY_PRIVATE_COPY = Path("/mnt/raid0/llm/tmp/cpu-queue-f8/runner.sh")
LEGACY_RESEARCH_COPY = ROOT / "repos/epyc-inference-research/artifacts/f8-evidence-20261021/cpu-queue-f8/runner.sh"


def epoch(iso: str) -> int:
    return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc).timestamp())


def run_predicate(mode: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CPU_QUEUE_F8_TEST_ONLY"] = "1"
    # The test entry must not initialize the queue even if given a fresh path.
    env["CPU_QUEUE_F8_Q"] = str(ROOT / ".test-queue-must-not-be-created")
    return subprocess.run(
        [str(RUNNER), mode, *args],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=5,
    )


def legacy_source_result(function: str, at: str, duration_s: int | None = None) -> str:
    """Run the exact v1 fixture function with only date's clock inputs pinned."""
    now = epoch(at)
    day = at[:10]
    script = r'''
source "$LEGACY_FIXTURE"
real_date=$(command -v date)
NOW=$NOW_INPUT
FAKEDAY=$DAY_INPUT
date() {
  if [[ "$*" == "-u +%s" ]]; then printf '%s\n' "$NOW"
  elif [[ "$*" == "-u +%F" ]]; then printf '%s\n' "$FAKEDAY"
  else command "$real_date" "$@"; fi
}
if [[ "$FUNCTION" == "in_blackout" ]]; then
  if in_blackout; then printf 'blackout\n'; else rc=$?; [[ $rc == 1 ]] && printf 'open\n' || exit "$rc"; fi
else
  if admission_guard "$DURATION_INPUT"; then printf 'defer\n'; else rc=$?; [[ $rc == 1 ]] && printf 'admit\n' || exit "$rc"; fi
fi
'''
    env = os.environ.copy()
    env.update(LEGACY_FIXTURE=str(LEGACY_FIXTURE), NOW_INPUT=str(now), DAY_INPUT=day, FUNCTION=function)
    if duration_s is not None:
        env["DURATION_INPUT"] = str(duration_s)
    result = subprocess.run(
        ["bash", "-c", script], env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False, timeout=5,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.strip()

def legacy_source_admission(at: str, duration_s: int) -> str:
    return legacy_source_result("admission_guard", at, duration_s)


def run_normal_runner_after_lock_wait(pair_mode: bool) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    """Run the real entrypoint with fake date/queue/lock/executor commands."""
    temp = tempfile.TemporaryDirectory(prefix="cpu-queue-f8-integration-")
    base = Path(temp.name)
    q = base / "queue"
    bin_dir = base / "bin"
    bin_dir.mkdir()
    for name in ("pending", "running", "done", "log", "pairlock"):
        (q / name).mkdir(parents=True, exist_ok=True)
    now_file = base / "now.epoch"
    waited_file = base / "lock-waited"
    marker_file = base / "job-ran"
    now_file.write_text(str(epoch("2026-10-31T00:09:00Z")))
    advance_to = epoch("2026-10-31T00:12:00Z")
    job = q / "pending" / "boundary-job.sh"
    job.write_text(f"#!/usr/bin/env bash\necho ran >> {marker_file}\n")
    job.chmod(0o755)
    (q / "PAIR_OK").touch() if pair_mode else None
    (q / "pairguard.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    (q / "pairguard.sh").chmod(0o755)
    # Job duration is read from the native queue file as the normal runner does.
    job.write_text(f"#maxjob_s=300\n#!/usr/bin/env bash\necho ran >> {marker_file}\n")
    job.chmod(0o755)

    commands = {
        "date": '''#!/usr/bin/env bash
if [[ "$*" == "-u +%s" ]]; then cat "$NOW_FILE"; else exec /usr/bin/date "$@"; fi
''',
        "sleep": '''#!/usr/bin/env bash
now=$(cat "$NOW_FILE"); echo $((now + ${1:-1})) > "$NOW_FILE"
''',
        "region-lock": '''#!/usr/bin/env bash
case ${1:-} in
  status)
    if [[ ${FAKE_PAIR_MODE:-0} == 1 ]]; then echo 'q0 HELD build[peer] 123'; else echo 'q0 free -'; fi
    ;;
  run)
    echo entered > "$LOCK_WAITED_FILE"
    echo "$WAIT_ADVANCE_EPOCH" > "$NOW_FILE"
    while [[ $# -gt 0 && $1 != -- ]]; do shift; done
    [[ $# -gt 0 ]] && shift
    "$@"
    ;;
  *) echo "unexpected region-lock command: $*" >&2; exit 64 ;;
esac
''',
        "taskset": '''#!/usr/bin/env bash
[[ ${1:-} == -c ]] || exit 64
shift 2
# Paired claims have no region-lock run command; advance the same fake clock
# at the final executor boundary to model pair-guard/setup delay.
echo "$WAIT_ADVANCE_EPOCH" > "$NOW_FILE"
echo taskset-boundary >> "$LOCK_WAITED_FILE"
exec "$@"
''',
        "nice": '''#!/usr/bin/env bash
if [[ ${1:-} == -n ]]; then shift 2; fi
exec "$@"
''',
        "setsid": '''#!/usr/bin/env bash
shift
exec "$@"
''',
        "nohup": "#!/usr/bin/env bash\nexit 0\n",
    }
    for name, body in commands.items():
        path = bin_dir / name
        path.write_text(body)
        path.chmod(0o755)

    env = os.environ.copy()
    env.update({
        "PATH": f"{bin_dir}:{env['PATH']}",
        "CPU_QUEUE_F8_Q": str(q),
        "CPU_QUEUE_F8_RL": str(bin_dir / "region-lock"),
        "NOW_FILE": str(now_file),
        "WAIT_ADVANCE_EPOCH": str(advance_to),
        "LOCK_WAITED_FILE": str(waited_file),
        "JOB_MARKER": str(marker_file),
        "FAKE_PAIR_MODE": "1" if pair_mode else "0",
        "STOP_AT": "2026-10-31T00:12:30Z",
    })
    result = subprocess.run(
        [str(RUNNER), "integration-test"], env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10,
    )
    state = {
        "job_pending": (q / "pending" / job.name).is_file(),
        "job_done": (q / "done" / job.name).exists(),
        "job_running": (q / "running" / job.name).exists(),
        "waited": waited_file.is_file(),
        "job_started": marker_file.is_file(),
        "log": (q / "log" / job.name.replace(".sh", ".log")).read_text()
        if (q / "log" / job.name.replace(".sh", ".log")).exists() else "",
    }
    temp.cleanup()
    return result, state


class CpuQueueF8RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not RUNNER.is_file():
            raise AssertionError(f"tracked successor missing: {RUNNER}")
        if not LEGACY_FIXTURE.is_file():
            raise AssertionError(f"v1 regression fixture missing: {LEGACY_FIXTURE}")
        fixture_sha = hashlib.sha256(LEGACY_FIXTURE.read_bytes()).hexdigest()
        if fixture_sha != LEGACY_FIXTURE_SHA256:
            raise AssertionError(f"v1 fixture changed: {fixture_sha} != {LEGACY_FIXTURE_SHA256}")
        for historical_source in (LEGACY_PRIVATE_COPY, LEGACY_RESEARCH_COPY):
            if historical_source.is_file():
                actual = hashlib.sha256(historical_source.read_bytes()).hexdigest()
                if actual != LEGACY_SHA256:
                    raise AssertionError(
                        f"legacy v1 source changed at {historical_source}: "
                        f"{actual} != {LEGACY_SHA256}"
                    )

    def assert_blackout(self, at: str, expected: bool) -> None:
        result = run_predicate("--blackout", str(epoch(at)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "blackout" if expected else "open")

    def assert_admission(self, at: str, duration_s: int, expected: bool) -> None:
        result = run_predicate("--admission", str(epoch(at)), str(duration_s))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "admit" if expected else "defer")

    def test_daily_blackout_uses_utc_half_open_endpoints(self) -> None:
        cases = (
            ("2026-10-31T00:00:00Z", False),
            ("2026-10-31T00:14:59Z", False),
            ("2026-10-31T00:15:00Z", True),
            ("2026-10-31T06:29:59Z", True),
            ("2026-10-31T06:30:00Z", False),
            ("2026-10-31T23:59:00Z", False),
        )
        for at, expected in cases:
            with self.subTest(at=at):
                self.assert_blackout(at, expected)

    def test_job_admission_checks_same_day_and_next_day_blackout(self) -> None:
        for duration in (20 * 60, 24 * 60, 30 * 60):
            with self.subTest(at="00:00", duration=duration):
                self.assert_admission("2026-10-31T00:00:00Z", duration, False)
            with self.subTest(at="23:59", duration=duration):
                self.assert_admission("2026-10-31T23:59:00Z", duration, False)

    def test_half_open_job_and_blackout_endpoints(self) -> None:
        # Ending exactly as the blackout starts does not overlap it. Crossing
        # the start by one second does. At 06:30 the blackout has ended.
        self.assert_admission("2026-10-31T00:14:59Z", 1, True)
        self.assert_admission("2026-10-31T00:14:59Z", 2, False)
        self.assert_admission("2026-10-31T06:30:00Z", 5 * 60, True)
        self.assert_admission("2026-10-31T06:31:00Z", 5 * 60, True)
        # A long job must scan recurring windows beyond tomorrow as well; the
        # endpoint at next day's 00:15 is allowed, one second beyond is not.
        self.assert_admission("2026-10-31T06:30:00Z", 17 * 60 * 60 + 45 * 60, True)
        self.assert_admission("2026-10-31T06:30:00Z", 17 * 60 * 60 + 45 * 60 + 1, False)
        self.assert_admission("2026-10-31T06:30:00Z", 2 * 86400, False)

    def test_normal_admission_path_calls_the_tested_predicate(self) -> None:
        source = RUNNER.read_text()
        main = source.split("cpu_queue_f8_main() {", 1)[1]
        self.assertRegex(
            main,
            r"if ! cpu_queue_f8_admission_allowed \"\$now\" \"\$fmax\"; then\s+continue",
        )
        self.assertNotRegex(main, r"00:15:00 \+1 day")

    def test_test_only_cli_and_sourcing_do_not_initialize_queue(self) -> None:
        q = ROOT / ".test-queue-must-not-be-created"
        self.assertFalse(q.exists())
        result = run_predicate("--admission", str(epoch("2026-10-31T00:00:00Z")), "1800")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "defer")
        self.assertFalse(q.exists())
        source_result = subprocess.run(
            ["bash", "-c", 'source "$1"; type cpu_queue_f8_admission_allowed >/dev/null',
             "bash", str(RUNNER)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=5,
        )
        self.assertEqual(source_result.returncode, 0, source_result.stderr)
        self.assertFalse(q.exists())

    def test_normal_mode_requires_an_explicit_bounded_stop(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cpu-queue-f8-stop-") as temp:
            q = Path(temp) / "queue"
            env = os.environ.copy()
            env.pop("STOP_AT", None)
            env.update(CPU_QUEUE_F8_Q=str(q))
            result = subprocess.run(
                [str(RUNNER), "worker-test"], env=env, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=5,
            )
            self.assertEqual(result.returncode, 64)
            self.assertIn("explicit UTC STOP_AT", result.stderr)
            self.assertFalse(q.exists())

    def test_real_entry_rechecks_after_region_lock_wait_before_job_start(self) -> None:
        for pair_mode in (False, True):
            with self.subTest(pair_mode=pair_mode):
                result, state = run_normal_runner_after_lock_wait(pair_mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(state["waited"], "controlled lock wait did not execute")
                self.assertTrue(state["job_pending"], "late job was not returned to pending")
                self.assertFalse(state["job_done"])
                self.assertFalse(state["job_running"])
                self.assertFalse(state["job_started"], "job process started after its window closed")
                self.assertIn("daily UTC blackout after lock wait", state["log"])

    def test_exact_v1_source_is_a_negative_control(self) -> None:
        # The preserved v1 correctly classifies the blackout itself, but its
        # tomorrow-only admission guard misses 00:00 -> 00:30 on the same day.
        self.assertEqual(legacy_source_result("in_blackout", "2026-10-31T00:00:00Z"), "open")
        self.assertEqual(legacy_source_admission("2026-10-31T00:00:00Z", 30 * 60), "admit")
        self.assertEqual(legacy_source_result("in_blackout", "2026-10-31T00:15:00Z"), "blackout")
        self.assertEqual(legacy_source_admission("2026-10-31T23:59:00Z", 30 * 60), "defer")

    def test_invalid_arguments_are_refused(self) -> None:
        result = run_predicate("--admission", "-1", "30")
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid", result.stderr.lower())
        # Decimal strings with a leading zero remain decimal, not octal.
        self.assert_admission("2026-10-31T06:30:00Z", 8, True)
        result = run_predicate("--admission", str(epoch("2026-10-31T06:30:00Z")), "0008")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "admit")


if __name__ == "__main__":
    unittest.main()
