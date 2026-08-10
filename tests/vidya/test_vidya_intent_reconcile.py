"""PR3: intent frames must resolve to a real ratification artifact.

The check passes on the live ledger only because there are no intent frames at all. A test suite
that asserted just that would lock in the vacuum, so every path that MATTERS is exercised on a
synthetic ledger: a frame naming a real file passes, a frame naming a missing file fails, a frame
naming nothing fails, and a path escaping the repo fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from frames import make_frame  # noqa: E402
from intent_reconcile import reconcile  # noqa: E402
from ledger import Ledger  # noqa: E402

AT = "2026-08-10T00:00:00Z"
FT_INTENT = "epyc.vidya/frame/human_intent_recorded/v1"


def intent(artifact):
    assertion = {"intent": "ratify the thing"}
    if artifact is not None:
        assertion["ratification_artifact"] = artifact
    return make_frame(
        frame_type=FT_INTENT,
        assertion=assertion,
        provenance={"method": "operator", "about": "ratification"},
        actor="operator", authority_scope="ratification", created_at=AT,
    )


def build(tmp_path, frames):
    led = Ledger(tmp_path / "ledger.jsonl")
    for f in frames:
        led.append(f)
    return tmp_path / "ledger.jsonl"


def test_empty_ledger_passes_and_says_it_is_vacuous():
    r = reconcile(Path("/nonexistent/ledger.jsonl"))
    assert r["ok"] is True
    assert r["intent_frames"] == 0


def test_frame_naming_a_real_artifact_reconciles(tmp_path):
    real = "docs/design/vidya-pilot-spec.md"
    assert (Path(__file__).resolve().parents[2] / real).is_file(), "fixture needs a real file"
    path = build(tmp_path, [intent(real)])
    r = reconcile(path)
    assert r["ok"] is True and r["intent_frames"] == 1


def test_frame_naming_a_missing_artifact_is_a_defect(tmp_path):
    path = build(tmp_path, [intent("artifacts/operator/ratify-does-not-exist.json")])
    r = reconcile(path)
    assert r["ok"] is False
    assert r["unreconciled"][0]["reason"] == "no such file in the repo"


def test_frame_with_no_artifact_reference_is_a_defect(tmp_path):
    path = build(tmp_path, [intent(None)])
    r = reconcile(path)
    assert r["ok"] is False
    assert r["unreconciled"][0]["reason"] == "no artifact reference at all"


def test_a_path_escaping_the_repo_does_not_count(tmp_path):
    """`/etc/passwd` exists; it is not a ratification artifact."""
    path = build(tmp_path, [intent("../../../../etc/passwd")])
    assert reconcile(path)["ok"] is False


def test_the_live_ledger_currently_has_no_intent_frames():
    """Records the 2026-08-10 state. If this ever fails, the vacuum ended — read the result."""
    r = reconcile()
    assert r["intent_frames"] == 0
    assert r["ok"] is True
