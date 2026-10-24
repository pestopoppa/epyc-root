"""P1-PHASE2: a journal trial's regime reaches the loop reader's LINEUP tier (DESIGN 5.1, 12.3).

Real path end to end: journal fixture -> `autopilot_journal.emit` -> `Ledger` -> `loop_beliefs.
prepare` with a `{scope: lineup, stack_regime}` target. A row carrying an AP-55 fingerprint is
found at that regime; a row without one, however recent, is not (Phase-1 AC9: "No beliefs at
this regime" until the first post-restart trial)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))
sys.path.insert(0, str(REPO / "tests" / "vidya"))

import loop_beliefs as lb  # noqa: E402
from adapters import autopilot_journal as apj  # noqa: E402
from ledger import Ledger  # noqa: E402
from test_autopilot_journal_adapter import SCOPE, _entry_digest, row, write_journal  # noqa: E402

AS_OF = "2026-10-24T12:00:00+00:00"
REGIME = "a1b2c3d4e5f60718"


class _Sync:
    def status(self, ledger, index):
        return {"fresh": True, "lag_entries": 0, "index_max_id": 1, "synced_max_id": 1,
                "last_sync": "2026-10-24T11:00:00Z"}

    def sync(self, ledger, index):
        return {"action": "noop"}


@pytest.fixture
def alarm(tmp_path):
    cfg = tmp_path / "alarm_config.yaml"
    cfg.write_text(f"backend: file\nfile:\n  path: {tmp_path / 'alarms.jsonl'}\n")
    return {"alarm_state": tmp_path / "alarm_state.json", "alarm_config": cfg}


def _fp(trial_id, regime, **over):
    r = row(trial_id, **over)
    if regime:
        r["measurement"]["infra_fingerprint"] = regime
    r["measurement"]["attestation"]["sha256"] = _entry_digest(r)
    return r


def _lineup(tmp_path, alarm, rows, regime=REGIME):
    root = write_journal(tmp_path / "orch", rows)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    for frame in apj.emit(root, as_of="2026-10-24T00:00:00Z"):
        ledger.append(frame)
    ans = lb.prepare("test.loop", {"scope": "lineup", "stack_regime": regime},
                     ledger=tmp_path / "ledger.jsonl", index_path=tmp_path / "index.yaml",
                     as_of=AS_OF, sync_module=_Sync(), known_good=tmp_path / "kg.json", **alarm)
    assert ans["status"] == "ready", ans.get("detail")
    return ans, ans["evidence"]


def test_a_fingerprinted_trial_reaches_the_lineup_tier(tmp_path, alarm):
    ans, ev = _lineup(tmp_path, alarm, [_fp(1, REGIME)])
    assert ev["tiers"]["lineup"] == 1 and ev["nonempty_target"] is True and ev["banner"] is None
    assert [c["tier"] for c in ev["claims"]] == ["lineup"]


def test_a_belief_scope_trial_reaches_the_lineup_tier(tmp_path, alarm):
    r = _fp(1, REGIME, belief_scope={**SCOPE, "stack_regime": REGIME})
    _, ev = _lineup(tmp_path, alarm, [r])
    assert ev["tiers"]["lineup"] == 1 and ev["nonempty_target"] is True


def test_a_trial_without_a_fingerprint_does_not_reach_the_lineup_tier(tmp_path, alarm):
    ans, ev = _lineup(tmp_path, alarm, [_fp(1, "")])
    assert ev["tiers"]["lineup"] == 0 and ev["nonempty_target"] is False
    assert ans["banner"].startswith("No beliefs at this regime")


def test_another_regime_does_not_reach_this_lineup(tmp_path, alarm):
    ans, ev = _lineup(tmp_path, alarm, [_fp(1, "0" * 16)])
    assert ev["tiers"]["lineup"] == 0
    assert ans["banner"].startswith("No beliefs at this regime")


def test_only_the_post_restart_trial_is_found_at_the_new_regime(tmp_path, alarm):
    old, new = _fp(1, "0" * 16), _fp(2, REGIME)
    _, ev = _lineup(tmp_path, alarm, [old, new])
    assert ev["tiers"]["lineup"] == 1
    assert len(ev["claims"]) == 1 and ev["claims"][0]["stack_regime"] == REGIME
