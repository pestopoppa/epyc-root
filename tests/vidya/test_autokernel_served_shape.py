"""AutoKernel served-shape oracle calibration: strict re-derivation, projection, scoped-store wiring (VB-AK-SERVED-SHAPE)."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

VIDYA = Path(__file__).resolve().parents[2] / "scripts/vidya"
sys.path.insert(0, str(VIDYA))

import claim_tuple as ct  # noqa: E402
import ingest_sources as ing  # noqa: E402
import loop_beliefs as lb  # noqa: E402
import scoped_ingest as si  # noqa: E402
from adapters import autokernel_served_shape as ss  # noqa: E402
from ledger import Ledger  # noqa: E402

COMMIT = "dd3d9721ca37321ad9159520bbd9616e3d0d6228"
MODEL_SHA = "6" * 64
# (shape, type) -> per-width anchor NMSE; the IQ3_XXS shexp case is above the generic cap (anchor-relative).
NMSE = {("ds41_expert_gate_up", "Q4_0"): [3.3e-5, 1e-9, 0.0, 2e-9, 3e-9],
        ("ds41_shexp_down", "IQ3_XXS"): [1e-4, 5.96e-4, 2e-4, 1e-4, 1e-4]}
WIDTHS = (1, 2, 3, 4, 5)


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _w(p: Path, o) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o, indent=1, sort_keys=True), encoding="utf-8")


def make_store(tmp: Path, *, launch_drift: bool = False, second_cal: bool = True) -> Path:
    store = tmp / "store"
    unit = store / "served_shape"
    build = tmp / "build-calib"
    (build / "bin").mkdir(parents=True)
    digests = {}
    for name in ("libggml-cpu.so", "test-backend-ops"):
        (build / "bin" / name).write_bytes(name.encode())
        digests[name] = _sha(name.encode())
    launch = tmp / "launch.json"
    _w(launch, {"model": {"path": "/m/DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf", "sha256": MODEL_SHA}})
    launch_sha = _sha(launch.read_bytes())
    if launch_drift:
        _w(launch, {"model": {"path": "/m/other.gguf", "sha256": MODEL_SHA}, "regenerated": True})
    meas, cases, rel = [], [], []
    for (shape, typ), vals in NMSE.items():
        for n, v in zip(WIDTHS, vals):
            meas.append({"shape_name": shape, "type_a": typ, "n": n, "nmse": v})
            if v >= ss.NMSE_CAP:
                rel.append([shape, typ, n])
            cases.append({"shape_name": shape, "type_a": typ, "n": n,
                          "max_nmse": ss.derive_bound(v, v >= ss.NMSE_CAP)})
    manifest = {"schema": "epyc.autokernel.served_shape_manifest.v1", "case_set_id": "served_shape_lowbit_v1",
                "lane": "ds41", "seed_scheme": ss.SEED_SCHEME, "cases": cases, "anchor_relative": rel,
                "partition": ["ds41_expert_gate_up", "ds41_shexp_down"]}
    _w(unit / "manifest.json", manifest)
    (unit / "patch.cpp").write_text("\n".join(f"case {c['max_nmse']:g}" for c in cases), encoding="utf-8")
    prov = {"anchor_commit": COMMIT, "anchor_build": str(build), "binary_digests": digests, "launch": str(launch),
            "launch_sha256": launch_sha}
    for ts in (["20261021T145108Z", "20261021T154353Z"] if second_cal else ["20261021T154353Z"]):
        _w(unit / f"calibration-{ts}.json",
           {"schema": ss.CAL_SCHEMA, "case_set_id": "served_shape_lowbit_v1", "lane": "ds41",
            "seed_scheme": ss.SEED_SCHEME, "measurements": meas,
            "provenance": {**prov, "measured_at": f"2026-10-21T{ts[9:11]}:{ts[11:13]}:{ts[13:15]}+00:00"}})
    return store


def tuples(unit: Path):
    return [(ss.project_verifier if r["kind"] == "verifier" else ss.project_measurement)(r)
            for r in ss.native_rows(unit)]


def test_projects_measurement_and_verifier_per_shape_type(tmp_path):
    store = make_store(tmp_path)
    rows = ss.native_rows(store / "served_shape")
    assert len(rows) == 4 and {r["kind"] for r in rows} == {"measurement", "verifier"}
    assert rows[0]["reps"] == 2 and rows[0]["launch"]["binding"] == "verified"
    for t in tuples(store / "served_shape"):
        assert t.protocol_id == "" and t.observation["retrofit"] is True
        assert t.applicability["model_file"].startswith("DeepSeek-V4.1-Flash-1017-MXFP4")
        assert t.applicability["model_sha256"] == MODEL_SHA and t.applicability["build_sha"] == COMMIT
        q, tt, _ = ct.grade(t)
        assert (q, tt) == ("Judged", "Located")
    ver = [t for t in tuples(store / "served_shape") if t.source_kind == ss.VERIFIER_KIND]
    assert all(t.decided_proposition.startswith("PASS:") and "max_nmse" in t.decided_proposition for t in ver)
    assert all(t.source_class == "verifier" and t.value <= 1.0 for t in ver)
    rel = next(t for t in ver if "IQ3_XXS" in t.measurement_id)
    assert "anchor-relative for n=2" in rel.decided_proposition


def test_refuses_when_manifest_cap_does_not_rederive(tmp_path):
    store = make_store(tmp_path)
    p = store / "served_shape/manifest.json"
    m = json.loads(p.read_text())
    m["cases"][0]["max_nmse"] *= 2
    p.write_text(json.dumps(m))
    (store / "served_shape/patch.cpp").write_text("\n".join(f"{c['max_nmse']:g}" for c in m["cases"]))
    with pytest.raises(ct.ProjectionError, match="re-derives the manifest"):
        ss.native_rows(store / "served_shape")


def test_refuses_on_anchor_build_rehash_mismatch_and_disagreeing_calibrations(tmp_path):
    store = make_store(tmp_path)
    (tmp_path / "build-calib/bin/test-backend-ops").write_bytes(b"swapped")
    with pytest.raises(ct.ProjectionError, match="re-hashes"):
        ss.native_rows(store / "served_shape")
    store2 = make_store(tmp_path / "b")
    p = store2 / "served_shape/calibration-20261021T145108Z.json"
    c = json.loads(p.read_text())
    c["provenance"]["binary_digests"]["libggml-cpu.so"] = "0" * 64
    p.write_text(json.dumps(c))
    with pytest.raises(ct.ProjectionError):
        ss.native_rows(store2 / "served_shape")


def test_refuses_when_patch_lacks_a_cap(tmp_path):
    store = make_store(tmp_path)
    (store / "served_shape/patch.cpp").write_text("nothing")
    with pytest.raises(ct.ProjectionError, match="patch.cpp"):
        ss.native_rows(store / "served_shape")


def test_launch_drift_declares_no_model_binding(tmp_path):
    store = make_store(tmp_path, launch_drift=True)
    rows = ss.native_rows(store / "served_shape")
    assert rows[0]["launch"]["binding"].startswith("drifted")
    for t in tuples(store / "served_shape"):
        assert "model_file" not in t.applicability and t.extra["launch_binding"].startswith("drifted")


def test_ingest_source_and_loop_beliefs_reach_the_target(tmp_path):
    store = make_store(tmp_path)
    src = ing.SOURCES["autokernel-served-shape"]
    assert src.units(store / "served_shape") == [store / "served_shape"]
    frames = []
    for t in tuples(store / "served_shape"):
        frames.extend(ct.to_frames(t, as_of="2026-10-24T00:00:00Z", adapter_id=ss.ADAPTER_ID, authority=ss.AUTHORITY))
    target = lb.Target.from_mapping({"model_file": "DeepSeek-V4.1-Flash-1017-MXFP4-experts-00001-of-00009.gguf",
                                     "backend": "cpu"})
    ev = lb.evaluate_frames(frames, [target], as_of="2026-10-24T01:00:00Z")
    assert ev["tiers"]["target"] == 4


def test_scoped_store_ingest_is_idempotent_and_memoises_refusals(tmp_path):
    store = make_store(tmp_path)
    led = tmp_path / "ledger.jsonl"
    memo = tmp_path / "memo.json"
    r1 = si.ingest_scoped_store(led, store, as_of="2026-10-24T00:00:00Z", memo_path=memo)
    assert r1["served_shape_projected"] == 4 and r1["new_claims"] == 4 and r1["refusals"] == []
    assert len(Ledger(led)) == 12
    r2 = si.ingest_scoped_store(led, store, as_of="2026-10-24T00:01:00Z", memo_path=memo)
    assert r2["served_shape_known"] == 4 and r2["frames_appended"] == 0 and len(Ledger(led)) == 12
    bad = make_store(tmp_path / "bad")
    (bad / "served_shape/patch.cpp").write_text("x")
    memo2 = tmp_path / "memo2.json"
    led2 = tmp_path / "ledger2.jsonl"
    a = si.ingest_scoped_store(led2, bad, as_of="2026-10-24T00:00:00Z", memo_path=memo2)
    b = si.ingest_scoped_store(led2, bad, as_of="2026-10-24T00:01:00Z", memo_path=memo2)
    assert len(a["refusals"]) == 1 and b["served_shape_memo_refused"] == 1 and b["refusals"] == []


def _recalibrate_against_current_recipe(store: Path, ts: str = "20261024T120000Z") -> Path:
    """P1-PHASE2-SERVED-SHAPE-RECAL: a third run of the same anchor binary (same NMSE, same digests) that recorded
    the sha256 the regenerated launch recipe has NOW."""
    unit = store / "served_shape"
    base = json.loads((unit / "calibration-20261021T154353Z.json").read_text())
    launch = Path(base["provenance"]["launch"])
    base["provenance"]["launch_sha256"] = _sha(launch.read_bytes())
    base["provenance"]["measured_at"] = f"2026-10-24T{ts[9:11]}:{ts[11:13]}:{ts[13:15]}+00:00"
    out = unit / f"calibration-{ts}.json"
    _w(out, base)
    return out


def test_recalibration_against_current_recipe_binds_model_with_the_same_claim_ids(tmp_path):
    store = make_store(tmp_path, launch_drift=True)
    drifted = {t.measurement_id: t for t in tuples(store / "served_shape")}
    assert all("model_file" not in t.applicability for t in drifted.values())
    assert all("launch_bound_calibrations" not in t.extra for t in drifted.values())
    _recalibrate_against_current_recipe(store)
    rows = ss.native_rows(store / "served_shape")
    assert rows[0]["launch"]["binding"] == "verified" and rows[0]["reps"] == 3
    assert rows[0]["launch"]["bound_calibrations"] == ["calibration-20261024T120000Z.json"]
    bound = {t.measurement_id: t for t in tuples(store / "served_shape")}
    assert set(bound) == set(drifted)                      # same claim ids, re-scoped
    for t in bound.values():
        assert t.applicability["model_file"] == "other.gguf" and t.applicability["model_sha256"] == MODEL_SHA
        assert t.extra["launch_binding"] == "verified"
        assert t.extra["launch_bound_calibrations"] == ["calibration-20261024T120000Z.json"]
        assert ct.grade(t)[:2] == ("Judged", "Located")


def test_recalibration_with_different_nmse_or_binary_refuses_rather_than_binding(tmp_path):
    store = make_store(tmp_path, launch_drift=True)
    p = _recalibrate_against_current_recipe(store)
    c = json.loads(p.read_text())
    c["measurements"][1]["nmse"] = c["measurements"][1]["nmse"] * 1.5
    p.write_text(json.dumps(c))
    with pytest.raises(ct.ProjectionError, match="disagree on a NMSE"):
        ss.native_rows(store / "served_shape")
    store2 = make_store(tmp_path / "b", launch_drift=True)
    p2 = _recalibrate_against_current_recipe(store2)
    c2 = json.loads(p2.read_text())
    c2["provenance"]["binary_digests"]["test-backend-ops"] = "1" * 64
    p2.write_text(json.dumps(c2))
    with pytest.raises(ct.ProjectionError, match="binary digests"):
        ss.native_rows(store2 / "served_shape")


def test_bound_calibrations_naming_different_models_refuse(tmp_path):
    store = make_store(tmp_path, launch_drift=True)
    p = _recalibrate_against_current_recipe(store)
    other = tmp_path / "launch2.json"
    _w(other, {"model": {"path": "/m/third.gguf", "sha256": "7" * 64}})
    q = _recalibrate_against_current_recipe(store, ts="20261024T130000Z")
    c = json.loads(q.read_text())
    c["provenance"]["launch"], c["provenance"]["launch_sha256"] = str(other), _sha(other.read_bytes())
    q.write_text(json.dumps(c))
    assert p.is_file()
    with pytest.raises(ct.ProjectionError, match="different models"):
        ss.native_rows(store / "served_shape")


def test_reingest_after_recalibration_reaches_the_model_target(tmp_path):
    store = make_store(tmp_path, launch_drift=True)
    led = Ledger(tmp_path / "ledger.jsonl")
    ing.ingest(led, "autokernel-served-shape", [store / "served_shape"], as_of="2026-10-22T00:00:00Z")
    target = lb.Target.from_mapping({"model_file": "other.gguf", "backend": "cpu"})
    before = lb.evaluate_frames([r.frame for r in led], [target], as_of="2026-10-22T00:30:00Z")
    assert before["tiers"].get("target", 0) == 0
    _recalibrate_against_current_recipe(store, ts="20261022T120000Z")
    ing.ingest(led, "autokernel-served-shape", [store / "served_shape"], as_of="2026-10-23T00:00:00Z")
    after = lb.evaluate_frames([r.frame for r in led], [target], as_of="2026-10-23T00:30:00Z")
    assert after["tiers"]["target"] == 4
