"""VB-NEMOTRON-BOLT-FOLD-WIRE: Nemotron 3.5 Bolt fold records -> OBSERVATION tuples graded by the one shared ladder."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import nemotron_bolt_fold as nb  # noqa: E402

WHEN = "2026-10-24T12:00:00Z"
CAND = "/k/builds/cpu-20261021-59c1b915f-nemotron/bin/llama-server"
CTL = "/k/builds/cpu-20261020-dd3d9721c/bin/llama-server"
GPU = "/k/builds/gpu-20261021-59c1b915f-nemotron/bin/llama-server"
MODEL = "/m/Nemotron-Bolt.gguf"
REAL = Path("/mnt/raid0/llm/tmp/batch-20261024/wt-research/artifacts/nemotron-bolt-champion-20261021")
BENCH = ("| model | size | params | backend | ngl | threads | fa | test | t/s |\n| --- | --: | --: | --- | --: | --: | --: | --: | --: |\n"
         "| nemotron_h_moe 75B.A9B IQ2_XXS - 2.0625 bpw |  20.50 GiB |    74.04 B | ROCm       |  99 |       8 |   1 |           pp512 |        899.17 ± 2.40 |\n"
         "| nemotron_h_moe 75B.A9B IQ2_XXS - 2.0625 bpw |  20.50 GiB |    74.04 B | ROCm       |  99 |       8 |   1 |           tg128 |         53.44 ± 0.29 |\n\n"
         "build: 59c1b915f (10348)\n")
LOAD = " 10:40:39 up 8 days,  2:55,  0 users,  load average: 97.91, 271.31, 256.78\nq0  HELD\n"
ERR = ("[region-lock] held gpu-quiet shared; running: taskset -c 72-79 env X=1 /k/builds/gpu/bin/llama-bench -m " + MODEL +
       " -ngl 99 -fa 1 -p 512 -n 128 -r 3 -t 8 -o md\n")


def _tbo(n, backend, ok=True):
    tail = f"  {n if ok else n - 1}/{n} tests passed\n"
    return (f"Testing\n\nBackend 1/1: {backend}\n  ADD(type=f32): \x1b[1;32mOK\x1b[0m\n{tail}  Backend {backend}: "
            f"\x1b[1;32m{'OK' if ok else 'FAILED'}\x1b[0m\n1/1 backends passed\n")


def build(d: Path, *, ident_same=True, coh_loop=False):
    d.mkdir(parents=True, exist_ok=True)
    files = {"bench_gpu.md": BENCH, "bench_load.txt": LOAD, "bench_gpu.err": ERR}
    outs = []
    for think in (True, False):
        for i, pr in enumerate(("sky", "fib")):
            outs.append({"think": think, "prompt": pr, "content": f"answer {pr}", "reasoning_len": 50 if think else 0,
                         "finish": "length" if (think and i == 1) else "stop", "n": 100, "rep_loop": coh_loop and think and i == 0})
    vs = [{"t": 1.0, "vram_used": [350_000_000], "srv_pid_in_kfd": True}] + [
        {"t": 2.0 + i, "vram_used": [22_000_000_000], "srv_pid_in_kfd": True} for i in range(5)]
    rt = [{"prompt_n": 1808, "predicted_n": 256, "prompt_per_second": 950.0 + i, "predicted_per_second": 51.0 + i} for i in range(3)]
    files["gpu_coh.json"] = json.dumps({"argv": [GPU, "-m", MODEL], "outputs": outs, "vram_samples": vs,
                                        "recipe_timings": rt, "server_dead": True})
    def greedy(binp, same):
        return json.dumps({"bin": binp, "argv": [binp, "-m", "/m/Qwen3.6-35B-A3B-MTP-Q8_0.gguf"], "outputs": [
            {"prompt": p, "content": f"text {p}" + ("" if same or p != "b" else "X"), "tokens_predicted": 256,
             "draft_n": 300, "draft_n_accepted": 180} for p in ("a", "b", "c")]})
    files["greedy_ctl.json"] = greedy(CTL, True)
    files["greedy_cand.json"] = greedy(CAND, ident_same)
    files["tbo_cpu_ADD.log"] = _tbo(99, "CPU")
    files["tbo_gpu_cand_ADD.log"] = _tbo(99, "ROCm0")
    files["tbo_gpu_ctl_ADD.log"] = _tbo(99, "ROCm0")
    files["tbo_cpu_TOP_K.log"] = _tbo(445, "CPU", ok=False)
    for k, v in files.items():
        (d / k).write_text(v)
    (d / "SHA256SUMS").write_text("".join(f"{hashlib.sha256((d / k).read_bytes()).hexdigest()}  artifacts/x/{k}\n" for k in files))
    return d


def write(tmp_path, **kw):
    art = build(tmp_path / "art", **kw)
    return nb.write_belief_measurements(tmp_path, run_id="nbf-t", producer="t", artifact_dir=art, emitted_at=WHEN)


def _rows(side):
    return [json.loads(x) for x in side.read_text().splitlines()]


def _by(side):
    return {r["extra"]["ident"]: r for r in _rows(side)}


def test_round_trip_and_ladder(tmp_path):
    side = write(tmp_path)
    natives = nb.native_rows(side)
    idents = {n["row"]["extra"]["ident"] for n in natives}
    assert idents == {"llamabench:pp512", "llamabench:tg128", "recipe:pp", "recipe:tg", "coherence:on", "coherence:off",
                      "residency", "greedy-identity:qwen36", "tbo:cpu:ADD", "tbo:cpu:TOP_K", "tbo:gpu_cand:ADD", "tbo:gpu_ctl:ADD"}
    for n in natives:
        t = nb.project(n)
        assert t.protocol_id == "" and t.attestation_present is True
        g = ct.grade(t)
        assert g[0] == "Judged" and ct.grade(dataclasses_replace_obs(t))[:2] == g[:2]
    by = {n["row"]["extra"]["ident"]: nb.project(n) for n in natives}
    assert by["llamabench:pp512"].value == pytest.approx(899.17) and by["llamabench:tg128"].value == pytest.approx(53.44)
    assert by["llamabench:pp512"].reps == 3 and by["llamabench:pp512"].extra["load1"] == pytest.approx(97.91)
    assert by["residency"].value == pytest.approx(5 / 6)
    assert by["coherence:on"].value == 1.0 and by["coherence:on"].extra["n_finish_length"] == 1
    assert by["greedy-identity:qwen36"].value == 1.0 and by["greedy-identity:qwen36"].extra["champion_sha"] == "dd3d9721c"
    assert by["tbo:cpu:TOP_K"].value == pytest.approx(444 / 445)
    assert by["tbo:gpu_ctl:ADD"].category == "BASELINE" and by["tbo:gpu_cand:ADD"].category == "CANDIDATE"
    assert nb.frames_for_sidecar(side, as_of=WHEN)


def dataclasses_replace_obs(t):
    import dataclasses
    return dataclasses.replace(t, observation={})


def test_speed_rows_never_carry_a_gating_field(tmp_path):
    side = write(tmp_path)
    for n in nb.native_rows(side):
        t = nb.project(n)
        if t.metric in nb.SPEED_METRICS:
            assert t.observation == {} and nb.CAVEAT in t.claim
            assert not set(t.extra) & set(nb.FORBIDDEN_SPEED_EXTRA)
            assert ct.grade(t)[0] == "Judged"
    # a speed row that grows a floor is refused
    pp = _by(side)["llamabench:pp512"]
    bad = ns_seal(dict(pp, extra=dict(pp["extra"], noise_floor_rel=0.01)))
    assert any("noise_floor_rel" in p for p in nb.row_problems(bad))
    bad = ns_seal(dict(pp, extra={k: v for k, v in pp["extra"].items() if k != "caveat"}))
    assert any("caveat" in p for p in nb.row_problems(bad))


def ns_seal(row):
    from adapters import _native_sidecar as ns
    row = {k: v for k, v in row.items() if k != "row_sha256"}
    return ns.seal(row)


def test_values_must_rederive(tmp_path):
    by = _by(write(tmp_path))
    cases = [("llamabench:pp512", {"value": 900.0}, "source_line"), ("residency", {"value": 1.0}, "n_resident"),
             ("coherence:on", {"value": 0.5}, "clean / total"), ("greedy-identity:qwen36", {"value": 0.5}, "n_identical"),
             ("tbo:cpu:TOP_K", {"value": 1.0}, "passed / total"), ("recipe:tg", {"value": 99.0}, "mean of extra.values")]
    for ident, patch, needle in cases:
        assert any(needle in p for p in nb.row_problems(ns_seal(dict(by[ident], **patch)))), ident
    r = by["greedy-identity:qwen36"]
    e = dict(r["extra"], n_identical=2)
    assert any("re-derive" in p for p in nb.row_problems(ns_seal(dict(r, extra=e))))
    e = dict(r["extra"], champion_sha="deadbee")
    assert any("champion_sha" in p for p in nb.row_problems(ns_seal(dict(r, extra=e))))
    r = by["tbo:cpu:TOP_K"]
    assert any("summary_line" in p for p in nb.row_problems(ns_seal(dict(r, extra=dict(r["extra"], summary_line="445/445 tests passed")))))
    # unsealed edit
    assert any("row_sha256" in p for p in nb.row_problems(dict(by["residency"], value=1.0)))


def test_foreign_and_protocol_rows_refused(tmp_path):
    side = write(tmp_path)
    r = _rows(side)[0]
    assert nb.row_problems(dict(r, schema="other"))
    assert any("protocol_id" in p for p in nb.row_problems(ns_seal(dict(r, protocol_id="P-1"))))
    assert any("metric" in p for p in nb.row_problems(ns_seal(dict(r, metric="foreign_metric"))))
    side.write_text(json.dumps(dict(r, value=r["value"] + 1)) + "\n")
    assert nb.native_rows(side) == ()
    with pytest.raises(ct.ProjectionError):
        nb.project({"row": dict(r, schema="other")})


def test_no_sidecar_zero_rows(tmp_path):
    assert nb.native_rows(tmp_path / "missing.jsonl") == ()


def test_unverified_sources_yield_no_rows(tmp_path):
    art = build(tmp_path / "art")
    (art / "gpu_coh.json").write_text("{}")  # mutated after SHA256SUMS
    side = nb.write_belief_measurements(tmp_path, run_id="r", producer="p", artifact_dir=art, emitted_at=WHEN)
    idents = set(_by(side))
    assert not any(i.startswith(("coherence", "residency", "recipe")) for i in idents) and "llamabench:pp512" in idents
    (art / "SHA256SUMS").unlink()
    with pytest.raises(nb.CaptureError, match="SHA256SUMS"):
        nb.write_belief_measurements(tmp_path, run_id="r", producer="p", artifact_dir=art)
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "SHA256SUMS").write_text(f"{'0' * 64}  x\n")
    with pytest.raises(nb.CaptureError, match="no verifiable"):
        nb.write_belief_measurements(tmp_path, run_id="r", producer="p", artifact_dir=empty)


def test_broken_identity_and_loops_are_carried_not_hidden(tmp_path):
    side = write(tmp_path, ident_same=False, coh_loop=True)
    by = _by(side)
    assert by["greedy-identity:qwen36"]["value"] == pytest.approx(2 / 3)
    assert by["coherence:on"]["value"] == pytest.approx(0.5)
    assert nb.project({"row": by["coherence:on"], "sidecar_path": str(side)}).observation["outcome_native"] == "1/2 coherent"


def test_mutated_attestation_grades_down(tmp_path):
    side = write(tmp_path)
    (tmp_path / "art" / "greedy_cand.json").write_text("{}")
    n = next(x for x in nb.native_rows(side) if x["row"]["extra"]["ident"] == "greedy-identity:qwen36")
    t = nb.project(n)
    assert t.attestation_present is False and t.attestation_verified is None
    assert ct.grade(t)[0] == "Judged"  # an observation: capped, never promoted; the attestation flag carries the loss


def test_cli_write(tmp_path, capsys):
    art = build(tmp_path / "art")
    assert nb.main(["write", "--artifact-dir", str(art), "--out-dir", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["rows"] == 12


@pytest.mark.skipif(not REAL.is_dir(), reason="real artifact dir absent")
def test_real_artifact_dir(tmp_path):
    side = nb.write_belief_measurements(tmp_path, run_id="real", producer="t", artifact_dir=REAL, emitted_at=WHEN)
    by = _by(side)
    assert len(by) == 30
    assert by["llamabench:pp512"]["value"] == pytest.approx(899.17) and by["llamabench:tg128"]["value"] == pytest.approx(53.44)
    assert by["llamabench:pp512"]["extra"]["load1"] == pytest.approx(97.91) and by["llamabench:pp512"]["extra"]["build_sha"] == "59c1b915f"
    assert by["greedy-identity:qwen36"]["extra"]["n_identical"] == 3 == by["greedy-identity:qwen36"]["extra"]["n_total"]
    assert by["coherence:on"]["extra"]["n_total"] == 4 and by["coherence:off"]["extra"]["n_total"] == 4
    assert by["residency"]["extra"]["n_samples"] == 10
    assert by["tbo:cpu:MUL_MAT"]["extra"]["total"] == 1139 and by["tbo:gpu_ctl:MUL_MAT_ID"]["extra"]["passed"] == 815
    for n in nb.native_rows(side):
        assert ct.grade(nb.project(n))[0] == "Judged"

