"""RTG-55 MHS-3 operability: a fail-closed leakage guard must never stall SILENTLY.

Covers the startup preflight (one ERROR + a journal event, start not refused), the
consecutive-rejection circuit alarm (threshold, rate limit, clear on recovery), recovery
without restart (a failed build is never cached forever), the negative cache for a
malformed pool, and the narrowed generic-reference pattern.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "scripts" / "autopilot"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from scripts.autopilot import eval_leakage_monitor as mon  # noqa: E402
from scripts.autopilot.experiment_journal import ExperimentJournal  # noqa: E402
from scripts.autopilot.species import prompt_forge as pf  # noqa: E402

EPYC_ROOT_ALARM = Path("/mnt/raid0/llm/epyc-root/scripts/coordination/alarm_channel.py")
LEAKY = "Use gsm8k_00003 as the worked example."


def _write_pool(path: Path) -> Path:
    rows = [{"__pool_metadata__": True}] + [
        {"id": f"gsm8k_{i:05d}", "suite": "gsm8k", "prompt": f"q{i}"} for i in range(1, 6)
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


class FakeAlarm:
    def __init__(self):
        self.raised: list[tuple[str, dict]] = []
        self.cleared: list[str] = []

    def raise_alarm(self, message, evidence):
        self.raised.append((message, evidence))
        return True

    def clear_alarm(self, message):
        self.cleared.append(message)
        return True


class Clock:
    def __init__(self):
        self.now = 1_000.0

    def __call__(self):
        return self.now


@pytest.fixture
def pool_env(tmp_path, monkeypatch):
    pool = tmp_path / "question_pool.jsonl"
    monkeypatch.setenv(pf.EVAL_ID_VOCAB_SOURCES_ENV, str(pool))
    pf.clear_eval_id_vocabulary_cache()
    yield pool
    pf.set_eval_leakage_observer(None)
    pf.clear_eval_id_vocabulary_cache()


def _guard_verdict(text: str = "Always show your arithmetic.") -> str | None:
    """One guard evaluation exactly as PromptForge performs it."""
    return pf.eval_leakage_reason(text, pf.load_eval_id_vocabulary())


def _ledger(journal_dir: Path, event: str | None = None) -> list[dict]:
    rows = ExperimentJournal(journal_dir=journal_dir).ledger_events(mon.LEDGER_EVENT_TYPE)
    return [r for r in rows if event is None or r["event"] == event]


def _monitor(tmp_path, state, alarm, clock=None, threshold=3):
    journal = ExperimentJournal(journal_dir=tmp_path / "journal")
    return mon.EvalLeakageMonitor(
        journal=journal,
        state=state,
        alarm=alarm,
        prompt_forge_module=pf,
        threshold=threshold,
        reassert_s=900.0,
        clock=clock or Clock(),
    ).install()


# ── preflight ─────────────────────────────────────────────────────────────


def test_preflight_missing_pool_logs_one_error_and_journals(pool_env, tmp_path, caplog):
    state: dict = {}
    monitor = _monitor(tmp_path, state, FakeAlarm())
    with caplog.at_level(logging.INFO, logger="autopilot.eval_leakage_monitor"):
        assert monitor.preflight() is False  # reports failure; never raises / refuses start
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    text = errors[0].getMessage()
    assert "EVAL-LEAKAGE PREFLIGHT FAILED" in text
    assert str(pool_env) in text  # names the missing path
    assert pf.EVAL_ID_VOCAB_SOURCES_ENV in text  # names the fix
    events = _ledger(tmp_path / "journal", "preflight_failed")
    assert len(events) == 1
    assert events[0]["problem_paths"] == [str(pool_env)]
    assert events[0]["error"].startswith("missing_eval_id_source:")
    status = state[mon.STATE_KEY]
    assert status["last_error"].startswith("missing_eval_id_source:")
    assert status["problem_paths"] == [str(pool_env)]
    assert status["alarm_active"] is False


def test_preflight_ok_is_quiet(pool_env, tmp_path, caplog):
    _write_pool(pool_env)
    state: dict = {}
    monitor = _monitor(tmp_path, state, FakeAlarm())
    with caplog.at_level(logging.INFO, logger="autopilot.eval_leakage_monitor"):
        assert monitor.preflight() is True
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert _ledger(tmp_path / "journal") == []
    assert state[mon.STATE_KEY]["vocabulary_available"] is True


# ── circuit alarm + recovery ──────────────────────────────────────────────


def test_alarm_after_n_rejections_rate_limited_then_cleared_on_restore(pool_env, tmp_path):
    state: dict = {}
    alarm, clock = FakeAlarm(), Clock()
    monitor = _monitor(tmp_path, state, alarm, clock)
    monitor.preflight()

    for _ in range(2):
        assert _guard_verdict().startswith("eval_leakage_vocabulary_unavailable")
    assert alarm.raised == []  # below threshold
    assert state[mon.STATE_KEY]["consecutive_unavailable_rejections"] == 2

    assert _guard_verdict().startswith("eval_leakage_vocabulary_unavailable")
    assert len(alarm.raised) == 1
    message, evidence = alarm.raised[0]
    assert "3 consecutive mutations REJECTED" in message and str(pool_env) in message
    assert evidence["consecutive"] == 3
    assert state[mon.STATE_KEY]["alarm_active"] is True
    assert len(_ledger(tmp_path / "journal", "alarm_raised")) == 1

    # Rate limit: more rejections inside the re-assert window do not call the channel.
    clock.now += 60
    _guard_verdict()
    _guard_verdict()
    assert len(alarm.raised) == 1
    # After the window one re-assertion (the channel dedupes; no new journal event).
    clock.now += 901
    _guard_verdict()
    assert len(alarm.raised) == 2
    assert len(_ledger(tmp_path / "journal", "alarm_raised")) == 1

    # Recovery WITHOUT restart: restore the pool; the very next mutation is evaluated.
    _write_pool(pool_env)
    assert _guard_verdict() is None
    assert _guard_verdict(LEAKY).startswith("eval_instance_leakage")  # guard is live again
    assert len(alarm.cleared) == 1
    status = state[mon.STATE_KEY]
    assert status["alarm_active"] is False
    assert status["consecutive_unavailable_rejections"] == 0
    assert status["last_error"] == ""
    cleared = _ledger(tmp_path / "journal", "alarm_cleared")
    assert len(cleared) == 1 and cleared[0]["after_consecutive"] == 6


def test_success_resets_the_consecutive_count(pool_env, tmp_path):
    alarm = FakeAlarm()
    monitor = _monitor(tmp_path, {}, alarm)
    _guard_verdict()
    _guard_verdict()
    _write_pool(pool_env)
    _guard_verdict()
    pool_env.unlink()
    _guard_verdict()
    _guard_verdict()
    assert monitor.consecutive == 2
    assert alarm.raised == [] and alarm.cleared == []


def test_fix_text_never_suggests_git_and_pins_the_pool_identity():
    """Review finding 2: the pool is gitignored, so git cannot restore it."""
    text = mon.EvalLeakageMonitor(prompt_forge_module=pf, alarm=FakeAlarm()).fix_text()
    assert "git checkout" not in text and "git -C" not in text
    assert "64218c27e07400acf3b10a3cac05a410d5ee67814f353788ab75a19c84dde584" in text
    assert "1350221880" in text
    assert pf.EVAL_ID_VOCAB_SOURCES_ENV in text
    assert "NEVER rebuild" in text
    assert "BYTE-IDENTICAL" in text


def test_threshold_is_env_tunable(monkeypatch):
    monkeypatch.setenv(mon.THRESHOLD_ENV, "5")
    assert mon.EvalLeakageMonitor(prompt_forge_module=pf, alarm=FakeAlarm()).threshold == 5
    monkeypatch.setenv(mon.THRESHOLD_ENV, "0")  # invalid -> default
    assert mon.EvalLeakageMonitor(prompt_forge_module=pf, alarm=FakeAlarm()).threshold == 3


def test_observer_failure_never_changes_a_verdict(pool_env):
    def boom(available, error):
        raise RuntimeError("observer down")

    pf.set_eval_leakage_observer(boom)
    assert _guard_verdict().startswith("eval_leakage_vocabulary_unavailable")
    _write_pool(pool_env)
    assert _guard_verdict(LEAKY).startswith("eval_instance_leakage")


def test_propose_path_feeds_the_monitor(pool_env, tmp_path):
    """The live PromptForge rejection path is what the circuit counts."""
    alarm = FakeAlarm()
    monitor = _monitor(tmp_path, {}, alarm, threshold=1)
    forge = pf.PromptForge(prompts_dir=tmp_path, auto_commit=False)
    verdict = forge._transfer_safety_verdict(
        original_content="Base\n",
        mutated_content="Base\nBe careful.\n",
        failure_context="",
        per_suite_quality=None,
        description="d",
    )
    assert not verdict.valid
    assert verdict.reason.startswith("eval_leakage_vocabulary_unavailable")
    assert monitor.consecutive == 1 and len(alarm.raised) == 1


# ── real alarm channel (sandboxed: file backend, disabled push, temp state) ──


@pytest.mark.skipif(not EPYC_ROOT_ALARM.is_file(), reason="epyc-root alarm channel not on host")
def test_real_alarm_channel_raise_and_clear(tmp_path, monkeypatch):
    config = tmp_path / "alarm_config.json"
    record = tmp_path / "alarms.jsonl"
    config.write_text(
        json.dumps({"enabled": False, "backend": "file", "file": {"path": str(record)}})
    )
    monkeypatch.setenv("ALARM_CONFIG_PATH", str(config))
    monkeypatch.setenv("ALARM_STATE_PATH", str(tmp_path / "alarm_state.json"))
    monkeypatch.setenv("ALARM_FILE_PATH", str(record))
    monkeypatch.setenv("ALARM_BACKEND", "file")
    client = mon.AlarmChannelClient(EPYC_ROOT_ALARM)
    assert client.raise_alarm("test raise", {"consecutive": 3}) is True
    state = json.loads((tmp_path / "alarm_state.json").read_text())
    assert mon.ALARM_KEY in state["active"]
    assert state["active"][mon.ALARM_KEY]["severity"] == "critical"
    assert client.clear_alarm("test clear") is True
    state = json.loads((tmp_path / "alarm_state.json").read_text())
    assert mon.ALARM_KEY not in state["active"]
    events = [json.loads(line)["event"] for line in record.read_text().splitlines()]
    assert "raised" in events and "cleared" in events


def test_missing_alarm_channel_is_loud_not_fatal(monkeypatch, tmp_path, caplog):
    monkeypatch.setenv(mon.ALARM_SCRIPT_ENV, str(tmp_path / "absent.py"))
    client = mon.AlarmChannelClient()
    with caplog.at_level(logging.ERROR, logger="autopilot.eval_leakage_monitor"):
        assert client.raise_alarm("x", {}) is False
        assert client.raise_alarm("x", {}) is False
    assert len([r for r in caplog.records if "NOBODY WAS PAGED" in r.getMessage()]) == 1


# ── vocabulary cache: no permanent failure, bounded re-parse ─────────────


def test_missing_source_is_never_cached(pool_env):
    assert not pf.load_eval_id_vocabulary().available
    _write_pool(pool_env)
    assert pf.load_eval_id_vocabulary().available


def test_malformed_pool_is_negative_cached_by_identity(pool_env, monkeypatch):
    pool_env.write_text('{"id": "gsm8k_00001"}\n{not json}\n{"id": "gsm8k_00002"}\n')
    calls = {"n": 0}
    real = pf._iter_eval_rows

    def counting(path):
        calls["n"] += 1
        return real(path)

    monkeypatch.setattr(pf, "_iter_eval_rows", counting)
    first = pf.load_eval_id_vocabulary()
    assert first.error.startswith("eval_id_source_unreadable")
    for _ in range(5):
        assert pf.load_eval_id_vocabulary() is first
    assert calls["n"] == 1  # the malformed pool was parsed ONCE, not on every mutation

    # A replaced file has a new identity: recovery is immediate, no TTL wait.
    _write_pool(pool_env)
    assert pf.load_eval_id_vocabulary().available
    assert calls["n"] == 2


def test_negative_cache_expires_after_ttl(pool_env, monkeypatch):
    pool_env.write_text("{not json}\n")
    ticks = {"t": 100.0}
    monkeypatch.setattr(pf.time, "monotonic", lambda: ticks["t"])
    monkeypatch.setenv(pf.EVAL_ID_VOCAB_NEG_TTL_ENV, "30")
    calls = {"n": 0}
    real = pf._iter_eval_rows

    def counting(path):
        calls["n"] += 1
        return real(path)

    monkeypatch.setattr(pf, "_iter_eval_rows", counting)
    pf.load_eval_id_vocabulary()
    ticks["t"] += 29
    pf.load_eval_id_vocabulary()
    assert calls["n"] == 1
    ticks["t"] += 2
    pf.load_eval_id_vocabulary()
    assert calls["n"] == 2


# ── narrowed generic pattern (reviewer note 3) ───────────────────────────


@pytest.mark.parametrize("text", ["task_index = 0", "sample_id = 1", "task_id: 7", "item_idx=3"])
def test_code_shaped_assignments_are_not_leaks(text):
    vocab = pf.EvalIdVocabulary.from_rows([{"id": "gsm8k_00001", "suite": "gsm8k"}])
    assert vocab.find_leaks(text) == [], text


@pytest.mark.parametrize(
    "text",
    ["if task_id == 17:", "when sample_id is 4", "question id: 42", "task id = 9", "sample #12"],
)
def test_prose_and_comparison_references_still_leak(text):
    vocab = pf.EvalIdVocabulary.from_rows([{"id": "gsm8k_00001", "suite": "gsm8k"}])
    assert vocab.find_leaks(text), text


# ── wiring ────────────────────────────────────────────────────────────────


def test_autopilot_startup_wires_preflight_and_observer():
    source = (ROOT / "scripts" / "autopilot" / "autopilot.py").read_text()
    body = source[source.index("def _run_loop_inner(") :]
    assert "EvalLeakageMonitor(" in body and ".install()" in body
    assert "leakage_monitor.preflight()" in body
    assert body.index("leakage_monitor.preflight()") < body.index("gate = SafetyGate(")


def test_dashboard_summary_exposes_guard_status(tmp_path):
    from src.api.routes import dashboard

    state_path = tmp_path / "autopilot_state.json"
    state_path.write_text(json.dumps({"eval_leakage_guard": {"alarm_active": True}}))
    summary = dashboard._autopilot_state_summary(state_path=state_path)
    assert summary["eval_leakage_guard"] == {"alarm_active": True}
