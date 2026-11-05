"""Shadow mode: zero side effects on the flags dir (snapshot proof + an enforced write guard), and the diff report."""
import glob
import hashlib
import json
import os
import shutil

import pytest

from rf2 import T0, rf

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "legacy")


@pytest.fixture(autouse=True)
def _unguard():
    yield
    rf.unguard()


def snapshot(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        for n in dn + fn:
            p = os.path.join(dp, n)
            st = os.lstat(p)
            h = hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.isfile(p) else "dir"
            out[os.path.relpath(p, root)] = (st.st_mtime_ns, st.st_size, h)
    return out


def legacy_flags(tmp_path):
    """A flags dir in the live layout: legacy v3 manifests, smoke PASS for some, one open legacy grant, one done row,
    one live dry run occupying production cores."""
    flags = tmp_path / "flags"
    for d in ("ready", "grants", "dryrun", "filing-done"):
        (flags / d).mkdir(parents=True)
    lroot = tmp_path / "launchers"
    lroot.mkdir()
    for i, p in enumerate(sorted(glob.glob(os.path.join(FIX, "*.json")))):
        m = json.load(open(p))
        lp = lroot / f"{m['id']}.sh"
        lp.write_text("#!/bin/bash\nexec true\n")
        if isinstance(m.get("launcher"), dict):
            m["launcher"]["path"] = str(lp)
        if str(m.get("stop_file", "")).startswith("/"):
            m["stop_file"] = str(tmp_path / "stops" / (m["id"] + ".STOP"))
        (flags / "ready" / (m["id"] + ".json")).write_text(json.dumps(m))
        if i % 3:
            (flags / "dryrun" / m["id"]).mkdir()
            (flags / "dryrun" / m["id"] / "PASS.json").write_text(json.dumps({"launcher_sha256": rf.sha256(str(lp))}))
    (flags / "grants" / "akagg-ch26b-mmap-abi-20261102.grant").write_text(
        f"regions=24-47 start={rf.iso(T0 - 600)} end={rf.iso(T0 + 3600)} holds=q1\n")
    (flags / "grants" / "codex-ni-s18-qwenvl-cpu-r1-20261031.ended").write_text("rc=0 time=x reason=job-rc-0:exited\n")
    (flags / "dryrun" / "live-smoke").mkdir()
    (flags / "dryrun" / "live-smoke" / "RUNNING.json").write_text(json.dumps(
        {"regions": "mi210_0,72-75", "deadline": rf.iso(T0 + 900), "started": rf.iso(T0 - 60)}))
    return flags


def test_shadow_once_has_zero_side_effects(tmp_path):
    flags = legacy_flags(tmp_path)
    before = snapshot(flags)
    log = tmp_path / "shadow.log"
    w, plan = rf.shadow_once(str(flags), str(log), now=T0)
    assert snapshot(flags) == before
    text = log.read_text()
    assert "SHADOW-TICK" in text and "SHADOW-UNMAPPED c6-pre-mmq-capture-build-20261104" in text
    assert plan.grants and all(f"SHADOW-GRANT {g.id} " in text for g in plan.grants)
    occupied = set(range(24, 48)) | {72, 73, 74, 75}
    assert not any(g.cores & occupied for g in plan.grants), "shadow granted onto live-occupied tokens"
    assert not any(g.gpu != "none" for g in plan.grants), "the live dry run holds the gpu"
    # second tick: same decisions are not re-logged; the snapshot is still identical (via the CLI entry point)
    rf.unguard()
    assert rf.main(["shadow", "--once", "--flags", str(flags), "--log", str(log)]) == 0
    assert snapshot(flags) == before
    ids = [x.split()[2] for x in log.read_text().splitlines() if " SHADOW-GRANT " in x]
    assert len(ids) == len(set(ids)) and set(g.id for g in plan.grants) <= set(ids)


def test_write_guard_refuses_every_write_under_flags(tmp_path):
    flags = legacy_flags(tmp_path)
    rf.guard_readonly(str(flags))
    target = flags / "grants" / "x.grant"
    for attempt in (lambda: open(target, "w"), lambda: open(flags / "ready" / "a.json", "a"),
                    lambda: os.open(str(target), os.O_WRONLY | os.O_CREAT),
                    lambda: os.rename(flags / "ready", flags / "ready2"), lambda: os.remove(flags / "grants" / "akagg-ch26b-mmap-abi-20261102.grant"),
                    lambda: os.mkdir(flags / "new"), lambda: os.utime(flags / "ready"),
                    lambda: shutil.rmtree(flags / "dryrun"), lambda: rf.write_text(str(target), "x"),
                    lambda: rf.write_grant(str(flags), rf.Grant("x", frozenset({1}))),
                    lambda: rf.tick(str(flags), T0, rf.Measurement(), {}, print)):
        with pytest.raises(rf.ShadowWriteRefused):
            attempt()
    assert open(flags / "ready" / os.listdir(flags / "ready")[0]).read()    # reads still work
    assert not target.exists()
    with pytest.raises(rf.ShadowWriteRefused):
        rf.shadow_once(str(flags), str(flags / "shadow.log"), now=T0)      # a log under flags is refused up front
    rf.write_text(str(tmp_path / "outside.txt"), "ok")                       # outside the flags dir: allowed


def test_diff_report(tmp_path):
    k = tmp_path / "keeper.log"
    k.write_text("\n".join([
        "2026-11-05T10:00:00Z GRANT a regions=48-71 start=2026-11-05T10:00Z end=2026-11-05T12:00Z holds=q2 (x)",
        "2026-11-05T10:02:00Z GRANT b regions=mi210_0,88-95,184-191 start=x end=y holds=gpu-quiet,q3 (x)",
        "2026-11-05T15:51:06Z GRANT dbl regions=72-75 start=x end=y holds=q3 (x)",
        "2026-11-05T15:51:06Z GRANT dbl regions=80-83 start=x end=y holds=q3 (x)",
        "2026-11-05T10:00:00Z IDLE-WHY q1: not whole-free: 20 cores free",
        "2026-11-05T10:02:00Z IDLE-WHY q1: not whole-free: 20 cores free",
        "2026-11-05T10:00:00Z IDLE-WHY gpu-quiet: device quiet 1/2 samples",
        "2026-11-04T10:00:00Z GRANT old regions=0-3 start=x end=y holds=q0 (x)"]) + "\n")
    s = tmp_path / "shadow.log"
    s.write_text("\n".join([
        "2026-11-05T09:58:00Z SHADOW-GRANT a cpus=48-71 gpu=none ram=8 start=x end=y rank=50 quiet=0",
        "2026-11-05T10:02:00Z SHADOW-GRANT b cpus=88-95 gpu=shared ram=8 start=x end=y rank=40 quiet=0",
        "2026-11-05T11:00:00Z SHADOW-GRANT c cpus=0-3 gpu=none ram=8 start=x end=y rank=40 quiet=0",
        "2026-11-05T10:00:00Z SHADOW-IDLE-WHY q1 free=6: held-for a"]) + "\n")
    d = rf.diff(str(k), str(s), "2026-11-05")
    assert d["live_grants"] == 4 and d["shadow_grants"] == 3 and d["matched"] == 2
    rows = {r["id"]: r for r in d["rows"]}
    assert rows["a"]["start_delta_s"] == 120 and rows["a"]["cpus_match"] and rows["a"]["gpu_match"]
    assert rows["b"]["gpu_match"] is False and rows["b"] in d["disagreements"]
    assert rows["c"]["only"] == "shadow" and rows["dbl"]["only"] == "live" and rows["dbl"]["double_grant"]
    assert "old" not in rows
    assert d["idle"]["live"]["quarter_h"] > 0 and d["idle"]["live"]["gpu_h"] > 0
    assert d["idle"]["shadow"]["quarter_h"] == round(120 / 3600 * 6 / 24, 2)
    md = rf.diff_markdown(d)
    assert "DOUBLE-GRANT" in md and "| b |" in md


def test_status_and_map_report_are_read_only(tmp_path, capsys):
    flags = legacy_flags(tmp_path)
    before = snapshot(flags)
    assert rf.main(["status", "--flags", str(flags), "--json"]) == 0
    st = json.loads(capsys.readouterr().out)
    assert st["counts"]["running"] == 1 and st["counts"]["done"] == 1
    assert rf.main(["map-report", "--flags", str(flags), "--json"]) == 0
    r = json.loads(capsys.readouterr().out)
    assert r["total"] == len(glob.glob(os.path.join(FIX, "*.json"))) and r["unmapped"] >= 2
    assert snapshot(flags) == before
