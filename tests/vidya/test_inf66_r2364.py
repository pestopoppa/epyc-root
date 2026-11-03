"""INF-66 R23-64 thread sweep -> strict sealed reader -> shared grade (VB-R2364-SWEEP-WIRE). Read-only."""
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import inf66_r2364 as ad  # noqa: E402

AS_OF = "2026-11-03T12:00:00Z"
_SWEEP = "data/inf66/r23-64-thread-sweep-20261025"
REAL = next((p for p in (Path(os.environ.get("INF66_R2364_DIR", "/nonexistent")),
                         Path("/workspace/repos/epyc-inference-research") / _SWEEP,
                         Path("/workspace/tmp/r2364") / _SWEEP) if p.is_dir()),
            Path("/nonexistent"))
BUILD = "/mnt/raid0/llm/kernels/builds/cpu-20261023-141e4bcf5-lbh/bin"
MODEL = "/m/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf"
THREADS = {"t48": 48, "t64": 64, "t96": 96}
ARM_ROWS = {"t48": [(100, 2000.0)], "t64": [(100, 2500.0)], "t96": [(100, 2100.0)]}  # (pred_n, pred_ms)


def _tps(arm):
    return ARM_ROWS[arm][0][0] / (ARM_ROWS[arm][0][1] / 1000.0)


def _build(root: Path, tamper_floor_unit=False) -> Path:
    d = root / "sweep"
    (d / "runs").mkdir(parents=True)
    launches, arms = [], {}
    for arm in THREADS:
        vals = []
        for r in (1, 2):
            label = f"{arm}_r{r}"
            n, ms = ARM_ROWS[arm][0]
            ms = ms * (1 + 0.01 * r)
            rows = [{"pred_n": n, "pred_ms": ms}, {"pred_n": 4, "pred_ms": 1.0}]
            (d / "runs" / f"{label}.rows.jsonl").write_text("\n".join(json.dumps(x) for x in rows) + "\n")
            (d / "runs" / f"{label}.argv").write_text("\n".join(
                ["taskset", f"{BUILD}/llama-server", "-t", str(THREADS[arm]), "-m", MODEL]) + "\n")
            (d / "runs" / f"{label}.env").write_text("GGML_IQK=1\nHOME=/tmp\n")
            tps = n / (ms / 1000.0)
            vals.append(tps)
            launches.append({"arm": arm, "label": label, "n_dec": 1, "round": r, "status": "valid", "tps": tps})
        m = sum(vals) / 2
        sd = (sum((v - m) ** 2 for v in vals) / 1) ** 0.5
        arms[arm] = {"mean": m, "sd": sd, "n": 2, "values": vals, "ci95": [m - 1, m + 1], "cv_pct": 100 * sd / m}
    vs = {a: {"effect_pct": (arms[a]["mean"] / arms["t48"]["mean"] - 1) * 100, "boot_ci95_pct": [-1.0, 1.0],
              "ci_excludes_zero": False, "mde_floor_pct": 1.0, "mde_observed_pct": 2.0} for a in ("t64", "t96")}
    ana = {"arms": arms, "control": "t48", "excluded": [], "launches": launches, "unit": "launch",
           "floor": {"n": 6, "sd_pct": 0.609, "unit": "arm" if tamper_floor_unit else "launch"}, "vs_control": vs}
    (d / "ANALYSIS.json").write_text(json.dumps(ana, sort_keys=True))
    (d / "RESULT.txt").write_text(
        "R23-64 -- champion 141e4bcf5 (build 1)\nrounds run: 2   finished: 2026-10-25T22:29:05Z\n"
        f"  t64    {vs['t64']['effect_pct']:.2f}%  CI [-1.00, 1.00]%  MDE(observed) 2.00%  n=2v2  RESOLVED\n"
        f"  t96    {vs['t96']['effect_pct']:.2f}%  CI [-1.00, 1.00]%  MDE(observed) 2.00%  n=2v2  UNRESOLVED\n")
    _seal(d)
    return d


def _seal(d: Path):
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  ./{p.relative_to(d)}"
             for p in sorted(d.rglob("*")) if p.is_file() and p.name != "SHA256SUMS"]
    (d / "SHA256SUMS").write_text("\n".join(lines) + "\n")


def test_synthetic_sweep_projects_arms_and_effects_with_verdicts_verbatim(tmp_path):
    d = _build(tmp_path)
    rows = ad.native_rows(d)
    assert len(rows) == 5  # 3 arm means + 2 effects
    tuples = {t.measurement_id: t for t in map(ad.project, rows)}
    t48 = tuples["inf66-r2364:t48:decode_tps_mean"]
    assert t48.category == "BASELINE" and t48.applicability["threads"] == 48 and t48.protocol_id == ""
    assert t48.applicability["quant"] == "UD-IQ4_XS" and t48.applicability["build_sha"] == "141e4bcf5"
    assert t48.observation["noise_floor_rel"] == pytest.approx(0.00609)
    assert tuples["inf66-r2364:t64:vs_t48:effect_pct"].observation["outcome_native"] == "RESOLVED"
    assert tuples["inf66-r2364:t96:vs_t48:effect_pct"].observation["outcome_native"] == "UNRESOLVED"
    for t in tuples.values():
        ct.grade(t)


@pytest.mark.parametrize("mutate", ["rows", "analysis", "unsealed_argv", "floor_unit", "argv_threads", "verdict_missing"])
def test_tamper_is_refused(tmp_path, mutate):
    d = _build(tmp_path, tamper_floor_unit=(mutate == "floor_unit"))
    if mutate == "rows":
        p = d / "runs" / "t48_r1.rows.jsonl"
        p.write_text(p.read_text().replace("2020.0", "2021.0").replace('"pred_n": 100', '"pred_n": 101'))
    elif mutate == "analysis":
        a = json.loads((d / "ANALYSIS.json").read_text())
        a["arms"]["t48"]["mean"] += 1
        (d / "ANALYSIS.json").write_text(json.dumps(a))
        _seal(d)
    elif mutate == "unsealed_argv":
        (d / "runs" / "t48_r1.argv").write_text("changed")
    elif mutate == "argv_threads":
        p = d / "runs" / "t64_r1.argv"
        p.write_text(p.read_text().replace("\n64\n", "\n48\n"))
        _seal(d)
    elif mutate == "verdict_missing":
        (d / "RESULT.txt").write_text("champion 141e4bcf5\nfinished: 2026-10-25T22:29:05Z\n")
        _seal(d)
    if mutate == "rows":
        pass  # rows edit without resealing: SHA256SUMS mismatch
    with pytest.raises(ct.ProjectionError):
        ad.native_rows(d)


def test_cli_ingest_synthetic_refused_zero(tmp_path, capsys):
    d = _build(tmp_path)
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "inf66-r2364", "--path", str(d), "--as-of", AS_OF, "--dry-run"])
    rep = json.loads(capsys.readouterr().out)
    assert rc == 0 and rep["refused"] == [] and rep["rows_projected"] == 5 and not ledger.exists()


@pytest.mark.skipif(not REAL.is_dir(), reason="research sweep not checked out")
def test_real_sweep_projects_refused_zero(tmp_path, capsys):
    rc = cli.main(["--ledger", str(tmp_path / "l.jsonl"), "--json", "ingest", "inf66-r2364", "--path", str(REAL),
                   "--as-of", AS_OF, "--dry-run"])
    rep = json.loads(capsys.readouterr().out)
    assert rc == 0 and rep["refused"] == [] and rep["declined"] == [] and rep["rows_projected"] == 5
    by = {t.measurement_id: t for t in map(ad.project, ad.native_rows(REAL))}
    assert by["inf66-r2364:t48:decode_tps_mean"].value == pytest.approx(44.29703003300727)
    assert by["inf66-r2364:t64:vs_t48:effect_pct"].observation["outcome_native"] == "RESOLVED"
    assert by["inf66-r2364:t96:vs_t48:effect_pct"].observation["outcome_native"] == "UNRESOLVED"
