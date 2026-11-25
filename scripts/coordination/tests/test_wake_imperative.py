"""Wake prompts and bus nudges must give sessions an actionable instruction."""
import os
import sys
from argparse import Namespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import handoff_sessions as hs  # noqa: E402
import tmux_adapter as adapter  # noqa: E402


@pytest.mark.parametrize("builder", ["end", "idle", "continue", "transfer", "awaiting", "proposals"])
def test_wake_builders_have_imperative(tmp_path, builder):
    flags = str(tmp_path)
    entry = {"handoff": "handoffs/active/demo.md", "engine": "claude"}
    endfile = tmp_path / "row.ended"
    endfile.write_text("rc=0\n")
    builders = {
        "end": lambda: hs.end_prompt("demo", entry, flags, "row", str(endfile)),
        "idle": lambda: hs.idle_prompt("demo", entry, flags),
        "continue": lambda: hs.continue_prompt("demo", entry, flags),
        "transfer": lambda: hs.transfer_prompt("demo", entry, flags, repo=flags),
        "awaiting": lambda: hs.awaiting_prompt("demo", entry, flags, [{"path": "ready"}]),
        "proposals": lambda: hs.proposals_prompt("demo", entry, flags, {"ids": ["child"]}),
    }
    assert hs.IMPERATIVE_RE.search(builders[builder]())


def test_ensure_imperative_preserves_existing_and_inserts_after_header():
    original = "[version] status\nRead the handoff."
    assert hs.ensure_imperative(original) == original
    assert hs.ensure_imperative("[version] status\nDetails.", "Act now.") == (
        "[version] status\nAct now.\nDetails.")
    assert hs.ensure_imperative("status", "Act now.") == "Act now. status"


def test_nudge_sends_imperative_without_newline(monkeypatch):
    sent = []
    monkeypatch.setattr(adapter, "load_config", lambda: {})
    monkeypatch.setattr(adapter, "probe", lambda *a: {
        "seconds_since_last_nudge": None, "nudge_ok": True, "target": "test:pane"})
    monkeypatch.setattr(adapter, "composer_faint_is_placeholder", lambda *a: False)
    monkeypatch.setattr(adapter, "_read_composer_row", lambda *a: ("", None))
    monkeypatch.setattr(adapter, "_send_message_chunked", lambda target, text: (sent.append(text) or 0, ""))
    monkeypatch.setattr(adapter, "_await_state", lambda *a, **kw: ("text_present" if len(sent) == 1 else "text_echoed", None))
    monkeypatch.setattr(adapter, "_fragment_occurrences", lambda *a: 1)
    monkeypatch.setattr(adapter, "_tmux", lambda *a: (sent.append("Enter") or 0, ""))
    monkeypatch.setattr(adapter, "_await_composer_consumed", lambda *a, **kw: (True, "", None))
    monkeypatch.setattr(adapter, "record", lambda *a, **kw: None)
    monkeypatch.setattr(adapter.time, "sleep", lambda *a: None)
    args = Namespace(message="A bus update is waiting.", agent="demo", quiet_s=0,
                     heartbeat_max_age=0, min_interval_s=0, dry_run=False, settle_s=0)
    assert adapter.cmd_nudge(args) == 0
    assert hs.IMPERATIVE_RE.search(sent[0])
    assert "\n" not in sent[0]
    assert sent[0].endswith(args.message)
    assert sent[1] == "Enter"
