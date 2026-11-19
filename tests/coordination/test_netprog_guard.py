"""D9 net-progress guard (handoff_sessions.netprog_record + token_guards.netprog_verdict / wrapup_progress)."""
from __future__ import annotations

import json

from scripts.coordination import handoff_sessions as hs
from scripts.coordination import token_guards as tg

FLIP = "-- [ ] task a\n+- [x] task a ✅ 2026-11-18\n"
FLIP_BELIEF = "-- [ ] task a\n+- [x] task a: PASS 3/3, 41.2 tok/s ✅ 2026-11-18 [belief: clm_1]\n"
PREP_CC = "-- [ ] **VB-X9-PREP — prepare the packet**\n+- [x] **VB-X9-PREP — prepare the packet** custody pinned ✅ 2026-11-18 [belief: cc]\n"
OPEN2 = "+- [ ] new prep 1\n+- [ ] new prep 2\n"
EDIT_TICK = "-- [x] old done\n+- [x] old done (reworded)\n"


def _run(monkeypatch, tmp_path, diffs):
    monkeypatch.setattr(hs, "wrapup_diff", lambda sha, repo=None: diffs[sha])
    e, park = {}, None
    for i, sha in enumerate(diffs):
        e["last_wrapup"] = sha
        park = hs.netprog_record(str(tmp_path), "slugx", e) or park
    return e, park


def test_wrapup_progress_counts_only_real_flips():
    assert tg.wrapup_progress(FLIP + OPEN2) == {"closed": 1, "opened": 2, "belief": False}
    assert tg.wrapup_progress(EDIT_TICK) == {"closed": 0, "opened": 0, "belief": False}
    assert tg.wrapup_progress(FLIP_BELIEF)["belief"] is True


def test_netprog_parks_prep_only_turns_and_digests(monkeypatch, tmp_path):
    e, park = _run(monkeypatch, tmp_path, {f"aaaaaa{i}": OPEN2 for i in range(6)})
    assert park and park.startswith("no-net-progress:") and "opened 12 >= closed 0" in park
    assert e["parked"]["reason"] == park
    d = [json.loads(l) for l in (tmp_path / hs.AUTONOMY_DIGEST_NAME).read_text().splitlines()]
    assert d[-1]["action"] == "PARK" and d[-1]["why"] == park
    assert tg.auto_unpark_eligible(e, 0.0)  # R2/R5 auto-unpark applies


def test_netprog_not_parked_when_a_turn_has_a_result(monkeypatch, tmp_path):
    diffs = {f"bbbbbb{i}": OPEN2 for i in range(9)}
    diffs["bbbbbb4"] = FLIP_BELIEF
    e, park = _run(monkeypatch, tmp_path, diffs)
    assert park is None and "parked" not in e


def test_netprog_not_parked_on_net_closes(monkeypatch, tmp_path):
    e, park = _run(monkeypatch, tmp_path, {f"cccccc{i}": FLIP for i in range(7)})
    assert park is None and "parked" not in e


def test_netprog_prep_only_rule_b_ignores_closes():
    # prep ticks (closes) every turn but no result: rule (a) silent, (b) parks at 8
    hist = [{"closed": 2, "opened": 1, "result": False}] * 8
    assert tg.netprog_verdict(hist[:6]) is None
    assert tg.netprog_verdict(hist[:7]) is None
    assert tg.netprog_verdict(hist).startswith("no-net-progress: last 8 turns 0 results (closed 16")


def test_belief_cc_on_prep_line_is_not_a_result():
    assert tg.wrapup_progress(PREP_CC) == {"closed": 1, "opened": 0, "belief": False}
    assert not tg.belief_result("+- [x] **VB-Q38-7** wire Qwen3-0.6B v10 ✅ 2026-11-18 [belief: clm_9]")
    assert tg.belief_result("+- [x] **VB-Q38-7** NO-GO ✅ 2026-11-18 [belief: clm_9]")


def _filing(F, rid, handoff, status="pass"):
    (F / "filing-done").mkdir(exist_ok=True)
    (F / "filing-done" / f"{rid}.FILED").write_text(f"FILED {rid}: {status} rc=0\n")
    (F / "filing-done" / f"{rid}.verdict.json").write_text(json.dumps({"handoff_task": handoff + ":ROW"}))


def test_turn_result_only_for_owned_rows(tmp_path):
    e = {"handoff": "handoffs/active/mine.md", "last_resume": "2020-01-01T00:00:00Z"}
    _filing(tmp_path, "other-r1", "handoffs/active/theirs.md")
    assert not hs.turn_result(str(tmp_path), "mine", e)
    _filing(tmp_path, "old-r1", "handoffs/active/mine.md", status="SUPERSEDED SUPERSEDED-BY old-r2")
    assert not hs.turn_result(str(tmp_path), "mine", e)
    _filing(tmp_path, "mine-r1", "handoffs/active/mine.md")
    assert hs.turn_result(str(tmp_path), "mine", e)


def test_netprog_same_sha_is_not_double_counted(monkeypatch, tmp_path):
    monkeypatch.setattr(hs, "wrapup_diff", lambda sha, repo=None: FLIP)
    e = {"last_wrapup": "eeeeee1"}
    hs.netprog_record(str(tmp_path), "s", e)
    hs.netprog_record(str(tmp_path), "s", e)
    assert [t["closed"] for t in e["netprog"]] == [1, 0]
