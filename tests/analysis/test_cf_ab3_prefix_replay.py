"""CF-AB-3 replay engine on a synthetic trajectory (zero inference)."""
import importlib.util
import json
from pathlib import Path

import pytest

_P = Path(__file__).resolve().parents[2] / "scripts" / "analysis" / "cf_ab3_prefix_replay.py"
_s = importlib.util.spec_from_file_location("cf_ab3_prefix_replay", _P)
m = importlib.util.module_from_spec(_s)
_s.loader.exec_module(m)


def _traj(n_turns=14, out_chars=6000, window=8000):
    turns = []
    for i in range(n_turns):
        turns.append({"assistant": f"step {i}", "tool_results": [
            {"tool": "peek", "args": f"f{i}", "text": (f"line{i} " * (out_chars // 6))[:out_chars], "error": False}]})
    return {"base": "SYSTEM " * 50, "window": window, "turns": turns}


def test_control_arm_is_pure_append_so_prefix_is_everything_but_the_new_turn():
    rows = m.replay(_traj(), arms=("A0",))["A0"]
    late = [r for r in rows if r["turn"] >= 8]
    assert late and all(r["reprefill_fraction"] < 0.2 for r in late)
    # pure append: the common prefix is the whole previous prompt
    assert all(r["common_prefix_tok_est"] >= rows[i - 1]["prompt_tok_est"] - 1
               for i, r in enumerate(rows) if i)
    assert all(r["common_prefix_tok_est"] > 0 for r in rows)


def test_masking_arms_rewrite_history_and_cost_prefix():
    out = m.replay(_traj())
    a0 = sum(r["reprefill_fraction"] for r in out["A0"])
    a5 = sum(r["reprefill_fraction"] for r in out["A5"])
    assert a5 > a0  # an old result turning into a stub moves the first differing token earlier


def test_shift_bound_recovers_moved_run_and_is_a_fraction():
    prev = "A" * 100 + "".join(chr(97 + (i * 7) % 26) for i in range(3000))
    cur = "B" * 300 + prev[100:]
    pre = m.common_prefix(prev, cur)
    assert pre == 0
    rec = m.shift_recoverable_chars(prev, cur, pre)
    assert rec >= 2900
    rows = m.replay(_traj())["A4"]
    assert all(0.0 <= r["shift_recoverable_fraction_of_tail"] <= 1.0 for r in rows)


def test_blocked_when_tool_text_missing(tmp_path):
    f = tmp_path / "t.json"
    f.write_text(json.dumps({"base": "x", "turns": [{"assistant": "a"}]}))
    with pytest.raises(m.Blocked):
        m.load(f)
    assert m.main([str(f)]) == 3


def test_probe_bep_corpus_reports_blocked(tmp_path):
    d = tmp_path / "r" / "traces"
    d.mkdir(parents=True)
    (d / "a.jsonl").write_text(json.dumps({"turn": 1, "raw_output": "x", "prompt_chars": 10,
                                           "prompt_has_last_output": True, "prompt_tail": "tail"}) + "\n")
    rep = m.probe_bep_corpus(tmp_path)
    assert rep["blocked"] and rep["turns"] == 1 and rep["turns_with_prompt_tail"] == 1
