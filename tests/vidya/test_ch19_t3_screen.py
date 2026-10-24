"""VB-CH19-T3-SCREEN-WIRE: the CH-19.2 T3 speed screen projects to re-derived, scoped OBSERVATION tuples.

The fixture under ``fixtures/ch19_t3_screen/`` is a TRIMMED COPY of the real 2026-10-21 screen (preflight plus pairs 1-3,
provenance ``pairs`` set to 3, summary regenerated with the producer's own renderer); the real directory, when present
on this host, is checked against the producer's printed summary.
"""
import json
import shutil
import statistics
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import ch19_t3_screen as m  # noqa: E402

FIX = ROOT / "tests" / "vidya" / "fixtures" / "ch19_t3_screen" / "20261021T191000Z"
REAL = Path("/mnt/raid0/llm/tmp/intake-fixes-20261020/t3-ch19-screen/20261021T191000Z")
AS_OF = "2026-10-24T12:00:00Z"


@pytest.fixture(autouse=True)
def _no_producer(monkeypatch, tmp_path):
    monkeypatch.setattr(m, "PRODUCER_PATH", tmp_path / "absent-producer.sh")


@pytest.fixture
def unit(tmp_path):
    dst = tmp_path / "screen" / FIX.name
    shutil.copytree(FIX, dst)
    return dst


def _load(u):
    return [json.loads(x) for x in (u / "records.jsonl").read_text().splitlines()]


def _save(u, rows, *, resummarise=True):
    (u / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    if resummarise:
        body = [r for r in rows if not r["arm"].startswith("preflight")]
        per = {}
        for r in body:
            if r["valid"] and r["avg_ts"] is not None:
                per.setdefault((r["n_prompt"], r["n_gen"], r["n_depth"]), {}).setdefault(
                    r["arm"].split("-")[0], {})[r["switch"]] = r["avg_ts"]
        inv = sorted({r["arm"] + ": " + r["why"] for r in body if not r["valid"]})
        (u / "summary.txt").write_text(m._summary_text(per, inv))


def _tuples(u):
    return [m.project(n) for n in m.native_rows(u)]


def test_fixture_projects_ratio_arm_and_invalid_rows(unit):
    nat = m.native_rows(unit)
    assert sorted(n["kind"] for n in nat).count("ratio") == 4
    assert [n["kind"] for n in nat].count("arm_median") == 8
    assert [n["kind"] for n in nat].count("invalid") == 1
    for t in _tuples(unit):
        assert ct.grade(t)[:2] == ("Judged", "Located")  # no protocol: the shared ladder says OBSERVATION
        assert t.protocol_id == "" and t.attestation_verified is True


def test_ratio_is_the_median_of_pair_ratios_with_a_derived_floor(unit):
    rows = _load(unit)
    proc = {}
    for r in rows:
        if r["arm"].startswith("p") and (r["n_prompt"], r["n_depth"]) == (512, 0):
            proc.setdefault(r["arm"].split("-")[0], {})[r["switch"]] = r["avg_ts"]
    want = statistics.median([v["on"] / v["off"] for v in proc.values()])
    offs = [proc[p]["off"] for p in sorted(proc)]
    floor = max(abs(b / a - 1) for a, b in zip(offs, offs[1:]))
    t = next(t for t in _tuples(unit) if t.metric == "ch19_t3_upgate_on_over_off_pp512_d0")
    assert t.value == pytest.approx(want)
    assert t.observation["noise_floor_rel"] == pytest.approx(floor)
    assert t.observation["anchor_value"] == 1.0 and t.observation["n_pairs"] == 3
    assert t.observation["effect_rel"] == pytest.approx(want - 1)
    assert t.observation["retrofit"] is True and "outcome" not in t.observation
    assert t.applicability["knob_family"] == "moe_fused_upgate" and t.applicability["quant"] == "Q8_0"
    assert t.extra["llama_bench_protocol"]["autokernel_hardened"] == ["ordinary"]
    assert t.extra["aa_off"]["n_processes"] == 3


def test_invalid_preflight_stays_a_valueless_row(unit):
    inv = next(t for t in _tuples(unit) if t.metric == "ch19_t3_upgate_invalid_arm")
    assert inv.value is None and inv.observation == {}
    assert "INVALID" in inv.claim and "wrapper_rc=1" in inv.claim
    assert inv.extra["wrapper_rc"] == 1 and inv.extra["marker"] == 1 and inv.extra["arm"] == "preflight-on"


def test_floor_is_absent_when_the_records_do_not_support_one(unit):
    rows = [r for r in _load(unit) if not r["arm"].startswith(("p3-",))]
    prov = json.loads((unit / "provenance.json").read_text())
    prov["pairs"] = 2
    (unit / "provenance.json").write_text(json.dumps(prov))
    _save(unit, rows)
    for t in _tuples(unit):
        if t.metric.startswith("ch19_t3_upgate_") and "invalid" not in t.metric:
            assert "noise_floor_rel" not in t.observation
            assert "noise_floor_absent" in t.extra


def test_an_invalid_arm_pair_drops_out_of_the_median_but_stays_a_row(unit):
    rows = _load(unit)
    for r in rows:
        if r["arm"] == "p3-B-on":
            r["valid"], r["why"] = 0, "ON arm without fused marker"
            r["marker"] = 0
    log = unit / "p3-B-on" / "run.log"
    log.write_text("\n".join(l for l in log.read_text().splitlines() if "fused MoE up+gate" not in l) + "\n")
    _save(unit, rows)
    ts = _tuples(unit)
    assert sum(t.metric == "ch19_t3_upgate_invalid_arm" for t in ts) == 5  # preflight + 4 results of the arm
    ratio = next(t for t in ts if t.metric == "ch19_t3_upgate_on_over_off_tg128_d0")
    assert ratio.observation["n_pairs"] == 2


@pytest.mark.parametrize("mutate", [
    "summary", "avg_ts", "samples_ns", "marker_in_log", "valid_flag", "binary_sha", "order", "placement_skew",
    "bench_jsonl", "recipe_env", "model"])
def test_strict_reader_refuses_a_record_that_does_not_rederive(unit, mutate):
    rows = _load(unit)
    if mutate == "summary":
        s = (unit / "summary.txt").read_text().replace("OFF median   922.97", "OFF median   999.99")
        (unit / "summary.txt").write_text(s)
    elif mutate == "avg_ts":
        rows[3]["avg_ts"] = rows[3]["raw"]["avg_ts"] = rows[3]["avg_ts"] * 1.05
        _save(unit, rows)
    elif mutate == "samples_ns":
        rows[3]["raw"]["samples_ns"][0] += 50_000_000
        _save(unit, rows)
    elif mutate == "marker_in_log":
        log = unit / "p1-B-on" / "run.log"
        log.write_text("\n".join(l for l in log.read_text().splitlines() if "fused MoE up+gate" not in l) + "\n")
    elif mutate == "valid_flag":
        for r in rows:
            if r["arm"] == "p2-A-off":
                r["valid"], r["why"] = 0, "wrapper_rc=1"
        _save(unit, rows)
    elif mutate == "binary_sha":
        for r in rows:
            r["llama_bench_sha256"] = "0" * 64
        _save(unit, rows)
    elif mutate == "order":
        rows = [r for r in rows if r["arm"] == "preflight-on"] + sorted(
            (r for r in rows if r["arm"] != "preflight-on"), key=lambda r: r["arm"][::-1])
        _save(unit, rows)
    elif mutate == "placement_skew":
        p = unit / "p2-A-off" / "canonical" / "placement.log"
        p.write_text(p.read_text().replace("25.0%", "55.0%", 1))
    elif mutate == "bench_jsonl":
        (unit / "p1-A-off" / "bench.jsonl").write_text("")
    elif mutate == "recipe_env":
        log = unit / "p1-A-off" / "run.log"
        log.write_text(log.read_text().replace("OMP_PLACES=cores", "OMP_PLACES=threads"))
    elif mutate == "model":
        prov = json.loads((unit / "provenance.json").read_text())
        prov["model"] = "/mnt/raid0/llm/models/Other-Q4_K_M.gguf"
        (unit / "provenance.json").write_text(json.dumps(prov))
    with pytest.raises(ct.ProjectionError):
        m.native_rows(unit)


def test_hardened_row_without_the_flag_is_refused_by_the_shared_protocol_rule(unit):
    rows = _load(unit)
    for r in rows:
        if r["arm"] == "p1-A-off":
            r["raw"]["autokernel_hardened"] = True
    _save(unit, rows)
    bench = unit / "p1-A-off" / "bench.jsonl"
    lines = [json.loads(x) for x in bench.read_text().splitlines()]
    for ln in lines:
        ln["autokernel_hardened"] = True
    bench.write_text("".join(json.dumps(x) + "\n" for x in lines))
    log = unit / "p1-A-off" / "run.log"
    keep = [x for x in log.read_text().splitlines() if not x.startswith("{")]
    log.write_text("\n".join(keep + [json.dumps(x) for x in lines]) + "\n")
    with pytest.raises(ct.ProjectionError, match="unrequested_hardened"):
        m.native_rows(unit)


def test_producer_pin_is_enforced_when_the_script_exists(unit, monkeypatch, tmp_path):
    script = tmp_path / "t3.sh"
    script.write_text("#!/bin/bash\necho edited\n")
    monkeypatch.setattr(m, "PRODUCER_PATH", script)
    with pytest.raises(ct.ProjectionError, match="differs from the pin"):
        m.native_rows(unit)
    import hashlib
    monkeypatch.setattr(m, "PRODUCER_SHA256", hashlib.sha256(script.read_bytes()).hexdigest())
    assert m.native_rows(unit)


def test_records_changed_between_read_and_projection_is_refused(unit):
    nat = m.native_rows(unit)
    with (unit / "records.jsonl").open("a") as f:
        f.write("\n")
    with pytest.raises(ct.ProjectionError, match="changed between read"):
        m.project(nat[0])


def test_screen_rows_without_summary_are_refused_but_a_preflight_only_run_projects_its_invalid_row(unit):
    (unit / "summary.txt").unlink()
    with pytest.raises(ct.ProjectionError, match="incomplete screen"):
        m.native_rows(unit)
    rows = [r for r in _load(unit) if r["arm"] == "preflight-on"]
    prov = json.loads((unit / "provenance.json").read_text())
    (unit / "records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    for arm in ("p1-A-off", "p1-B-on", "p2-A-off", "p2-B-on", "p3-A-off", "p3-B-on"):
        shutil.rmtree(unit / arm)
    prov["pairs"] = 3
    (unit / "end.txt").unlink()
    nat = m.native_rows(unit)
    assert [n["kind"] for n in nat] == ["invalid"]


def test_ingest_source_projects_the_fixture_parent_dir():
    class L:
        def __init__(self):
            self.frames = []

        def append(self, f):
            self.frames.append(f)

    rep = ingest_sources.ingest(L(), "ch19-t3-screen", [FIX.parent], as_of=AS_OF, dry_run=True)
    assert rep["units_projected"] == 1 and rep["rows_projected"] == 13 and not rep["refused"]


@pytest.mark.skipif(not (REAL / "records.jsonl").is_file(), reason="real screen not on this host")
def test_real_screen_rederives_every_summary_figure():
    nat = m.native_rows(REAL)
    got = {(n["test"], n["depth"]): n for n in nat if n["kind"] == "ratio"}
    stated = {}
    for line in (REAL / "summary.txt").read_text().splitlines()[1:]:
        name, rest = line.split(" OFF median")[0].strip(), line
        stated[name] = float(rest.split("ON/OFF median ")[1].split(" ")[0])
    assert len(got) == 4
    for (test, depth), n in got.items():
        assert round(n["value"], 4) == stated[f"{test} @ d{depth}"]
        assert n["n_pairs"] == 5
    assert [n["kind"] for n in nat].count("invalid") == 1
    assert all(m.project(n).metric for n in nat)
