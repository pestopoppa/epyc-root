"""U4-NOISE-1 GPU -> CPU timing contamination sessions -> measurement ClaimTuples (VB-GPU-CPU-NOISE-WIRE).

Source: one session directory written by research ``scripts/benchmark/gpu_cpu_noise/`` (driver +
analyzer): ``RUN_RECORD.json`` (``epyc.gpu_cpu_noise.run_record.v1``: prereg path + sha256, schedule
sha256, binaries, host state), ``schedule.json``, ``reps.jsonl`` (``epyc.gpu_cpu_noise.rep.v1``, one
self-hashed row per rep), ``END.json`` and the analyzer's primary ``ANALYSIS.json``.

STRICT READER. Before anything projects it re-hashes the pre-registration against the sha256 the
driver recorded BEFORE the first measured rep, re-hashes ``schedule.json``, re-hashes every rep row
(``content_sha256``), and re-derives from the rows themselves every DETERMINISTIC number the
analyzer reports: row and hash-bad counts, the per-condition valid fraction and invalid reasons,
every point bias (pooled-median ratio over the paired blocks, the A/A one included), the paired
block count, and every process- and arm-unit variance ratio, sigma_add and its degrees of freedom.
Any difference refuses the session. The bootstrap / t / F intervals and the pre-registered verdicts
are carried verbatim from the analyzer (they are seeded resamples; this reader does not re-run
them and does not re-decide them).

Absence is never filled: a session whose ``END.json`` is not ``rc 0 / complete`` (the aborted
``20261022T164830Z``, END rc=5 ``gpu-warmup-failed``), a dry/stub run, or a directory without an
analysis projects ZERO rows. Invalid reps stay rows in ``reps.jsonl``; they are excluded exactly as
the pre-registered primary analysis excludes them, and counted in ``extra``.

PROJECTION ONLY. ``claim_tuple.grade()`` decides; no ladder here. The pre-registration is a
harness-local document, not a ratified ``MEASUREMENT.md`` protocol (the OCC-1 precedent), so
``protocol_id`` is EMPTY and every tuple is an OBSERVATION; the prereg sha256 rides in the claim
text and ``extra``. A bench-class (W1) contamination estimate is NOT a serving speed number
(INSTRUMENT-CLASS-1); W2 is a served whole-host CPU model, and its DG/AK cells are not its decision
(addendum section 8) -- the W2 CO-RUN / W1-transfer verdict is carried instead.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shlex
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.gpu_cpu_noise/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "gpu-cpu-noise"
RUN_SCHEMA = "epyc.gpu_cpu_noise.run_record.v1"
REP_SCHEMA = "epyc.gpu_cpu_noise.rep.v1"
MAX_BYTES = 64 << 20
CONDS = ("G1", "G2", "G3", "G4", "S8")
METRICS = {"tg": "decode (tg)", "pp": "prefill (pp)"}
COND_TEXT = {
    "G1": "27B GPU server resident, idle (host threads 184-191, node 3)",
    "G2": "27B GPU decode loop, 1 stream (host threads 184-191, node 3)",
    "G3": "27B GPU prefill-heavy loop (host threads 184-191, node 3)",
    "G4": "27B GPU decode loop with host threads 136-143 (node 1)",
    "S8": "GPU idle + 8 ALU spinners on 184-191 (SMT-only control)",
}
# quantity -> (metric suffix, unit, direction, noise unit or None for bias)
QUANTITIES = (
    ("bias_pct", "%", "higher_better", None),
    ("vr_process", "ratio", "lower_better", "process"),
    ("sigma_add_pct", "%", "lower_better", "process"),
    ("vr_arm", "ratio", "lower_better", "arm"),
)
TOL = 1e-9
_QUANT = re.compile(r"-((?:UD-)?I?Q\d(?:_[A-Z0-9]+)*|BF16|F16)(?:-\d{5}-of-\d{5})?\.gguf$")
_BUILD = re.compile(r"/kernels/builds/cpu-\d{8}-([0-9a-f]{7,40})/")
_SHA = re.compile(r"[0-9a-f]{64}")


# ------------------------------------------------------------------ reading

def _read(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
    except OSError as exc:
        raise ProjectionError(f"gpu-cpu-noise input unreadable: {path}: {exc}") from exc
    if len(raw) > MAX_BYTES:
        raise ProjectionError(f"gpu-cpu-noise input exceeds bound: {path}")
    return raw


def _json(path: Path) -> tuple[Any, str]:
    raw = _read(path)
    try:
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    except ValueError as exc:
        raise ProjectionError(f"gpu-cpu-noise {path.name} is not JSON") from exc


def _row_hash_ok(row: dict) -> bool:
    body = json.dumps({k: v for k, v in row.items() if k != "content_sha256"}, sort_keys=True).encode()
    return hashlib.sha256(body).hexdigest() == row.get("content_sha256")


# ------------------------------------------------------------------ re-derivation (deterministic parts)

def _rep_value(row: dict, metric: str) -> float | None:
    samples = (row.get(metric) or {}).get("samples_ts") or []
    return float(sum(samples) / len(samples)) if samples else None


def _organize(rows: list[dict], metric: str) -> dict:
    """runs[(block, run, cond)] = [(log rep value, [log samples])]; a retry replaces its failure."""
    by_id: dict[str, dict] = {}
    for row in rows:
        if row.get("phase") != "measure" or not row["_hash_ok"]:
            continue
        if row.get("valid") and _rep_value(row, metric) is not None:
            by_id[row["rep_id"].replace("-retry", "")] = row
    runs: dict = defaultdict(list)
    for row in by_id.values():
        logs = [math.log(x) for x in (row[metric].get("samples_ts") or []) if x and x > 0]
        runs[(row["block"], row["run"], row["cond"])].append((math.log(_rep_value(row, metric)), logs))
    return runs


def _pooled_var(groups: list[list[float]]) -> tuple[float, int]:
    ss = df = 0.0
    for g in groups:
        if len(g) >= 2:
            mean = sum(g) / len(g)
            ss += sum((x - mean) ** 2 for x in g)
            df += len(g) - 1
    return (ss / df if df else float("nan")), int(df)


def _pooled_bias(cand: dict, anch: dict, blocks: list) -> float:
    c = [v for b in blocks for v in cand[b]]
    a = [v for b in blocks for v in anch[b]]
    return 100 * (math.exp(statistics.median(c) - statistics.median(a)) - 1)


def _derive(runs: dict, cond: str) -> dict:
    blocks = sorted({b for (b, _, c) in runs})
    paired = [b for b in blocks if any(c == cond for (bb, _, c) in runs if bb == b)
              and any(c == "G0" for (bb, _, c) in runs if bb == b)]
    cand = {b: [v for (bb, _, c), reps in runs.items() if bb == b and c == cond for v, _ in reps] for b in paired}
    anch = {b: [v for (bb, _, c), reps in runs.items() if bb == b and c == "G0" for v, _ in reps] for b in paired}
    paired = [b for b in paired if cand[b] and anch[b]]
    out: dict[str, Any] = {"n_blocks": len(paired),
                           "n_reps": sum(len(reps) for k, reps in runs.items() if k[2] == cond),
                           "n_samples": sum(len(s) for k, reps in runs.items() if k[2] == cond for _, s in reps)}
    if len(paired) >= 2:
        out["bias_pct"] = _pooled_bias(cand, anch, paired)
    for unit in ("process", "arm"):
        if unit == "process":
            gk = [[v for v, _ in reps] for k, reps in runs.items() if k[2] == cond]
            g0 = [[v for v, _ in reps] for k, reps in runs.items() if k[2] == "G0"]
        else:
            gk = [s for k, reps in runs.items() if k[2] == cond for _, s in reps]
            g0 = [s for k, reps in runs.items() if k[2] == "G0" for _, s in reps]
        vk, dfk = _pooled_var(gk)
        v0, df0 = _pooled_var(g0)
        u: dict[str, Any] = {"df_k": dfk, "df_0": df0}
        if dfk and df0 and v0 > 0:
            u.update(vr=vk / v0, sigma_add_pct=100 * math.sqrt(max(0.0, vk - v0)),
                     sd_k_pct=100 * math.sqrt(vk), sd_0_pct=100 * math.sqrt(v0))
        out[unit] = u
    return out


def _derive_aa(runs: dict) -> dict:
    by_block = defaultdict(list)
    for (b, j, c), reps in runs.items():
        if c == "G0":
            by_block[b].append((j, [v for v, _ in reps]))
    pairs = [(sorted(v)[0][1], sorted(v)[1][1]) for _, v in sorted(by_block.items()) if len(v) >= 2]
    out: dict[str, Any] = {"n_blocks": len(pairs)}
    if len(pairs) >= 2:
        cand = {i: p[1] for i, p in enumerate(pairs)}
        anch = {i: p[0] for i, p in enumerate(pairs)}
        out["bias_pct"] = _pooled_bias(cand, anch, list(range(len(pairs))))
    return out


def _same(derived: float | int | None, stated: Any, what: str) -> None:
    if derived is None or stated is None:
        if derived is not None or stated is not None:
            raise ProjectionError(f"gpu-cpu-noise {what}: estimable on one side only "
                                  f"(re-derived {derived!r}, analysis {stated!r})")
        return
    if isinstance(derived, int) and not isinstance(derived, bool):
        if stated != derived:
            raise ProjectionError(f"gpu-cpu-noise {what} does not re-derive ({derived} vs {stated})")
        return
    if not isinstance(stated, (int, float)) or abs(derived - stated) > TOL * max(1.0, abs(derived)):
        raise ProjectionError(f"gpu-cpu-noise {what} does not re-derive ({derived!r} vs {stated!r})")


# ------------------------------------------------------------------ scope

def _scope(rr: dict) -> tuple[dict, dict]:
    """Applicability + workload identity, from the run record's own argv only."""
    if rr.get("workload") == "w2-q38fn":
        w2 = rr.get("w2") or {}
        argv = w2.get("server_argv") or []
        inner = shlex.split(argv[-1]) if argv else []
        try:
            model = inner[inner.index("-m") + 1]
            binary = next(t for t in inner if t.endswith("/llama-server"))
        except (ValueError, StopIteration) as exc:
            raise ProjectionError("gpu-cpu-noise W2 server argv names no -m model or llama-server") from exc
        kernel = {"binary": binary, "binary_sha256": rr.get("q38fn_server_sha256"),
                  "ggml_cpu_sha256": rr.get("q38fn_ggml_cpu_sha256")}
        workload = {"name": "w2-q38fn", "instrument_class": "serving",
                    "text": "served whole-host CPU model (Qwen3.8-Flash-Next UD-IQ4_XS, production :8074 "
                            "recipe on 0-95, one persistent server; rep = 1 prefill + 2 decode requests)"}
    else:
        argv = shlex.split(rr.get("bench_cmd") or "")
        try:
            model = argv[argv.index("-m") + 1]
        except (ValueError, IndexError) as exc:
            raise ProjectionError("gpu-cpu-noise W1 bench_cmd names no -m model") from exc
        binary = rr.get("bench_binary") or ""
        kernel = {"binary": binary, "binary_sha256": rr.get("bench_binary_sha256")}
        workload = {"name": "w1", "instrument_class": "bench",
                    "text": "bench-class canonical llama-bench (Qwen3.6-35B-A3B-MTP-Q8_0 pp512/tg128 -r 3, "
                            "0-95 -t 96)"}
    if not all(isinstance(v, str) and _SHA.fullmatch(v) for k, v in kernel.items() if k != "binary"):
        raise ProjectionError("gpu-cpu-noise run record binary sha256 missing or malformed")
    scope: dict[str, Any] = {"model_file": model, "backend": "cpu", "kernel": kernel,
                             "run_id": rr["session"], "scope_basis": "native"}
    quant = _QUANT.search(model)
    if quant:
        scope["quant"] = quant.group(1)
    build = _BUILD.search(binary)
    if build:
        scope["build_sha"] = build.group(1)
    return scope, workload


# ------------------------------------------------------------------ native rows

def native_rows(session_dir: str | Path) -> tuple[dict, ...]:
    """Strictly re-derived native rows for one session directory; void sessions -> ()."""
    d = Path(session_dir)
    if d.is_file():
        d = d.parent
    if not (d / "RUN_RECORD.json").is_file():
        return ()
    rr, rr_sha = _json(d / "RUN_RECORD.json")
    if not isinstance(rr, dict) or rr.get("schema") != RUN_SCHEMA:
        raise ProjectionError("gpu-cpu-noise RUN_RECORD schema is not epyc.gpu_cpu_noise.run_record.v1")
    if rr.get("session") != d.name:
        raise ProjectionError("gpu-cpu-noise RUN_RECORD session differs from its directory")
    if rr.get("mode") != "run":
        return ()                                    # dry-run / stub: an instrument test, not a measurement
    if not (d / "END.json").is_file():
        return ()                                    # still running or killed without an END: no claim
    end, end_sha = _json(d / "END.json")
    if end.get("session") != d.name:
        raise ProjectionError("gpu-cpu-noise END session differs from its directory")
    if end.get("rc") != 0 or end.get("reason") != "complete":
        return ()                                    # aborted session: zero rows, END says why
    if not isinstance(end.get("blocks_done"), int) or end["blocks_done"] < int(rr.get("blocks_min", 1)):
        raise ProjectionError("gpu-cpu-noise END claims complete with fewer than blocks_min blocks")
    if not (d / "ANALYSIS.json").is_file():
        return ()

    prereg_path = Path(rr.get("prereg") or "")
    if not prereg_path.is_file():
        raise ProjectionError(f"gpu-cpu-noise pre-registration not on disk: {prereg_path}")
    prereg_sha = hashlib.sha256(_read(prereg_path)).hexdigest()
    if prereg_sha != rr.get("prereg_sha256"):
        raise ProjectionError("gpu-cpu-noise pre-registration bytes differ from the sha256 recorded "
                              "before the first measured rep")
    sched_sha = hashlib.sha256(_read(d / "schedule.json")).hexdigest()
    if sched_sha != rr.get("schedule_sha256"):
        raise ProjectionError("gpu-cpu-noise schedule.json differs from RUN_RECORD.schedule_sha256")

    raw = _read(d / "reps.jsonl")
    reps_sha = hashlib.sha256(raw).hexdigest()
    try:
        rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    except ValueError as exc:
        raise ProjectionError("gpu-cpu-noise reps.jsonl line is not JSON") from exc
    for row in rows:
        if row.get("schema") != REP_SCHEMA or row.get("session") != d.name:
            raise ProjectionError("gpu-cpu-noise rep row schema/session drifted")
        row["_hash_ok"] = _row_hash_ok(row)

    an, an_sha = _json(d / "ANALYSIS.json")
    if an.get("session") != d.name or an.get("include_invalid") is not False:
        raise ProjectionError("gpu-cpu-noise ANALYSIS.json is not this session's primary analysis")
    ident = an.get("analyzer")
    if ident is not None:                            # research 5fe010c63+: the analysis names its inputs
        if not isinstance(ident, dict) or ident.get("reps_jsonl_sha256") != reps_sha \
                or ident.get("run_record_sha256") != rr_sha:
            raise ProjectionError("gpu-cpu-noise ANALYSIS.json was computed over different reps.jsonl / "
                                  "RUN_RECORD.json bytes than are on disk")
    _same(len(rows), an.get("n_rows"), "n_rows")
    _same(sum(1 for r in rows if not r["_hash_ok"]), an.get("n_hash_bad"), "n_hash_bad")
    meas = [r for r in rows if r.get("phase") == "measure"]
    conds = [c for c in CONDS if any(r.get("cond") == c for r in meas)]
    if an.get("conds") is not None and an["conds"] != conds:
        raise ProjectionError("gpu-cpu-noise ANALYSIS conds differ from the measured rows")
    for c in ["G0"] + conds:
        n = sum(1 for r in meas if r["cond"] == c)
        frac = round(sum(1 for r in meas if r["cond"] == c and r.get("valid")) / max(1, n), 3)
        _same(frac, (an.get("valid_frac") or {}).get(c), f"valid_frac[{c}]")
    reasons = sorted({w for r in meas for w in (r.get("why_invalid") or [])})
    if reasons != an.get("invalid_reasons"):
        raise ProjectionError("gpu-cpu-noise invalid_reasons do not re-derive")
    workload_name = "w2-q38fn" if any(r.get("workload") == "w2-q38fn" for r in rows) else "w1"
    if (rr.get("workload") or "w1") != workload_name or an.get("workload", "w1") != workload_name:
        raise ProjectionError("gpu-cpu-noise workload differs between run record, rows and analysis")

    scope, workload = _scope(rr)
    common = {
        "session": d.name, "session_dir": str(d), "workload": workload, "scope": scope,
        "date": str(rr.get("start", ""))[:10], "start": rr.get("start"), "end": end.get("time"),
        "prereg": {"path": str(prereg_path), "sha256": prereg_sha, "verified": True},
        "digests": {"run_record": rr_sha, "schedule": sched_sha, "reps_jsonl": reps_sha,
                    "end": end_sha, "analysis": an_sha},
        "analysis_path": str(d / "ANALYSIS.json"), "analysis_sha256": an_sha,
        "analyzer_identity": ident if ident is not None else {
            "absent": "analysis predates research 5fe010c63; bound by re-derivation only"},
        "producer": {"code_head": rr.get("code_head"), "driver_sha256": rr.get("driver_sha256"),
                     "seed": rr.get("seed")},
        "gpu_job": {"server_sha256": rr.get("gpu_server_sha256"), "hip_sha256": rr.get("gpu_hip_sha256"),
                    "linkage_rc": rr.get("gpu_linkage_rc")},
        "host": {"health_tier": rr.get("host_health_tier"), "loadavg": rr.get("loadavg"),
                 "thp_enabled": rr.get("thp_enabled")},
        "rows": {"total": len(rows), "measure": len(meas),
                 "invalid": sum(1 for r in meas if not r.get("valid")), "invalid_reasons": reasons},
        "classes": an.get("classes"), "gates": an.get("gates"), "w2": an.get("w2"),
    }

    natives: list[dict] = []
    for m in METRICS:
        mm = (an.get("metrics") or {}).get(m) or {}
        runs = _organize(rows, m)
        aa_d, aa_s = _derive_aa(runs), mm.get("aa") or {}
        _same(aa_d["n_blocks"], aa_s.get("n_blocks"), f"{m} A/A n_blocks")
        _same(aa_d.get("bias_pct"), aa_s.get("bias_pct"), f"{m} A/A bias")
        if "bias_pct" in aa_d:
            natives.append({**common, "metric_key": m, "cond": "AA", "quantity": "bias_pct",
                            "value": aa_s["bias_pct"], "n": aa_d["n_blocks"], "stated": aa_s})
        for c in conds:
            cs = (mm.get("cond") or {}).get(c) or {}
            der = _derive(runs, c)
            bias_s, noise_s = cs.get("bias") or {}, cs.get("noise") or {}
            _same(der["n_blocks"], bias_s.get("n_blocks"), f"{m}/{c} n_blocks")
            _same(der.get("bias_pct"), bias_s.get("bias_pct"), f"{m}/{c} bias")
            for unit in ("process", "arm"):
                du, su = der[unit], noise_s.get(unit) or {}
                _same(du["df_k"], su.get("df_k"), f"{m}/{c} {unit} df_k")
                _same(du["df_0"], su.get("df_0"), f"{m}/{c} {unit} df_0")
                for key in ("vr", "sigma_add_pct", "sd_k_pct", "sd_0_pct"):
                    _same(du.get(key), su.get(key), f"{m}/{c} {unit} {key}")
            verdict = cs.get("verdict") or {}
            for quantity, _unit, _dir, nunit in QUANTITIES:
                if nunit is None:
                    value, stated = bias_s.get("bias_pct"), bias_s
                else:
                    su = noise_s.get(nunit) or {}
                    value = su.get("sigma_add_pct" if quantity == "sigma_add_pct" else "vr")
                    stated = su
                if value is None:
                    continue                         # not estimable (e.g. W2 prefill has 1 sample/rep)
                n = {None: der["n_blocks"], "process": der["n_reps"], "arm": der["n_samples"]}[nunit]
                natives.append({**common, "metric_key": m, "cond": c, "quantity": quantity,
                                "value": value, "n": int(n), "stated": stated, "verdict": verdict,
                                "w2_cond": ((an.get("w2") or {}).get("cond") or {}).get(c)})
    return tuple(natives)


# ------------------------------------------------------------------ projection

def _fmt_ci(ci: Any, unit: str) -> str:
    if isinstance(ci, list) and len(ci) == 2:
        sign = "+" if unit == "%" else ""
        return f" [95% CI {ci[0]:{sign}.2f},{ci[1]:{sign}.2f}]{unit}"
    return " [CI not estimable]"


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or native.get("quantity") not in {q[0] for q in QUANTITIES}:
        raise ProjectionError("gpu-cpu-noise native row missing")
    quantity, cond, m = native["quantity"], native["cond"], native["metric_key"]
    unit, direction, nunit = next((u, dr, nu) for q, u, dr, nu in QUANTITIES if q == quantity)
    stated, wl = native["stated"], native["workload"]
    if quantity == "bias_pct":
        ci = _fmt_ci(stated.get("ci_pct"), "%")
        what = (f"A/A bias (G0 vs G0, same blocks) = {native['value']:+.2f}%{ci}" if cond == "AA" else
                f"bias under {cond} ({COND_TEXT[cond]}) = {native['value']:+.2f}%{ci} vs G0 "
                f"(pooled-median ratio - 1)")
        basis = f"scored: {native['n']} paired blocks"
    else:
        ci_key = "sigma_add_ci_pct" if quantity == "sigma_add_pct" else "vr_ci"
        sym = "sigma_add" if quantity == "sigma_add_pct" else "variance ratio"
        what = (f"{nunit}-unit {sym} under {cond} ({COND_TEXT[cond]}) = {native['value']:.2f}"
                f"{'%' if unit == '%' else ''}{_fmt_ci(stated.get(ci_key), unit if unit == '%' else '')} "
                f"vs G0 (df {stated.get('df_k')}/{stated.get('df_0')})")
        basis = (f"scored: {native['n']} valid {cond} reps" if nunit == "process"
                 else f"scored: {native['n']} {cond} within-rep samples")
    is_w2 = wl["name"] == "w2-q38fn"
    if is_w2:
        w2c = native.get("w2_cond") or {}
        verdict = (f"W2 CO-RUN={w2c.get('corun')}; W1-transfer={w2c.get('w1_transfer')}"
                   if cond != "AA" else f"W2 V1 A/A gate={((native.get('w2') or {}).get('gates') or {}).get('V1_aa')}")
    else:
        vd = native.get("verdict") or {}
        verdict = (" ".join(f"{k}={(vd.get(k) or {}).get('verdict')}" for k in ("DG", "AK", "IND"))
                   if cond != "AA" else f"V1 A/A pass={stated.get('pass')}")
    prereg = native["prereg"]["sha256"]
    claim = (f"U4-NOISE-1 {wl['name'].upper()} session {native['session']}: CPU {METRICS[m]} {what}; "
             f"{wl['text']}; GPU job = champion dd3d9721c 27B Q8+DFlash2 (server sha256 "
             f"{(native['gpu_job']['server_sha256'] or '')[:12]}); instrument_class={wl['instrument_class']}, "
             f"floor unit={nunit or 'process'}; pre-registration sha256 {prereg[:16]} (harness-local, not a "
             f"ratified protocol); pre-registered verdict: {verdict}."
             + (" A bench-class contamination estimate, not a serving speed number." if not is_w2 else
                " W2 DG/AK cells are not its decision (addendum section 8)."))
    observation: dict[str, Any] = {"outcome_native": verdict[:120]}
    if quantity == "bias_pct":
        observation["effect_rel"] = native["value"] / 100
    mid = f"u4-noise-1:{wl['name']}:{native['session']}:{cond}:{m}:{quantity}"
    return ClaimTuple(
        measurement_id=mid, metric=f"gpu_cpu_noise_{m}_{quantity}", value=float(native["value"]),
        date=native["date"], category="BASELINE" if cond == "AA" else "CANDIDATE", claim=claim,
        metric_direction=direction, protocol_id="", reps=native["n"], reps_basis=basis, unit=unit,
        attestation_path=native["analysis_path"], attestation_sha256=native["analysis_sha256"],
        attestation_locator=f"gpu-cpu-noise:{native['session_dir']}#{cond}/{m}/{quantity}",
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability=dict(native["scope"]), observation=observation,
        extra={"adapter": ADAPTER_ID, "cond": cond, "metric_key": m, "quantity": quantity,
               "floor_unit": nunit or "process", "stated": stated, "verdict": native.get("verdict"),
               "w2_cond": native.get("w2_cond"), "workload": wl, "prereg": native["prereg"],
               "digests": native["digests"], "producer": native["producer"],
               "analyzer_identity": native["analyzer_identity"], "gpu_job": native["gpu_job"],
               "host": native["host"], "rows": native["rows"], "gates": native["gates"],
               "direction_basis": ("bias = median(cond)/median(G0) - 1 of a CPU throughput; higher = "
                                   "less slowdown" if quantity == "bias_pct" else
                                   "variance ratio / added sigma vs G0; lower = less added noise")},
    )


def frames_for_session(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "native_rows", "project", "frames_for_session"]
