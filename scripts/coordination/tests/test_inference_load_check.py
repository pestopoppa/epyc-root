#!/usr/bin/env python3
"""Tests for inference_load_check.py (B7 quiet-window detector).

All external tools (pgrep, rocm-smi) and /slots HTTP are mocked at the module's
subprocess/HTTP boundary — rocm-smi and pgrep may be absent in this env, so the
tests must never call them live. Exercises quiet vs serial_ok vs busy, plus the
conservative-on-missing-tool fallbacks.

Run:
    /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest \
        scripts/coordination/tests/test_inference_load_check.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import inference_load_check as ic  # noqa: E402


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class FakeProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


ROCM_IDLE = '{"card0": {"GPU use (%)": "0", "VRAM Total Used Memory (B)": "13094912"}}'
ROCM_BUSY_VRAM = (
    '{"card0": {"GPU use (%)": "0", "VRAM Total Used Memory (B)": "'
    + str(42 * 1024 ** 3)
    + '"}}'
)
ROCM_BUSY_UTIL = '{"card0": {"GPU use (%)": "97", "VRAM Total Used Memory (B)": "1000000"}}'
ROCM_JUNK = "not json at all"

_BENCH_KEY = "|".join(ic.BENCH_CLI_EVAL_PATTERNS)


def make_run(pgrep_map=None, rocm=None, rocm_missing=False):
    """Build a fake ic._run that routes by argv[0] and pgrep pattern (argv[-1])."""
    pgrep_map = pgrep_map or {}

    def _run(cmd, timeout=6.0):
        if cmd[0] == "pgrep":
            pattern = cmd[-1]
            if pattern not in pgrep_map:
                return FakeProc(returncode=1, stdout="")  # no match
            out = pgrep_map[pattern]
            if out is None:  # simulate pgrep unavailable for this call
                return None
            return FakeProc(returncode=0 if out else 1, stdout=out)
        if cmd[0] == "rocm-smi":
            if rocm_missing:
                return None
            return FakeProc(returncode=0, stdout=rocm or "")
        return None

    return _run


@pytest.fixture(autouse=True)
def _no_lock(monkeypatch):
    """Default: autopilot lock not held (real lock file irrelevant to unit tests)."""
    monkeypatch.setattr(ic, "_autopilot_lock_held", lambda *a, **k: False)


# --------------------------------------------------------------------------- #
# QUIET
# --------------------------------------------------------------------------- #
def test_quiet_when_all_clear(monkeypatch):
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_IDLE))
    quiet, reasons = ic.is_quiet_window()
    assert quiet is True
    assert reasons == []
    result = ic.classify_load()
    assert result["state"] == "quiet"
    assert result["busy_reasons"] == []


def test_quiet_with_idle_resident_server(monkeypatch):
    # A resident llama-server whose slots are all idle is not decode traffic.
    monkeypatch.setattr(
        ic, "_run",
        make_run(pgrep_map={"llama-server": "111 /usr/bin/llama-server --port 8080"},
                 rocm=ROCM_IDLE),
    )
    monkeypatch.setattr(ic, "_slots_active_count", lambda port, timeout: 0)
    quiet, reasons = ic.is_quiet_window()
    assert quiet is True, reasons
    assert ic.classify_load()["state"] == "quiet"


# --------------------------------------------------------------------------- #
# BUSY
# --------------------------------------------------------------------------- #
def test_busy_llama_decode(monkeypatch):
    monkeypatch.setattr(
        ic, "_run",
        make_run(pgrep_map={"llama-server": "111 /usr/bin/llama-server --port 8080"},
                 rocm=ROCM_IDLE),
    )
    monkeypatch.setattr(ic, "_slots_active_count", lambda port, timeout: 2)
    quiet, reasons = ic.is_quiet_window()
    assert quiet is False
    assert any("decoding" in r for r in reasons)
    assert ic.classify_load()["state"] == "busy"


def test_busy_bench_running(monkeypatch):
    monkeypatch.setattr(
        ic, "_run",
        make_run(pgrep_map={_BENCH_KEY: "222 /opt/llama/llama-bench -m foo.gguf"},
                 rocm=ROCM_IDLE),
    )
    result = ic.classify_load()
    assert result["state"] == "busy"
    assert any("bench" in r for r in result["busy_reasons"])


def test_busy_heavy_download(monkeypatch):
    monkeypatch.setattr(
        ic, "_run",
        make_run(pgrep_map={"aria2c": "333 aria2c https://hf.co/x/resolve/main/model.gguf"},
                 rocm=ROCM_IDLE),
    )
    result = ic.classify_load()
    assert result["state"] == "busy"
    assert any("download" in r for r in result["busy_reasons"])


def test_incidental_curl_is_not_a_download(monkeypatch):
    # curl to a health endpoint (no model marker) must NOT count as a download.
    monkeypatch.setattr(
        ic, "_run",
        make_run(pgrep_map={"curl": "444 curl http://localhost:8000/health"},
                 rocm=ROCM_IDLE),
    )
    assert ic.heavy_download_state()["running"] is False
    assert ic.classify_load()["state"] == "quiet"


def test_busy_mi210_util(monkeypatch):
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_BUSY_UTIL))
    assert ic.mi210_state()["occupied"] is True
    assert ic.classify_load()["state"] == "busy"


def test_busy_autopilot_process(monkeypatch):
    monkeypatch.setattr(
        ic, "_run",
        make_run(pgrep_map={"autopilot.py start": "555 python scripts/autopilot/autopilot.py start"},
                 rocm=ROCM_IDLE),
    )
    result = ic.classify_load()
    assert result["state"] == "busy"
    assert any("autopilot" in r for r in result["busy_reasons"])


def test_busy_autopilot_lock_held(monkeypatch):
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_IDLE))
    monkeypatch.setattr(ic, "_autopilot_lock_held", lambda *a, **k: True)
    assert ic.autopilot_state()["running"] is True
    assert ic.classify_load()["state"] == "busy"


# --------------------------------------------------------------------------- #
# SERIAL_OK / conservative-on-missing-tool
# --------------------------------------------------------------------------- #
def test_serial_ok_when_rocm_absent(monkeypatch):
    # rocm-smi absent ⇒ GPU unconfirmable ⇒ not quiet, but nothing positively busy.
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm_missing=True))
    quiet, reasons = ic.is_quiet_window()
    assert quiet is False
    assert any("MI210" in r and "unconfirmable" in r for r in reasons)
    result = ic.classify_load()
    assert result["state"] == "serial_ok"
    assert result["busy_reasons"] == []


def test_serial_ok_when_rocm_unparseable(monkeypatch):
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_JUNK))
    assert ic.mi210_state()["confirmable"] is False
    assert ic.classify_load()["state"] == "serial_ok"


def test_serial_ok_when_server_present_but_unprobeable(monkeypatch):
    # Resident server, /slots unreachable ⇒ unconfirmed decode ⇒ not quiet, not busy.
    monkeypatch.setattr(
        ic, "_run",
        make_run(pgrep_map={"llama-server": "111 /usr/bin/llama-server --port 8080"},
                 rocm=ROCM_IDLE),
    )
    monkeypatch.setattr(ic, "_slots_active_count", lambda port, timeout: None)
    quiet, reasons = ic.is_quiet_window()
    assert quiet is False
    assert any("unconfirmed" in r for r in reasons)
    assert ic.classify_load()["state"] == "serial_ok"


def test_conservative_when_pgrep_missing(monkeypatch):
    # Every pgrep call returns None (tool unavailable). GPU idle & confirmable.
    def _run(cmd, timeout=6.0):
        if cmd[0] == "pgrep":
            return None
        if cmd[0] == "rocm-smi":
            return FakeProc(returncode=0, stdout=ROCM_IDLE)
        return None

    monkeypatch.setattr(ic, "_run", _run)
    quiet, reasons = ic.is_quiet_window()
    assert quiet is False
    assert any("pgrep unavailable" in r for r in reasons)
    result = ic.classify_load()
    # No positive competitor could be observed ⇒ serial_ok, never a false "quiet".
    assert result["state"] == "serial_ok"
    assert result["busy_reasons"] == []


def test_no_llama_processes_state_none(monkeypatch):
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_IDLE))
    assert ic.llama_decode_state()["state"] == "none"


def test_signals_are_json_serializable(monkeypatch):
    import json

    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_IDLE))
    result = ic.classify_load()
    json.dumps(result)  # must not raise
    assert set(result) >= {"ts", "state", "quiet", "quiet_blockers", "busy_reasons", "signals"}


# --------------------------------------------------------------------------- #
# CLI exit codes
# --------------------------------------------------------------------------- #
def test_cli_exit_codes(monkeypatch):
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_IDLE))
    assert ic.main(["--require", "quiet"]) == 0
    assert ic.main([]) == 0  # quiet ⇒ 0

    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm_missing=True))
    assert ic.main(["--require", "quiet"]) == 1     # serial_ok fails quiet gate
    assert ic.main(["--require", "serial_ok"]) == 0  # serial_ok passes serial gate
    assert ic.main([]) == 10                          # serial_ok bare exit code


# --------------------------------------------------------------------------- #
# C1 — autopilot SUPERVISOR detection (liveness signal during restart delay)
# --------------------------------------------------------------------------- #
def test_c1_supervisor_process_counts_as_running(monkeypatch):
    # Only the supervisor is live (main loop absent during its <=30s restart delay).
    monkeypatch.setattr(
        ic, "_run",
        make_run(
            pgrep_map={
                "autopilot_supervisor.py": "999 python scripts/autopilot/autopilot_supervisor.py",
            },
            rocm=ROCM_IDLE,
        ),
    )
    st = ic.autopilot_state()
    assert st["running"] is True
    assert 999 in st["pids"]
    assert st["detail"] == "running"
    assert ic.classify_load()["state"] == "busy"


def test_c1_supervisor_and_loop_both_counted(monkeypatch):
    monkeypatch.setattr(
        ic, "_run",
        make_run(
            pgrep_map={
                "autopilot.py start": "555 python scripts/autopilot/autopilot.py start",
                "autopilot_supervisor.py": "999 python scripts/autopilot/autopilot_supervisor.py",
            },
            rocm=ROCM_IDLE,
        ),
    )
    st = ic.autopilot_state()
    assert st["running"] is True
    assert st["pids"] == [555, 999]  # sorted, de-duplicated


def test_c1_no_autopilot_processes_is_stopped(monkeypatch):
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_IDLE))
    st = ic.autopilot_state()
    assert st["running"] is False
    assert st["detail"] == "stopped"


# --------------------------------------------------------------------------- #
# M4 (2026-08-12) — RESIDENCY IS NOT WORK
#
# `mi210_state()` used to OR utilisation with VRAM residency into one `occupied`
# boolean. A loaded-but-idle model therefore read BUSY, and the coordinator daemon
# rejected every queued lane row behind it — 572 `lane cpu busy` rejections and a
# 3h47m window at zero compute on the night of 2026-08-11/12.
#
# `test_busy_mi210_vram` used to live here asserting `state == "busy"` for exactly
# this input. It was DELETED, not adjusted: it pinned the defect. Its replacement
# is `test_m4_resident_vram_is_parked_not_busy` below, which asserts the opposite.
#
# The compliant-path controls are as load-bearing as the bites: a legitimately busy
# device must still read BUSY (`test_m4_util_above_floor_is_still_busy`,
# `test_m4_decode_on_a_resident_device_is_busy`), and no unreadable probe may ever
# read FREE (`test_m4_unreadable_probe_is_unknown_never_free`).
# --------------------------------------------------------------------------- #
ROCM_RESIDENT = ROCM_BUSY_VRAM                      # 42 GB held, 0% utilisation
ROCM_MIXED = (
    '{"card0": {"GPU use (%)": "0", "VRAM Total Used Memory (B)": "13094912"},'
    ' "card1": {"GPU use (%)": "0", "VRAM Total Used Memory (B)": "'
    + str(42 * 1024 ** 3) + '"}}'
)
ROCM_NO_CARDS = '{"system": "not a card dict"}'


def test_m4_resident_vram_is_parked_not_busy(monkeypatch):
    """THE CENTRAL ASSERTION. 42 GB resident, 0% utilisation ⇒ RESIDENT, not BUSY."""
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_RESIDENT))
    gpu = ic.mi210_state()
    assert gpu["device_state"] == ic.DEVICE_RESIDENT
    assert gpu["util_occupied"] is False
    assert gpu["vram_resident"] is True

    result = ic.classify_load()
    assert result["state"] == "parked"
    assert result["busy_reasons"] == []          # nothing is working
    assert result["parked_reasons"]              # and the reason is named


def test_m4_occupied_key_is_unchanged_for_pre_split_callers(monkeypatch):
    """`occupied` stays the OR, so nothing that predates the split changes meaning."""
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_RESIDENT))
    assert ic.mi210_state()["occupied"] is True
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_BUSY_UTIL))
    assert ic.mi210_state()["occupied"] is True
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_IDLE))
    assert ic.mi210_state()["occupied"] is False


def test_m4_util_above_floor_is_still_busy(monkeypatch):
    """COMPLIANT PATH: a legitimately busy device must still read BUSY."""
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_BUSY_UTIL))
    gpu = ic.mi210_state()
    assert gpu["device_state"] == ic.DEVICE_BUSY
    assert gpu["util_occupied"] is True
    result = ic.classify_load()
    assert result["state"] == "busy"
    assert result["parked_reasons"] == []
    assert any("MI210" in r for r in result["busy_reasons"])


def test_m4_decode_on_a_resident_device_is_busy(monkeypatch):
    """COMPLIANT PATH: residency + a decoding slot is WORK. `parked` must not win."""
    monkeypatch.setattr(
        ic, "_run",
        make_run(pgrep_map={"llama-server": "111 /usr/bin/llama-server --port 8080"},
                 rocm=ROCM_RESIDENT),
    )
    monkeypatch.setattr(ic, "_slots_active_count", lambda port, timeout: 3)
    result = ic.classify_load()
    assert result["state"] == "busy"
    assert result["parked_reasons"] == []


def test_m4_free_device_is_free(monkeypatch):
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_IDLE))
    assert ic.mi210_state()["device_state"] == ic.DEVICE_FREE
    assert ic.classify_load()["state"] == "quiet"


def test_m4_any_resident_card_makes_the_device_resident(monkeypatch):
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_MIXED))
    gpu = ic.mi210_state()
    assert gpu["device_state"] == ic.DEVICE_RESIDENT
    assert gpu["cards"]["card0"]["vram_resident"] is False
    assert gpu["cards"]["card1"]["vram_resident"] is True


def test_m4_unreadable_probe_is_unknown_never_free(monkeypatch):
    """FAIL CLOSED. Every unreadable path is `unknown`; none may read `free`."""
    for kwargs in ({"rocm_missing": True}, {"rocm": ROCM_JUNK},
                   {"rocm": ROCM_NO_CARDS}, {"rocm": ""}):
        monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, **kwargs))
        gpu = ic.mi210_state()
        assert gpu["device_state"] == ic.DEVICE_UNKNOWN, kwargs
        assert gpu["device_state"] not in (ic.DEVICE_FREE, ic.DEVICE_RESIDENT), kwargs
        assert gpu["occupied"] is None, kwargs
        assert gpu["confirmable"] is False, kwargs
        assert ic.classify_load()["state"] == "serial_ok", kwargs


def test_m4_resident_with_an_unconfirmed_probe_stays_serial_ok(monkeypatch):
    """`parked` is a POSITIVE claim; an unconfirmed probe forfeits it.

    Resident VRAM plus a missing pgrep means "something is loaded AND I cannot
    see the process table". That is `serial_ok` ("cannot confirm"), not the
    specific `parked`. Both admit the same work, so this costs nothing and keeps
    the label honest.
    """
    def _run(cmd, timeout=6.0):
        if cmd[0] == "pgrep":
            return None
        if cmd[0] == "rocm-smi":
            return FakeProc(returncode=0, stdout=ROCM_RESIDENT)
        return None

    monkeypatch.setattr(ic, "_run", _run)
    result = ic.classify_load()
    assert ic.mi210_state()["device_state"] == ic.DEVICE_RESIDENT
    assert result["state"] == "serial_ok"
    assert result["parked_reasons"] == []


def test_m4_parked_still_blocks_quiet(monkeypatch):
    """Nothing that would LOAD a model is newly permitted by M4."""
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_RESIDENT))
    quiet, reasons = ic.is_quiet_window()
    assert quiet is False
    assert any(r.startswith(ic._MI210_RESIDENT_BLOCKER) for r in reasons)
    assert ic.main(["--require", "quiet"]) == 1


def test_m4_parked_exit_codes(monkeypatch):
    """`parked` gets its own bare exit code and passes the serial_ok gate."""
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_RESIDENT))
    assert ic.main([]) == 15
    assert ic.main(["--require", "serial_ok"]) == 0
    assert ic.main(["--require", "quiet"]) == 1
    # ...and a genuinely busy device is still refused by BOTH gates.
    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_BUSY_UTIL))
    assert ic.main([]) == 20
    assert ic.main(["--require", "serial_ok"]) == 1
    assert ic.main(["--require", "quiet"]) == 1


def test_m4_result_is_json_serializable(monkeypatch):
    import json as _json

    monkeypatch.setattr(ic, "_run", make_run(pgrep_map={}, rocm=ROCM_RESIDENT))
    _json.dumps(ic.classify_load())
