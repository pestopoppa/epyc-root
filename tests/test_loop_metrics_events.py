import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/handoffs/loop_metrics_events.py"
SPEC = importlib.util.spec_from_file_location("loop_events", SCRIPT)
events = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(events)


def event(kind, ordinal, **extra):
    return dict(
        kind=kind,
        producer="quarter-writer",
        session="fixture",
        ordinal=ordinal,
        at_ns=ordinal * 3_600_000_000_000,
        **extra,
    )


def session():
    return [
        event("coverage_open", 0, resources=["q0"]),
        event("reservation_open", 1, resource="q0", reservation="grant-a"),
        event("attempt_begin", 2, attempt="one", phase="launcher-admission"),
        event("attempt_end", 3, attempt="one", phase="launcher-admission", rc=6),
        event("reservation_close", 4, resource="q0", reservation="grant-a"),
        event("coverage_close", 5, expected_events=4),
    ]


def test_actual_cli_append_and_reader_preserves_bytes(tmp_path):
    ledger = tmp_path / "events.jsonl"
    for row in session():
        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--ledger",
                str(ledger),
                "--event",
                json.dumps(row),
            ],
            check=True,
        )
    raw = ledger.read_bytes()
    assert len(raw.splitlines()) == 6
    report = events.fold([json.loads(line) for line in raw.splitlines()])[0]
    assert report["status"] == "sealed"
    assert report["calendar_unreserved_hours"] == {"q0": 2}
    assert report["attempt_phases"]["launcher-admission"] == {
        "attempts": 1,
        "failures": 1,
        "failure_rate": 1.0,
    }
    assert ledger.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [ledger]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda rows: rows[:-1],
        lambda rows: rows[1:],
        lambda rows: rows[:2] + rows[3:],
        lambda rows: rows + [rows[-1]],
        lambda rows: [
            dict(r, expected_events=99) if r["kind"] == "coverage_close" else r
            for r in rows
        ],
        lambda rows: [
            dict(r, at_ns=0) if r["kind"] == "attempt_end" else r for r in rows
        ],
    ],
)
def test_crash_lost_duplicate_or_inconsistent_events_cannot_seal(mutate):
    rows = mutate(session())
    assert all(r["status"] == "unknown" for r in events.fold(rows))


def test_overlapping_reservations_union_without_double_count():
    rows = [
        event("coverage_open", 0, resources=["q0"]),
        event("reservation_open", 1, resource="q0", reservation="a"),
        event("reservation_open", 2, resource="q0", reservation="b"),
        event("reservation_close", 3, resource="q0", reservation="a"),
        event("reservation_close", 4, resource="q0", reservation="b"),
        event("coverage_close", 5, expected_events=4),
    ]
    assert events.fold(rows)[0]["calendar_unreserved_hours"] == {"q0": 2}


def test_metadata_cap_fails_visible_without_replacement(tmp_path):
    p = tmp_path / "events"
    row = session()[0]
    events.append(p, row)
    before = p.read_bytes()
    ino = p.stat().st_ino
    with pytest.raises(ValueError, match="cap reached"):
        events.append(p, row, cap=len(before))
    assert p.read_bytes() == before and p.stat().st_ino == ino


@pytest.mark.parametrize(
    "change",
    [
        {"message": "private text"},
        {"reason": "arbitrary text"},
        {"ordinal": True},
        {"producer": "path/escape"},
    ],
)
def test_no_freeform_message_fields_or_malformed_metadata(change, tmp_path):
    row = dict(session()[0], **change)
    with pytest.raises(ValueError):
        events.append(tmp_path / "no-event", row)
    assert not list(tmp_path.iterdir())


def test_symlink_destination_refused(tmp_path):
    target = tmp_path / "target"
    target.write_text("original")
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(OSError):
        events.append(link, session()[0])
    assert target.read_text() == "original"


def test_actual_shell_admission_hook_captures_suppressed_rc12_and_preserves_rc_stdout(
    tmp_path,
):
    hook = ROOT / "scripts/coordination/loop_metrics_hook.sh"
    ledger = tmp_path / "events"
    env = dict(
        os.environ,
        LOOP_METRICS_LEDGER=str(ledger),
        LOOP_METRICS_HELPER=str(SCRIPT),
        SELF=str(tmp_path / "caller"),
    )
    shell = """set -uo pipefail
source "$1"
lm_start calendar-admission
trap lm_close EXIT
lm_attempt_begin
value=$(printf 'native refusal output'; exit 12); rc=$?
lm_admission_result "$rc"
printf '%s' "$value"
exit "$rc"
"""
    result = subprocess.run(
        ["/bin/bash", "-c", shell, "fixture", str(hook)],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 12 and result.stdout == "native refusal output"
    report = events.fold([json.loads(l) for l in ledger.read_bytes().splitlines()])[0]
    assert report["status"] == "sealed"
    assert report["attempt_phases"]["calendar-admission"] == {
        "attempts": 1,
        "failures": 1,
        "failure_rate": 1.0,
    }


def test_shell_metadata_failure_cannot_change_command_outcome_or_seal(tmp_path):
    hook = ROOT / "scripts/coordination/loop_metrics_hook.sh"
    env = dict(
        os.environ,
        LOOP_METRICS_LEDGER=str(tmp_path / "missing/events"),
        LOOP_METRICS_HELPER=str(SCRIPT),
        SELF="fixture",
    )
    result = subprocess.run(
        [
            "/bin/bash",
            "-c",
            'source "$1"; lm_start; trap lm_close EXIT; lm_attempt_begin; printf payload; lm_admission_result 0; exit 7',
            "fixture",
            str(hook),
        ],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 7 and result.stdout == "payload"
    assert "coverage remains unknown" in result.stderr
    assert not (tmp_path / "missing/events").exists()


def test_real_launcher_completed_check_unchanged_and_opt_in_only(tmp_path):
    script = ROOT / "scripts/coordination/filler_run12.sh"
    for enabled in (False, True):
        base = tmp_path / str(enabled)
        base.mkdir()
        (base / "grants").mkdir()
        ledger = base / "metrics"
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith(("FILLER_", "LOOP_METRICS_"))
        }
        env.update(
            FILLER_FLAGS_DIR=str(base),
            FILLER_GRANTS_DIR=str(base / "grants"),
            FILLER_STATE_DIR=str(base / "state"),
            FILLERS_MD=str(base / "absent-fillers"),
            FILLER_GPU_LOCK=str(base / "gpu.lock"),
            FILLER_RL=str(base / "never-called"),
        )
        if enabled:
            env.update(LOOP_METRICS_LEDGER=str(ledger), LOOP_METRICS_HELPER=str(SCRIPT))
        done = subprocess.run(
            [
                "/bin/bash",
                str(script),
                "--id",
                "SYNTHETIC-LOOP5",
                "--class",
                "cpu",
                "--cmd",
                "exit 99",
                "--stop",
                str(base / "STOP"),
                "--complete-cmd",
                "true",
                "--workdir",
                str(base),
            ],
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert done.returncode == 0, done.stderr
        assert (base / "grants/SYNTHETIC-LOOP5.complete").exists()
        assert (base / "grants/SYNTHETIC-LOOP5.ended").read_text().startswith("rc=0 ")
        assert ledger.exists() == enabled
        if enabled:
            report = events.fold(
                [json.loads(l) for l in ledger.read_bytes().splitlines()]
            )[0]
            assert report["status"] == "sealed"
            assert report["attempt_phases"]["launcher-admission"]["attempts"] == 0


def counter(ordinal=0, **extra):
    return dict(
        kind="idle_counter",
        producer="keeper",
        session="boot1",
        ordinal=ordinal,
        at_ns=1_000_000_000 + ordinal * 3_600_000_000_000,
        monotonic_ns=1 + ordinal * 3_600_000_000_000,
        boot_id="same-boot",
        hz=100,
        idle_ticks={"cpu0": 100 + ordinal * 360000},
        **extra,
    )


def test_kernel_accounted_idle_cpu_hours_excludes_iowait_and_never_whole_resource_hours():
    report = events.fold_idle([counter(), counter(1)])[0]
    assert report["status"] == "observed"
    assert report["kernel_accounted_cpu_idle_hours"] == 1
    assert report["iowait"] == "excluded"
    assert "whole-resource" in report["basis"]


@pytest.mark.parametrize(
    "change",
    [
        {"boot_id": "next-boot"},
        {"hz": 250},
        {"idle_ticks": {"cpu1": 360100}},
        {"idle_ticks": {"cpu0": 1}},
        {"monotonic_ns": 1},
        {"ordinal": 0},
    ],
)
def test_kernel_counter_discontinuities_refuse_idle_value(change):
    b = counter(1)
    b.update(change)
    report = events.fold_idle([counter(), b])[0]
    assert report["status"] == "unknown"
    assert "kernel_accounted_cpu_idle_hours" not in report


def test_actual_kernel_counter_cli_and_append_only_prefix(tmp_path):
    cpu = min(os.sched_getaffinity(0))
    ledger = tmp_path / "kernel.jsonl"
    command = [
        sys.executable,
        str(SCRIPT),
        "--ledger",
        str(ledger),
        "--capture-cpus",
        str(cpu),
        "--session",
        "SYNTHETIC-kernel-control",
    ]
    subprocess.run(command + ["--ordinal", "0"], check=True)
    prefix = ledger.read_bytes()
    inode = ledger.stat().st_ino
    subprocess.run(command + ["--ordinal", "1"], check=True)
    assert ledger.read_bytes().startswith(prefix) and ledger.stat().st_ino == inode
    samples = [json.loads(l) for l in ledger.read_bytes().splitlines()]
    report = events.fold_idle(samples)[0]
    assert report["status"] == "observed"
    assert report["kernel_accounted_cpu_idle_hours"] >= 0
    assert report["cpus"] == ["cpu" + str(cpu)]


def test_exact_calendar_source_admission_block_records_rc12(tmp_path):
    proposal = ROOT / "tests/fixtures/loop5/calendar_admission.sh"
    text = proposal.read_text()
    lines = text.splitlines()
    at = lines.index("    lm_attempt_begin")
    block = "\n".join(lines[at : at + 3])
    assert "r=$($F/grant_ok.sh " in block and 'lm_admission_result "$rc"' in block
    command = tmp_path / "grant_ok.sh"
    command.write_text("#!/bin/bash\nprintf native-output\nexit 12\n")
    # Use the existing executable shell via a private helper; no grant/row/lock is created.
    command.chmod(0o700)
    ledger = tmp_path / "metadata"
    env = dict(
        os.environ,
        F=str(tmp_path),
        id="SYNTHETIC",
        gib="1",
        W="1",
        regs="0-23",
        LOOP_METRICS_LEDGER=str(ledger),
        LOOP_METRICS_HELPER=str(SCRIPT),
        SELF="fixture",
    )
    body = (
        'source "$1"; lm_start calendar-admission; trap lm_close EXIT\n'
        + block
        + '\nprintf "%s" "$r"\nexit "$rc"\n'
    )
    result = subprocess.run(
        [
            "/bin/bash",
            "-c",
            body,
            "fixture",
            str(ROOT / "scripts/coordination/loop_metrics_hook.sh"),
        ],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 12 and result.stdout == "native-output"
    report = events.fold([json.loads(l) for l in ledger.read_bytes().splitlines()])[0]
    assert report["attempt_phases"]["calendar-admission"]["failure_rate"] == 1


def test_exact_keeper_hook_records_actual_kernel_metadata_without_running_tick(
    tmp_path,
):
    hook = ROOT / "scripts/coordination/loop_metrics_hook.sh"
    block = "source " + str(hook) + "; lm_kernel_sample"
    ledger = tmp_path / "kernel"
    env = dict(
        os.environ, LOOP_METRICS_LEDGER=str(ledger), LOOP_METRICS_HELPER=str(SCRIPT)
    )
    result = subprocess.run(
        ["/bin/bash", "-uc", block + "\n" + block],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    rows = [json.loads(l) for l in ledger.read_bytes().splitlines()]
    assert len(rows) == 2 and len(rows[0]["idle_ticks"]) == 96
    assert events.fold_idle(rows)[0]["status"] == "observed"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["kernel"]


def test_nonregular_event_destination_refuses_without_blocking(tmp_path):
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(OSError):
        events.append(fifo, session()[0])


def test_dispatch_rc64_preserved_in_distinct_job_phase(tmp_path):
    hook = ROOT / "scripts/coordination/loop_metrics_hook.sh"
    ledger = tmp_path / "events"
    env = dict(
        os.environ,
        LOOP_METRICS_LEDGER=str(ledger),
        LOOP_METRICS_HELPER=str(SCRIPT),
        SELF="fixture",
    )
    body = 'source "$1"; lm_start; trap lm_close EXIT; lm_attempt_begin; lm_job_dispatched; LM_RESULT=64; lm_attempt_end 0; exit 64'
    result = subprocess.run(
        ["/bin/bash", "-c", body, "fixture", str(hook)],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 64
    report = events.fold([json.loads(l) for l in ledger.read_bytes().splitlines()])[0]
    assert report["status"] == "sealed"
    assert report["attempt_phases"]["launcher-admission"] == {
        "attempts": 1,
        "failures": 0,
        "failure_rate": 0,
    }
    assert report["attempt_phases"]["job-outcome"] == {
        "attempts": 1,
        "failures": 1,
        "failure_rate": 1,
    }


@pytest.mark.parametrize("enabled", [False, True])
def test_standalone_copied_launcher_needs_no_helper_and_preserves_exit_trap(
    tmp_path, enabled
):
    import shutil

    script = tmp_path / "filler_run12.sh"
    shutil.copyfile(ROOT / "scripts/coordination/filler_run12.sh", script)
    flags = tmp_path / "flags"
    flags.mkdir()
    sentinel = tmp_path / "exit-trap"
    bash_env = tmp_path / "bash-env"
    bash_env.write_text("trap 'printf owner-exit > \"$TEST_EXIT_SENTINEL\"' EXIT\n")
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("FILLER_", "LOOP_METRICS_", "BASH_ENV"))
    }
    env.update(
        FILLER_FLAGS_DIR=str(flags),
        FILLER_STATE_DIR=str(tmp_path / "state"),
        FILLERS_MD=str(tmp_path / "absent"),
        FILLER_RL=str(tmp_path / "never-called"),
        FILLER_GPU_LOCK=str(tmp_path / "gpu.lock"),
        BASH_ENV=str(bash_env),
        TEST_EXIT_SENTINEL=str(sentinel),
        LOOP_METRICS_HOOK=str(tmp_path / "missing-helper"),
    )
    if enabled:
        env["LOOP_METRICS_LEDGER"] = str(tmp_path / "metadata")
    done = subprocess.run(
        [
            "/bin/bash",
            str(script),
            "--id",
            "SYNTHETIC-STANDALONE",
            "--class",
            "cpu",
            "--cmd",
            "exit 99",
            "--stop",
            str(tmp_path / "STOP"),
            "--complete-cmd",
            "true",
            "--workdir",
            str(tmp_path),
        ],
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert done.returncode == 0, done.stderr
    assert sentinel.read_text() == "owner-exit"
    assert not (tmp_path / "metadata").exists()
    assert "No such file" not in done.stderr and "command not found" not in done.stderr
    if enabled:
        assert "existing EXIT trap preserved" in done.stderr
    else:
        assert not done.stderr


def test_standalone_copied_launcher_stop_refusal_never_dispatches_job(tmp_path):
    import datetime as dt
    import shutil
    import signal
    import time

    script = tmp_path / "filler_run12.sh"
    shutil.copyfile(ROOT / "scripts/coordination/filler_run12.sh", script)
    # Explicit SYNTHETIC admission boundary: no canonical grant, allocator or native compute.
    (tmp_path / "dryrun_check.py").write_text(
        'import sys\nraise SystemExit(0 if sys.argv[1]=="admit" else 99)\n'
    )
    flags = tmp_path / "flags"
    grants = flags / "grants"
    grants.mkdir(parents=True)
    stop = tmp_path / "STOP"
    stop.write_text("SYNTHETIC existing stop\n")
    now = dt.datetime.now(dt.timezone.utc)
    start = (now - dt.timedelta(seconds=10)).isoformat()
    end = (now + dt.timedelta(hours=1)).isoformat()
    rid = "SYNTHETIC-STANDALONE-STOP"
    (grants / (rid + ".grant")).write_text(f"regions=0-23 start={start} end={end}\n")
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("FILLER_", "LOOP_METRICS_", "BASH_ENV"))
    }
    env.update(
        FILLER_FLAGS_DIR=str(flags),
        FILLER_STATE_DIR=str(tmp_path / "state"),
        FILLERS_MD=str(tmp_path / "absent"),
        FILLER_RL=str(tmp_path / "must-never-run"),
        FILLER_GPU_LOCK=str(tmp_path / "gpu.lock"),
        FILLER_POLL="0.01",
    )
    payload = tmp_path / "payload-must-not-run"
    with (tmp_path / "stdout").open("w") as log:
        proc = subprocess.Popen(
            [
                "/bin/bash",
                str(script),
                "--id",
                rid,
                "--class",
                "cpu",
                "--cmd",
                "touch " + str(payload),
                "--stop",
                str(stop),
                "--workdir",
                str(tmp_path),
            ],
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        fd = os.pidfd_open(proc.pid)
        try:
            deadline = time.monotonic() + 5
            while not (grants / (rid + ".ended")).exists():
                assert proc.poll() is None
                if time.monotonic() > deadline:
                    raise AssertionError("native STOP branch not reached")
                time.sleep(0.01)
        finally:
            signal.pidfd_send_signal(fd, signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                signal.pidfd_send_signal(fd, signal.SIGKILL)
                proc.wait(timeout=3)
            os.close(fd)
    assert proc.returncode == 143
    assert "reason=stop-file-before-start" in (grants / (rid + ".ended")).read_text()
    assert stop.read_text() == "SYNTHETIC existing stop\n"
    assert not payload.exists() and not (tmp_path / "loop_metrics_hook.sh").exists()
    assert "command not found" not in (tmp_path / "stdout").read_text()
