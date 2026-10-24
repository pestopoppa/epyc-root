"""VB-AKX-LB32-WRITE: AKX-ALL-LB3.2 attribution sidecar -> OBSERVATION tuples graded by the one shared ladder.

Fixture `fixtures/akx_lb32/` was written by the research producer (`akx_lb3_attribution/beliefs.py`, branch
f8/akx-lb3-2a-attribution-20261024 @ c0d77e890) from a synthetic SPLIT_UNRESOLVED verdict (F 6% at t48, 7% at t96,
seed class node:mask_build). Its attested paths are the worktree it was written in; the tests re-home the rows into
tmp_path and re-seal them, so the attestation is exercised for real.
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import akx_lb32 as ax  # noqa: E402

FX = Path(__file__).resolve().parent / "fixtures" / "akx_lb32"
WHEN = "2026-10-24T13:00:00Z"


def fixture_rows():
    return [json.loads(l) for l in (FX / ax.SIDECAR_NAME).read_text().splitlines() if l.strip()]


def rehome(tmp_path, mutate=None):
    """Copy VERDICT.json + PREDECLARATION.md to tmp_path, point every row at them, re-derive ids and seals."""
    for name in ("VERDICT.json", "PREDECLARATION.md"):
        shutil.copy(FX / name, tmp_path / name)
    rows = []
    for r in fixture_rows():
        r["results_path"] = str(tmp_path / "VERDICT.json")
        r["extra"]["predeclaration_path"] = str(tmp_path / "PREDECLARATION.md")
        if mutate:
            mutate(r)
        r.pop("row_sha256", None)
        ns.seal(r)
        rows.append(r)
    side = tmp_path / ax.SIDECAR_NAME
    side.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    return side


def write(tmp_path):
    """End-to-end builder for test_ingest_sources: a re-homed, attested sidecar."""
    return rehome(Path(tmp_path))


def test_fixture_rows_are_well_formed_as_written():
    rows = fixture_rows()
    assert len(rows) == 13
    for r in rows:
        bad = [p for p in ax.row_problems(r) if "predeclaration no longer" not in p]
        assert bad == [], bad


def test_round_trip_cells_and_verdict_graded_by_shared_ladder(tmp_path):
    side = rehome(tmp_path)
    natives = ax.native_rows(side)
    assert len(natives) == 13 and all(n["attestation_present"] for n in natives)
    tuples = [ax.project(n) for n in natives]
    cells = [t for t in tuples if t.extra["kind"] == "cell"]
    verdict = [t for t in tuples if t.extra["kind"] == "verdict"]
    assert len(cells) == 12 and len(verdict) == 1
    v = verdict[0]
    assert v.extra["verdict"] == "SPLIT_UNRESOLVED" and v.extra["seed_class"] == "node:mask_build"
    assert v.value == pytest.approx(0.06)
    c = next(t for t in cells if t.extra["threads"] == 48 and t.extra["n_prompt"] == 4)
    assert c.value == pytest.approx(0.06) and c.applicability["knobs"]["n_prompt"] == 4
    for t in tuples:
        assert t.protocol_id == "" and t.attestation_present is True
        assert ct.grade(t)[:2] == ("Judged", "Located")
    assert ax.frames_for_sidecar(side, as_of=WHEN)


@pytest.mark.parametrize("mutate,needle", [
    (lambda r: r.__setitem__("value", r["value"] + 0.01), "value must equal"),
    (lambda r: r.__setitem__("protocol_id", "lb3-proto"), "protocol_id must be empty"),
    (lambda r: r["extra"].__setitem__("threads", 64), "threads"),
])
def test_rows_that_do_not_re_derive_void_the_file(tmp_path, mutate, needle):
    first = {"done": False}

    def once(r):
        if not first["done"]:
            first["done"] = True
            mutate(r)
    side = rehome(tmp_path, once)
    assert ax.native_rows(side) == ()            # the writer is atomic: one bad row voids the whole file
    bad = fixture_rows()[0]
    mutate(bad)
    assert any(needle in p for p in ax.row_problems(bad))


def test_verdict_must_follow_from_its_own_numbers(tmp_path):
    def flip(r):
        if r["extra"]["kind"] == "verdict":
            r["extra"]["verdict"] = "LANE_LARGE"
    side = rehome(tmp_path, flip)
    assert ax.native_rows(side) == ()
    row = next(r for r in fixture_rows() if r["extra"]["kind"] == "verdict")
    row["extra"]["verdict"] = "INVALID"
    assert any("INVALID never projects" in p for p in ax.row_problems(row))


def test_edited_predeclaration_voids_the_rows(tmp_path):
    side = rehome(tmp_path)
    (tmp_path / "PREDECLARATION.md").write_text("# edited after the run\n")
    assert ax.native_rows(side) == ()


def test_missing_verdict_file_keeps_rows_but_attestation_absent(tmp_path):
    side = rehome(tmp_path)
    (tmp_path / "VERDICT.json").unlink()
    natives = ax.native_rows(side)
    assert len(natives) == 13 and not any(n["attestation_present"] for n in natives)


def test_ingest_source_is_wired():
    import ingest_sources
    src = ingest_sources.SOURCES["akx-lb32"]
    assert src.module == "akx_lb32" and src.task == "VB-AKX-LB32-WRITE"
    assert src.units(FX) == [FX / ax.SIDECAR_NAME]
