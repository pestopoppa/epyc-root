"""VB-SPEC-RNG-1-2-WIRE: SPEC-RNG.1.2 launcher dirs project to re-derived, INDICATIVE observation tuples."""
import hashlib
import json
import random
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import spec_rng_1_2 as srng  # noqa: E402

REAL = Path("/mnt/raid0/llm/tmp/f8-launchers-20261023/spec-rng-1-2-gpu-run")
REASON = "distribution invariant but no demonstrated reproducibility gain: not worth a fold slot"
BINARY_DIR = "/mnt/raid0/llm/worktrees/spec-rng-argv-20261022/build-hip-poskey/bin"
SERVER_ARGV = [f"{BINARY_DIR}/llama-server", "-m", "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf",
               "--port", "18385", "-np", "4", "-b", "512", "-ub", "512", "--kv-unified",
               "-md", "/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf", "--spec-type", "draft-dflash",
               "--spec-draft-n-max", "7", "--device", "ROCm0"]
WEIGHTS = [40, 25, 15, 10, 6, 4]


def _records(n_cell=300, probe_seeds=40, seed=11):
    rng = random.Random(seed)
    rows, t = [], 1792790000.0
    for ai, arm in enumerate(srng.ARMS):
        depth = int(arm[1:])
        for p in range(srng.N_PROMPTS):
            for k in range(n_cell):
                toks = [100 * p + rng.choices(range(len(WEIGHTS)), WEIGHTS)[0] for _ in range(srng.K_TOKENS)]
                dn = depth * rng.randint(1, 3)
                t += 0.5
                rows.append({"phase": "main", "arm": arm, "prompt": p, "seed": 1_000_000 + ai * 100_000 + p * 10_000 + k,
                             "ok": True, "t1": t, "tokens": toks, "draft_n": dn,
                             "draft_n_accepted": rng.randint(0, dn // 3) if dn else 0})
    for i in range(probe_seeds):
        for r in srng.RNGS:
            toks = [rng.randrange(1000) for _ in range(24)]
            for cond in ("alone", "batched"):
                rows.append({"phase": "probe", "rng": r, "cond": cond, "seed": 5_000_000 + i, "ok": True,
                             "tokens": toks, "draft_n": 30, "draft_n_accepted": 6})
    return rows


def _seal(run: Path, rows: list, *, predeclaration: bytes | None = None) -> None:
    """Write the launcher files exactly as the runner + launcher would, from `rows`."""
    out = run / "out"
    out.mkdir(parents=True, exist_ok=True)
    raw = "".join(json.dumps(r) + "\n" for r in rows).encode()
    (out / "records.jsonl").write_bytes(raw)
    pre = run / "PREDECLARATION.md"
    if predeclaration is not None or not pre.exists():
        pre.write_bytes(predeclaration or b"# spec-rng-1-2 synthetic fixture: decision rule\n")
    res = srng.rederive(rows)
    verdict = dict(res, reason=REASON, records_sha256=hashlib.sha256(raw).hexdigest())
    (out / "verdict.json").write_text(json.dumps(verdict, indent=1))
    (run / "VERDICT.json").write_text(json.dumps({"verdict": res["verdict"], "reason": REASON,
                                                  "probe": res["probe"], "gates": res["gates"]}))
    comps = {n: {k: c[k] for k in ("A", "B", "role", "min_p", "bonferroni_threshold", "mean_tv", "pass",
                                   "pos0_null_pass")} for n, c in res["comparisons"].items()}
    (run / "RUN_RECORD.json").write_text(json.dumps({
        "item": run.name, "handoff": "speculative-decoding-mtp-refresh.md SPEC-RNG.1.2",
        "verdict": res["verdict"], "reason": REASON, "gates": res["gates"], "comparisons": comps,
        "acceptance": res["acceptance"], "probe": res["probe"], "n_cell": res["n_cell"],
        "binary_dir": BINARY_DIR, "branch": "experimental/spec-rng-argv-20261022",
        "head": "261db6c7ef5c1ac58d231b6d835529504b45978d", "llama_server_sha256": "a" * 64,
        "predeclaration_sha256": hashlib.sha256(pre.read_bytes()).hexdigest(),
        "runner_pin": "2f8af0e2d2f790da5ff65172596565e64d4195b2",
        "argv": ["env", "X=0", "taskset", "-c", "184-191", *SERVER_ARGV], "server_generations": 1,
        "claim_class": "INDICATIVE correctness (no throughput claim)", "rule": "PREDECLARATION.md"}))
    (run / "PINSHA").write_text("2f8af0e2d2f790da5ff65172596565e64d4195b2\n")
    (out / "environ_proof.gen1.json").write_text(json.dumps({
        "graphs": "ON", "LLAMA_RNG_POSKEY_in_environ": None, "rng_poskey_on_cmdline": False,
        "cmdline": " ".join(SERVER_ARGV)}))


def write(tmp_path: Path) -> Path:
    """A small synthetic SPEC-RNG.1.2 launcher dir (generated rows, DO-NOT-CARRY) for the ingest test."""
    run = Path(tmp_path) / "spec-rng-1-2-gpu-run"
    run.mkdir(parents=True, exist_ok=True)
    _seal(run, _records())
    return run


@pytest.fixture(scope="module")
def base_rows():
    return _records()


@pytest.fixture()
def run(tmp_path, base_rows):
    r = tmp_path / "spec-rng-1-2-gpu-run"
    r.mkdir()
    _seal(r, base_rows)
    return r


def _project(run):
    return [ct.registered()[srng.SOURCE_KIND](n) for n in srng.native_rows(run)]


def test_round_trip_projects_eight_judged_located_observations(run):
    tuples = _project(run)
    comps = [t.extra["component"] for t in tuples]
    assert comps == ["P3", "P7", "C3", "C7", "X0", "acceptance_depth3", "acceptance_depth7", "probe"]
    pre = hashlib.sha256((run / "PREDECLARATION.md").read_bytes()).hexdigest()
    for t in tuples:
        assert ct.grade(t)[:2] == ("Judged", "Located")
        assert t.protocol_id == "" and t.source_class == "verifier" and t.binding_kind == ""
        assert pre in t.decided_proposition and "DO-NOT-CARRY" in t.decided_proposition
        assert t.extra["predeclaration_sha256"] == pre and t.attestation_verified is True
        assert t.observation["retrofit"] is True and t.observation["outcome"] == "null"
        assert "tok" not in t.metric and t.unit in ("p", "fraction", "seeds")
        assert ct.grade(t) == ct.grade(replace(t, observation={}))
    p3 = tuples[0]
    assert p3.metric == "spec_rng_chi2_min_p" and p3.reps == 300
    assert p3.observation["anchor_value"] == pytest.approx(0.01 / 33)
    assert p3.extra["n_cell"] == {f"{a}/{p}": 300 for a in ("p3", "p0") for p in range(3)}
    assert tuples[2].category == "BASELINE" and p3.category == "CANDIDATE"
    probe = tuples[-1]
    assert probe.value == 0 and probe.observation["n_pairs"] == 40 and probe.extra["sign_p_one_sided"] == 1.0
    a = probe.applicability
    assert a["backend"] == "gpu" and a["np"] == 4 and a["knobs"]["dflash2"] is True
    assert a["kernel"]["build_path"] == f"{BINARY_DIR}/llama-server"


def test_frames_carry_the_decided_proposition(run):
    t = _project(run)[0]
    frames = ct.to_frames(t, as_of="2026-10-24T09:00:00Z", adapter_id=srng.ADAPTER_ID)
    assert len(frames) == 3
    assert frames[1]["assertion"]["decided_proposition"] == t.decided_proposition


def test_tampered_request_row_is_refused(run, base_rows):
    rows = [dict(r) for r in base_rows]
    rows[7] = dict(rows[7], tokens=[999] * 12)
    raw = "".join(json.dumps(r) + "\n" for r in rows).encode()
    (run / "out" / "records.jsonl").write_bytes(raw)
    with pytest.raises(ct.ProjectionError, match="records_sha256"):
        srng.native_rows(run)
    # Re-sealing the digest alone does not help: the statistics no longer re-derive.
    v = json.loads((run / "out" / "verdict.json").read_text())
    v["records_sha256"] = hashlib.sha256(raw).hexdigest()
    (run / "out" / "verdict.json").write_text(json.dumps(v))
    with pytest.raises(ct.ProjectionError, match="re-derived"):
        srng.native_rows(run)


def test_tampered_stated_statistic_is_refused(run):
    v = json.loads((run / "out" / "verdict.json").read_text())
    v["acceptance"]["depth7"]["p"] *= 1.001
    (run / "out" / "verdict.json").write_text(json.dumps(v))
    with pytest.raises(ct.ProjectionError, match="acceptance.depth7.p"):
        srng.native_rows(run)


def test_edited_predeclaration_is_refused(run):
    (run / "PREDECLARATION.md").write_bytes(b"# a rule written after the run\n")
    with pytest.raises(ct.ProjectionError, match="predeclaration_sha256"):
        srng.native_rows(run)


def test_foreign_verdict_dir_is_declined(tmp_path):
    other = tmp_path / "gpu-zos-1a"
    other.mkdir()
    (other / "VERDICT.json").write_text(json.dumps({"verdict": "OPEN"}))
    (other / "RUN_RECORD.json").write_text(json.dumps({"item": "gpu-zos-1a", "handoff": "gpu-serving GPU-ZOS-1a"}))
    assert srng.native_rows(other) == []
    bare = tmp_path / "bare"
    bare.mkdir()
    (bare / "VERDICT.json").write_text("{}")
    assert srng.native_rows(bare) == []


def test_inconclusive_run_projects_nothing(tmp_path):
    run = tmp_path / "short"
    run.mkdir()
    _seal(run, _records(n_cell=120, probe_seeds=10))   # V1 fails: cells below 300
    assert json.loads((run / "VERDICT.json").read_text())["verdict"] == "INCONCLUSIVE"
    assert srng.native_rows(run) == []


def test_environ_readback_mismatch_drops_scope_not_the_claim(run):
    (run / "out" / "environ_proof.gen1.json").write_text(json.dumps({
        "graphs": "OFF", "LLAMA_RNG_POSKEY_in_environ": None, "rng_poskey_on_cmdline": False,
        "cmdline": " ".join(SERVER_ARGV)}))
    tuples = _project(run)
    assert len(tuples) == 8 and all(t.applicability == {} for t in tuples)


def test_registered_without_a_ladder():
    assert ct.source_classes()[srng.SOURCE_KIND] == "verifier"
    assert "verifier" not in ct.ladders()


@pytest.mark.skipif(not (REAL / "out" / "records.jsonl").is_file(), reason="real SPEC-RNG.1.2 run not on this host")
def test_real_run_re_derives_and_projects():
    tuples = _project(REAL)
    assert len(tuples) == 8
    by = {t.extra["component"]: t for t in tuples}
    assert by["P3"].value == pytest.approx(0.0010896395583385504, rel=1e-9)
    assert by["acceptance_depth3"].extra["welch_p"] == pytest.approx(0.11836444482479738, rel=1e-9)
    assert by["probe"].value == 0 and by["probe"].reps == 48
    assert all("0af228a0ee1af4408877ca8221108fb37ffd9a14d24e9dd71becc34ef0f8254f" in t.decided_proposition
               and "DO-NOT-CARRY" in t.decided_proposition for t in tuples)
    assert all(ct.grade(t)[:2] == ("Judged", "Located") for t in tuples)


# --- write side: rule sha + analyzed_at on the verdict files, out/belief_measurements.jsonl ------------------------
import os  # noqa: E402
import subprocess  # noqa: E402

from adapters import _native_sidecar as NS  # noqa: E402

ANALYZED = "2026-10-24T12:00:00Z"


def _stamp_and_sidecar(run: Path, *, sidecar: bool = True) -> list[dict]:
    """What the research runner's `analyze --summary` writes (test-local writer in the runner's vocabulary)."""
    legacy = srng.native_rows(run)[0]["run"]
    pre = legacy["predeclaration_sha256"]
    ov = json.loads((run / srng.VERDICT_OUT).read_text())
    ov.update(predeclaration_sha256=pre, analyzed_at=ANALYZED)
    (run / srng.VERDICT_OUT).write_text(json.dumps(ov, indent=1))
    ov_sha = hashlib.sha256((run / srng.VERDICT_OUT).read_bytes()).hexdigest()
    top = json.loads((run / "VERDICT.json").read_text())
    top.update(predeclaration_sha256=pre, analyzed_at=ANALYZED, records_sha256=legacy["records_sha256"],
               verdict_sha256=ov_sha)
    (run / "VERDICT.json").write_text(json.dumps(top))
    if not sidecar:
        return []
    r = dict(legacy, verdict_sha256=ov_sha)
    rows = []
    for comp in [c[0] for c in srng.COMPARISONS] + ["acceptance_depth3", "acceptance_depth7", "probe"]:
        core = srng._core(comp, r["derived"])
        row = {"schema": srng.SIDECAR_SCHEMA, "run_name": run.name, "component": comp, **core,
               "metric_direction": "higher_better", "decided_proposition": srng._proposition(comp, r),
               "verdict": r["verdict"], "reason": r["reason"], "predeclaration_sha256": pre,
               "records_sha256": r["records_sha256"], "verdict_sha256": ov_sha,
               "inputs": {"out/records.jsonl": r["records_sha256"], "PREDECLARATION.md": pre},
               "analyzed_at": ANALYZED, "emitted_at": ANALYZED, "runner": {"file": "spec_rng_1_2.py", "sha256": "0" * 64}}
        row["content_sha256"] = NS.content_hash(row)
        rows.append(row)
    (run / srng.SIDECAR).write_text("".join(json.dumps(x) + "\n" for x in rows))
    return rows


def _rewrite_sidecar(run: Path, edit) -> None:
    rows = [json.loads(x) for x in (run / srng.SIDECAR).read_text().splitlines()]
    (run / srng.SIDECAR).write_text("".join(json.dumps(x) + "\n" for x in edit(rows)))


def _reseal(row: dict) -> dict:
    row["content_sha256"] = NS.content_hash({k: v for k, v in row.items() if k != "content_sha256"})
    return row


def test_stamped_verdicts_without_sidecar_still_read_as_retrofit(run):
    _stamp_and_sidecar(run, sidecar=False)
    tuples = _project(run)
    assert len(tuples) == 8 and all(t.observation["retrofit"] is True for t in tuples)
    assert tuples[0].extra["analyzed_at"] == ANALYZED and "write_side_gap" in tuples[0].extra


def test_verified_sidecar_clears_retrofit_and_keeps_every_value(run):
    before = _project(run)
    _stamp_and_sidecar(run)
    after = _project(run)
    assert [(t.value, t.reps, t.decided_proposition) for t in after] == \
        [(t.value, t.reps, t.decided_proposition) for t in before]
    for t in after:
        assert t.observation["retrofit"] is False and t.extra["write_side"]["path"].endswith(srng.SIDECAR)
        assert ct.grade(t)[:2] == ("Judged", "Located")


@pytest.mark.parametrize("field,value,match", [
    ("predeclaration_sha256", "0" * 64, "predeclaration_sha256"),
    ("analyzed_at", "2026-10-24 12:00", "analyzed_at"),
])
def test_wrong_stamp_on_out_verdict_is_refused(run, field, value, match):
    _stamp_and_sidecar(run, sidecar=False)
    ov = json.loads((run / srng.VERDICT_OUT).read_text())
    ov[field] = value
    (run / srng.VERDICT_OUT).write_text(json.dumps(ov))
    with pytest.raises(ct.ProjectionError, match=match):
        srng.native_rows(run)


def test_wrong_stamp_on_top_level_verdict_is_refused(run):
    _stamp_and_sidecar(run, sidecar=False)
    top = json.loads((run / "VERDICT.json").read_text())
    top["verdict_sha256"] = "1" * 64
    (run / "VERDICT.json").write_text(json.dumps(top))
    with pytest.raises(ct.ProjectionError, match="verdict_sha256"):
        srng.native_rows(run)


@pytest.mark.parametrize("edit,match", [
    (lambda rows: rows[:-1], "eight"),
    (lambda rows: [{**rows[0], "value": 0.5}] + rows[1:], "content_sha256"),
    (lambda rows: [_reseal({**rows[0], "value": rows[0]["value"] * 1.01})] + rows[1:], "value"),
    (lambda rows: [_reseal({**r, "verdict": "CARRY"}) for r in rows], "verdict"),
    (lambda rows: [_reseal({**r, "unit": "tok/s"}) for r in rows], "unit"),
    (lambda rows: [_reseal({**rows[0], "decided_proposition": rows[0]["decided_proposition"] + "!"})] + rows[1:],
     "decided_proposition"),
    (lambda rows: [_reseal({**r, "inputs": {**r["inputs"], "PREDECLARATION.md": "2" * 64}}) for r in rows],
     "records and rule"),
])
def test_sidecar_tamper_is_refused(run, edit, match):
    _stamp_and_sidecar(run)
    _rewrite_sidecar(run, edit)
    with pytest.raises(ct.ProjectionError, match=match):
        srng.native_rows(run)


def _runner() -> Path | None:
    for cand in (os.environ.get("SPEC_RNG_RUNNER"),
                 "/workspace/repos/epyc-inference-research/scripts/benchmark/spec_rng_1_2/spec_rng_1_2.py"):
        if cand and Path(cand).is_file() and "def finish(" in Path(cand).read_text():
            return Path(cand)
    return None


@pytest.mark.skipif(_runner() is None, reason="no SPEC-RNG.1.2 runner with the belief write side on this host")
def test_the_research_runner_output_cross_verifies(run):
    rec = run / "out" / "records.jsonl"
    subprocess.run(["/usr/bin/python3", "-B", "-I", str(_runner()), "analyze", "--records", str(rec), "--out",
                    str(run / srng.VERDICT_OUT), "--summary", str(run / "VERDICT.json")], check=True,
                   capture_output=True)
    ov = json.loads((run / srng.VERDICT_OUT).read_text())
    # the fixture's verdict reason is the run's reason; the runner states its own (identical rule text)
    assert ov["predeclaration_sha256"] == hashlib.sha256((run / "PREDECLARATION.md").read_bytes()).hexdigest()
    rr = json.loads((run / "RUN_RECORD.json").read_text())
    rr["reason"] = ov["reason"]
    (run / "RUN_RECORD.json").write_text(json.dumps(rr))
    tuples = _project(run)
    assert len(tuples) == 8 and all(t.observation["retrofit"] is False for t in tuples)
