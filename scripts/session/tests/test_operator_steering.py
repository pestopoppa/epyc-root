"""Tests for the operator-steering scripts (idle_alarm, status_digest, pending_operator_cmds, recheck_blocker).

Run: python3 -m pytest scripts/session/tests/test_operator_steering.py -q   (no compute, no live flags dir)
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import idle_alarm as IA  # noqa: E402
import pending_operator_cmds as POC  # noqa: E402
import recheck_blocker as RB  # noqa: E402
import status_digest as SD  # noqa: E402

T0 = 1_795_000_000  # arbitrary epoch


def _ts(t):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(free_per_tick, util="q0=1% q1=60% q2=1% q3=1% gpu=0%", step=150, extra=""):
    lines = []
    for i, free in enumerate(free_per_tick):
        t = _ts(T0 + i * step)
        lines.append(f"{t} SNAPSHOT free={free} busy=q1:rowx cands=3 assigned=0 lanes cpu=3 gpu=6 util {util} vram=0%")
        lines.append(f"{t} IDLE-WHY q0: grant big-row needs q0,q1,q2: q1 busy")
        lines.append(f"{t} IDLE-WHY gpu-quiet: {extra or 'no runnable row'}")
    return "\n".join(lines), T0 + (len(free_per_tick) - 1) * step


Q_CPU = {"buckets": {"GRANTABLE": [{"id": "big-row", "shape": "multi-quarter(3)"}], "RUNNING": []}}
Q_GPU = {"buckets": {"GRANTABLE": [{"id": "g1", "shape": "gpu-q3"}], "RUNNING": []}}


# ---------------------------------------------------------------- idle_alarm
def test_alarm_fires_after_5_min_with_ready_row_and_copies_idle_why():
    text, now = _log(["q0,q2"] * 4)  # 3 gaps x 150 s = 450 s > 300
    snaps, why, _ = IA.parse_log(text)
    r = IA.evaluate(snaps, why, Q_CPU, now=now)
    regs = {a["region"] for a in r["alarms"]}
    assert r["alarm"] and regs == {"q0", "q2"}
    a = next(a for a in r["alarms"] if a["region"] == "q0")
    assert "IDLE-WHY q0: grant big-row needs q0,q1,q2" in a["reason"]


def test_no_alarm_under_threshold_or_without_ready_rows():
    text, now = _log(["q0"] * 2)  # 150 s
    snaps, why, _ = IA.parse_log(text)
    assert not IA.evaluate(snaps, why, Q_CPU, now=now)["alarm"]
    text, now = _log(["q0"] * 5)
    snaps, why, _ = IA.parse_log(text)
    assert not IA.evaluate(snaps, why, {"buckets": {"GRANTABLE": []}}, now=now)["alarm"]
    # a GPU-only backlog does not alarm a free CPU quarter
    assert not IA.evaluate(snaps, why, Q_GPU, now=now)["alarm"]


def test_streak_resets_when_region_was_busy():
    text, now = _log(["q0", "q0", "q2", "q0", "q0"])
    snaps, why, _ = IA.parse_log(text)
    assert IA.free_streak(snaps, "q0") == 150
    assert not IA.evaluate(snaps, why, Q_CPU, now=now)["alarm"]


def test_suppressions_disk_pause_hold_quiet_guard_running_cover():
    text, now = _log(["q0"] * 5)
    snaps, why, _ = IA.parse_log(text)
    r = IA.evaluate(snaps, why, Q_CPU, now=now, admission="DISK-PAUSE: free disk under the floor")
    assert not r["alarm"] and r["suppressed"][0]["cause"].startswith("DISK-PAUSE")
    r = IA.evaluate(snaps, why, Q_CPU, now=now, admission="HOLD-ADMISSIONS owner=op reason=x")
    assert not r["alarm"]
    r = IA.evaluate(snaps, why, Q_CPU, now=now, guards={"q0"})
    assert not r["alarm"] and "quiet-guard" in r["suppressed"][0]["cause"]
    q = {"buckets": {"GRANTABLE": Q_CPU["buckets"]["GRANTABLE"], "RUNNING": [{"id": "r", "regions": "0-23"}]}}
    assert not IA.evaluate(snaps, why, q, now=now)["alarm"]


def test_gpu_free_but_busy_util_or_running_grant_is_not_idle():
    text, now = _log(["gpu-quiet"] * 5, util="q0=60% q1=60% q2=60% q3=60% gpu=100%")
    snaps, why, _ = IA.parse_log(text)
    assert IA.free_streak(snaps, "gpu-quiet") == 0
    text, now = _log(["gpu-quiet"] * 5)
    snaps, why, _ = IA.parse_log(text)
    assert IA.evaluate(snaps, why, Q_GPU, now=now)["alarm"]
    q = {"buckets": {"GRANTABLE": Q_GPU["buckets"]["GRANTABLE"], "RUNNING": [{"regions": "mi210_0,88-95"}]}}
    assert not IA.evaluate(snaps, why, q, now=now)["alarm"]


def test_gpu_smoke_gap_under_one_tick_suppressed():
    text, now = _log(["gpu-quiet"] * 3, step=200, extra="smoke queued for g1, assigned next tick")
    snaps, why, _ = IA.parse_log(text)
    r = IA.evaluate(snaps, why, Q_GPU, now=now)   # 400 s free, 2 ticks = 400 -> not < 2 ticks: alarm
    assert r["alarm"]
    r = IA.evaluate(snaps, why, Q_GPU, now=now, idle_s=100)
    assert r["alarm"]
    text, now = _log(["gpu-quiet"] * 3, step=400, extra="smoke queued")   # streak 800 < 2*400? no -> equal
    snaps, why, _ = IA.parse_log(text)
    text2, now2 = _log(["c88", "gpu-quiet", "gpu-quiet"], step=400, extra="smoke running")  # streak 400 < 800
    s2, w2, _ = IA.parse_log(text2)
    r2 = IA.evaluate(s2, w2, Q_GPU, now=now2)
    assert not r2["alarm"] and "smoke gap" in r2["suppressed"][0]["cause"]


def test_keeper_stale_alarm():
    text, now = _log(["q1"] * 2)
    snaps, why, _ = IA.parse_log(text)
    r = IA.evaluate(snaps, why, Q_CPU, now=now + 1000)
    assert r["alarm"] and r["alarms"][0]["kind"] == "keeper-stale"
    assert IA.evaluate([], {}, Q_CPU, now=now)["alarm"]


def test_cli_writes_flag_and_retires_it(tmp_path, monkeypatch):
    text, now = _log(["q0"] * 5)
    (tmp_path / IA.KEEPER_LOG).write_text(text)
    monkeypatch.setattr(IA, "queue_json", lambda f: Q_CPU)
    monkeypatch.setattr(IA, "admission_reason", lambda f: None)
    monkeypatch.setattr(IA.time, "time", lambda: now)
    assert IA.main(["--flags", str(tmp_path)]) == IA.ALARM
    doc = json.loads((tmp_path / IA.FLAG_NAME).read_text())
    assert doc["alarms"][0]["kind"] == "idle-with-backlog"
    monkeypatch.setattr(IA, "queue_json", lambda f: {"buckets": {}})
    assert IA.main(["--flags", str(tmp_path)]) == IA.NO_ALARM
    assert not (tmp_path / IA.FLAG_NAME).exists() and (tmp_path / (IA.FLAG_NAME + ".cleared")).exists()


def test_watch_exits_on_first_alarm(tmp_path, monkeypatch):
    text, now = _log(["q0"] * 5)
    (tmp_path / IA.KEEPER_LOG).write_text(text)
    calls = {"n": 0}

    def fake_once(flags, idle_s, stale_s):
        calls["n"] += 1
        return {"alarm": calls["n"] >= 2, "alarms": [{"kind": "idle-with-backlog", "region": "q0", "free_s": 400,
                                                      "ready": ["x"], "ready_n": 1, "reason": "why"}]
                if calls["n"] >= 2 else [], "suppressed": []}
    monkeypatch.setattr(IA, "run_once", fake_once)
    monkeypatch.setattr(IA.time, "sleep", lambda s: None)
    assert IA.main(["--flags", str(tmp_path), "--watch"]) == IA.ALARM and calls["n"] == 2


def test_watch_alarms_on_new_traceback(tmp_path, monkeypatch):
    lp = tmp_path / IA.KEEPER_LOG
    lp.write_text("2026-11-21T00:00:00Z start\n")
    monkeypatch.setattr(IA, "run_once", lambda *a: (_ for _ in ()).throw(AssertionError("not reached")))

    def sleep(_):
        with open(lp, "a") as fh:
            fh.write("Traceback (most recent call last):\n")
    monkeypatch.setattr(IA.time, "sleep", sleep)
    assert IA.main(["--flags", str(tmp_path), "--watch"]) == IA.ALARM
    assert json.loads((tmp_path / IA.FLAG_NAME).read_text())["alarms"][0]["kind"] == "keeper-traceback"


# ---------------------------------------------------------------- pending_operator_cmds
def test_accumulator_add_dedupe_combined_clear(tmp_path):
    d = str(tmp_path)
    a, new = POC.add("sudo systemctl restart foo", "foo wedged", "pm", "sudo", d)
    assert new
    assert POC.add("sudo  systemctl restart foo", "again", "pm", "sudo", d) == (a, False)
    POC.add("bash scripts/operator/ratify_x.sh --apply", "ratify x", "pm", "ratify", d)
    es = POC.entries(d)
    assert [e["kind"] for e in es] == ["ratify", "sudo"]
    line = POC.combined(d)
    assert "\n" not in line and line.index("ratify_x") < line.index("systemctl") and "clear --all" in line
    assert POC.combined(d, script=True).startswith("#!/bin/bash")
    assert POC.clear(d, session="pm") == 2 and POC.entries(d) == [] and POC.combined(d) == ""
    assert len(os.listdir(tmp_path / "done")) == 2


def test_accumulator_refuses_bad_input(tmp_path):
    for cmd, reason, kind in (("", "r", "sudo"), ("a\nb", "r", "sudo"), ("x", " ", "sudo"), ("x", "r", "bogus")):
        try:
            POC.add(cmd, reason, "s", kind, str(tmp_path))
        except ValueError:
            continue
        raise AssertionError((cmd, reason, kind))
    assert POC.main(["--dir", str(tmp_path), "add", "--cmd", "", "--reason", "r"]) == 2


def test_accumulator_many_entries_becomes_script(tmp_path):
    for i in range(5):
        POC.add(f"echo {i}", "r", "s", "host", str(tmp_path))
    assert POC.combined(str(tmp_path)).startswith("#!/bin/bash")


# ---------------------------------------------------------------- recheck_blocker
def test_recheck_which_python_model_disk(tmp_path):
    assert RB.check("which", ["sh"])[0] == RB.CLEAR
    assert RB.check("which", ["definitely-not-a-binary-xyz"])[0] == RB.BLOCKED
    v = f"{sys.version_info.major}.{sys.version_info.minor}"
    assert RB.check("python", [v])[0] in (RB.CLEAR, RB.BLOCKED)   # depends on pythonX.Y on PATH
    assert RB.check("python", ["3.99"])[0] == RB.BLOCKED
    assert RB.check("python", ["three"])[0] == RB.UNKNOWN
    f = tmp_path / "m.gguf"
    assert RB.check("model", [str(f)])[0] == RB.BLOCKED
    f.write_bytes(b"")
    assert "empty" in RB.check("model", [str(f)])[1]
    f.write_bytes(b"x")
    assert RB.check("model", [str(tmp_path / "*.gguf")])[0] == RB.CLEAR
    assert RB.check("disk", ["0", str(tmp_path)])[0] == RB.CLEAR
    assert RB.check("disk", ["1e12", str(tmp_path)])[0] == RB.BLOCKED
    assert RB.check("disk", ["abc"])[0] == RB.UNKNOWN


def test_recheck_row_states():
    q = {"buckets": {"RUNNING": [{"id": "a", "reason": "grant open"}], "BLOCKED": [{"id": "b", "reason": "STOP"}]}}
    assert RB.row("a", qjson=q)[0] == RB.CLEAR
    assert RB.row("b", qjson=q)[0] == RB.BLOCKED
    assert RB.row("b", want="blocked", qjson=q)[0] == RB.CLEAR
    assert RB.row("zz", qjson=q)[0] == RB.UNKNOWN


def test_recheck_codex_missing(monkeypatch):
    monkeypatch.setattr(RB.shutil, "which", lambda b: None)
    assert RB.codex_login()[0] == RB.BLOCKED


def test_recheck_cli_exit_code_and_json(capsys):
    assert RB.main(["which", "sh", "--json"]) == RB.CLEAR
    assert json.loads(capsys.readouterr().out)["verdict"] == "CLEAR"


# ---------------------------------------------------------------- status_digest
def _flags(tmp_path):
    for d in ("ready", "grants", "filing-done"):
        (tmp_path / d).mkdir()
    (tmp_path / "ready" / "r1.json").write_text(json.dumps({"id": "r1", "owner": "own"}))
    (tmp_path / "grants" / "r1.ended").write_text("")
    (tmp_path / "ready" / "r2.json").write_text(json.dumps({"id": "r2", "owner": "own"}))
    (tmp_path / "grants" / "r2.ended").write_text("")
    (tmp_path / "filing-done" / "r2.FILED").write_text("")
    return str(tmp_path)


def test_digest_unfiled_and_rows_by_owner(tmp_path):
    assert [x["id"] for x in SD.unfiled(_flags(tmp_path))] == ["r1"]
    q = {"buckets": {"RUNNING": [{"id": "a", "owner": "o", "end": "E", "ends_in_min": 5}],
                     "GRANTABLE": [{"id": "b", "owner": "o", "rank": 3}], "SMOKE-QUEUED": []}}
    r = SD.rows_by_owner(q)["o"]
    assert [x["state"] for x in r] == ["RUNNING", "QUEUED"] and "5 min" in r[0]["eta"]


def test_digest_watched_handoffs_blockers(tmp_path):
    root = tmp_path / "root"
    (root / "handoffs/active").mkdir(parents=True)
    (root / "handoffs/active/.index-state.json").write_text(json.dumps({"handoffs": {
        "h.md": {"row_id": "X-1", "open": 2, "blocked": 1, "closed": 4, "last_advanced": "2026-11-21"}}}))
    boxes = {"A": {"file": "handoffs/active/h.md", "id": "A", "line": 3, "state": "open", "gate": ["Y-2"],
                   "gate_open": True, "class": "inference", "holds": [], "lint": {"ok": True}, "text": "- [ ] **A** x"},
             "B": {"file": "handoffs/active/h.md", "id": "B", "line": 9, "state": "done"}}
    out = SD.watched_handoffs(str(tmp_path), ["h"], root=str(root), box_doc={"boxes": boxes})
    assert out[0]["open"] == 2 and len(out[0]["boxes"]) == 1
    assert out[0]["boxes"][0]["blocker"].startswith("gate open: Y-2")
    assert SD.watched_handoffs(str(tmp_path), ["nope"], root=str(root), box_doc={"boxes": {}})[0]["error"]


def test_digest_lineage_from_disk(tmp_path):
    d = tmp_path / "data" / "ak-lineage-c18-20261121"
    d.mkdir(parents=True)
    (d / "ledger.json").write_text(json.dumps({"champion": "ak/champion/x", "current_c": 17, "next_c": 18,
                                               "current_fold": "f", "production": "p", "features": [1, 2]}))
    lin = SD.lineage(str(tmp_path))
    assert lin["current_c"] == 17 and lin["features"] == 2


def test_digest_render_has_all_seven_sections(tmp_path, monkeypatch):
    d = {"as_of": "T", "rows_by_owner": {}, "idle": [{"region": "q0", "free_min": 9, "reason": "why"}],
         "unfiled": [], "handoffs": [], "operator_cmds": [{"id": "i", "kind": "sudo", "session": "s", "reason": "r"}],
         "operator_cmds_combined": "( sudo x ) && clear", "lineage": {"error": "none"},
         "disk": {"path": "/", "free_gib": 1, "floor_gib": 150, "resume_gib": 180, "headroom_gib": -149,
                  "paused": True}}
    out = SD.render(d)
    for n in range(1, 8):
        assert f"## {n}." in out
    assert "DISK-PAUSE ACTIVE" in out and "( sudo x )" in out and "q0 free 9 min: why" in out
