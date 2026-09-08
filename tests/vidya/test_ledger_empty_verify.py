"""SC73 — `ledger.verify()` must not report OK on an empty or deleted ledger.

A verifier that passes on the absence of the thing it verifies is the fail-open shape
(`feedback_fail_open_defaults_conceal_their_own_corruption`): the strongest possible reading of
"chain=OK" was produced by having no chain at all. `verify()` returned a list of problems, and the
empty ledger produced no problems — because the loop never ran. A truncated-to-zero or deleted
ledger is internally consistent (any prefix of a hash chain chains), so only the ledger's ABSENCE
from the verifier's expectations catches it.

Two requirements before OK: the ledger must not be empty, and — when the caller holds a declared
count (a published checkpoint frontier) — the ledger must not be shorter than it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import frames as fr  # noqa: E402
from ledger import Ledger  # noqa: E402

NOW = "2026-09-07T00:00:00Z"


def _frame(i):
    return fr.make_frame(
        frame_type="epyc.vidya/frame/evidence_supports_claim/v1",
        assertion={"claim_id": f"clm-{i}", "evidence_id": f"evd-{i}",
                   "grade": {"Q": "Judged", "T": "Anchored"}},
        provenance={"method": "test", "anchor": f"anchor:{i}"},
        actor="test", authority_scope="test", created_at=NOW)


def test_a_missing_ledger_does_not_verify(tmp_path):
    """CATCHES: verify() on a ledger file that does not exist returned [] — chain=OK on nothing."""
    led = Ledger(tmp_path / "never-created.jsonl")
    problems = led.verify()
    assert problems, "a missing ledger must not verify clean"
    assert any("no records" in p for p in problems)


def test_an_empty_ledger_does_not_verify(tmp_path):
    """CATCHES: verify() on a ledger truncated to zero bytes returned [] — the file is gone in
    every way that matters while still existing."""
    path = tmp_path / "empty.jsonl"
    path.write_text("")
    problems = Ledger(path).verify()
    assert problems, "an empty ledger must not verify clean"
    assert any("no records" in p for p in problems)


def test_a_deleted_ledger_is_not_covered_by_a_stale_head_cache(tmp_path):
    """MUTATION for the two above: the append-time head cache must not resurrect a vanished file
    into a clean verdict."""
    path = tmp_path / "ledger.jsonl"
    led = Ledger(path)
    led.append(_frame(1))
    led.append(_frame(2))
    path.unlink()
    problems = led.verify()
    assert problems and any("no records" in p for p in problems)


def test_a_non_empty_ledger_still_verifies_clean(tmp_path):
    """MUTATION for the emptiness refusals: the guard must bite on absence, not on everything."""
    led = Ledger(tmp_path / "ok.jsonl")
    for i in range(3):
        led.append(_frame(i))
    assert led.verify() == []


def test_a_ledger_shorter_than_the_declared_count_fails(tmp_path):
    """CATCHES: truncation below the last published checkpoint frontier. Any prefix of a hash
    chain chains — only the declared count sees that records are missing."""
    led = Ledger(tmp_path / "truncated.jsonl")
    for i in range(3):
        led.append(_frame(i))
    problems = led.verify(expected_count=5)
    assert any("declared" in p for p in problems)


def test_a_ledger_at_or_past_the_declared_count_passes(tmp_path):
    """MUTATION for the truncation check: appending past a checkpoint is legal — the ledger only
    fails when it is SHORTER than what was declared."""
    led = Ledger(tmp_path / "grown.jsonl")
    for i in range(3):
        led.append(_frame(i))
    assert led.verify(expected_count=3) == []
    led.append(_frame(3))
    assert led.verify(expected_count=3) == []
