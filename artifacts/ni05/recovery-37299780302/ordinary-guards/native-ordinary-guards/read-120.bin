#!/usr/bin/env python3
"""SS-BENCH-GATE-b — the launcher must not SPAWN onto a live bench's cores.

The bench's campaign-continuity gate keys on CORE OVERLAP between the bench's
pinned cores and any foreign process's threads. `guard_against_running_bench`
(a) refuses lifecycle actions while a bench is detectable; this suite covers
the durable half (b): the placement guard reads the bench's REAL core claim
from the live processes and refuses overlapping spawns or pins default-affinity
spawns (the incident's sidecar shape) to a non-overlapping subset.

The parsing and decision logic are pure (no live processes): /proc reading is
behind an injectable proc_root/detect seam, and the placement decision takes
(placement, claim) directly.
"""

from __future__ import annotations

import subprocess
import sys
from argparse import Namespace
from pathlib import Path

import pytest

import scripts.server.bench_core_claim as bcc
import scripts.server.orchestrator_stack as stack
import scripts.server.stack_commands as sc

from scripts.server.bench_core_claim import (
    EMPTY_BENCH_CLAIM,
    BenchClaim,
    BenchObservationError,
    BenchPlacementRefusal,
    decide_placement,
    detect_running_cpu_bench,
    enforce_placement,
    format_cpu_list,
    host_core_set,
    is_bench_process,
    parse_cpu_list,
    placement_overlaps,
    read_bench_claim,
)

BENCH_PROC = ((4242, "python laguna_q4_cpu_bench_runner.py --run"),)


def _claim(*ranges: tuple[int, int], unobservable: bool = False) -> BenchClaim:
    cores: set[int] = set()
    for start, end in ranges:
        cores.update(range(start, end + 1))
    return BenchClaim(
        unobservable=unobservable,
        cores=frozenset(cores),
        procs=BENCH_PROC,
    )


def _fake_proc_tree(tmp_path: Path, pid: int, main: str, threads: dict[str, str]) -> Path:
    """A /proc-like tree for one pid: status + task/<tid>/status per thread."""
    pdir = tmp_path / str(pid)
    pdir.mkdir(parents=True, exist_ok=True)
    (pdir / "status").write_text(f"Cpus_allowed_list:\t{main}\n")
    task = pdir / "task"
    for tid, cpu_list in threads.items():
        (task / tid).mkdir(parents=True)
        (task / tid / "status").write_text(f"Cpus_allowed_list:\t{cpu_list}\n")
    return tmp_path


# --------------------------------------------------------------------------- #
# Pure parsing: Linux Cpus_allowed_list syntax, mirroring the bench runner
# --------------------------------------------------------------------------- #


def test_parse_cpu_list_single_range() -> None:
    assert parse_cpu_list("0-95") == set(range(96))


def test_parse_cpu_list_multiple_ranges() -> None:
    assert parse_cpu_list("0-23,96-119") == set(range(24)) | set(range(96, 120))


def test_parse_cpu_list_single_cpu() -> None:
    assert parse_cpu_list("4") == {4}


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "abc",
        "0-5,",
        "0-5,9-",
        "8-4",
        "0-5,x",
        "1-2-3",
        " 0-5",
        "0-5 ",
    ],
)
def test_parse_cpu_list_refuses_malformed(bad: str) -> None:
    with pytest.raises(BenchObservationError):
        parse_cpu_list(bad)


def test_format_cpu_list_folds_ranges() -> None:
    assert format_cpu_list({0, 1, 2, 96, 97}) == "0-2,96-97"


def test_format_cpu_list_single_cpu() -> None:
    assert format_cpu_list({4}) == "4"


def test_format_cpu_list_full_range() -> None:
    assert format_cpu_list(set(range(96))) == "0-95"


def test_placement_overlaps_detects_intersection() -> None:
    assert placement_overlaps("48-95", set(range(96)))
    assert not placement_overlaps("96-191", set(range(96)))


def test_placement_overlaps_refuses_malformed_placement() -> None:
    with pytest.raises(BenchObservationError):
        placement_overlaps("bogus", set(range(96)))


# --------------------------------------------------------------------------- #
# Detection predicate — single source of truth, shared with (a)
# --------------------------------------------------------------------------- #


def test_is_bench_process_matches_driver_names() -> None:
    assert is_bench_process("python laguna_q4_cpu_bench_runner.py --run")
    assert is_bench_process("python x_bench_runner.py")
    assert is_bench_process("/usr/bin/llama-bench -m /models/q4.gguf")
    assert is_bench_process("python v7_quality_gate_runner.py")
    assert is_bench_process("python run_e8_quality_baseline_reseed.py")


def test_is_bench_process_excludes_supervisors_naming_a_bench() -> None:
    assert not is_bench_process("/usr/local/bin/earlyoom --prefer ^llama-bench$")
    assert not is_bench_process("python orchestrator_stack.py status")


def test_detection_uses_executable_or_script_not_author_prompt(monkeypatch) -> None:
    prompt = "Implement CPU source. Do not run llama-bench or laguna_q4_cpu_bench_runner.py."
    commands = [
        ("node /usr/local/share/npm-global/bin/codex exec -C /lane " + prompt, False),
        ("/opt/codex/bin/codex exec -C /lane " + prompt, False),
        ("python3 ordinary_actor.py " + prompt, False),
        ("/usr/local/bin/earlyoom --prefer ^llama-bench$", False),
        ("/build/bin/llama-bench -m /models/q4.gguf --note earlyoom", True),
        ("/venv/bin/python3 -u -X dev -W ignore /r/laguna_q4_cpu_bench_runner.py --run", True),
        ("python3 -- /r/x_bench_runner.py --run", True),
        ("python /r/v7_quality_gate_runner.py", True),
        ("python /r/run_e8_quality_baseline_reseed.py", True),
        ("bash -c 'python laguna_q4_cpu_bench_runner.py'", True),
        ("taskset -c 0-95 /build/bin/llama-bench -m /model", True),
        ("python -c 'import runpy; runpy.run_path(\"bench_runner.py\")'", True),
    ]
    for command, expected in commands:
        assert is_bench_process(command) is expected, command
    output = "PID COMMAND\n" + "\n".join(
        f"{200 + index} {command}" for index, (command, _) in enumerate(commands)
    )
    monkeypatch.setattr(bcc.subprocess, "run", lambda *_a, **_k:
                        subprocess.CompletedProcess([], 0, stdout=output, stderr=""))
    assert [pid for pid, _ in detect_running_cpu_bench()] == [
        200 + index for index, (_, expected) in enumerate(commands) if expected
    ]


def test_detect_running_cpu_bench_skips_probe_and_supervisors(monkeypatch) -> None:
    out = subprocess.CompletedProcess(
        [],
        0,
        stdout=(
            "PID COMMAND\n"
            "100 python laguna_q4_cpu_bench_runner.py --run\n"
            "101 /usr/bin/llama-bench -m /models/q4.gguf\n"
            "102 /usr/local/bin/earlyoom --prefer ^llama-bench$\n"
            "103 python orchestrator_stack.py status\n"
            "104 python v7_quality_gate_runner.py\n"
        ),
        stderr="",
    )
    monkeypatch.setattr(bcc.subprocess, "run", lambda *_a, **_k: out)
    found = detect_running_cpu_bench()
    assert [pid for pid, _cmd in found] == [100, 101, 104]


# --------------------------------------------------------------------------- #
# Reading the claim from a live process (injectable /proc seam)
# --------------------------------------------------------------------------- #


def test_read_bench_claim_no_bench_is_empty(tmp_path: Path) -> None:
    claim = read_bench_claim(proc_root=tmp_path, detect=lambda: [])
    assert claim.empty
    assert claim is EMPTY_BENCH_CLAIM


def test_read_bench_claim_unions_main_and_threads(tmp_path: Path) -> None:
    root = _fake_proc_tree(tmp_path, 4242, main="0-95", threads={"4242": "0-95", "5000": "0-47"})
    claim = read_bench_claim(proc_root=root, detect=lambda: list(BENCH_PROC))
    assert not claim.empty and not claim.unobservable
    assert claim.cores == frozenset(range(96))


def test_read_bench_claim_unions_across_drivers(tmp_path: Path) -> None:
    root = _fake_proc_tree(tmp_path, 4242, main="0-47", threads={"4242": "0-47"})
    root = _fake_proc_tree(root, 9999, main="96-119", threads={"9999": "96-119"})
    claim = read_bench_claim(
        proc_root=root,
        detect=lambda: [
            (4242, "python laguna_q4_cpu_bench_runner.py --run"),
            (9999, "python v7_quality_gate_runner.py"),
        ],
    )
    assert claim.cores == frozenset(range(48)) | frozenset(range(96, 120))


def test_read_bench_claim_malformed_thread_list_is_unobservable(tmp_path: Path) -> None:
    root = _fake_proc_tree(tmp_path, 4242, main="0-95", threads={"4242": "0-95", "5000": "bogus"})
    claim = read_bench_claim(proc_root=root, detect=lambda: list(BENCH_PROC))
    assert claim.unobservable


def test_read_bench_claim_descending_range_is_unobservable(tmp_path: Path) -> None:
    root = _fake_proc_tree(tmp_path, 4242, main="95-0", threads={"4242": "95-0"})
    claim = read_bench_claim(proc_root=root, detect=lambda: list(BENCH_PROC))
    assert claim.unobservable


def test_read_bench_claim_missing_status_is_unobservable(tmp_path: Path) -> None:
    root = _fake_proc_tree(tmp_path, 4242, main="0-95", threads={"4242": "0-95", "5000": "0-47"})
    (root / "4242" / "task" / "5000" / "status").unlink()
    claim = read_bench_claim(proc_root=root, detect=lambda: list(BENCH_PROC))
    assert claim.unobservable


def test_read_bench_claim_vanished_pid_is_unobservable(tmp_path: Path) -> None:
    claim = read_bench_claim(proc_root=tmp_path, detect=lambda: list(BENCH_PROC))
    assert claim.unobservable


def test_read_bench_claim_thread_churn_is_unobservable(tmp_path: Path, monkeypatch) -> None:
    root = _fake_proc_tree(tmp_path, 4242, main="0-95", threads={"4242": "0-95"})
    calls = {"n": 0}

    def flaky_list_tids(task_dir: Path) -> list[str]:
        calls["n"] += 1
        return ["4242"] if calls["n"] == 1 else ["4242", "9999"]

    monkeypatch.setattr(bcc, "_list_task_tids", flaky_list_tids)
    claim = read_bench_claim(proc_root=root, detect=lambda: list(BENCH_PROC))
    assert claim.unobservable


# --------------------------------------------------------------------------- #
# Pure placement decision — (placement, claim) in, kind out
# --------------------------------------------------------------------------- #


def test_empty_claim_proceeds_with_explicit_placement() -> None:
    kind, effective, _reason = decide_placement("48-95", force=False, claim=EMPTY_BENCH_CLAIM)
    assert (kind, effective) == ("proceed", None)


def test_empty_claim_proceeds_with_default_affinity() -> None:
    kind, effective, _reason = decide_placement(None, force=False, claim=EMPTY_BENCH_CLAIM)
    assert (kind, effective) == ("proceed", None)


def test_bench_claiming_0_95_refuses_placement_48_95() -> None:
    kind, _effective, reason = decide_placement("48-95", force=False, claim=_claim((0, 95)))
    assert kind == "refuse"
    assert "0-95" in reason


def test_bench_claiming_0_95_allows_placement_96_191() -> None:
    kind, effective, _reason = decide_placement("96-191", force=False, claim=_claim((0, 95)))
    assert (kind, effective) == ("proceed", None)


def test_bench_claiming_0_95_refuses_whole_host_placement() -> None:
    kind, _effective, _reason = decide_placement("0-191", force=False, claim=_claim((0, 95)))
    assert kind == "refuse"


def test_overlapping_placement_bypasses_with_force() -> None:
    kind, effective, _reason = decide_placement("48-95", force=True, claim=_claim((0, 95)))
    assert (kind, effective) == ("proceed", None)


def test_unobservable_claim_refuses_explicit_placement() -> None:
    kind, _effective, reason = decide_placement(
        "96-191", force=False, claim=_claim(unobservable=True)
    )
    assert kind == "refuse"
    assert "unobservable" in reason


def test_unobservable_claim_refuses_default_affinity() -> None:
    kind, _effective, _reason = decide_placement(None, force=False, claim=_claim(unobservable=True))
    assert kind == "refuse"


def test_unobservable_claim_bypasses_with_force() -> None:
    kind, effective, _reason = decide_placement(None, force=True, claim=_claim(unobservable=True))
    assert (kind, effective) == ("proceed", None)


def test_malformed_declared_placement_refuses() -> None:
    kind, _effective, reason = decide_placement("bogus", force=False, claim=_claim((0, 95)))
    assert kind == "refuse"
    assert "cannot be parsed" in reason


def test_malformed_declared_placement_bypasses_with_force() -> None:
    kind, effective, _reason = decide_placement("bogus", force=True, claim=_claim((0, 95)))
    assert (kind, effective) == ("proceed", None)


def test_default_affinity_pins_off_claim() -> None:
    kind, effective, _reason = decide_placement(
        None,
        force=False,
        claim=_claim((0, 95)),
        host_cores=frozenset(range(192)),
    )
    assert (kind, effective) == ("pin", "96-191")


def test_default_affinity_pins_off_partial_claim() -> None:
    kind, effective, _reason = decide_placement(
        None,
        force=False,
        claim=_claim((48, 143)),
        host_cores=frozenset(range(192)),
    )
    assert (kind, effective) == ("pin", "0-47,144-191")


def test_default_affinity_refuses_when_bench_claims_every_host_core() -> None:
    kind, _effective, reason = decide_placement(
        None, force=False, claim=_claim((0, 191)), host_cores=frozenset(range(192))
    )
    assert kind == "refuse"
    assert "every host core" in reason


def test_default_affinity_refuses_when_host_set_unknown() -> None:
    kind, _effective, reason = decide_placement(
        None, force=False, claim=_claim((0, 95)), host_cores=None
    )
    assert kind == "refuse"
    assert "host core set unknown" in reason


def test_default_affinity_pins_even_with_force() -> None:
    kind, effective, _reason = decide_placement(
        None,
        force=True,
        claim=_claim((0, 95)),
        host_cores=frozenset(range(192)),
    )
    assert (kind, effective) == ("pin", "96-191")


def test_default_affinity_no_fallback_bypasses_with_force() -> None:
    kind, effective, _reason = decide_placement(
        None, force=True, claim=_claim((0, 191)), host_cores=frozenset(range(192))
    )
    assert (kind, effective) == ("proceed", None)


# --------------------------------------------------------------------------- #
# enforce_placement — the launcher-facing entry point
# --------------------------------------------------------------------------- #


def test_enforce_placement_refusal_prints_incident_context_and_raises(capsys) -> None:
    with pytest.raises(BenchPlacementRefusal):
        enforce_placement(
            "48-95",
            force=False,
            label="llama-server for frontdoor",
            claim=_claim((0, 95)),
        )
    out = capsys.readouterr().out
    assert "REFUSING to spawn llama-server for frontdoor" in out
    assert "requested placement 48-95 overlaps CPU bench cores 0-95" in out
    assert "PID 4242" in out
    assert "2026-07-27" in out


def test_enforce_placement_unobservable_prints_and_raises(capsys) -> None:
    with pytest.raises(BenchPlacementRefusal):
        enforce_placement(None, force=False, label="sidecar", claim=_claim(unobservable=True))
    assert "REFUSING to spawn sidecar" in capsys.readouterr().out


def test_enforce_placement_pins_default_affinity_off_claim(capsys) -> None:
    pinned = enforce_placement(
        None,
        force=False,
        label="orchestrator API (uvicorn)",
        claim=_claim((0, 95)),
        host_cores=frozenset(range(192)),
    )
    assert pinned == "96-191"
    assert "Pinning orchestrator API (uvicorn) to cores 96-191" in capsys.readouterr().out


def test_enforce_placement_refuses_when_host_set_unreadable(capsys, tmp_path: Path) -> None:
    with pytest.raises(BenchPlacementRefusal):
        enforce_placement(
            None,
            force=False,
            label="sidecar",
            claim=_claim((0, 95)),
            online_path=tmp_path / "missing-online",
        )
    assert "REFUSING to spawn sidecar" in capsys.readouterr().out


def test_enforce_placement_proceeds_when_no_bench(capsys) -> None:
    result = enforce_placement("48-95", force=False, label="x", claim=EMPTY_BENCH_CLAIM)
    assert result is None
    assert capsys.readouterr().out == ""


def test_host_core_set_reads_sys_online(tmp_path: Path) -> None:
    online = tmp_path / "online"
    online.write_text("0-191\n")
    assert host_core_set(online) == frozenset(range(192))


def test_host_core_set_unreadable_is_none(tmp_path: Path) -> None:
    assert host_core_set(tmp_path / "missing") is None


# --------------------------------------------------------------------------- #
# Integration: orchestrator_stack guarded prefix + CLI wiring
# --------------------------------------------------------------------------- #


def test_guarded_numa_prefix_passes_through_when_bench_free(monkeypatch) -> None:
    monkeypatch.setattr(stack, "_numa_prefix", lambda role, idx: ["taskset", "-c", "0-95"])
    monkeypatch.setattr(stack, "enforce_placement", lambda *_a, **_k: None)
    assert stack._bench_guarded_numa_prefix("frontdoor", 0, bench_force=False) == [
        "taskset",
        "-c",
        "0-95",
    ]


def test_guarded_numa_prefix_pins_default_affinity(monkeypatch) -> None:
    monkeypatch.setattr(stack, "_numa_prefix", lambda role, idx: [])
    monkeypatch.setattr(stack, "enforce_placement", lambda *_a, **_k: "96-191")
    assert stack._bench_guarded_numa_prefix("embedder", 0, bench_force=False) == [
        "taskset",
        "-c",
        "96-191",
    ]


def test_guarded_numa_prefix_refusal_propagates(monkeypatch) -> None:
    monkeypatch.setattr(stack, "_numa_prefix", lambda role, idx: ["taskset", "-c", "48-95"])

    def _refuse(*_a, **_k):
        raise BenchPlacementRefusal()

    monkeypatch.setattr(stack, "enforce_placement", _refuse)
    with pytest.raises(BenchPlacementRefusal):
        stack._bench_guarded_numa_prefix("frontdoor", 0, bench_force=False)


def test_guarded_numa_prefix_forwards_force_to_enforce_placement(monkeypatch) -> None:
    monkeypatch.setattr(stack, "_numa_prefix", lambda role, idx: ["taskset", "-c", "48-95"])
    captured: dict[str, object] = {}

    def fake_enforce(placement, **_k):
        captured["placement"] = placement
        captured.update(_k)
        return None

    monkeypatch.setattr(stack, "enforce_placement", fake_enforce)
    stack._bench_guarded_numa_prefix("frontdoor", 0, bench_force=True, label="wrapped")
    assert captured["force"] is True
    assert captured["placement"] == "48-95"
    assert captured["label"] == "wrapped"


def test_placement_from_prefix_shapes() -> None:
    assert stack._placement_from_prefix(["taskset", "-c", "0-95"]) == "0-95"
    assert (
        stack._placement_from_prefix(["numactl", "--interleave=all", "--", "taskset", "-c", "0-95"])
        == "0-95"
    )
    assert stack._placement_from_prefix([]) is None
    with pytest.raises(BenchPlacementRefusal):
        stack._placement_from_prefix(["taskset"])


def test_main_returns_2_on_bench_placement_refusal(monkeypatch) -> None:
    """The per-spawn refusal maps to exit 2, same as the CLI-level guard."""

    def _refuse(_args):
        raise BenchPlacementRefusal()

    monkeypatch.setattr(sc, "cmd_reload", _refuse, raising=True)
    monkeypatch.setattr(stack, "guard_against_running_bench", lambda *_a, **_k: True, raising=True)
    monkeypatch.setattr(sys, "argv", ["orchestrator_stack.py", "reload", "orchestrator"])
    assert stack.main() == 2


def test_cmd_reload_forwards_allow_during_bench_as_bench_force(monkeypatch) -> None:
    """--allow-during-bench must reach start_server as bench_force.

    Without this the flag would be inert at the per-spawn layer: the CLI-level
    guard lets the command through, then the placement guard would refuse every
    overlapping spawn anyway.
    """
    entry = next(server for server in sc.HOT_SERVERS + sc.WARM_SERVERS if server["port"] == 8080)
    captured: dict[str, object] = {}
    new_info = stack.ProcessInfo(
        role=entry["roles"][0],
        pid=222,
        port=8080,
        started_at="after",
        model_path="new",
        log_file="new.log",
    )

    monkeypatch.setattr(sc, "load_state", lambda: {})
    monkeypatch.setattr(sc, "save_state", lambda _value: None)
    monkeypatch.setattr(sc, "_refresh_runtime_facts_manifest", lambda *_a, **_k: None)
    monkeypatch.setattr(sc, "kill_process", lambda _pid: None)
    monkeypatch.setattr(sc.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(sc, "_pids_on_port", lambda _port: [])
    monkeypatch.setattr(sc, "RegistryLoader", lambda: object())

    def fake_start_server(port, roles, registry, *args, **kwargs):
        captured["bench_force"] = kwargs.get("bench_force")
        return new_info

    monkeypatch.setattr(sc, "start_server", fake_start_server)

    rc = sc.cmd_reload(Namespace(components=["server_8080"], allow_during_bench=True))
    assert rc == 0
    assert captured["bench_force"] is True


def test_cmd_reload_defaults_bench_force_to_false(monkeypatch) -> None:
    """Without --allow-during-bench the per-spawn guard must NOT bypass."""
    entry = next(server for server in sc.HOT_SERVERS + sc.WARM_SERVERS if server["port"] == 8080)
    captured: dict[str, object] = {}
    new_info = stack.ProcessInfo(
        role=entry["roles"][0],
        pid=222,
        port=8080,
        started_at="after",
        model_path="new",
        log_file="new.log",
    )

    monkeypatch.setattr(sc, "load_state", lambda: {})
    monkeypatch.setattr(sc, "save_state", lambda _value: None)
    monkeypatch.setattr(sc, "_refresh_runtime_facts_manifest", lambda *_a, **_k: None)
    monkeypatch.setattr(sc, "kill_process", lambda _pid: None)
    monkeypatch.setattr(sc.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(sc, "_pids_on_port", lambda _port: [])
    monkeypatch.setattr(sc, "RegistryLoader", lambda: object())

    def fake_start_server(port, roles, registry, *args, **kwargs):
        captured["bench_force"] = kwargs.get("bench_force")
        return new_info

    monkeypatch.setattr(sc, "start_server", fake_start_server)

    rc = sc.cmd_reload(Namespace(components=["server_8080"]))
    assert rc == 0
    assert captured["bench_force"] is False
