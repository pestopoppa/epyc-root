"""LOOP-38: three-state Codex pane liveness + guarded nudge. Fixtures only: no real tmux, no real session.

conftest.py puts a record-only stub `tmux` first on PATH; every tmux interaction here is injected, and the
stub's `invoked` log must stay free of send-keys.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
_spec = importlib.util.spec_from_file_location("codex_pane_liveness", BASE / "codex_pane_liveness.py")
cpl = importlib.util.module_from_spec(_spec)
sys.modules["codex_pane_liveness"] = cpl
_spec.loader.exec_module(cpl)

BUSY = "working (12s * esc to interrupt)"
BARE = "› \n  gpt-5  ~/x"
STALLED = "goal stalled\n› "
WIN = {"index": "2", "name": "NI", "pane_pid": 1, "dead": False, "target": "agent:2"}


def test_pane_text_alone_never_clears_a_session():
    r = cpl.classify(None, "unreadable", [BARE, BARE, BARE])
    assert r["state"] == cpl.UNKNOWN


def test_compacting_pane_looks_idle_but_runtime_active_means_alive():
    r = cpl.classify("active", "ends in token_count", [BARE] * 3)
    assert r["state"] == cpl.COMPACTING
    assert cpl.classify("active", "", [BUSY] * 3)["state"] == cpl.WORKING
    assert cpl.classify("idle", "", ["compacting context"] * 3)["state"] == cpl.COMPACTING


def test_idle_needs_runtime_terminal_and_clean_reads_and_busy_outranks():
    assert cpl.classify("idle", "ends in task_complete", [BARE] * 3)["state"] == cpl.IDLE
    assert cpl.classify("idle", "", [BARE, BUSY, BARE])["state"] == cpl.WORKING
    assert cpl.classify("idle", "", [BARE, None, BARE])["state"] == cpl.UNKNOWN
    r = cpl.classify("idle", "", [STALLED] * 3)
    assert r["state"] == cpl.IDLE and r["goal_stalled_on_pane"] is True
    assert cpl.classify("active", "", [STALLED] * 3)["state"] == cpl.COMPACTING   # stalled text is not evidence


def _rollout(tmp_path, last_type, source="user"):
    p = tmp_path / "rollout-1.jsonl"
    p.write_text(json.dumps({"payload": {"thread_source": source}}) + "\n"
                 + json.dumps({"payload": {"type": last_type}}) + "\n")
    return p


@pytest.mark.parametrize("last,want", [("task_complete", "idle"), ("turn_aborted", "idle"),
                                       ("token_count", "active"), ("reasoning", "active")])
def test_real_rollout_parse_path_feeds_classification(tmp_path, last, want):
    ad = cpl._adapter()
    state, why = ad.codex_state_from_rollouts([_rollout(tmp_path, last)])
    assert state == want
    r = cpl.classify(state, why, [BARE] * 3)
    assert r["state"] == (cpl.IDLE if want == "idle" else cpl.COMPACTING)


def test_subagent_rollout_is_refused_so_state_is_unknown(tmp_path):
    state, why = cpl._adapter().codex_state_from_rollouts([_rollout(tmp_path, "task_complete", "subagent")])
    assert state is None
    assert cpl.classify(state, why, [BARE] * 3)["state"] == cpl.UNKNOWN


def _tmux_ok(*a):
    if a[0] == "list-windows":
        return 0, "2\tNI\t1\t0\n3\trefactor\t2\t0\n3\tdup\t4\t0"
    return 0, ""


def _nudge(**kw):
    sent = []
    base = dict(tmux_fn=_tmux_ok, runtime_fn=lambda pid: ("idle", "fx"), pane_fn=lambda t: BARE,
                composer_fn=lambda t: ("› ", None), send_fn=lambda t, x: sent.append((t, x)) or (0, ""),
                sleep=lambda s: None, samples=3, poll_s=0)
    base.update(kw)
    return cpl.nudge("agent:2", "continue", **base), sent


def test_nudge_dry_run_types_nothing():
    (rc, msg), sent = _nudge()
    assert rc == 0 and msg.startswith("DRY-RUN") and not sent


@pytest.mark.parametrize("runtime", ["active", None])
def test_nudge_refuses_non_idle_runtime(runtime):
    (rc, msg), sent = _nudge(runtime_fn=lambda pid: (runtime, "fx"), send=True)
    assert rc == 2 and msg.startswith("REFUSED") and not sent


def test_nudge_refuses_on_busy_pane_nonempty_composer_ambiguous_window_and_bad_text():
    assert _nudge(pane_fn=lambda t: BUSY, send=True)[0][0] == 2
    assert _nudge(composer_fn=lambda t: ("› half typed", None), send=True)[0][0] == 2
    assert _nudge(composer_fn=lambda t: (None, "unreadable"), send=True)[0][0] == 2
    rc, msg = cpl.nudge("3", "x", tmux_fn=_tmux_ok, runtime_fn=lambda p: ("idle", ""), pane_fn=lambda t: BARE,
                        sleep=lambda s: None)
    assert rc == 2 and "matched 2" in msg
    assert cpl.nudge("agent:2", "a\nb", tmux_fn=_tmux_ok)[0] == 2
    assert cpl.nudge("agent:9", "x", tmux_fn=_tmux_ok)[0] == 2


def test_nudge_requires_idle_on_both_samples():
    seq = iter([("idle", ""), ("active", "")])
    (rc, msg), sent = _nudge(runtime_fn=lambda pid: next(seq), send=True)
    assert rc == 2 and not sent


def test_nudge_send_path_verifies_consumption(monkeypatch):
    ad = cpl._adapter()
    monkeypatch.setattr(ad, "_await_composer_consumed", lambda *a, **k: (True, "› ", None))
    (rc, msg), sent = _nudge(send=True)
    assert rc == 0 and msg.startswith("SENT") and sent == [("agent:2", "continue")]
    cleared = []
    monkeypatch.setattr(ad, "_await_composer_consumed", lambda *a, **k: (False, "› continue", None))
    monkeypatch.setattr(ad, "_clear_own_pending", lambda t, b, **k: cleared.append(t) or (True, "ok"))
    (rc, msg), _ = _nudge(send=True)
    assert rc == 2 and msg.startswith("UNDELIVERED") and cleared == ["agent:2"]


def test_no_real_keystrokes_reached_tmux():
    stub_log = os.path.join(os.environ["TMUX_TMPDIR"], "invoked")
    assert not os.path.exists(stub_log) or "send-keys" not in open(stub_log).read()


if __name__ == "__main__":
    raise SystemExit("REFUSING: pytest-fixture suite; run: "
                     "python -m pytest scripts/coordination/tests/test_codex_pane_liveness.py -q")
