"""GPU-HOST-FOREIGN: an urgent GPU row blocked only by foreign busy on 88-95/184-191 is logged, alerted on the 2nd sample."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "rowflow"))
import rowflow as rf  # noqa: E402

OPT = frozenset(rf.GPU_HOST_TOKENS | {rf.GPU})
PROC = {"pid": 4242, "cmd": "python3 -m pytest -q", "cwd": "/mnt/raid0/llm/worktrees/other-sess/x", "affinity": "0-191", "cpu": 90, "busy_pct": 100.0}


def run(flags, cands, free, procs, roots=(), emits=None, logs=None):
    logs = [] if logs is None else logs
    e = (lambda *a, **k: emits.append(a)) if emits is not None else (lambda *a, **k: None)
    return rf.gpu_host_foreign(flags, cands, free, [], set(), logs.append, procs=procs, roots=set(roots),
                               parent=lambda p: 1, emit=e)


def test_logs_and_alerts_on_second_sample(tmp_path):
    f = str(tmp_path)
    c = {"id": "ak-gv-r6", "rank": 4, "options": [OPT]}
    free = {rf.GPU}
    emits, logs = [], []
    assert run(f, [c], free, [PROC], emits=emits, logs=logs)["ak-gv-r6"] == [PROC]
    assert logs[0].startswith("GPU-HOST-FOREIGN 4242 python3 -m pytest -q other-sess cwd=/mnt/raid0/llm/worktrees/other-sess/x affinity=0-191")
    assert emits == []
    run(f, [c], free, [PROC], emits=emits)
    assert len(emits) == 1 and emits[0][1] == "gpu-host-foreign" and emits[0][2] == "ak-gv-r6"
    run(f, [c], free, [PROC], emits=emits)
    assert len(emits) == 1   # once per episode


def test_not_urgent_or_other_blocker_or_owned_is_silent(tmp_path):
    f = str(tmp_path)
    logs = []
    assert run(f, [{"id": "a", "rank": 50, "options": [OPT]}], {rf.GPU}, [PROC], logs=logs) == {}
    assert run(f, [{"id": "b", "rank": 4, "options": [OPT]}], set(rf.GPU_HOST_TOKENS), [PROC], logs=logs) == {}   # gpu-quiet busy
    assert run(f, [{"id": "c", "rank": 4, "options": [OPT]}], set(OPT), [PROC], logs=logs) == {}                   # nothing blocks
    assert run(f, [{"id": "d", "rank": 4, "options": [OPT]}], {rf.GPU}, [PROC], roots={4242}, logs=logs) == {"d": []}  # granted pid
    assert logs == []


def test_allocate_hook_never_kills(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(os, "kill", lambda *a: called.append(a))
    run(str(tmp_path), [{"id": "x", "rank": 1, "options": [OPT]}], {rf.GPU}, [PROC])
    assert called == []


def test_floating_idle_process_is_ignored_busy_one_blocks(tmp_path):
    f = str(tmp_path)
    c = {"id": "ak-c22-knee", "rank": 4, "options": [OPT]}
    ff = {"pid": 3874678, "cmd": "/snap/firefox/x/firefox -contentproc", "cwd": "/", "affinity": "0-191", "cpu": 190,
          "ticks": 100, "ts": 1000.0}
    logs = []
    assert run(f, [c], {rf.GPU}, [ff], logs=logs)["ak-c22-knee"] == []
    assert run(f, [c], {rf.GPU}, [dict(ff, ticks=105, ts=1060.0)], logs=logs)["ak-c22-knee"] == []   # ~0.1% busy
    assert any(l.startswith("GPU-HOST-FOREIGN-IGNORED 3874678") for l in logs)
    assert not any(l.startswith("GPU-HOST-FOREIGN 3874678") for l in logs)
    hz = os.sysconf("SC_CLK_TCK")
    hot = dict(ff, ticks=105 + 60 * hz, ts=1120.0)   # 100% of a core over 60 s: sustained foreign load still blocks
    assert run(f, [c], {rf.GPU}, [hot])["ak-c22-knee"] == [hot]


def test_pinned_process_blocks(tmp_path):
    p = {"pid": 7, "cmd": "stress", "cwd": "/", "affinity": "184-191", "cpu": 186}
    c = {"id": "g", "rank": 4, "options": [OPT]}
    assert run(str(tmp_path), [c], {rf.GPU}, [p])["g"] == [p]
