"""P1-K: KPF-18 item-7 records gain argv-derived scope and paired value-bearing serving claims.

Fixtures are real runner-authored records copied unmodified (tests/vidya/fixtures/belief_p1/kpf_serving).
"""
import json
import shutil
import statistics
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import kv_prefix_fork as kpf  # noqa: E402

FX = Path(__file__).parent / "fixtures" / "belief_p1" / "kpf_serving"
AS_OF = "2026-10-21T18:00:00Z"


@pytest.fixture()
def gpu(tmp_path):
    shutil.copytree(FX / "gpu27b_item7", tmp_path / "gpu")
    return tmp_path / "gpu" / "belief_measurements.jsonl"


@pytest.fixture()
def cpu(tmp_path):
    shutil.copytree(FX / "cpu35b_item7", tmp_path / "cpu")
    return tmp_path / "cpu" / "belief_measurements.jsonl"


def _records(sidecar):
    return [json.loads(line) for line in sidecar.read_text().splitlines()]


def _tuples(sidecar):
    return [kpf.project(n) for n in kpf.native_rows(sidecar)]


def _measure(tuples, metric):
    return [t for t in tuples if t.metric == metric]


def test_gpu_item7_projects_legacy_plus_three_measures_per_ab_pair(gpu):
    natives = kpf.native_rows(gpu)
    assert len(natives) == 4 + 2 * 3  # 4 legacy per-record claims, then A1/B1 and A2/B2 x 3 measures
    assert sum(1 for n in natives if n.get("measure")) == 6
    tuples = [kpf.project(n) for n in natives]
    assert len({t.measurement_id for t in tuples}) == len(tuples)
    for t in tuples:
        assert ct.grade(t)[:2] == ("Judged", "Located")  # n=1, no protocol: the shared ladder decides


def test_gpu_scope_comes_from_the_records_own_argv(gpu):
    for t in _tuples(gpu):
        a = t.applicability
        assert a["model_file"] == "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"
        assert a["quant"] == "Q8_0" and a["backend"] == "gpu" and a["np"] == 4
        assert a["build_sha"] == "a1f0c8cf9" and a["scope_basis"] == "native"
        assert a["kernel"]["execution_digest"] == "2be7a16ed6d3712d82a36c668417b4dcec8d9cadd13a682e069cb4d57b9d0635"
        assert a["knob_family"] == "slot_serving" and a["varied"] == ["slot_fork"]
        k = a["knobs"]
        assert k["b"] == 512 and k["ub"] == 512 and k["kv_unified"] is True and k["dflash2"] is True
        assert k["cache_type_k"] == "q8_0" and k["spec_type"] == "draft-dflash" and k["np"] == 4
        assert "device" not in a  # argv says ROCm0, not the card: never guessed


def test_cpu_scope(cpu):
    t = _tuples(cpu)[0]
    a = t.applicability
    assert a["model_file"].endswith("Qwen3.6-35B-A3B-MTP-Q8_0.gguf") and a["quant"] == "Q8_0"
    assert a["backend"] == "cpu" and a["np"] == 4 and a["knobs"]["ub"] == 2048
    assert "build_sha" not in a  # a worktree build dir names no commit; none is invented


def test_ttft_claim_is_value_bearing_against_the_fork_off_arm(gpu):
    recs = _records(gpu)
    on, off = recs[1], recs[0]
    t = [x for x in _measure(_tuples(gpu), "kpf_fanout_ttft_median_ms")
         if x.extra["window_id"] == on["window_id"]][0]
    assert t.value == statistics.median(on["ttft_ms"]) and t.unit == "ms" and t.reps == 4
    assert t.metric_direction == "lower_better"
    obs = t.observation
    assert obs["anchor_value"] == statistics.median(off["ttft_ms"]) and obs["n_pairs"] == 1
    assert obs["effect_rel"] == pytest.approx((t.value - obs["anchor_value"]) / obs["anchor_value"])
    assert obs["effect_rel"] < -0.8  # about 8x faster first token
    assert "outcome" not in obs and "decisive" not in obs  # no verdict the record does not hold
    assert t.extra["anchor_window_id"] == off["window_id"]


def test_prefill_and_decode_measures(gpu):
    recs = _records(gpu)
    tuples = _tuples(gpu)
    pre = [x for x in _measure(tuples, "kpf_prompt_tokens_processed") if x.extra["arm"] == "fork_on"][0]
    assert (pre.value, pre.observation["anchor_value"]) == (74512, 254512)
    dec = [x for x in _measure(tuples, "kpf_aggregate_decode_tok_s")][0]
    assert dec.metric_direction == "higher_better" and dec.unit == "t/s"
    assert dec.value == recs[1]["decode_tok_s"]["aggregate"]
    assert dec.observation["anchor_value"] == recs[0]["decode_tok_s"]["aggregate"]


def test_observation_and_scope_ride_the_frames_and_never_move_the_grade(gpu):
    for t in _tuples(gpu):
        assert ct.grade(t) == ct.grade(replace(t, observation={}, applicability={}))
    t = _measure(_tuples(gpu), "kpf_fanout_ttft_median_ms")[0]
    frames = ct.to_frames(t, as_of=AS_OF, adapter_id=kpf.ADAPTER_ID, authority=kpf.AUTHORITY)
    again = ct.to_frames(t, as_of=AS_OF, adapter_id=kpf.ADAPTER_ID, authority=kpf.AUTHORITY)
    assert [f["frame_id"] for f in frames] == [f["frame_id"] for f in again]
    source, _, evidence = frames
    assert source["assertion"]["applicability"]["knob_family"] == "slot_serving"
    assert evidence["assertion"]["observation"]["anchor_value"]
    assert evidence["assertion"]["unit"] == "ms"
    assert len(kpf.frames_for_sidecar(gpu, as_of=AS_OF)) == 3 * 10


def test_cpu_pair_projects_measures_and_a_lone_record_does_not(cpu, tmp_path):
    tuples = _tuples(cpu)
    assert len(tuples) == 2 + 3
    first_line = cpu.read_text().splitlines()[1]  # fork_on only: no fork_off partner in the file
    lone = tmp_path / "lone"
    (lone / "rows").mkdir(parents=True)
    for p in (cpu.parent / "rows").iterdir():
        shutil.copy(p, lone / "rows" / p.name)
    (lone / "belief_measurements.jsonl").write_text(first_line + "\n")
    assert len(kpf.native_rows(lone / "belief_measurements.jsonl")) == 1


def test_unpaired_dry_run_fixture_is_unchanged(tmp_path):
    shutil.copytree(Path(__file__).parent / "fixtures" / "kpf", tmp_path / "k")
    assert not any(n.get("measure") for n in kpf.native_rows(tmp_path / "k" / "belief_measurements.jsonl"))


def test_mismatched_windows_do_not_pair(gpu):
    natives = [n for n in kpf.native_rows(gpu) if n.get("measure") == "fanout_ttft_ms"]
    bad = dict(natives[0], anchor=natives[1]["anchor"])  # A2 as the anchor of B1
    with pytest.raises(ct.ProjectionError, match="paired"):
        kpf.project(bad)


def test_mutated_rows_demote_attestation_of_the_measure_claims(gpu):
    rows = sorted((gpu.parent / "rows").glob("*.jsonl"))[0]  # the A1 rows file: the anchor's
    rows.write_text(rows.read_text() + "x\n")
    measures = [kpf.project(n) for n in kpf.native_rows(gpu) if n.get("measure")]
    anchored_on_a1 = [t for t in measures if t.extra["anchor_run_id"].endswith("-1")]
    assert anchored_on_a1 and all(t.attestation_present is False for t in anchored_on_a1)
    others = [t for t in measures if not t.extra["anchor_run_id"].endswith("-1")]
    assert others and all(t.attestation_present is True for t in others)


def test_a_record_whose_readback_disagrees_declares_no_scope(gpu):
    rec = _records(gpu)[0]
    rec["argv_readback"]["proc_cmdline_matches_argv"] = False
    assert kpf._applicability(rec) == {}
    rec2 = _records(gpu)[0]
    rec2["argv"] = [t for t in rec2["argv"] if t not in ("-m", "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf")]
    assert kpf._applicability(rec2) == {}


def test_champion_arm_is_a_valid_arm_and_varies_the_binary(gpu):
    rec = _records(gpu)[0]
    rec["arm"] = "champion"
    body = {k: v for k, v in rec.items() if k != "record_sha256"}
    rec["record_sha256"] = kpf._digest(body)
    assert kpf.validate_row(rec) == []
    assert kpf._applicability(rec)["varied"] == ["binary"]


def test_ingest_source_finds_nested_run_dirs(tmp_path):
    root = tmp_path / "kpf18cpu"
    for sub in ("run-1", "rerun/item7"):
        (root / sub).mkdir(parents=True)
        (root / sub / "belief_measurements.jsonl").write_text("")
    units = ingest_sources.SOURCES["kv-prefix-fork"].units(root)
    assert {p.parent.relative_to(root).as_posix() for p in units} == {"run-1", "rerun/item7"}
