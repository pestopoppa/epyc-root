"""P1-D: AutoKernel serving floors project as BASELINE observations, graded by the one ladder.

Fixture: tests/vidya/fixtures/belief_p1/floor/q27b -- the real 27B GPU floor
(`q27b-9a3f1392a-gpu-dflash2-np1`, median 81.12 t/s, floor 0.807%, n=10) with its launch
residency trimmed, plus the store's `loop-status.json` target block (see PROVENANCE.json).
"""
from __future__ import annotations

import copy
import dataclasses
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

from adapters import _ak_store_manifest as store_manifest  # noqa: E402
from adapters import autokernel_serving_floor as floor  # noqa: E402
from claim_tuple import ProjectionError, grade, registered, to_frames  # noqa: E402

STORE = ROOT / "tests/vidya/fixtures/belief_p1/floor/q27b"
MODEL = "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"


def _floor_path() -> Path:
    paths = floor.floor_paths(STORE)
    assert len(paths) == 1, "derive the P1 fixtures first (derive_fixtures.py)"
    return paths[0]


def _native(manifest=None, doc=None):
    path = _floor_path()
    real, digest = floor.read_floor(path)
    return floor.native_rows(real if doc is None else doc,
                             locator=f"{floor.LOCATOR_PREFIX}{path}", sha256=digest,
                             store_manifest=manifest)


def test_real_27b_floor_projects_one_baseline_observation():
    (native,) = _native(store_manifest.load(STORE))
    tup = floor.project(native)
    assert tup.category == "BASELINE" and tup.metric == "aggregate_tok_s" and tup.unit == "t/s"
    assert tup.value == pytest.approx(81.1165241567493) and tup.reps == 10
    assert tup.observation == {"outcome": "floor", "noise_floor_rel": pytest.approx(0.00807),
                               "retrofit": True}
    assert tup.date.startswith("2026-10-04")
    assert "residency proven" in tup.claim and "0.807%" in tup.claim
    assert grade(tup)[:2] == ("Judged", "Located")  # no protocol: an observation
    assert tup.measurement_id.startswith("ak-floor:v1:q27b-9a3f1392a-gpu-dflash2-np1:")


def test_store_manifest_scopes_the_floor_to_its_model_when_the_recipe_matches():
    manifest = store_manifest.load(STORE)
    assert manifest["recipe"] == "q27b-9a3f1392a-gpu-dflash2-np1"
    (native,) = _native(manifest)
    scope = floor.project(native).applicability
    assert scope["model_file"] == MODEL and scope["backend"] == "gpu"
    assert len(scope["model_sha256"]) == 64
    assert scope["recipe"] == "q27b-9a3f1392a-gpu-dflash2-np1" and scope["np"] == 1
    assert scope["scope_basis"] == "store_manifest"


def test_a_manifest_for_another_recipe_adds_no_model():
    manifest = copy.deepcopy(store_manifest.load(STORE))
    manifest["recipe"] = "q27b-b0ba1d427-gpu-dflash2-np1"
    (native,) = _native(manifest)
    scope = floor.project(native).applicability
    assert "model_file" not in scope and scope["scope_basis"] == "native"


def test_a_manifest_contradicting_the_floor_backend_adds_no_model():
    manifest = copy.deepcopy(store_manifest.load(STORE))
    manifest["scope"]["backend"] = "cpu"
    (native,) = _native(manifest)
    scope = floor.project(native).applicability
    assert "model_file" not in scope and scope["backend"] == "gpu"


def test_without_a_manifest_the_floor_keeps_its_native_scope_only():
    (native,) = _native(None)
    scope = floor.project(native).applicability
    assert scope == {"recipe": "q27b-9a3f1392a-gpu-dflash2-np1", "np": 1, "backend": "gpu",
                     "scope_basis": "native"}


def test_grade_is_invariant_under_observation_and_scope():
    tup = floor.project(_native(store_manifest.load(STORE))[0])
    assert grade(tup) == grade(dataclasses.replace(tup, observation={}, applicability={}))


def test_frames_are_byte_stable_and_carry_the_floor():
    (native,) = _native(store_manifest.load(STORE))
    a = to_frames(floor.project(native), as_of="t", adapter_id=floor.ADAPTER_ID)
    b = to_frames(floor.project(native), as_of="t", adapter_id=floor.ADAPTER_ID)
    assert [f["frame_id"] for f in a] == [f["frame_id"] for f in b]
    evidence = a[2]["assertion"]
    assert evidence["observation"]["outcome"] == "floor"
    assert evidence["observation"]["noise_floor_rel"] == "0.00807"
    assert evidence["value"] == "81.1165241567"
    assert a[0]["provenance"]["retrofit"] is True


@pytest.mark.parametrize("mutate,match", [
    (lambda d: d.update(median_tok_s=90.0), "re-derive"),
    (lambda d: d.update(n=9), "n"),
    (lambda d: d.update(floor_pct=0.5), "p95_dev_pct"),
    (lambda d: d.update(unit="furlongs"), "unit"),
    (lambda d: d.update(median_tok_s=float("nan")), "positive finite"),
    (lambda d: d.pop("recipe"), "recipe"),
])
def test_a_floor_that_does_not_rederive_is_refused(mutate, match):
    doc, _ = floor.read_floor(_floor_path())
    mutate(doc)
    (native,) = _native(None, doc)
    with pytest.raises(ProjectionError, match=match):
        floor.project(native)


def test_a_mutated_native_row_is_refused():
    (native,) = _native(None)
    native = copy.deepcopy(native)
    native["locator"] = "elsewhere"
    with pytest.raises(ProjectionError):
        floor.project(native)


def test_matched_v2_floors_and_other_documents_project_nothing():
    for doc in ({"schema": "epyc.autokernel.serving_floor.v2"}, {"schema": "x"}, [], None):
        assert floor.native_rows(doc, locator=f"{floor.LOCATOR_PREFIX}/x", sha256="a" * 64) == []


def test_registered_as_a_measurement_projection():
    assert registered()[floor.SOURCE_KIND] is floor.project


def test_store_manifest_reads_nothing_it_cannot_parse(tmp_path):
    assert store_manifest.load(tmp_path) == {}
    (tmp_path / "loop-status.json").write_text(json.dumps({"schema": "other"}))
    assert store_manifest.load(tmp_path) == {}
    body = json.loads((STORE / "loop-status.json").read_text())
    body["target"]["original_target"]["execution"]["model"] = {}
    (tmp_path / "loop-status.json").write_text(json.dumps(body))
    assert store_manifest.load(tmp_path) == {}
