"""PB-QCOST-1 prefill-cost records as value-bearing, scoped OBSERVATION beliefs (VB-PBQ-1).

Native records: one run unit of the PB-QCOST-1 harness, in either of two layouts.

* ORIGINAL (``pb_qcost_1.py``, 2026-10-21): ``<run>/pb_qcost_1.jsonl`` (one ``run`` row per (n generating slots,
  prefill length, rep), each carrying its per-interval ``c`` / ``dn`` / ``iter_ms``, plus the ``port_ownership`` row
  with the launched argv) beside ``<run>/summary.json`` (schema ``epyc.pbqcost1.run.v1``).
* CONFIRM (``pb_qcost_1_q.py`` + ``verdict_q.py``, 2026-10-23 launcher dir): ``<unit>/out/run/pb_qcost_1.jsonl`` (all
  three ``-ub`` phases, raw ``t_ms`` per interval, one ``port_ownership`` + ``proof`` row per phase), ``out/run/summary.json``,
  ``out/run/graphs_proof_ub*.json``, and at the unit root ``VERDICT.json``, ``RUN_RECORD.json``, ``PREDECLARATION.md``.

PROJECTION ONLY. ``claim_tuple.grade()`` decides; this module holds no ladder and no new rule. Every projected number is
RE-DERIVED from the jsonl rows with the producer's own pure fit code (copied below, not re-designed) and compared with
the producer's stated value at its printed precision; any disagreement is a ``ProjectionError`` (refused, never
repaired). The confirm run's 95 % CIs are re-derived the same way (the producer's seeded cluster bootstrap).

Tuples, per n generating slots (n in {1, 4}):

* original, and the confirm's ub-512 phase (the original protocol): ``intercept`` (A, ms per 512-normalised server
  iteration at c = 0), ``c_slope`` (B, ms per normalised iteration per cached token), ``noise_floor`` (train rmse,
  ms/iter) and ``heldout_p99_abs`` (refit held-out P99 absolute residual, ms/iter). q is held at ONE value per n there
  (504 / 480 tokens per iteration), so these carry no q coefficient.
* confirm q axis (``t_ms = a_n + b*q + d*q*c`` over the three ub phases, RAW ms per iteration): ``q_a`` (ms/iter),
  ``q_b`` (ms per token), ``q_d`` (ms per token x cached token), ``q_noise_floor`` and ``q_heldout_p99_abs`` (raw
  ms/iter); ``q_a`` / ``q_b`` / ``q_d`` carry their producer CIs.

Both runs are INDICATIVE, and ``protocol_id`` stays empty: the shared ladder grades them as located observations. The
grade and its cause ride in ``applicability.recipe`` (the only free-text scope key the carrier permits) and verbatim in
``extra``. The original run record states no grade of its own; its grade is the one the confirm's PREDECLARATION.md
(sha256 ``f45aef1a...``, section 0) states for that exact jsonl, pinned below by the jsonl's digest. The confirm's grade
is VERDICT.json's own; its cause is read from the files (``sibling_summary`` null, the sampler's file present one
directory up from where ``verdict_q`` reads it).

Retrofit: neither producer wrote ``belief_measurements.jsonl``; every projection says ``observation.retrofit``.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters._argv_scope import flag, scope_from_argv  # noqa: E402
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

SCHEMA = "epyc.pbqcost1.run.v1"
ADAPTER_ID = "vidya.adapters.pb_qcost/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "pb-qcost-measurement"
KNOB_FAMILY = "slot_serving"
ROWS = "pb_qcost_1.jsonl"
SUMMARY = "summary.json"
CONFIRM_DIR = Path("out") / "run"
VERDICT = "VERDICT.json"
RUN_RECORD = "RUN_RECORD.json"
PREDECLARATION = "PREDECLARATION.md"
_MAX_BYTES = 32 << 20

# --- the producers' fixed constants (pb_qcost_1.py / pb_qcost_1_q.py) -------------------------------------------
TRAIN = (4000, 16000, 64000)
HELD = (8000, 32000)
NS = (1, 4)
IT_Q = 512
BASE_UB = 512
C_REF = 32000
BOOT_SEED, BOOT_N = 20261023, 2000

#: The original run's grade, by the jsonl digest it applies to. The run record itself states none; the source is the
#: confirm run's pinned predeclaration (§0), quoted verbatim. A different original-layout run gets no grade text.
ORIGINAL_GRADES = {
    "a82cdf93dc8ca304703f057822586d61f746600bc8791036a3d7023e41c2699e": {
        "grade": "INDICATIVE",
        "cause": "The 21:29Z run is graded INDICATIVE because it ran beside the KVU-12 np8 CPU timing.",
        "source": "pb-qcost-1-confirm PREDECLARATION.md section 0 (sha256 "
                  "f45aef1a43976af3d707aea4e7d61875a83e343ec726a61e1725316b385d3e06); not in the run record",
    },
}

U_NORM = "ms per server iteration (q normalised to 512 tokens)"
U_RAW = "ms per server iteration (raw)"
#: metric key -> (metric name, unit). Units are copied from the producers' own field names / unit strings.
METRICS = {
    "intercept": ("pbqcost_intercept_ms_per_iter_c0", U_NORM),
    "c_slope": ("pbqcost_c_slope_ms_per_iter_per_cached_token", "ms per server iteration per cached token "
                                                                 "(q normalised to 512 tokens)"),
    "noise_floor": ("pbqcost_noise_floor_train_rmse_ms_per_iter", U_NORM),
    "heldout_p99_abs": ("pbqcost_heldout_p99_abs_residual_ms_per_iter", U_NORM),
    "q_a": ("pbqcost_q_a_ms_per_iter", U_RAW),
    "q_b": ("pbqcost_q_b_ms_per_token", "ms per token"),
    "q_d": ("pbqcost_q_d_ms_per_token_cached_token", "ms per token x cached token"),
    "q_noise_floor": ("pbqcost_q_noise_floor_train_rmse_ms_per_iter", U_RAW),
    "q_heldout_p99_abs": ("pbqcost_q_heldout_p99_abs_residual_ms_per_iter", U_RAW),
}


# --- the producers' pure statistics, copied verbatim in behaviour (pb_qcost_1_q.py) --------------------------------
def _pct(v: list[float], p: float) -> float | None:
    if not v:
        return None
    s = sorted(v)
    if len(s) == 1:
        return s[0]
    x = (len(s) - 1) * p / 100.0
    lo = int(math.floor(x))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (x - lo)


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float] | None:
    if len(xs) < 2 or max(xs) == min(xs):
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return my - b * mx, b


def _resid(meas: list[float], pred: list[float]) -> dict:
    if not meas:
        return {"n": 0}
    r = [m - p for m, p in zip(meas, pred)]
    ar = [abs(x) for x in r]
    return {"n": len(r), "rmse": round(math.sqrt(statistics.fmean(x * x for x in r)), 3),
            "p99_abs": round(_pct(ar, 99), 3), "p99_under_prediction": round(_pct(r, 99), 3)}


def _solve3(m: list[list[float]], v: list[float]) -> list[float] | None:
    a = [row[:] + [v[i]] for i, row in enumerate(m)]
    for c in range(3):
        piv = max(range(c, 3), key=lambda r: abs(a[r][c]))
        if abs(a[piv][c]) < 1e-12:
            return None
        a[c], a[piv] = a[piv], a[c]
        for r in range(3):
            if r != c:
                f = a[r][c] / a[c][c]
                a[r] = [x - f * y for x, y in zip(a[r], a[c])]
    return [a[i][3] / a[i][i] for i in range(3)]


def _feat(i: dict) -> list[float]:
    return [1.0, i["dn"] / 512.0, i["dn"] * i["c"] / (512.0 * C_REF)]


def _suff(ivs: list[dict]) -> tuple[list[list[float]], list[float]]:
    xtx = [[0.0] * 3 for _ in range(3)]
    xty = [0.0] * 3
    for i in ivs:
        x, y = _feat(i), i["t_ms"]
        for a in range(3):
            xty[a] += x[a] * y
            for b in range(3):
                xtx[a][b] += x[a] * x[b]
    return xtx, xty


def _coef(xtx, xty) -> dict | None:
    k = _solve3(xtx, xty)
    if k is None:
        return None
    return {"a_ms": k[0], "b_ms_per_token": k[1] / 512.0, "d_ms_per_token_cached": k[2] / (512.0 * C_REF)}


def _pred(co: dict, i: dict) -> float:
    return co["a_ms"] + co["b_ms_per_token"] * i["dn"] + co["d_ms_per_token_cached"] * i["dn"] * i["c"]


def _valid_runs(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("kind") == "run" and r.get("ttft_ms") and not r.get("skipped")
            and r.get("http") == 200]


def _usable(rows: list[dict]) -> list[dict]:
    """``pb_qcost_1_q.usable``: run rows of COMPLETED phases only; rows with no phase_id are legacy and kept."""
    done = {r["phase_id"] for r in rows if r.get("kind") == "phase_done"}
    return [r for r in rows if r.get("kind") != "run" or "phase_id" not in r or r["phase_id"] in done]


def _interval_fit(rows: list[dict], n: int) -> dict | None:
    """``analyse()`` interval level at n (ub 512 only): ``iter_ms = A + B*c`` on TRAIN, residuals on HELD-OUT."""
    rn = [r for r in _valid_runs(rows) if r.get("ub", BASE_UB) == BASE_UB and r.get("n_gen") == n]
    iv = [{**i, "length": r["length"]} for r in rn for i in (r.get("intervals") or [])]
    ivt = [i for i in iv if i["length"] in TRAIN]
    ivh = [i for i in iv if i["length"] in HELD]
    fit = _ols([i["c"] for i in ivt], [i["iter_ms"] for i in ivt])
    if not fit:
        return None
    noise = _resid([i["iter_ms"] for i in ivt], [fit[0] + fit[1] * i["c"] for i in ivt])
    held = _resid([i["iter_ms"] for i in ivh], [fit[0] + fit[1] * i["c"] for i in ivh])
    dns = [i["dn"] for i in iv]
    return {"A": round(fit[0], 1), "B": round(fit[1], 6), "noise_rmse": noise.get("rmse"), "noise_n": noise["n"],
            "p99_abs": held.get("p99_abs"), "p99_under": held.get("p99_under_prediction"), "held_n": held["n"],
            "q_median": statistics.median(dns) if dns else None, "requests": len(rn)}


def _q_fit(rows: list[dict], n: int) -> dict | None:
    """``analyse_q()`` at n: pooled ``t_ms = a + b*q + d*q*c`` over all ub phases, seeded cluster-bootstrap CIs."""
    rn = [r for r in _valid_runs(rows) if r.get("n_gen") == n]
    ivs = []
    for k, r in enumerate(rn):
        for i in r.get("intervals") or []:
            ivs.append({**i, "length": r["length"], "ub": r.get("ub", BASE_UB), "req": k,
                        "t_ms": i.get("t_ms") if i.get("t_ms") is not None else i["dt_s"] * 1000.0})
    tr = [i for i in ivs if i["length"] in TRAIN]
    ho = [i for i in ivs if i["length"] in HELD]
    co = _coef(*_suff(tr)) if len(tr) >= 3 else None
    if not co:
        return None
    rmse = math.sqrt(statistics.fmean((i["t_ms"] - _pred(co, i)) ** 2 for i in tr))
    byreq: dict = {}
    for i in tr:
        byreq.setdefault(i["req"], []).append(i)
    suff = {k: _suff(v) for k, v in byreq.items()}
    keys, rng, bs = sorted(suff), random.Random(BOOT_SEED), []
    for _ in range(BOOT_N):
        xtx = [[0.0] * 3 for _ in range(3)]
        xty = [0.0] * 3
        for k in (rng.choice(keys) for _ in keys):
            a, b = suff[k]
            for p in range(3):
                xty[p] += b[p]
                for q in range(3):
                    xtx[p][q] += a[p][q]
        c2 = _coef(xtx, xty)
        if c2:
            bs.append(c2)

    def ci(key: str) -> list[float] | None:
        if len(bs) <= 50:
            return None
        return [round(_pct([x[key] for x in bs], 2.5), 8), round(_pct([x[key] for x in bs], 97.5), 8)]

    held = _resid([i["t_ms"] for i in ho], [_pred(co, i) for i in ho]) if ho else {"n": 0}
    levels = {}
    for u in sorted({i["ub"] for i in ivs}):
        dn = [i["dn"] for i in ivs if i["ub"] == u]
        levels[str(u)] = {"median_dn": statistics.median(dn), "n_intervals": len(dn),
                          "n_requests": len({i["req"] for i in ivs if i["ub"] == u})}
    return {"coef": {k: round(v, 8) for k, v in co.items()}, "ci95_a": ci("a_ms"), "ci95_b": ci("b_ms_per_token"),
            "ci95_d": ci("d_ms_per_token_cached"), "noise_rmse": round(rmse, 2), "noise_n": len(tr),
            "p99_abs": held.get("p99_abs"), "p99_under": held.get("p99_under_prediction"), "held_n": held["n"],
            "levels": levels}


# --- reading --------------------------------------------------------------------------------------------------------
def _read(path: Path) -> tuple[bytes, str]:
    if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= _MAX_BYTES:
        raise ProjectionError(f"{path.name} is not a bounded regular file")
    raw = path.read_bytes()
    return raw, hashlib.sha256(raw).hexdigest()


def _json(path: Path) -> tuple[Any, str]:
    raw, digest = _read(path)
    try:
        return json.loads(raw), digest
    except (ValueError, RecursionError) as exc:
        raise ProjectionError(f"{path.name} is not JSON: {exc}") from exc


def _rows(path: Path) -> tuple[list[dict], str]:
    raw, digest = _read(path)
    rows = []
    for line in raw.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProjectionError(f"{ROWS} has a torn line: {exc}") from exc
        if not isinstance(row, dict):
            raise ProjectionError(f"{ROWS} has a non-object row")
        rows.append(row)
    return rows, digest


def _same(stated: Any, derived: Any, what: str) -> None:
    if stated != derived:
        raise ProjectionError(f"{what} does not re-derive from {ROWS}: stated {stated!r}, re-derived {derived!r}")


def _per_n(mapping: Any, n: int) -> dict:
    value = (mapping or {}).get(str(n)) if isinstance(mapping, dict) else None
    if not isinstance(value, dict):
        raise ProjectionError(f"record has no per-n block for n={n}")
    return value


def _argv_ok(owner: dict) -> list[str]:
    argv = owner.get("argv")
    if not (owner.get("ok") is True and isinstance(argv, list) and argv and all(isinstance(t, str) for t in argv)):
        raise ProjectionError("port_ownership row does not prove the launched argv")
    return argv


def _q_int(value: Any) -> int | None:
    return int(value) if type(value) in (int, float) and float(value).is_integer() and value > 0 else None


def _base(run_name: str, layout: str, digest: str, rows_path: Path, date: str, argv: list[str], binary: str,
          binary_sha: str, grade: str, cause: str, grade_source: str) -> dict:
    return {"run_name": run_name, "layout": layout, "rows_sha256": digest, "rows_path": str(rows_path), "date": date,
            "argv": argv, "binary": binary, "binary_sha256": binary_sha, "grade": grade, "grade_cause": cause,
            "grade_source": grade_source}


def _original(path: Path) -> list[dict]:
    summary, summary_sha = _json(path / SUMMARY)
    if not isinstance(summary, dict) or summary.get("schema") != SCHEMA:
        return []
    if "analysis_q" in summary or "ubs" in summary:
        return []  # the confirm driver's inner out/run dir: its unit is the launcher dir holding VERDICT.json
    rows, digest = _rows(path / ROWS)
    owners = [r for r in rows if r.get("kind") == "port_ownership"]
    if len(owners) != 1:
        raise ProjectionError(f"{ROWS} must hold exactly one port_ownership row (has {len(owners)})")
    argv = _argv_ok(owners[0])
    readback = (summary.get("server") or {}).get("readback") or {}
    if not (readback.get("proc_cmdline") == argv and readback.get("proc_cmdline_matches_argv") is True
            and readback.get("exe_matches_binary") is True):
        raise ProjectionError("summary server readback does not match the port_ownership argv")
    binary, binary_sha = summary.get("binary"), summary.get("binary_sha256")
    if not (isinstance(binary, str) and argv[0] == binary and isinstance(binary_sha, str) and len(binary_sha) == 64):
        raise ProjectionError("summary binary / binary_sha256 do not name the launched executable")
    known = ORIGINAL_GRADES.get(digest)
    grade, cause, source = ((known["grade"], known["cause"], known["source"]) if known
                            else ("", "the run record states no grade", ""))
    base = _base(path.name, "original", digest, path / ROWS, str(summary.get("finished") or ""), argv, binary,
                 binary_sha, grade, cause, source)
    base.update({"summary_sha256": summary_sha, "status": summary.get("status"), "overall": summary.get("overall"),
                 "np": summary.get("np")})
    out = []
    for n in NS:
        il = _per_n((summary.get("analysis") or {}).get("per_n"), n).get("interval_level") or {}
        fit = _interval_fit(rows, n)
        if fit is None:
            continue
        held = il.get("refit_model_heldout") or {}
        _same(il.get("refit_intercept_ms_at_c0"), fit["A"], f"n={n} refit_intercept_ms_at_c0")
        _same(il.get("refit_slope_ms_per_cached_token"), fit["B"], f"n={n} refit_slope_ms_per_cached_token")
        _same(il.get("noise_floor_train_rmse_ms_per_iter"), fit["noise_rmse"], f"n={n} noise floor")
        _same(il.get("noise_floor_n_intervals"), fit["noise_n"], f"n={n} noise-floor interval count")
        _same(held.get("p99_abs"), fit["p99_abs"], f"n={n} refit held-out p99_abs")
        _same(held.get("n"), fit["held_n"], f"n={n} refit held-out count")
        common = {**base, "phase": "ub512", "n": n, "q_tokens": _q_int(fit["q_median"]), "unit_native": il.get("unit"),
                  "fit": fit}
        out += [{**common, "metric_key": "intercept", "value": fit["A"], "reps": fit["noise_n"]},
                {**common, "metric_key": "c_slope", "value": fit["B"], "reps": fit["noise_n"]},
                {**common, "metric_key": "noise_floor", "value": fit["noise_rmse"], "reps": fit["noise_n"]},
                {**common, "metric_key": "heldout_p99_abs", "value": fit["p99_abs"], "reps": fit["held_n"]}]
    return out


def _proofs(run_dir: Path, rows: list[dict]) -> dict:
    """``verdict_q.proofs``: the per-phase graphs / own-pid VRAM / HSA-knob proof of each completed phase."""
    done = sorted({r["ub"] for r in rows if r.get("kind") == "phase_done"})
    res, ok = {}, True
    for ub in done:
        f = run_dir / f"graphs_proof_ub{ub}.json"
        d = _json(f)[0] if f.exists() else {}
        good = (d.get("graphs") == "ON" and (d.get("own_pid_kfd_vram_mib_at_ready") or 0) > 0
                and d.get("HSA_OVERRIDE_CPU_AFFINITY_DEBUG_in_environ") == ["HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0"])
        res[str(ub)] = {"graphs": d.get("graphs"), "own_pid_vram_mib_ready": d.get("own_pid_kfd_vram_mib_at_ready"),
                        "hsa": d.get("HSA_OVERRIDE_CPU_AFFINITY_DEBUG_in_environ"), "ok": good}
        ok &= good
    return {"per_ub": res, "all_ok": bool(done) and ok}


def _masked(argv: list[str]) -> list[str]:
    """The argv with the per-phase flags (-b, -ub, --slot-save-path) masked: what every phase must share."""
    out, skip = [], False
    for tok in argv:
        if skip:
            out.append("<phase>")
            skip = False
            continue
        out.append(tok)
        skip = tok in ("-b", "--batch-size", "-ub", "--ubatch-size", "--slot-save-path")
    return out


def _confirm_grade(unit: Path, verdict: dict) -> tuple[str, str]:
    grade = verdict.get("grade")
    if not isinstance(grade, str) or not grade:
        raise ProjectionError("VERDICT.json states no grade")
    if verdict.get("sibling_summary") is None:
        read_at, written_at = unit / CONFIRM_DIR / "sibling_summary.json", unit / "out" / "sibling_summary.json"
        if not read_at.exists() and written_at.exists():
            cause = ("sibling-summary path defect: verdict_q reads out/run/sibling_summary.json but the sampler wrote "
                     "out/sibling_summary.json, so VERDICT.sibling_summary is null and the predeclared section-2 rule "
                     "could only grade INDICATIVE (fail-closed); the measured sibling load never entered the grade")
        else:
            cause = "VERDICT.sibling_summary is null: no sibling-load summary entered the grade"
    else:
        cause = "the predeclared section-2 sibling-load / proof condition was not met"
    return grade, cause


def _confirm(unit: Path) -> list[dict]:
    run_dir = unit / CONFIRM_DIR
    verdict, verdict_sha = _json(unit / VERDICT)
    if not (isinstance(verdict, dict) and isinstance(verdict.get("confirm"), dict)
            and isinstance(verdict.get("q_axis"), dict)):
        return []
    summary, summary_sha = _json(run_dir / SUMMARY)
    if not isinstance(summary, dict) or summary.get("schema") != SCHEMA:
        return []
    record, record_sha = _json(unit / RUN_RECORD)
    rows, digest = _rows(run_dir / ROWS)
    pre_sha = verdict.get("predeclaration_sha256")
    if not (isinstance(record, dict) and record.get("predeclaration_sha256") == pre_sha and pre_sha):
        raise ProjectionError("RUN_RECORD and VERDICT disagree on the predeclaration digest")
    if (unit / PREDECLARATION).exists() and _read(unit / PREDECLARATION)[1] != pre_sha:
        raise ProjectionError("PREDECLARATION.md does not hash to the digest the verdict cites")
    for name, key in (("verdict_q.py", "verdict_q_sha256"), ("pb_qcost_1_q.py", "driver_sha256")):
        if (unit / name).exists() and _read(unit / name)[1] != record.get(key):
            raise ProjectionError(f"{name} does not hash to RUN_RECORD.{key}")
    if record.get("label") != verdict.get("label"):
        raise ProjectionError("RUN_RECORD and VERDICT disagree on the label")
    binary, binary_sha = record.get("binary"), record.get("binary_sha256")
    if not (isinstance(binary_sha, str) and len(binary_sha) == 64 and summary.get("binary_sha256") == binary_sha
            and summary.get("binary") == binary):
        raise ProjectionError("RUN_RECORD and summary disagree on the binary or its sha256")
    # per-phase launch proof: port ownership, graphs proof readback, one shared argv shape
    owners = {r.get("ub"): r for r in rows if r.get("kind") == "port_ownership"}
    done = sorted({r["ub"] for r in rows if r.get("kind") == "phase_done"})
    if not done or set(done) - set(owners):
        raise ProjectionError("a completed phase has no port_ownership row")
    argvs = {}
    for ub in done:
        argv = _argv_ok(owners[ub])
        gp = _json(run_dir / f"graphs_proof_ub{ub}.json")[0] if (run_dir / f"graphs_proof_ub{ub}.json").exists() else {}
        if not (gp.get("proc_cmdline") == argv and gp.get("exe_matches_binary") is True and argv[0] == binary
                and flag(argv, "-ub", "--ubatch-size") == str(ub) and flag(argv, "-b", "--batch-size") == str(ub)):
            raise ProjectionError(f"ub {ub} phase readback does not prove its argv / binary")
        argvs[ub] = argv
    if len({tuple(_masked(a)) for a in argvs.values()}) != 1:
        raise ProjectionError("the ub phases launched different argv shapes beyond -b/-ub")
    proofs = _proofs(run_dir, rows)
    _same(verdict.get("proof"), proofs, "VERDICT.proof")
    _same(verdict.get("phases_done"), done, "VERDICT.phases_done")
    grade, cause = _confirm_grade(unit, verdict)
    usable = _usable(rows)
    base = _base(str(record.get("window_id") or unit.name), "confirm", digest, run_dir / ROWS,
                 str(record.get("time") or summary.get("finished") or ""), argvs.get(BASE_UB) or argvs[done[0]],
                 binary, binary_sha, grade, cause, "VERDICT.json grade; cause read from the run's files")
    sibling_file = unit / "out" / "sibling_summary.json"
    base.update({"summary_sha256": summary_sha, "verdict_sha256": verdict_sha, "run_record_sha256": record_sha,
                 "predeclaration_sha256": pre_sha, "label": verdict.get("label"), "proofs": proofs,
                 "phases_done": done, "confirm_overall": verdict.get("confirm_overall"),
                 "q_overall": verdict.get("q_overall"), "np": summary.get("np"),
                 "sibling_summary_unread": _json(sibling_file)[0] if sibling_file.exists() else None,
                 "tolerance_def": verdict.get("tolerance_def"), "model_native": verdict["q_axis"].get("model")})
    out = []
    for n in NS:
        c = _per_n(verdict["confirm"], n)
        fit = _interval_fit(usable, n)
        if fit is not None and BASE_UB in done:
            il = _per_n((summary.get("analysis") or {}).get("per_n"), n).get("interval_level") or {}
            _same(c.get("A_new"), fit["A"], f"VERDICT confirm n={n} A_new")
            _same(c.get("B_new"), fit["B"], f"VERDICT confirm n={n} B_new")
            _same(c.get("noise_floor_ms_per_iter"), fit["noise_rmse"], f"VERDICT confirm n={n} noise floor")
            _same(c.get("refit_heldout_p99_abs_ms_per_iter"), fit["p99_abs"], f"VERDICT confirm n={n} p99_abs")
            _same(c.get("refit_heldout_p99_under_ms_per_iter"), fit["p99_under"], f"VERDICT confirm n={n} p99_under")
            _same(il.get("refit_intercept_ms_at_c0"), fit["A"], f"summary n={n} refit_intercept_ms_at_c0")
            if "dA_ms" in c:
                _same(c["dA_ms"], round(fit["A"] - c["A_old"], 2), f"VERDICT confirm n={n} dA_ms")
                _same(c["dB_times_Cref_ms"], round((fit["B"] - c["B_old"]) * C_REF, 2),
                      f"VERDICT confirm n={n} dB_times_Cref_ms")
            common = {**base, "phase": "ub512", "n": n, "q_tokens": _q_int(fit["q_median"]),
                      "unit_native": il.get("unit"), "fit": fit, "confirm": c}
            out += [{**common, "metric_key": "intercept", "value": fit["A"], "reps": fit["noise_n"],
                     "anchor": c.get("A_old")},
                    {**common, "metric_key": "c_slope", "value": fit["B"], "reps": fit["noise_n"],
                     "anchor": c.get("B_old")},
                    {**common, "metric_key": "noise_floor", "value": fit["noise_rmse"], "reps": fit["noise_n"]},
                    {**common, "metric_key": "heldout_p99_abs", "value": fit["p99_abs"], "reps": fit["held_n"]}]
        q = _per_n((verdict["q_axis"] or {}).get("per_n"), n)
        if not isinstance(q.get("coef"), dict):
            continue  # the producer fitted no q model at this n; nothing to project
        qf = _q_fit(usable, n)
        if qf is None:
            raise ProjectionError(f"VERDICT q_axis n={n} states a fit the rows cannot produce")
        _same(q.get("coef"), qf["coef"], f"VERDICT q_axis n={n} coef")
        for key in ("ci95_a", "ci95_b", "ci95_d"):
            _same(q.get(key), qf[key], f"VERDICT q_axis n={n} {key}")
        _same(q.get("noise_floor_train_rmse_ms_per_iter"), qf["noise_rmse"], f"VERDICT q_axis n={n} noise floor")
        _same(q.get("n_train_intervals"), qf["noise_n"], f"VERDICT q_axis n={n} n_train_intervals")
        _same((q.get("heldout_interval") or {}).get("p99_abs"), qf["p99_abs"], f"VERDICT q_axis n={n} p99_abs")
        _same((q.get("heldout_interval") or {}).get("n"), qf["held_n"], f"VERDICT q_axis n={n} held-out count")
        _same(q.get("q_levels_by_ub"), qf["levels"], f"VERDICT q_axis n={n} q_levels_by_ub")
        sq = _per_n((summary.get("analysis_q") or {}).get("per_n"), n)
        _same(sq.get("coef"), qf["coef"], f"summary analysis_q n={n} coef")
        co = qf["coef"]
        common = {**base, "phase": "q_axis", "n": n, "q_tokens": None, "q_levels": qf["levels"], "fit": qf,
                  "q_verdict": q.get("verdict"), "q_identified": q.get("q_identified"),
                  "b_vs_assumed": q.get("b_vs_assumed_0.9865"), "d_vs_old": q.get("d_vs_2026_10_21_refit"),
                  "implied_intercept_ms_at_q512_c0": q.get("implied_intercept_ms_at_q512_c0")}
        old_d = (q.get("d_vs_2026_10_21_refit") or {}).get("d_old")
        out += [{**common, "metric_key": "q_a", "value": co["a_ms"], "reps": qf["noise_n"], "ci95": qf["ci95_a"]},
                {**common, "metric_key": "q_b", "value": co["b_ms_per_token"], "reps": qf["noise_n"],
                 "ci95": qf["ci95_b"], "anchor": 0.9865 if "b_vs_assumed_0.9865" in q else None},
                {**common, "metric_key": "q_d", "value": co["d_ms_per_token_cached"], "reps": qf["noise_n"],
                 "ci95": qf["ci95_d"], "anchor": old_d},
                {**common, "metric_key": "q_noise_floor", "value": qf["noise_rmse"], "reps": qf["noise_n"]},
                {**common, "metric_key": "q_heldout_p99_abs", "value": qf["p99_abs"], "reps": qf["held_n"]}]
    return out


def native_rows(unit_dir: str | Path) -> list[dict]:
    """One native row per (layout phase, n, metric); ``[]`` for a directory that is not a PB-QCOST-1 unit."""
    path = Path(unit_dir)
    if path.is_file():
        path = path.parent
    if (path / CONFIRM_DIR / ROWS).is_file() and (path / VERDICT).is_file():
        return _confirm(path)
    if (path / ROWS).is_file() and (path / SUMMARY).is_file():
        return _original(path)
    return []


# --- projection -----------------------------------------------------------------------------------------------------
def _fmt(x: float) -> str:
    return f"{x:.6g}"


def _recipe(native: dict) -> str:
    grade = native.get("grade") or "UNGRADED"
    if native["phase"] == "q_axis":
        q = "q varied by -b = -ub over " + "/".join(sorted((native.get("q_levels") or {}), key=int))
    elif native.get("q_tokens"):
        q = (f"single q: q held at {native['q_tokens']} tokens/iteration at n={native['n']}, the q coefficient is "
             "NOT measured by this tuple")
    else:
        q = "single q per n: the q coefficient is NOT measured by this tuple"
    return (f"PB-QCOST-1 {native['layout']} {native['run_name']} {native['phase']} | grade {grade}: "
            f"{native.get('grade_cause')} | {q} | shape departure -np {native.get('np')}")[:600]


def _scope(native: dict) -> dict:
    q_axis = native["phase"] == "q_axis"
    argv = native["argv"]
    spec = flag(argv, "--spec-type")
    scope = scope_from_argv(argv, binary=native["binary"], binary_sha256=native["binary_sha256"], family=KNOB_FAMILY,
                            varied=["b", "ub"] if q_axis else ["cached_prefix_tokens"],
                            dflash2=(spec == "draft-dflash") if spec else None)
    if not scope:
        return {}
    knobs = dict(scope.get("knobs") or {})
    if q_axis:
        knobs.pop("b", None)
        knobs.pop("ub", None)
    knobs["n_generating_slots"] = native["n"]
    if native.get("q_tokens"):
        knobs["q_tokens_per_iteration"] = native["q_tokens"]
    scope["knobs"] = knobs
    scope["run_id"] = f"pb-qcost-1:{native['run_name']}"
    scope["recipe"] = _recipe(native)
    return scope


def _claim(native: dict, metric: str, unit: str) -> str:
    n, key, v = native["n"], native["metric_key"], native["value"]
    where = (f"PB-QCOST-1 {native['layout']} run {native['run_name']}, {native['phase']}, n={n} generating slot(s)"
             f" (decode_rows {8 * n}), -np {native.get('np')}")
    text = f"{where}: {metric} = {_fmt(v)} {unit}"
    ci = native.get("ci95")
    if ci:
        text += f" (95% cluster-bootstrap CI {_fmt(ci[0])} to {_fmt(ci[1])})"
    if native.get("q_tokens"):
        text += f"; q fixed at {native['q_tokens']} tokens/iteration (q coefficient not measured)"
    if native["phase"] == "q_axis":
        text += f"; model {native.get('model_native')}; q-axis verdict {native.get('q_verdict')}"
    if native.get("confirm"):
        text += f"; confirm verdict {native['confirm'].get('verdict')}"
    text += f"; grade {native.get('grade') or 'UNGRADED'} ({native.get('grade_cause')})"
    return text


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    key = native.get("metric_key")
    if key not in METRICS or native.get("layout") not in ("original", "confirm") or native.get("n") not in NS:
        raise ProjectionError("PB-QCOST native row must name a known layout, n and metric")
    value = native.get("value")
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ProjectionError(f"PB-QCOST {key} value is not a finite number")
    digest = native.get("rows_sha256")
    if not (isinstance(digest, str) and len(digest) == 64):
        raise ProjectionError("PB-QCOST native row lost its jsonl digest")
    try:
        reread = hashlib.sha256(Path(native["rows_path"]).read_bytes()).hexdigest()
    except (OSError, KeyError, TypeError) as exc:
        raise ProjectionError(f"{ROWS} cannot be re-read for attestation: {exc}") from exc
    if reread != digest:
        raise ProjectionError(f"{ROWS} changed between read and projection")
    metric, unit = METRICS[key]
    obs: dict = {"retrofit": True}
    anchor = native.get("anchor")
    if type(anchor) in (int, float) and anchor:
        obs["anchor_value"] = float(anchor)
        obs["effect_rel"] = float(value) / float(anchor) - 1.0
        conf = native.get("confirm") or {}
        noise = conf.get("noise_floor_ms_per_iter")
        # the predeclared confirm tolerance (|dA| <= noise, |dB| x 32000 <= noise), expressed relative to the anchor
        if key == "intercept" and type(noise) in (int, float):
            obs["noise_floor_rel"] = noise / float(anchor)
        elif key == "c_slope" and type(noise) in (int, float):
            obs["noise_floor_rel"] = noise / (float(anchor) * C_REF)
    verdict = (native.get("confirm") or {}).get("verdict") if native["phase"] == "ub512" else native.get("q_verdict")
    if isinstance(verdict, str) and verdict:
        obs["outcome_native"] = verdict[:120]
    phase = native["phase"]
    name = native["run_name"]
    extra = {k: native.get(k) for k in (
        "layout", "phase", "n", "rows_sha256", "summary_sha256", "verdict_sha256", "run_record_sha256",
        "predeclaration_sha256", "label", "status", "overall", "confirm_overall", "q_overall", "phases_done",
        "proofs", "grade", "grade_cause", "grade_source", "unit_native", "model_native", "tolerance_def",
        "q_tokens", "q_levels", "ci95", "b_vs_assumed", "d_vs_old", "implied_intercept_ms_at_q512_c0",
        "q_identified", "sibling_summary_unread", "binary", "binary_sha256") if native.get(k) is not None}
    extra["argv"] = native["argv"]
    if native.get("sibling_summary_unread") is not None:
        extra["sibling_summary_note"] = ("the sampler's own summary, which verdict_q did not read; carried as recorded, "
                                         "it does not change the grade")
    extra["single_q_caveat"] = ("q varied (q-axis tuple)" if phase == "q_axis" else
                                "q held at one value per n; the q coefficient is not measured by this tuple")
    extra["write_side_gap"] = "the producer wrote no belief_measurements.jsonl; retrofit projection"
    return ClaimTuple(
        measurement_id=f"pbqcost:v1:{name}:{digest[:16]}:{phase}:n{native['n']}:{key}",
        metric=metric, value=value, unit=unit, date=str(native.get("date") or ""), category="BASELINE",
        claim=_claim(native, metric, unit), metric_direction="lower_better", protocol_id="",
        reps=native.get("reps") if type(native.get("reps")) is int and native["reps"] > 0 else None,
        reps_basis=("held-out-length (8k, 32k) server iterations, pooled over reps" if key.endswith("p99_abs")
                    else "train-length (4k, 16k, 64k) server iterations, pooled over reps"),
        attestation_locator=f"pbqcost:{name}:{ROWS}#{phase}:n{native['n']}:{key}", attestation_sha256=digest,
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        extra=extra, applicability=_scope(native), observation=obs)


__all__ = ["ADAPTER_ID", "AUTHORITY", "KNOB_FAMILY", "METRICS", "SOURCE_KIND", "native_rows", "project"]
