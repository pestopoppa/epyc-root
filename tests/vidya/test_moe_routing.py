"""VB-MOE-ROUTING-WIRE: stamped INF-72 RT-1 routing-trace analyses -> OBSERVATION tuples graded by the one shared ladder.

Fixtures are synthetic but shaped exactly like the research analysis JSONs (``skew_report`` / ``residency_curve`` /
``placement_replay_{same,cross}`` / ``locality_report``) after ``trace_io.stamp``; ``test_real_q38fn_set`` exercises the
regenerated Qwen3.8-Flash-Next set when it is on disk.
"""
import copy
import json
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
from adapters import moe_routing as mr  # noqa: E402
from ledger import Ledger  # noqa: E402

WHEN = "2026-10-24T12:00:00Z"
AS_OF = "2026-10-24T06:00:00Z"
L, E, K = 3, 16, 2
MODEL = "/mnt/raid0/llm/models/x/Synth-Q4-00001-of-00002.gguf"
DOMS = ("code", "prose")
CAP = 8


def shard(dom: str, part: str, **kw) -> dict:
    d = {"shard": f"/traces/{dom}/{part}/shard-0", "part": part, "domain": dom, "arch": "synth", "model": "Synth-Q4-00001-of-00002.gguf",
         "model_path": MODEL, "layers": L, "n_experts": [E], "top_k": [K], "chunk_size": 512,
         "corpus_sha256": ("a" if dom == "code" else "b") * 64, "tokens_sha256": "c" * 64, "corpus_tokens": 99,
         "llama_build_info": "b10303-ffc1bac82", "tool_format": "moe-trace-1",
         "rows_sha256": "1" * 64, "ids_sha256": ("2" if part == "decode" else "3") * 63 + ("0" if dom == "code" else "1"),
         "hashes_verified": True, "verified_marker": True, "quarantined": False,
         "hazard_guard": {"checks": 12, "sub_chance_checks": 0, "cv_min": 1.1, "cv_max": 3.2, "fatal": 0}}
    if part == "decode":   # 4 windows (ids 0..3), each 8 prefill rows + EOS-stopped decode rows (16 < 4 * CAP)
        d.update(first_window=0, n_windows=4, decode_tokens_per_window=CAP, rows=48, rows_prefill=32, rows_decode=16,
                 windows_prefill=4, windows_decode=4)
    else:                  # 8 prefill-only windows (ids 4..11)
        d.update(first_window=4, n_windows=8, decode_tokens_per_window=0, rows=64, rows_prefill=64, rows_decode=0,
                 windows_prefill=8, windows_decode=0)
    d.update(kw)
    return d


def traces(doms=DOMS, **kw) -> list:
    return [shard(d, p, **kw) for d in doms for p in ("decode", "bulk")]


def stamp(doc: dict, kind: str, doms=DOMS, **kw) -> dict:
    doc.update(analysis_kind=kind, provenance_schema=mr.PROVENANCE_SCHEMA, input_traces=traces(doms, **kw))
    doc["content_sha256"] = mr.content_sha256(doc)
    return doc


def skew_doc(**kw) -> dict:
    def layer(l, f):
        r = {"layer": l, "n_experts": E, "top_k": K, "selections": 1000 + l, "gini": 0.4 + 0.01 * l, "never_selected": l}
        for frac, n in (("top10", 2), ("top25", 4)):
            r.update({f"{frac}_n": n, f"{frac}_chance": n / E, f"{frac}_in_sample": f + 0.02 * l, f"{frac}_heldout": f + 0.01 * l,
                      f"{frac}_null": n / E + 0.003})
        return r
    doms = {}
    for i, d in enumerate(DOMS):
        doms[d] = {"prefill": {"summary": {"rows": 96, "windows": 12}, "per_layer": [layer(l, 0.5 + 0.1 * i) for l in range(L)]},
                   "decode": {"summary": {"rows": 16, "windows": 4}, "per_layer": [layer(l, 0.6 + 0.1 * i) for l in range(L)]}}
    return stamp({"arch": "synth", "n_experts": [E], "top_k": [K], "layers": L, "domains": doms, "overlap": {}, "gate": 0.6,
                  "rt5_verdict": {}}, "skew_report", **kw)


def residency_doc(**kw) -> dict:
    ks = [2, 3]
    curves = {}
    for B in DOMS:
        for ph in ("prefill", "decode"):
            lo = {}
            for A in DOMS:
                key = A if A != B else (f"{B}_even->{B}_odd(prefill)" if ph == "prefill" else f"{B}(same-domain prefill->decode)")
                lo[key] = {str(k): 0.2 + 0.05 * k + (0.1 if A == B else 0) for k in ks}
            curves[f"{B}/{ph}"] = {"selections": 5000, "chance": {str(k): k / E for k in ks}, "learned_on": lo,
                                   "oracle_in_sample": {str(k): 0.5 + 0.05 * k for k in ks}}
    return stamp({"arch": "synth", "n_experts": E, "top_k": [K], "layers": L, "ks": ks, "ks_same_fraction_of_pool": [3],
                  "ref_experts": 24, "curves": curves, "stationarity": {}, "rt7_verdict": {}}, "residency_curve", **kw)


def placement_doc(calib="same", dom="code", **kw) -> dict:
    def cfg(bins, ph, T, steps):
        arms = {"contiguous": {"max_over_mean": 1.67, "ci95": [1.66, 1.68]}, "null_random": {"max_over_mean": 1.65, "ci95": [1.64, 1.66]},
                "eplb_R0": {"max_over_mean": 1.60, "ci95": [1.5, 1.7]}, "deepinfer_R0": {"max_over_mean": 1.55, "ci95": [1.5, 1.6]},
                "eplb_R2": {"max_over_mean": 1.40, "ci95": [1.3, 1.5]}, "eplb_R2@random": {"max_over_mean": 1.58, "ci95": [1.5, 1.6]},
                "oracle_R2": {"max_over_mean": 1.20, "ci95": [1.1, 1.3]}, "null_uniform_mc": {"max_over_mean": 1.9},
                "integrality_floor": {"max_over_mean": 1.0}}
        return {"bins": bins, "phase": ph, "T": T, "steps": steps, "per_step_arm_steps": min(steps, 1000), "units_per_step": T * K, "R1": 2,
                "redundant_frac": 0.125, "arms": arms,
                "decision": {"baseline_ratio": 1.65, "best_practical": "deepinfer_R0", "best_practical_max_over_mean": 1.55,
                             "ratio_practical": 1.65 / 1.55, "best_idealized_dispatch": "eplb_R2", "best_idealized_dispatch_max_over_mean": 1.4,
                             "ratio_idealized_dispatch": 1.65 / 1.4, "best_bound": "oracle_R2", "best_bound_max_over_mean": 1.2,
                             "ratio_bound": 1.65 / 1.2, "ratio_measured_contiguous": 1.1}}
    doc = {"domain": dom, "arch": "synth", "E": E, "K": K, "layers": L, "calib": calib,
           "configs": {"B4/decode/T1": cfg(4, "decode", 1, 16), "B4/prefill/T8": cfg(4, "prefill", 8, 3)}}
    return stamp(doc, "placement_replay", doms=DOMS if calib == "cross" else (dom,), **kw)


def locality_doc(**kw) -> dict:
    doms = {}
    for d in DOMS:
        ir = [{"layer": l, "chance": K / E, "prefill": {"pairs": 80, "ir_mean": 0.3 + 0.01 * l, "ratio_to_chance": 2.0},
               "decode": {"pairs": 12, "ir_mean": 0.28 + 0.01 * l, "ratio_to_chance": 1.9}} for l in range(L)]
        lru = {str(l): {ph: {"selections": 200, "compulsory_miss_rate": 0.05,
                             "hit_rate": {"8": 0.3, "16": 0.55}, "uniform_chance_hit_rate": {"8": 0.5, "16": 1.0}}
                        for ph in ("prefill", "decode")} for l in (0, 2)}
        coact = [{"layer": l, "tokens": 96, "excess_fraction": 0.2 + 0.01 * l, "excess_fraction_noise": 0.05} for l in range(L)]
        doms[d] = {"ir": ir, "lru": lru, "coact": coact, "lru_windows": 6}
    return stamp({"domains": doms}, "locality_report", **kw)


def dump(tmp: Path, name: str, doc) -> Path:
    p = tmp / name
    p.write_text(json.dumps(doc, indent=1) + "\n")
    return p


def write(tmp: Path) -> Path:
    """BUILDERS entry for test_ingest_sources: the whole synthetic analysis set, projected to its sidecar."""
    tmp = Path(tmp)
    dump(tmp, "skew_report.json", skew_doc())
    dump(tmp, "residency_curve.json", residency_doc())
    dump(tmp, "placement_replay_same.json", [placement_doc("same", "code"), placement_doc("same", "prose")])
    dump(tmp, "placement_replay_cross.json", [placement_doc("cross", "code")])
    dump(tmp, "locality_report.json", locality_doc())
    return mr.write_belief_measurements(tmp, emitted_at=WHEN)


def rows_of(side: Path) -> list:
    return [json.loads(x) for x in side.read_text().splitlines()]


def natives(side: Path):
    return mr.native_rows(side)


# ---------------------------------------------------------------------------------------- round trip
def test_round_trip_all_four_analysis_kinds_graded_by_the_shared_ladder(tmp_path):
    side = write(tmp_path)
    ns_ = natives(side)
    by = {}
    for n in ns_:
        by.setdefault(n["row"]["metric"], []).append(n["row"])
    # skew: 2 domains x 2 phases x 2 fractions
    assert len(by["moe_skew_top10_share_heldout"]) == len(by["moe_skew_top25_share_heldout"]) == 4
    # residency: 2 B x 2 phases x 2 A x |{2,3}| k
    assert len(by["moe_residency_hit_rate"]) == 16
    # placement: (code same, prose same, code cross) x 2 configs x {contiguous, deepinfer_R0, eplb_R2, oracle_R2}
    assert len(by["moe_placement_max_over_mean"]) == 3 * 2 * 4
    # locality: IR 2 x 2, LRU 2 x 2 x 2 k, coactivation 2
    assert (len(by["moe_ir_t_mean"]), len(by["moe_lru_hit_rate"]), len(by["moe_coactivation_excess_fraction"])) == (4, 8, 2)
    for n in ns_:
        t = mr.project(n)
        assert t.protocol_id == "" and t.attestation_present is True and t.source_kind == mr.SOURCE_KIND
        assert ct.grade(t)[:2] == ("Judged", "Located")
        assert t.reps == (t.applicability["knobs"]["n"] if t.metric == "moe_placement_max_over_mean" else t.applicability["knobs"]["n_windows"])
    assert mr.frames_for_sidecar(side, as_of=AS_OF)


def test_scope_carries_model_arch_corpus_phase_chunk_calibration_and_n(tmp_path):
    side = write(tmp_path)
    ts = {(n["row"]["metric"], n["row"]["extra"]["subject"]["domain"], n["row"]["extra"]["subject"]["phase"], n["row"]["extra"]["payload"].get("k"),
           n["row"]["extra"]["payload"].get("learned_on"), n["row"]["extra"]["payload"].get("calib"), n["row"]["extra"]["payload"].get("arm")): mr.project(n)
          for n in natives(side)}
    t = ts[("moe_skew_top10_share_heldout", "code", "prefill", None, None, None, None)]
    a, k = t.applicability, t.applicability["knobs"]
    assert (a["model_file"], k["arch"], k["corpus_sha256"], k["phase"], k["chunk_size"]) == (
        "Synth-Q4-00001-of-00002.gguf", "synth", "a" * 64, "prefill", 512)
    assert k["calibration_source"] == "heldout:even-odd-window-split" and (k["n"], k["n_unit"], k["n_windows"]) == (12, "windows", 12)
    assert a["build_sha"] == "ffc1bac82" and a["scope_basis"] == "native" and a["shape"] == f"{L}L x {E}E top-{K}"
    assert t.value == pytest.approx(sum(0.5 + 0.01 * l for l in range(L)) / L)
    # decode tuples carry their n (EOS-stopped: 16 rows over 4 windows, cap 8 per window)
    d = ts[("moe_skew_top10_share_heldout", "code", "decode", None, None, None, None)].applicability["knobs"]
    assert (d["n_windows"], d["decode_rows"], d["decode_cap_per_window"], d["eos_stopped"]) == (4, 16, CAP, True)
    # residency: cross-domain calibration names the learned-on corpus; the same-domain prefill split scores the odd windows only
    cross = ts[("moe_residency_hit_rate", "code", "prefill", 2, "prose", None, None)]
    assert cross.applicability["recipe"] == "learned-on:prose:prefill:all-windows:corpus=" + "b" * 64
    assert cross.applicability["knobs"]["n_windows"] == 12
    same = ts[("moe_residency_hit_rate", "code", "prefill", 2, "code", None, None)]
    assert same.applicability["recipe"] == "learned-on:code:prefill:even-windows" and same.applicability["knobs"]["n_windows"] == 6
    assert same.observation["anchor_value"] == pytest.approx(2 / E)
    # placement: steps are n, calibration names the other domains' corpus-bearing shards
    pc = ts[("moe_placement_max_over_mean", "code", "decode", None, None, "cross", "contiguous")]
    assert pc.applicability["recipe"] == "cross-domain:prose:prefill" and pc.applicability["knobs"]["n"] == 16
    assert pc.observation["anchor_value"] == 1.65           # contiguous is read against the placement-free null
    pe = ts[("moe_placement_max_over_mean", "code", "decode", None, None, "same", "eplb_R2")]
    assert pe.observation["anchor_value"] == 1.67 and pe.value == 1.40 and pe.metric_direction == "lower_better"
    pp = ts[("moe_placement_max_over_mean", "code", "prefill", None, None, "same", "contiguous")]
    assert pp.applicability["knobs"]["n_windows"] == 3 and pp.applicability["recipe"] == "same-domain:prefill-windows-mod4!=3"
    # locality: the LRU analysis covers the first 6 windows (ids 0..5): 4 decode-shard windows + 2 bulk windows
    lru = ts[("moe_lru_hit_rate", "code", "prefill", 8, None, None, None)]
    assert lru.applicability["knobs"]["n_windows"] == 6
    assert ts[("moe_lru_hit_rate", "code", "decode", 8, None, None, None)].applicability["knobs"]["n_windows"] == 4


def test_domains_are_never_pooled_and_models_never_mixed(tmp_path):
    side = write(tmp_path)
    for n in natives(side):
        r = n["row"]
        doms = {t["domain"] for t in r["extra"]["input_traces"]}
        assert r["extra"]["subject"]["domain"] in doms
        assert doms == {r["extra"]["subject"]["domain"], *r["extra"]["subject"]["calibration_domains"]}
        assert len({t["model_path"] for t in r["extra"]["input_traces"]}) == 1
    # an extra, unnamed domain in a row's input_traces is a pooled row
    bad = rows_of(side)[0]
    bad["extra"]["input_traces"] = bad["extra"]["input_traces"] + [shard("prose", "bulk", shard=f"/traces/prose/bulk/shard-9")]
    assert any("pooling" in p or "calibration" in p for p in mr.row_problems(ns_reseal(bad)))
    # two models in one analysis
    mixed = rows_of(side)[0]
    mixed["extra"]["input_traces"][0]["model_path"] = "/models/other-model.gguf"
    assert any("different model_path" in p for p in mr.row_problems(ns_reseal(mixed)))


def ns_reseal(row):
    from adapters import _native_sidecar as ns
    row.pop("row_sha256", None)
    return ns.seal(row)


# ---------------------------------------------------------------------------------------- absence / refusal
def test_no_sidecar_or_foreign_file_yields_zero_rows(tmp_path):
    assert mr.native_rows(tmp_path / "moe_routing.beliefs.jsonl") == ()
    foreign = tmp_path / "x.jsonl"
    foreign.write_text(json.dumps({"schema": "something.else"}) + "\n")
    assert mr.native_rows(foreign) == ()
    with pytest.raises(mr.ProjectionError):
        mr.project({"row": {"schema": "something.else"}})


def test_unstamped_analysis_yields_no_row_and_nothing_is_backfilled(tmp_path, capsys):
    doc = skew_doc()
    legacy = {k: v for k, v in doc.items() if k not in ("content_sha256", "input_traces", "analysis_kind", "provenance_schema")}
    p = dump(tmp_path, "skew_report.json", legacy)
    plan = mr.plan_rows([p])
    assert plan["rows"] == [] and "no content_sha256" in plan["skipped"][0]["reason"]
    with pytest.raises(mr.CaptureError, match="no row projected"):
        mr.write_belief_measurements(tmp_path)
    assert not (tmp_path / mr.SIDECAR_NAME).exists()
    assert mr.main(["write", "--analysis-dir", str(tmp_path)]) == 3
    assert "no content_sha256" in capsys.readouterr().out


def test_edited_analysis_is_refused_by_its_content_hash(tmp_path):
    doc = skew_doc()
    doc["domains"]["code"]["prefill"]["per_layer"][0]["top10_heldout"] = 0.99
    p = dump(tmp_path, "skew_report.json", doc)
    assert "content_sha256 does not bind" in mr.plan_rows([p])["skipped"][0]["reason"]


@pytest.mark.parametrize("mut,why", [
    ({"quarantined": True}, "quarantined"),
    ({"verified_marker": False}, "VERIFIED"),
    ({"hashes_verified": False}, "not recomputed equal"),
    ({"hazard_guard": None}, "hazard guard did not run"),
    ({"hazard_guard": {"checks": 0, "sub_chance_checks": 0, "fatal": 0}}, "hazard guard did not run"),
])
def test_unverified_quarantined_or_guardless_shard_yields_no_row(tmp_path, mut, why):
    dump(tmp_path, "skew_report.json", skew_doc(**mut))
    plan = mr.plan_rows([tmp_path / "skew_report.json"])
    assert plan["rows"] == [] and plan["refused"] == [] and why in plan["skipped"][0]["reason"]
    # only the shard of one domain: that domain yields nothing, the other still projects
    doc = skew_doc()
    doc["input_traces"][0].update(mut)
    doc["content_sha256"] = mr.content_sha256(doc)
    p = dump(tmp_path, "skew_report.json", doc)
    got = mr.plan_rows([p])
    assert {r["extra"]["subject"]["domain"] for r in got["rows"]} == {"prose"} and got["skipped"]


def test_stride_hazard_is_refused_fail_closed_on_write_and_read(tmp_path):
    dump(tmp_path, "skew_report.json", skew_doc(hazard_guard={"checks": 12, "sub_chance_checks": 3, "fatal": 1}))
    plan = mr.plan_rows([tmp_path / "skew_report.json"])
    assert plan["rows"] == [] and plan["refused"] and mr.HAZARD in plan["refused"][0]["reason"]
    with pytest.raises(mr.CaptureError, match="stride-hazard"):
        mr.write_belief_measurements(tmp_path)
    assert mr.main(["write", "--analysis-dir", str(tmp_path)]) == 3 and not (tmp_path / mr.SIDECAR_NAME).exists()
    # a tampered sidecar that carries a hazard row is refused by name, not silently voided
    ok = tmp_path / "ok"
    ok.mkdir()
    side = write(ok)
    rows = rows_of(side)
    rows[0]["extra"]["input_traces"][0]["hazard_guard"]["fatal"] = 1
    bad = tmp_path / "bad.beliefs.jsonl"
    bad.write_text("\n".join(json.dumps(ns_reseal(r)) for r in rows) + "\n")
    with pytest.raises(mr.ProjectionError, match="fail-closed"):
        mr.native_rows(bad)


def test_flat_counts_and_sub_chance_reuse_are_stride_signatures(tmp_path):
    flat = skew_doc()
    flat["domains"]["code"]["prefill"]["per_layer"][1]["gini"] = 0.0
    flat["content_sha256"] = mr.content_sha256(flat)
    plan = mr.plan_rows([dump(tmp_path, "skew_report.json", flat)])
    # the flat layer sits inside the code/prefill rows only: those are refused, every other statistic still projects
    assert len(plan["refused"]) == 2 and all("code:moe_skew" in r["unit"] and mr.HAZARD in r["reason"] for r in plan["refused"])
    assert {(r["extra"]["subject"]["domain"], r["extra"]["subject"]["phase"]) for r in plan["rows"]} == {("code", "decode"), ("prose", "prefill"), ("prose", "decode")}
    w = tmp_path / "w"
    w.mkdir()
    side = write(w)
    r = next(r for r in rows_of(side) if r["metric"] == "moe_ir_t_mean")
    r["extra"]["payload"]["per_layer"] = [dict(x, ir_mean=0.001) for x in r["extra"]["payload"]["per_layer"]]
    r["value"] = 0.001
    assert any(p.startswith(mr.HAZARD) for p in mr.row_problems(ns_reseal(r)))


def test_rows_that_do_not_rederive_are_voided(tmp_path):
    side = write(tmp_path)
    rows = rows_of(side)

    def first(metric):
        return next(r for r in rows if r["metric"] == metric)

    def broken(metric, edit):
        r = copy.deepcopy(first(metric))
        edit(r)
        return mr.row_problems(ns_reseal(r))
    assert mr.row_problems(first("moe_skew_top10_share_heldout")) == []
    assert any("mean of per_layer.heldout" in p for p in broken("moe_skew_top10_share_heldout", lambda r: r.update(value=r["value"] + 0.05)))
    assert any("scope does not re-derive" in p for p in broken("moe_skew_top10_share_heldout", lambda r: r["extra"]["scope"].update(model_file="other.gguf")))
    assert any("scope does not re-derive" in p for p in broken("moe_skew_top10_share_heldout", lambda r: r["extra"]["scope"].update(corpus_sha256="e" * 64)))
    assert any("scope does not re-derive" in p for p in broken("moe_skew_top10_share_heldout", lambda r: r["extra"]["scope"].update(chunk_size=256)))
    assert any("scope does not re-derive" in p for p in broken("moe_skew_top10_share_heldout", lambda r: r["extra"]["scope"].update(n_windows=99)))
    assert any("equal arms_table[arm]" in p for p in broken("moe_placement_max_over_mean", lambda r: r.update(value=1.01)))
    assert any("roles must re-derive" in p for p in broken("moe_placement_max_over_mean", lambda r: r["extra"]["payload"].update(roles=["best_bound"])))
    assert any("chance must be k / n_experts" in p for p in broken("moe_residency_hit_rate", lambda r: r["extra"]["payload"].update(chance=0.5)))
    assert any("learned_on_key" in p for p in broken("moe_residency_hit_rate", lambda r: r["extra"]["payload"].update(learned_on="elsewhere")))
    assert any("mean of per_layer.hit_rate" in p for p in broken("moe_lru_hit_rate", lambda r: r.update(value=0.99)))
    assert any("measurement_id" in p for p in broken("moe_ir_t_mean", lambda r: r["extra"]["payload"]["per_layer"].append(dict(r["extra"]["payload"]["per_layer"][0], layer=9))) + broken("moe_coactivation_excess_fraction", lambda r: r["extra"]["subject"].update(phase="all")) + broken("moe_ir_t_mean", lambda r: r["extra"]["analysis"].update(content_sha256="f" * 64)))
    # a tampered row voids the whole (atomic) sidecar
    rows[3]["value"] = 5.0
    side.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert mr.native_rows(side) == ()


def test_mutated_attestation_grades_down(tmp_path):
    side = write(tmp_path)
    before = {n["row"]["measurement_id"]: ct.grade(mr.project(n)) for n in natives(side)}
    assert {g[:2] for g in before.values()} == {("Judged", "Located")}
    p = tmp_path / "skew_report.json"
    p.write_text(p.read_text().replace("synth", "synthX", 1))
    after = {n["row"]["measurement_id"]: n for n in natives(side)}
    skew_ids = [i for i, n in after.items() if n["row"]["extra"]["kind"] == "skew_report"]
    other_ids = [i for i in after if i not in skew_ids]
    assert skew_ids and all(after[i]["attestation_present"] is False for i in skew_ids)
    assert all(after[i]["attestation_present"] is True for i in other_ids)
    for i in skew_ids:
        t = mr.project(after[i])
        # the file no longer carries the hashed bytes: the carrier says so, and the ladder (not this adapter) decides what
        # that is worth; an observation is capped at Judged/Located whatever the attestation, so the grade never rises
        assert t.attestation_present is False and t.attestation_verified is None
        assert ct.grade(t)[:2] == before[i][:2] == ("Judged", "Located")


# ---------------------------------------------------------------------------------------- identity / idempotence
def test_claim_identity_is_content_derived_so_a_regenerated_sidecar_is_the_same_claims(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    sa = write(a)
    # same analyses, re-projected later: new emitted_at, new row_sha256, identical measurement ids / claim ids
    sb = mr.write_belief_measurements(a, emitted_at="2026-11-01T00:00:00Z")
    assert sa == sb
    ids_a = [r["measurement_id"] for r in rows_of(sa)]
    assert len(ids_a) == len(set(ids_a)) == len(natives(sa))
    for d in (b,):
        # the same documents copied to another directory (file path differs, content identical)
        for f in a.glob("*.json"):
            (d / f.name).write_text(f.read_text())
        sc = mr.write_belief_measurements(d, emitted_at="2026-12-01T00:00:00Z")
    assert [r["measurement_id"] for r in rows_of(sc)] == ids_a
    frames_a = {f["assertion"]["claim_id"] for f in mr.frames_for_sidecar(sa, as_of=AS_OF) if f["frame_type"].endswith("claim_proposed/v1")}
    frames_c = {f["assertion"]["claim_id"] for f in mr.frames_for_sidecar(sc, as_of="2027-01-01T00:00:00Z") if f["frame_type"].endswith("claim_proposed/v1")}
    assert frames_a == frames_c == {"clm_" + i for i in ids_a}


def test_only_new_reingest_is_a_noop_and_a_changed_analysis_is_new_claims(tmp_path, capsys):
    (tmp_path / "fx").mkdir()
    side = write(tmp_path / "fx")
    led = tmp_path / "ledger.jsonl"

    def ingest(*extra):
        rc = cli.main(["--ledger", str(led), "--json", "ingest", "moe-routing", "--path", str(side.parent), "--as-of", AS_OF, *extra])
        assert rc == 0
        return json.loads(capsys.readouterr().out)

    first = ingest("--only-new")
    n = first["rows_projected"]
    assert n == len(natives(side)) and first["frames_emitted"] == 3 * n and first["refused"] == []
    assert len(Ledger(led).read_all()) == 3 * n
    again = ingest("--only-new")                                            # the Done-when no-op
    assert again["frames_emitted"] == 0 and again["frames_skipped"] == 3 * n
    dry = ingest("--only-new", "--dry-run")
    assert dry["frames_emitted"] == 0 and len(Ledger(led).read_all()) == 3 * n
    # the same documents re-projected with a later emitted_at stay a no-op; a re-run analysis (new content) is new claims
    mr.write_belief_measurements(side.parent, emitted_at="2026-12-01T00:00:00Z")
    assert ingest("--only-new")["frames_emitted"] == 0
    other = skew_doc(hazard_guard={"checks": 13, "sub_chance_checks": 0, "cv_min": 1.1, "cv_max": 3.2, "fatal": 0})
    dump(side.parent, "skew_report.json", other)
    mr.write_belief_measurements(side.parent, emitted_at=WHEN)
    third = ingest("--only-new")
    assert third["frames_emitted"] == 3 * 8        # only the 4 + 4 skew claims of the re-run analysis are new


def test_cross_repo_parity_vector_for_content_sha256():
    """Pinned identically by research scripts/benchmark/moe_routing/test_moe_routing.py: one canonical form, two repos."""
    doc = {"b": [1, 2.5, {"z": None, "a": "xé"}], "a": True, "content_sha256": "ignored"}
    assert mr.canonical_json({k: v for k, v in doc.items() if k != "content_sha256"}) == '{"a":true,"b":[1,2.5,{"a":"xé","z":null}]}'
    assert mr.content_sha256(doc) == "5b555c920437a1117a4716709b68a2738e27a27c8550461ba8af16d55cb31ca4"


# ---------------------------------------------------------------------------------------- the real record
REAL = Path("/mnt/raid0/llm/tmp/batch-20261024/scratch-moe/q38fn")


@pytest.mark.skipif(not (REAL / "skew_report.json").is_file(), reason="regenerated Q38FN analysis set not on disk")
def test_real_q38fn_set(tmp_path):
    for f in REAL.glob("*.json"):
        (tmp_path / f.name).write_text(f.read_text())
    side = mr.write_belief_measurements(tmp_path, emitted_at=WHEN)
    ns_ = natives(side)
    assert len(ns_) == 309
    sc = ns_[0]["row"]["extra"]["scope"]
    assert (sc["model_file"], sc["arch"], sc["chunk_size"], sc["n_experts"], sc["top_k"], sc["layers"]) == (
        "Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf", "qwen4exp", 512, 512, 10, 48)
    assert {mr.project(n).source_kind for n in ns_} == {mr.SOURCE_KIND}
    dec = [mr.project(n) for n in ns_ if n["row"]["extra"]["kind"] == "skew_report" and n["row"]["extra"]["subject"]["phase"] == "decode"]
    assert dec and all(t.applicability["knobs"]["n_windows"] == 24 and t.applicability["knobs"]["eos_stopped"] is True for t in dec)
    assert all(ct.grade(mr.project(n))[:2] == ("Judged", "Located") for n in ns_)
    assert not math.isnan(sum(mr.project(n).value for n in ns_))


def test_committed_pre_emit_q38fn_jsons_yield_no_row():
    legacy = Path("/mnt/raid0/llm/tmp/batch-20261024/wt-research/data/moe-routing-rt1-q38fn-20261023")
    if not (legacy / "skew_report.json").is_file():
        pytest.skip("research worktree not on disk")
    plan = mr.plan_rows(mr.discover_analyses(legacy))
    stamped = [s for s in plan["skipped"] if "no content_sha256" in s["reason"]]
    if plan["rows"]:
        pytest.skip("the committed data has since been regenerated with the provenance emit")
    assert len(stamped) == 5 and plan["refused"] == []


def test_non_fatal_guard_sub_chance_count_is_carried_not_refused(tmp_path):
    """The real Qwen3.6 code shards: sub_chance_checks 1-2 of ~20k, fatal 0, VERIFIED. The tap's verdict is the guard's fatal count."""
    dump(tmp_path, "skew_report.json", skew_doc(hazard_guard={"checks": 20000, "sub_chance_checks": 2, "cv_min": 0.67, "cv_max": 4.6, "fatal": 0}))
    plan = mr.plan_rows([tmp_path / "skew_report.json"])
    assert plan["refused"] == [] and len(plan["rows"]) == 8
    side = mr.write_belief_measurements(tmp_path, emitted_at=WHEN)
    k = mr.project(natives(side)[0]).applicability["knobs"]
    assert (k["guard_checks"], k["guard_sub_chance_checks"]) == (20000, 2)
