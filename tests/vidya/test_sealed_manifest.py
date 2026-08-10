"""SC4 — sealed measurement manifests, the corpus that can actually reach Q4.

The first version of this adapter keyed claims on the manifest directory's BASENAME. That looked
fine in review and was wrong on the real tree: `sealed_package` is the basename of two different
runs and `input` is the basename of three different ARMS of one run, so six sealed manifests
produced three claims and distinct measurements silently merged. It is the same fake-identity bug
already fixed twice in this program (per-entry claim ids, per-entry source ids) — produced, this
time, by the substrate built to detect it.

So the uniqueness property is pinned first and directly, on paths shaped like the ones that broke.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

from adapters import sealed_manifest as sm  # noqa: E402

SEALED = {
    "status": "SEALED_FOR_OFFICIAL_SCORING",
    "capture_schema_version": "swe-capture/2",
    "observational_provenance": {"sealed_at_utc": "2026-07-27T09:43:34Z"},
    "arms": {"a": {"counts": {"resolved": 12, "unresolved": 8}}},
    "runner_sha256": "b" * 64,
}


def write(root: Path, rel: str, payload: dict) -> Path:
    p = root / "artifacts" / rel / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload))
    return p


# --- identity ------------------------------------------------------------------------------

def test_colliding_basenames_get_distinct_claim_ids(tmp_path, monkeypatch):
    """The exact shape that broke: same basename, different run."""
    monkeypatch.setattr(sm, "RESEARCH_ROOT", tmp_path)
    a = write(tmp_path, "run-20260727T095232Z/sealed_package", SEALED)
    b = write(tmp_path, "run-20260727T095334Z/sealed_package", SEALED)
    ids = {sm.frames_for_manifest(p, as_of="t")[1]["assertion"]["claim_id"] for p in (a, b)}
    assert len(ids) == 2, "two sealed runs collapsed into one claim"


def test_arms_of_one_run_do_not_merge(tmp_path, monkeypatch):
    """`input` named three arms of a single run — merging them fabricates an A/B comparison."""
    monkeypatch.setattr(sm, "RESEARCH_ROOT", tmp_path)
    paths = [write(tmp_path, f"run-1/{arm}/input", SEALED)
             for arm in ("fable_mtp", "fable_non_mtp", "stock_non_mtp")]
    ids = {sm.frames_for_manifest(p, as_of="t")[1]["assertion"]["claim_id"] for p in paths}
    assert len(ids) == 3


def test_identity_is_stable_across_runs(tmp_path, monkeypatch):
    """Re-ingest must not mint a second claim for the same manifest."""
    monkeypatch.setattr(sm, "RESEARCH_ROOT", tmp_path)
    p = write(tmp_path, "run-1/sealed_package", SEALED)
    assert (sm.frames_for_manifest(p, as_of="t1")[1]["assertion"]["claim_id"]
            == sm.frames_for_manifest(p, as_of="t2")[1]["assertion"]["claim_id"])


def test_identity_survives_a_manifest_outside_the_artifacts_root(tmp_path, monkeypatch):
    monkeypatch.setattr(sm, "RESEARCH_ROOT", tmp_path)
    p = tmp_path / "elsewhere" / "sealed_package" / "manifest.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(SEALED))
    frames = sm.frames_for_manifest(p, as_of="t")
    assert frames and frames[1]["assertion"]["claim_id"].startswith("clm_seal_")


# --- what counts as a result ---------------------------------------------------------------

def test_an_unsealed_manifest_is_not_a_result(tmp_path, monkeypatch):
    """A run in progress has numbers in it. That does not make them findings."""
    monkeypatch.setattr(sm, "RESEARCH_ROOT", tmp_path)
    p = write(tmp_path, "run-1/x", {**SEALED, "status": "IN_PROGRESS"})
    assert sm.frames_for_manifest(p, as_of="t") == []


def test_malformed_manifest_yields_nothing_rather_than_raising(tmp_path, monkeypatch):
    monkeypatch.setattr(sm, "RESEARCH_ROOT", tmp_path)
    p = tmp_path / "artifacts" / "run-1" / "manifest.json"
    p.parent.mkdir(parents=True)
    p.write_text("{not json")
    assert sm.frames_for_manifest(p, as_of="t") == []


def test_a_json_list_is_not_a_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(sm, "RESEARCH_ROOT", tmp_path)
    p = write(tmp_path, "run-1/x", SEALED)
    p.write_text("[]")
    assert sm.frames_for_manifest(p, as_of="t") == []


# --- grading -------------------------------------------------------------------------------

def test_missing_protocol_drops_to_observation():
    m = {k: v for k, v in SEALED.items() if k != "capture_schema_version"}
    q, _, reasons = sm.grade(m, artifacts_present=True)
    assert q == "Judged"
    assert any("OBSERVATION" in r for r in reasons)


def test_missing_counts_or_date_stops_short_of_witnessed():
    for drop in ("arms", "observational_provenance"):
        m = {k: v for k, v in SEALED.items() if k != drop}
        assert sm.grade(m, artifacts_present=True)[0] == "Verified"


def test_absent_artifacts_grade_down_rather_than_being_skipped():
    """Silently dropping these would hide exactly the decay the substrate is for."""
    q, t, reasons = sm.grade(SEALED, artifacts_present=False)
    assert (q, t) == ("Witnessed", "Anchored")
    assert any("proves nothing" in r for r in reasons)


def test_full_manifest_with_present_artifacts_reaches_attested():
    assert sm.grade(SEALED, artifacts_present=True)[:2] == ("Witnessed", "Attested")


def test_reps_sum_across_arms():
    m = {**SEALED, "arms": {"a": {"counts": {"x": 3}}, "b": {"counts": {"x": 4, "y": 1}}}}
    assert sm.reps(m) == 8


def test_reps_ignores_non_integer_counts():
    m = {**SEALED, "arms": {"a": {"counts": {"x": "many", "y": 2}}}}
    assert sm.reps(m) == 2


def test_attestations_collects_nested_authority_digests():
    m = {**SEALED, "authority": {"results.json": {"sha256": "c" * 64},
                                 "notes.md": {"sha256": "not-a-digest"}}}
    atts = sm.attestations(m)
    assert "authority/results.json" in atts
    assert "authority/notes.md" not in atts
    assert "runner_sha256" in atts


def test_artifacts_present_is_false_when_one_of_several_is_missing(tmp_path, monkeypatch):
    """All-or-nothing: a partially-present package is not an attested one."""
    monkeypatch.setattr(sm, "RESEARCH_ROOT", tmp_path)
    m = {**SEALED, "authority": {"a.json": {"sha256": "c" * 64},
                                 "b.json": {"sha256": "d" * 64}}}
    p = write(tmp_path, "run-1/x", m)
    (p.parent / "authority").mkdir()
    (p.parent / "authority" / "a.json").write_text("{}")
    assert sm._artifacts_present(p, m) is False
    (p.parent / "authority" / "b.json").write_text("{}")
    assert sm._artifacts_present(p, m) is True
