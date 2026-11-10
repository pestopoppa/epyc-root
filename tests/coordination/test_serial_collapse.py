"""Paired-mutation tests for scripts/coordination/serial_collapse.py (FM-8 detector)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("serial_collapse", ROOT / "scripts/coordination/serial_collapse.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


def user(text, side=False):
    return {"type": "user", "isSidechain": side, "sessionId": "s1", "message": {"role": "user", "content": text}}


def tool_result():
    return {"type": "user", "isSidechain": False,
            "message": {"content": [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]}}


def calls(*names, side=False):
    return {"type": "assistant", "isSidechain": side,
            "message": {"content": [{"type": "tool_use", "name": n, "input": {}} for n in names]}}


def task(width=0, tools=5):
    return [user("do the thing"), calls(*(["Bash"] * (tools - width) + ["Agent"] * width)), tool_result()]


def write(tmp_path, recs, extra_lines=()):
    p = tmp_path / "s.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in recs) + "".join(extra_lines))
    return p


def flat(*tasks):
    return [r for t in tasks for r in t]


def test_three_serial_tasks_flag(tmp_path):
    r = sc.analyze(write(tmp_path, flat(task(), task(), task())))
    assert r["flag"] and r["longest_zero_run"] == 3 and r["widths"] == [0, 0, 0]


def test_mutation_one_dispatch_breaks_run(tmp_path):
    r = sc.analyze(write(tmp_path, flat(task(), task(width=1), task())))
    assert not r["flag"] and r["widths"] == [0, 1, 0]


def test_task_tool_counts_as_dispatch(tmp_path):
    recs = flat(task(), task(), [user("x"), calls("Task", "Bash", "Bash", "Bash", "Bash")])
    assert not sc.analyze(write(tmp_path, recs))["flag"]


def test_two_serial_tasks_do_not_flag(tmp_path):
    assert not sc.analyze(write(tmp_path, flat(task(), task())))["flag"]


def test_short_segments_neither_extend_nor_break(tmp_path):
    recs = flat(task(), task(tools=1), task(), task())
    r = sc.analyze(write(tmp_path, recs))
    assert r["flag"] and r["completed_tasks"] == 3


def test_mutation_short_segments_do_not_count_as_tasks(tmp_path):
    r = sc.analyze(write(tmp_path, flat(task(tools=4), task(tools=4), task(tools=4))))
    assert not r["flag"] and r["completed_tasks"] == 0


def test_tool_result_turn_is_not_boundary(tmp_path):
    # one operator turn split by tool results stays one task
    recs = [user("go"), calls("Bash", "Bash"), tool_result(), calls("Bash", "Bash", "Bash"), tool_result()]
    r = sc.analyze(write(tmp_path, recs))
    assert r["boundaries"] == 1 and r["completed_tasks"] == 1


def test_sidechain_dispatches_are_not_main_width(tmp_path):
    t = [user("go"), calls("Bash", "Bash", "Bash", "Bash", "Bash"), calls("Agent", side=True)]
    r = sc.analyze(write(tmp_path, flat(t, task(), task())))
    assert r["flag"]


def test_mutation_main_dispatch_counts(tmp_path):
    t = [user("go"), calls("Bash", "Bash", "Bash", "Bash", "Bash"), calls("Agent")]
    assert not sc.analyze(write(tmp_path, flat(t, task(), task())))["flag"]


def test_sidechain_user_turn_is_not_boundary(tmp_path):
    recs = flat(task()) + [user("sub brief", side=True)]
    assert sc.analyze(write(tmp_path, recs))["boundaries"] == 1


def test_malformed_lines_counted(tmp_path):
    r = sc.analyze(write(tmp_path, flat(task(), task(), task()), ["{not json\n", "[1]\n"]))
    assert r["malformed_lines"] == 2 and r["flag"]


def test_run_threshold_param(tmp_path):
    p = write(tmp_path, flat(task(), task(), task()))
    assert not sc.analyze(p, run=4)["flag"]


def test_cli_flagged_only(tmp_path, capsys):
    p = write(tmp_path, flat(task(), task()))
    assert sc.main(["--files", str(p), "--flagged-only"]) == 0
    assert capsys.readouterr().out == ""


def note(kind=None, text="<task-notification>\n<task-id>a</task-id>"):
    r = user(text)
    if kind:
        r["origin"] = {"kind": kind}
    return r


def test_task_notifications_do_not_open_tasks(tmp_path):
    # one dispatched task whose completion notifications trigger more tool work
    t = [user("go"), calls("Agent", "Bash", "Bash", "Bash", "Bash"),
         note("task-notification"), calls(*["Bash"] * 5),
         note(), calls(*["Bash"] * 5), note(), calls(*["Bash"] * 5)]
    r = sc.analyze(write(tmp_path, t))
    assert r["boundaries"] == 1 and not r["flag"]


def test_mutation_human_origin_opens_tasks(tmp_path):
    t = [user("go"), calls("Agent", "Bash", "Bash", "Bash", "Bash")]
    for _ in range(3):
        t += [note("human", "next"), calls(*["Bash"] * 5)]
    r = sc.analyze(write(tmp_path, t))
    assert r["boundaries"] == 4 and r["flag"]


def test_peer_origin_meta_is_boundary(tmp_path):
    t = []
    for _ in range(3):
        r0 = note("peer", "Another Claude session sent a task")
        r0["isMeta"] = True
        t += [r0, calls(*["Bash"] * 5)]
    assert sc.analyze(write(tmp_path, t))["flag"]


def test_meta_without_origin_is_not_boundary(tmp_path):
    r0 = user("# Session Wrap-Up")
    r0["isMeta"] = True
    assert sc.analyze(write(tmp_path, [r0, calls(*["Bash"] * 5)]))["boundaries"] == 0
