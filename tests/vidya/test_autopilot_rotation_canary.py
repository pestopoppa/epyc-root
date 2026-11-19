"""VB-AP70-ROTATION-READ: `cli.py ingest autopilot-rotation` + the planning-context canary.

SYNTHETIC scratch ledger only. The fixtures follow the orchestrator producer schema (shape, no real
measurement), so passing here proves the reader path end to end and claims NOTHING about a native
AP-70 study: the box's DONE WHEN (a producer-written rotation set) still needs the observer's first
real run.
"""

from __future__ import annotations

import copy
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
import cli  # noqa: E402
from test_autopilot_journal_adapter import _rbundle, _rwrite  # noqa: E402

AS_OF = "2026-11-03T12:00:00+00:00"
REGIME = "a1b2c3d4e5f60718"


class _Sync:
    def status(self, ledger, index):
        return {"fresh": True, "lag_entries": 0, "index_max_id": 1, "synced_max_id": 1,
                "last_sync": "2026-11-03T11:00:00Z"}

    def sync(self, ledger, index):
        return {"action": "noop"}


def _regime(evs, digest=REGIME):
    for e in evs:
        if e.get("type") == apj.ROTATION_PIN:
            e["identity"]["infra_digest"] = digest
        if e.get("type") == apj.ROTATION_PAIR:
            e["incumbent"]["infra_digest"] = digest
    return evs


def _ingest(tmp_path, evs, *extra):
    root = _rwrite(tmp_path / "orch", evs)
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "autopilot-rotation", "--path", str(root),
                   "--as-of", "2026-11-03T00:00:00Z", *extra])
    return rc, ledger


def _prepare(tmp_path, ledger, regime=REGIME):
    cfg = tmp_path / "alarm.yaml"
    cfg.write_text(f"backend: file\nfile:\n  path: {tmp_path / 'alarms.jsonl'}\n")
    ans = lb.prepare("test.loop", {"scope": "lineup", "stack_regime": regime}, ledger=ledger,
                     index_path=tmp_path / "index.yaml", as_of=AS_OF, sync_module=_Sync(),
                     known_good=tmp_path / "kg.json", alarm_state=tmp_path / "st.json", alarm_config=cfg)
    assert ans["status"] == "ready", ans.get("detail")
    return ans, ans["evidence"]


def test_cli_ingest_projects_with_zero_refusals(tmp_path, capsys):
    rc, ledger = _ingest(tmp_path, _regime(_rbundle()))
    report = json.loads(capsys.readouterr().out)
    assert rc == 0 and report["refused"] == [] and report["rows_projected"] == 1
    assert report["frames_emitted"] == 3
    assert len(list(Ledger(ledger).read_all())) == 3


def test_summary_claim_reaches_the_planning_context_at_its_regime(tmp_path, capsys):
    _, ledger = _ingest(tmp_path, _regime(_rbundle()))
    capsys.readouterr()
    ans, ev = _prepare(tmp_path, ledger)
    assert ev["tiers"]["lineup"] == 1 and ev["nonempty_target"] is True
    claim = ev["claims"][0]
    assert claim["tier"] == "lineup" and claim["stack_regime"] == REGIME
    assert "AP-70 core-rotation observation" in json.dumps(ev) and "mean drop" in json.dumps(ev)
    # A different regime must not see it.
    _, other = _prepare(tmp_path, ledger, regime="0" * 16)
    assert other["tiers"]["lineup"] == 0


def test_boundaries_with_different_regimes_are_not_scoped(tmp_path, capsys):
    evs = _regime(_rbundle())
    pins = [e for e in evs if e["type"] == apj.ROTATION_PIN]
    pairs = [e for e in evs if e["type"] == apj.ROTATION_PAIR]
    pins[1]["identity"]["infra_digest"] = "ffff"
    pairs[1]["incumbent"]["infra_digest"] = "ffff"
    _, ledger = _ingest(tmp_path, evs)
    capsys.readouterr()
    _, ev = _prepare(tmp_path, ledger)
    assert ev["tiers"]["lineup"] == 0 and ev["nonempty_target"] is False


@pytest.mark.parametrize("name", ["identity_drift", "missing_sidecar", "synthetic_pair"])
def test_cli_refuses_a_bad_study_and_writes_nothing(tmp_path, capsys, name):
    evs = _regime(_rbundle())
    pair = [e for e in evs if e["type"] == apj.ROTATION_PAIR][0]
    if name == "identity_drift":
        pair["incumbent"]["infra_digest"] = "other"
    elif name == "missing_sidecar":
        pair["outgoing"]["question_sidecar_persistence"]["archive_complete"] = False
    else:
        pair["boundary_trial_id"] = 15
    rc, ledger = _ingest(tmp_path, evs)
    report = json.loads(capsys.readouterr().out)
    assert len(report["refused"]) == 1 and report["frames_emitted"] == 0
    assert not ledger.exists() or not list(Ledger(ledger).read_all())


def test_journal_without_rotation_records_is_declined(tmp_path, capsys):
    rc, ledger = _ingest(tmp_path, [])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0 and report["rows_projected"] == 0 and report["refused"] == []


def test_default_trial_ingest_is_unchanged(tmp_path):
    root = _rwrite(tmp_path, _regime(_rbundle()))
    assert list(apj.emit(root, as_of="2026-11-03T00:00:00Z")) == []
    assert copy.deepcopy(apj.ROTATION_TYPES) == apj.ROTATION_TYPES
