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


def control_fixture(tmp_path):
    """Retained, hash-bound evidence with the prospective control producer's shape."""
    import copy

    def ref(path):
        return {"path": str(path), "sha256": ns.file_sha256(path)}

    def save(path, value):
        path.write_text(json.dumps(value, sort_keys=True))

    rules = tmp_path / "rules"
    rules.mkdir()
    shutil.copy(FX / "PREDECLARATION.md", rules / "PREDECLARATION.md")
    rules.joinpath("pair-state").mkdir()
    for name in ("AMENDMENT-control-v2.md", "AMENDMENT-control-v2.sha256", "PAIR-DECLARATION.sh",
                 "AMENDMENT-affinity-v3.md", "REBASED-INSTRUMENTATION.patch", "pair-state/GRANT.txt"):
        (rules / name).write_text(name)
    roots = []
    controls = []
    for order in ("GM", "MG"):
        root = tmp_path / order
        root.mkdir()
        out = root / "out"
        out.mkdir()
        fields = dict(version=ax.CONTROL_VERSION, source="c72ec82f5417bb2937310326120f149b665e8400",
                      research="1" * 40, run="run-" + order, pair="pair-one", order=order,
                      G="/store/champion", M=str(root / "build-M"), threads="48", reported_threads="96",
                      grant="grant-one", champion="2" * 40)
        manifest = root / "INSTRUMENT.txt"
        manifest.write_text("".join(k + "=" + fields[k] + "\n" for k in ax.IDENTITY_KEYS))
        shutil.copy(FX / "VERDICT.json", root / "VERDICT.json")
        record = dict(schema="epyc.akx_lb32.run_record.v2", instrument=ax.CONTROL_VERSION,
                      run_id=fields["run"], pair_id=fields["pair"], arm_order=order,
                      manifest_sha256=ns.file_sha256(manifest), source_sha=fields["source"],
                      measurement_sha=fields["source"], research_sha=fields["research"],
                      control_build=fields["G"], measurement_build=fields["M"], verdict="SPLIT_UNRESOLVED")
        save(root / "RUN_RECORD.json", record)
        evidence = []
        for arm in ("G", "M"):
            for suffix in (".cache-options.txt", ".compiler-identity.txt", ".compiler-executables.txt", ".sha256"):
                path = out / ("B0." + arm + suffix)
                path.write_text(arm + suffix)
                evidence.append(ref(path))
        start_evidence = [ref(manifest)] + [ref(path) for path in sorted(rules.rglob("*")) if path.is_file()] + evidence
        start = dict(schema=ax.CONTROL_SCHEMA, instrument=fields, baseline_kind="champion_store_profiler_off",
                     baseline_claim="Verified champion profiler off", evidence=start_evidence)
        save(root / "CONTROL_CAPTURE_START.json", start)
        controls.append(dict(start=ref(root / "CONTROL_CAPTURE_START.json"), manifest=ref(manifest),
                             run_record=ref(root / "RUN_RECORD.json"), baseline_kind=start["baseline_kind"],
                             baseline_claim=start["baseline_claim"], identity=fields, evidence=evidence,
                             perf_informational=[]))
        roots.append(root)
    pair_path = rules / "PAIR_VERDICT.json"
    save(pair_path, dict(schema="epyc.akx_lb32.pair_verdict.v1", pair_id="pair-one", grant="grant-one",
                         pair_verdict="SPLIT_UNRESOLVED", GM="SPLIT_UNRESOLVED", MG="SPLIT_UNRESOLVED",
                         one_fixed_pair=True, no_averaging=True, runs=[ref(r / "VERDICT.json") for r in roots]))
    rows = []
    for r in fixture_rows():
        r["schema"] = ax.CONTROL_SCHEMA
        r["run_id"] = "run-GM"
        r["results_path"] = str(roots[0] / "VERDICT.json")
        r["extra"]["predeclaration_path"] = str(rules / "PREDECLARATION.md")
        r["extra"]["control_instrument"] = copy.deepcopy(controls[0])
        r["extra"]["control_instrument"]["pair_result"] = ref(pair_path)
        e = r["extra"]
        r["measurement_id"] = "akxlb32_" + ns.content_hash(dict(run_id=r["run_id"], kind=e["kind"],
            threads=e["threads"], n_prompt=e.get("n_prompt"), results=r["results_sha256"]))[:24]
        rows.append(ns.seal(r))
    return rows


def test_v2_control_round_trip_and_shared_grade(tmp_path):
    rows = control_fixture(tmp_path)
    side = tmp_path / ax.SIDECAR_NAME
    side.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert len(ax.native_rows(side)) == 13
    for row in rows:
        assert ax.row_problems(row) == []
        assert ct.grade(ax.project({"row": row}))[:2] == ("Judged", "Located")
    Path(rows[0]["extra"]["control_instrument"]["run_record"]["path"]).unlink()
    assert ax.native_rows(side) == ()


@pytest.mark.parametrize("target", ["start", "manifest", "run_record", "pair_result", "native", "evidence"])
def test_v2_changed_or_missing_bound_files_fail_closed(tmp_path, target):
    row = control_fixture(tmp_path)[0]
    c = row["extra"]["control_instrument"]
    ref = c["evidence"][0] if target == "evidence" else (
        {"path": row["results_path"]} if target == "native" else c[target])
    Path(ref["path"]).write_text("changed")
    assert ax.row_problems(row)
    Path(ref["path"]).unlink()
    assert ax.row_problems(row)


@pytest.mark.parametrize("mutation", ["grant", "order", "membership", "duplicate", "native", "record", "row", "escape", "identity"])
def test_v2_resealed_tampering_fails_closed(tmp_path, mutation):
    row = control_fixture(tmp_path)[0]
    c = row["extra"]["control_instrument"]
    pair_path = Path(c["pair_result"]["path"])
    pair = json.loads(pair_path.read_text())
    if mutation == "grant":
        pair["grant"] = "other-grant"
    elif mutation == "order":
        pair["runs"].reverse()
    elif mutation == "membership":
        unrelated = tmp_path / "VERDICT.json"
        shutil.copy(row["results_path"], unrelated)
        pair["runs"][0]["path"] = str(unrelated)
    elif mutation == "duplicate":
        pair["runs"][1] = pair["runs"][0]
    elif mutation == "native":
        path = Path(pair["runs"][1]["path"])
        native = json.loads(path.read_text())
        native["gating"]["cells"]["2"]["F_fa_wall_share"] = .9
        path.write_text(json.dumps(native))
        pair["runs"][1]["sha256"] = ns.file_sha256(path)
    elif mutation == "record":
        path = Path(c["run_record"]["path"])
        record = json.loads(path.read_text())
        record["pair_id"] = "other-pair"
        path.write_text(json.dumps(record))
        c["run_record"]["sha256"] = ns.file_sha256(path)
    elif mutation == "row":
        row["value"] += .01
        row["extra"]["F_fa_wall_share"] = row["value"]
    elif mutation == "escape":
        outside = tmp_path / "outside"
        outside.write_text("outside")
        c["evidence"][0] = dict(path=str(outside), sha256=ns.file_sha256(outside))
    else:
        c["identity"]["run"] = "other-run"
    pair_path.write_text(json.dumps(pair))
    c["pair_result"]["sha256"] = ns.file_sha256(pair_path)
    ns.seal(row)
    assert ax.row_problems(row)


def test_v2_without_nested_control_is_refused(tmp_path):
    row = control_fixture(tmp_path)[0]
    del row["extra"]["control_instrument"]
    ns.seal(row)
    assert ax.row_problems(row)
