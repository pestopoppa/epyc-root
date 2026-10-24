"""VB-Q38-T10-1-GATE-WIRE: Q38-T10.1 serving-gate phase run -> OBSERVATION tuples graded by the one shared ladder."""
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import q38_serving_gate as q  # noqa: E402

WHEN = "2026-10-24T12:00:00Z"
REAL = Path("/workspace/artifacts/gpu-queue-20261020/q38-t10-1/serving-gate/gpu-run-20261021T092041Z")
RULE_TEXT = None


def _rule(gate: Path):
    """A synthetic rule file whose sha256 satisfies the predeclared prefix/suffix is infeasible; patch the check instead."""
    (gate / "PREDECLARED_RULE.md").write_text("rule\n")
    (gate / "corpus.jsonl").write_text("{}\n")
    (gate / "corpus.sha256").write_text(hashlib.sha256(b"{}\n").hexdigest() + "  corpus.jsonl\n")


@pytest.fixture(autouse=True)
def _fake_rule_hash(monkeypatch):
    real = q._sha
    monkeypatch.setattr(q, "_sha", lambda p: ("350a2a20" + "0" * 52 + "ffb3") if Path(p).name == "PREDECLARED_RULE.md" else real(p))


def build(tmp_path, phase="gpu", *, trunc_ids=(), regress=0, gain=0, aa_break=None, n=70, tweak=None):
    gate = tmp_path / "gate"
    run = gate / f"{phase}-run-x"
    run.mkdir(parents=True)
    _rule(gate)
    corpus = hashlib.sha256(b"{}\n").hexdigest()
    tags = q.PHASES[phase]
    recs = {t: [] for t in tags}
    rows = []
    for i in range(n):
        pid = f"p{i:03d}"
        base = i % 5 != 0
        spec = base
        if i < regress:
            base, spec = True, False
        elif regress <= i < regress + gain:
            base, spec = False, True
        toks = list(range(10, 20 + i % 7))
        spec_toks = toks if i % 4 else toks[:-1] + [999]
        t = pid in trunc_ids
        for tag, tk in zip(tags, (toks, aa_break == pid and toks[:-1] + [1] or toks, spec_toks)):
            recs[tag].append({"id": pid, "tokens": tk, "content": "x", "truncated": t, "draft_n": 5 if tag == tags[2] else None})
        outcome = q._outcome(base, spec, t)
        rows.append({"id": pid, "kind": "gsm8k", "gold": "1", "base_pass": base, "base_reason": "ok", "spec_pass": spec,
                     "spec_reason": "ok", "truncated_any": t, "n_tok_base": len(toks), "n_tok_spec": len(spec_toks),
                     "first_divergence": q._first_div(toks, spec_toks), "token_identical": toks == spec_toks, "outcome": outcome})
    for tag, rs in recs.items():
        (run / f"{tag}.records.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rs))
    summary = {"corpus_sha256": corpus, "n_predict": 512, "threshold": 0.05, "min_n": 59,
               "roles": {phase: {"role": f"{phase}-role", "arms": {}, "n_corpus": n, "rows": rows, "verdict": "PASS",
                                 "phase_status": "RAN_rc0"}}}
    (run / "summary.json").write_text(json.dumps(summary))
    (run / "per_prompt.tsv").write_text("phase\tid\tkind\tbase_pass\tspec_pass\toutcome\tfd\tnb\tns\n" + "".join(
        f"{phase}\t{r['id']}\t{r['kind']}\t{r['base_pass']}\t{r['spec_pass']}\t{r['outcome']}\tNone\t0\t0\n" for r in rows))
    spec_argv = ["/nonexistent/bin/llama-server", "-m", "/m/Q.gguf", "-np", "4", "--device",
                 "ROCm0" if phase == "gpu" else "none", "--spec-type", "draft-dflash" if phase == "gpu" else "draft-mtp"]
    (run / f"config_echo.{phase}.json").write_text(json.dumps({
        "corpus_sha256": corpus, "n_predict": 512, "spec_argv": spec_argv, "off_argv": spec_argv[:-2] + ["none"],
        "argv_source": "x", "bin_dir": "/nonexistent/builds/gpu-20261006-4348de400/bin"}))
    srv = [{"label": f"{phase}_off", "dead_after": True, "libs": ["/l/libggml.so"], "child_in_kfd_samples": 5 if phase == "gpu" else 0,
            "busy_nonzero_samples": 5, "vram_peak_gib": 41.0},
           {"label": f"{phase}_spec", "dead_after": True, "libs": ["/l/libggml.so"], "child_in_kfd_samples": 5 if phase == "gpu" else 0,
            "busy_nonzero_samples": 5, "vram_peak_gib": 41.0}]
    (run / f"phase.{phase}.json").write_text(json.dumps({"phase": phase, "status": "COMPLETE", "servers": srv}))
    if tweak:
        tweak(run, gate)
    return run


def write(tmp_path, phase="gpu", fake_rule=True, **kw):
    run = build(tmp_path, phase, **kw)
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    orig = q._sha
    if fake_rule:  # standalone use (ingest harness): a synthetic rule file cannot hash to 350a2a20...ffb3
        q._sha = lambda p: ("350a2a20" + "0" * 52 + "ffb3") if Path(p).name == "PREDECLARED_RULE.md" else orig(p)
    try:
        return q.write_belief_measurements(out, run_dir=run, run_id="r1", producer="t", emitted_at=WHEN)
    finally:
        q._sha = orig


def test_round_trip_gpu_and_cpu_same_code_path(tmp_path):
    for phase in ("gpu", "cpu"):
        d = tmp_path / phase
        d.mkdir()
        side = write(d, phase, trunc_ids=("p003",), regress=1, gain=3)
        nat = q.native_rows(side)
        assert {n["row"]["metric"] for n in nat} == q.METRICS
        by = {n["row"]["metric"]: n["row"] for n in nat}
        r = by[q.M_R]
        assert r["value"] == 1 and by[q.M_G]["value"] == 2 and r["extra"]["phase"] == phase
        assert r["extra"]["n_excluded_truncated"] == 1 and r["extra"]["excluded_truncated"] == ["p003"]
        assert len(r["extra"]["prompts"]) == 70 and r["reps"] == 69
        assert by[q.M_P]["value"] == pytest.approx(sum(math.comb(3, i) for i in range(1, 4)) / 8)
        for t in map(q.project, nat):
            assert t.protocol_id == "" and t.attestation_present is True and t.observation["n_pairs"] == 69
            assert ct.grade(t)[:2] == ("Judged", "Located")
            assert t.applicability["backend"] == ("gpu" if phase == "gpu" else "cpu")
        assert q.frames_for_sidecar(side, as_of=WHEN)


def test_aa_not_identical_gives_no_rows(tmp_path):
    with pytest.raises(q.CaptureError, match="A/A"):
        write(tmp_path, aa_break="p001")


def test_aa_precondition_also_enforced_by_the_reader(tmp_path):
    side = write(tmp_path)
    row = json.loads(side.read_text().splitlines()[0])
    row["extra"]["prompts"][1]["aa_identical"] = False
    ns_ = q.ns
    row["row_sha256"] = ns_.row_digest(row)
    assert any("A/A" in p for p in q.row_problems(row))


def test_wrong_rule_sha_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "_sha", lambda p: "ab" * 32)
    with pytest.raises(q.CaptureError, match="not the predeclared rule"):
        write(tmp_path, fake_rule=False)


def test_corpus_mismatch_and_missing_phase_files_refused(tmp_path):
    def bad(run, gate):
        (gate / "corpus.sha256").write_text("ab" * 32 + "  corpus.jsonl\n")
    with pytest.raises(q.CaptureError, match="corpus"):
        write(tmp_path, tweak=bad)
    d = tmp_path / "m"
    d.mkdir()
    run = build(d)
    (run / "phase.gpu.json").unlink()
    with pytest.raises(q.CaptureError, match="exactly one phase"):
        q.write_belief_measurements(d / "out", run_dir=run, run_id="r", producer="t")


def test_guards_failure_gives_no_rows(tmp_path):
    def dead(run, gate):
        p = json.loads((run / "phase.gpu.json").read_text())
        p["servers"][0]["child_in_kfd_samples"] = 0
        (run / "phase.gpu.json").write_text(json.dumps(p))
    side = None
    with pytest.raises(q.CaptureError, match="guards"):
        write(tmp_path, tweak=dead)
    assert side is None


def test_summary_disagreeing_with_records_refused(tmp_path):
    def lie(run, gate):
        s = json.loads((run / "summary.json").read_text())
        s["roles"]["gpu"]["rows"][2]["n_tok_spec"] += 1
        (run / "summary.json").write_text(json.dumps(s))
    with pytest.raises(q.CaptureError, match="disagrees with the records"):
        write(tmp_path, tweak=lie)


def test_tamper_refusals(tmp_path):
    side = write(tmp_path, regress=1, gain=2)
    rows = [json.loads(x) for x in side.read_text().splitlines()]
    row = next(r for r in rows if r["metric"] == q.M_R)
    assert q.row_problems(row) == []

    def reseal(r):
        r["row_sha256"] = q.ns.row_digest(r)
        return q.row_problems(r)
    assert any("re-derive" in p for p in reseal(dict(row, value=0.0)))
    flipped = json.loads(json.dumps(row))
    flipped["extra"]["prompts"][0]["spec_pass"] = not flipped["extra"]["prompts"][0]["spec_pass"]
    assert any("outcome does not re-derive" in p or "re-derive" in p for p in reseal(flipped))
    bad_rule = json.loads(json.dumps(row))
    bad_rule["extra"]["rule_sha256"] = "ab" * 32
    assert any("predeclared rule" in p for p in reseal(bad_rule))
    assert q.row_problems(dict(row, value=5.0))  # self-hash breaks
    foreign = dict(row, schema="epyc.vidya.other.v1")
    assert q.row_problems(foreign)


def test_foreign_rows_void_the_file_and_no_sidecar_is_zero_rows(tmp_path):
    side = write(tmp_path)
    assert q.native_rows(tmp_path / "nope.jsonl") == ()
    side.write_text(side.read_text() + json.dumps({"schema": "foreign"}) + "\n")
    assert q.native_rows(side) == ()


def test_mutated_attestation_grades_down(tmp_path):
    side = write(tmp_path)
    before = {ct.grade(q.project(n))[:2] for n in q.native_rows(side)}
    summary = Path(json.loads(side.read_text().splitlines()[0])["results_path"])
    summary.write_text(summary.read_text() + " ")
    nat = q.native_rows(side)
    assert nat and all(n["attestation_present"] is False for n in nat)
    after = {ct.grade(q.project(n))[:2] for n in nat}
    assert after != before or before == {("Judged", "Located")}
    for n in nat:
        assert q.project(n).attestation_present is False


@pytest.mark.skipif(not REAL.is_dir(), reason="real GPU serving-gate run dir absent")
def test_real_gpu_run(tmp_path, monkeypatch):
    monkeypatch.undo()  # real sha of the real PREDECLARED_RULE.md
    side = q.write_belief_measurements(tmp_path, run_dir=REAL, run_id="real", producer="t", emitted_at=WHEN)
    by = {n["row"]["metric"]: n["row"] for n in q.native_rows(side)}
    e = by[q.M_R]["extra"]
    assert (e["R"], e["G"], e["n_clean"], e["n_excluded_truncated"], e["aa_identical"]) == (0, 0, 78, 2, "80/80")
    assert e["token_identical"] == 69 and e["rule_verdict"] == "PASS" and e["rule_sha256"].startswith("350a2a20")
    assert e["corpus_sha256"].startswith("224e7d92") and e["guards"]["hip_resident"] is True
    assert by[q.M_P]["value"] == 1.0
    for n in q.native_rows(side):
        assert ct.grade(q.project(n))[:2] == ("Judged", "Located")
