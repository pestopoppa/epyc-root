"""CH-19.2 T3 fused MoE up+gate speed screen as scoped OBSERVATION beliefs (VB-CH19-T3-SCREEN-WIRE).

Native record: one screen directory written by ``/mnt/raid0/llm/tmp/cpu-queue-f8/timing/t3-ch19-screen.sh``
(``<root>/t3-ch19-screen/<UTC>/``), e.g. ``20261021T191000Z``:

* ``records.jsonl``    one row per llama-bench result per arm (pair arm, switch, marker, valid/why, wrapper rc, binary and
                       libggml-cpu sha256, build commit, ``samples_ts``, the raw llama-bench row);
* ``provenance.json``  built_from, binary / libggml-cpu / libllama sha256, model, pairs, reps, depths, start;
* ``summary.txt`` / ``end.txt``   the producer's own per-test medians and end time;
* ``<arm>/{run.log,bench.jsonl,canonical/placement.log*}``  per-arm log (marker, recipe), jsonl, bench_canonical placement proof.

The producer script is pinned by sha256 (``PRODUCER_SHA256``); a script that exists on disk and hashes differently is
REFUSED. It lives under ``/mnt/raid0/llm/tmp`` (not a repo main), so ``producer_pins.py`` lists the pin as EXEMPT.

STRICT READER. Everything the producer printed is RE-DERIVED from ``records.jsonl`` and a difference is a
``ProjectionError`` (the whole screen is refused, never repaired):

* per-row ``avg_ts`` / ``stddev_ts`` from ``samples_ts``, ``samples_ts`` from the raw ``samples_ns``, the record columns
  from the raw llama-bench row, ``valid`` / ``why`` from wrapper rc + the run.log marker + the jsonl rows (the script's
  own rule), the marker from ``run.log``, the bench jsonl rows from the records' raw rows, the placement proof from
  ``placement.log`` (max node share <= the 40% threshold), the binary / libggml digests and build commit from
  ``provenance.json`` (and from disk when the build still exists), the strict ABAB arm order and the single window;
* every per-test median and ON/OFF ratio line of ``summary.txt`` (the producer's exact format) and ``end.txt``;
* the canonical recipe (``-t 96 -fa 1 -mmp 0``, ``taskset -c 0-95 numactl --interleave=all``, OMP stack, default
  ``-b 2048 -ub 512``, CPU backend) that the claim scope names.

llama-bench PROTOCOL (VB-LLAMA-BENCH-HARDEN-PROTOCOL): every result row goes through the shared
``_llama_bench_protocol.assess`` with the run.log ``Cmd:`` argv; a row that attests the hardened protocol without
``--autokernel-harden`` in that argv is refused.

PROJECTION ONLY. ``claim_tuple.grade()`` decides every grade; no ladder is registered here; ``protocol_id`` stays empty
(a one-window screen, not a codified protocol), so every tuple is an OBSERVATION. Tuples:

* ``ch19_t3_upgate_on_over_off_<test>_d<depth>``  median over the valid ABAB pairs of ON avg_ts / OFF avg_ts (the
  producer's statistic), ``observation.anchor_value`` 1.0, ``effect_rel`` = ratio - 1, ``n_pairs``;
* ``ch19_t3_upgate_<on|off>_median_ts_<test>_d<depth>``  median over the valid arm processes of avg_ts;
* one valueless row per INVALID result (``preflight-on`` here, wrapper rc 1: the 8-token ON smoke run lost its
  placement proof to a load still in progress). It carries the producer's ``why`` and no number, and projects as a
  tuple that bears no measurement; it is never dropped.

SAME-WINDOW NOISE FLOOR. The screen has no dedicated A/A arm, so the floor is derived from the A/A-like spread the
records do allow: the OFF arm is the SAME configuration run in 5 separate processes inside the same window, so the
ratios of ADJACENT OFF processes (OFF_{i+1} / OFF_i, i = 1..n-1, each an A/A pair at the same ABAB spacing as an
ON/OFF pair) are measured null effects. ``noise_floor_rel`` = max |OFF_{i+1}/OFF_i - 1| over those A/A pairs; the
sample CV, the A/A ratios and the ON arm's own A/A spread ride in ``extra``. With fewer than 3 valid OFF processes
for a test the floor is ABSENT (no ``noise_floor_rel`` key) and ``extra.noise_floor_basis`` says so; it is never
invented. The floor is carried with the ratio; no verdict is derived from it here.

Retrofit: the producer wrote no ``belief_measurements.jsonl``; every projection says ``observation.retrofit``.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import shlex
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapters import _llama_bench_protocol as _lbp  # noqa: E402
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.ch19_t3_screen/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "ch19-t3-screen-measurement"
KNOB_FAMILY = "moe_fused_upgate"
RECORDS = "records.jsonl"
PROVENANCE = "provenance.json"
SUMMARY = "summary.txt"
END = "end.txt"
_MAX_BYTES = 16 << 20

PRODUCER_PATH = Path("/mnt/raid0/llm/tmp/cpu-queue-f8/timing/t3-ch19-screen.sh")
PRODUCER_SHA256 = "f44f12add675495f7b5de6fb618b3461e4b3f1317355249c01bb9bea1a2815b3"
MARK = "fused MoE up+gate"
EXPECT_MODEL_NAME = "Qwen3.6-35B-A3B-MTP-Q8_0.gguf"
#: the script's predeclared tests: (n_prompt, n_gen) x depth
TESTS = ((512, 0), (0, 128))
DEPTHS = (0, 8192)
THRESHOLD_PCT = 40.0
MIN_FLOOR_PROCS = 3
REL = 1e-3  # samples are printed to 3-4 decimals: derived-vs-stated tolerance, relative

#: the canonical recipe the claim scope names (canonical_recipe.py as printed by bench_canonical.sh)
RECIPE_ENV = {"OMP_PROC_BIND": "spread", "OMP_PLACES": "cores", "OMP_WAIT_POLICY": "active", "OMP_DYNAMIC": "false",
              "GGML_IQK": "1", "GGML_IQK_Q8_0": "1"}
RECIPE_RAW = {"n_threads": 96, "flash_attn": 1, "use_mmap": False, "n_batch": 2048, "n_ubatch": 512,
              "backends": "CPU", "type_k": "f16", "type_v": "f16"}

U_RATIO = "ratio (ON t/s / OFF t/s)"
U_TS = "t/s (llama-bench avg_ts, median over arm processes)"


def _tname(n_prompt: int, n_gen: int) -> str:
    return f"pp{n_prompt}" if n_prompt else f"tg{n_gen}"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _close(a: float, b: float, rel: float = REL) -> bool:
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-3)


def _num(x: Any) -> bool:
    return type(x) in (int, float) and math.isfinite(x)


def _read_text(path: Path, what: str) -> str:
    try:
        if path.stat().st_size > _MAX_BYTES:
            raise ProjectionError(f"{what} is larger than {_MAX_BYTES} bytes")
        return path.read_text()
    except OSError as exc:
        raise ProjectionError(f"{what} unreadable: {exc}") from exc


def _read_json(path: Path, what: str) -> dict:
    try:
        data = json.loads(_read_text(path, what))
    except ValueError as exc:
        raise ProjectionError(f"{what} is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectionError(f"{what} must be a JSON object")
    return data


# --- the producer's own rules, re-applied --------------------------------------------------------------------------
def _expected_validity(*, rc: int, switch: str, has_marker: bool, n_rows: int) -> tuple[int, str]:
    """``arm()`` in the producer script, line for line: later rules overwrite earlier ones."""
    valid, why = 1, "ok"
    if rc != 0:
        valid, why = 0, f"wrapper_rc={rc}"
    if switch == "on" and not has_marker:
        valid, why = 0, "ON arm without fused marker"
    if switch == "off" and has_marker:
        valid, why = 0, "OFF arm with fused marker"
    if n_rows == 0:
        valid, why = 0, "no jsonl rows"
    return valid, why


def _jsonl(text: str, what: str) -> list[dict]:
    rows = []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ProjectionError(f"{what} line {n} is not JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ProjectionError(f"{what} line {n} is not an object")
        rows.append(row)
    return rows


def _arm_logs(unit: Path, arm: str) -> dict:
    d = unit / arm
    log_p = d / "run.log"
    if not log_p.is_file():
        raise ProjectionError(f"arm {arm}: run.log missing")
    log = _read_text(log_p, f"{arm}/run.log")
    cmd = next((ln.split(":", 1)[1].strip() for ln in log.splitlines() if ln.startswith("Cmd:")), None)
    env = next((ln.split(":", 1)[1].strip() for ln in log.splitlines() if ln.startswith("Env:")), None)
    binary = next((ln.split(":", 1)[1].strip() for ln in log.splitlines() if ln.startswith("Binary:")), None)
    bench_p = d / "bench.jsonl"
    bench = _jsonl(_read_text(bench_p, f"{arm}/bench.jsonl"), f"{arm}/bench.jsonl") if bench_p.is_file() else []
    # the script's ``grep -E '^\{' run.log > bench.jsonl``
    log_json = [ln for ln in log.splitlines() if ln.startswith("{")]
    if len(log_json) != len(bench):
        raise ProjectionError(f"arm {arm}: bench.jsonl has {len(bench)} rows, run.log has {len(log_json)} JSON lines")
    placement = _placement(d / "canonical", arm)
    return {"log": log, "log_sha256": _sha(log_p), "cmd": cmd, "env": env, "binary": binary, "bench": bench,
            "marker": MARK in log, "placement": placement}


def _placement(canon: Path, arm: str) -> dict:
    """bench_canonical's in-window placement proof, re-read: max node share and the rc file."""
    p, rcp = canon / "placement.log", canon / "placement.log.rc"
    if not p.is_file() or p.stat().st_size == 0:
        return {"present": False, "rc": None, "max_node_share_pct": None}
    text = _read_text(p, f"{arm}/placement.log")
    shares = [float(m.group(1)) for m in re.finditer(r"^\s*node \d+:\s+[\d.]+ MB\s+([\d.]+)%", text, re.M)]
    rc = None
    if rcp.is_file():
        try:
            rc = int(rcp.read_text().strip())
        except ValueError as exc:
            raise ProjectionError(f"arm {arm}: placement.log.rc is not an integer") from exc
    verdict = re.search(r"^nodes=(\d+) .*threshold=([\d.]+)%", text, re.M)
    passed = "PASS: placement within threshold." in text
    return {"present": True, "rc": rc, "max_node_share_pct": max(shares) if shares else None, "nodes": len(shares),
            "threshold_pct": float(verdict.group(2)) if verdict else None, "pass": passed,
            "sha256": _sha(p)}


def _check_row(row: dict, *, prov: dict, arm_logs: dict, idx: int) -> None:
    arm = row.get("arm")
    where = f"records.jsonl row {idx} ({arm})"
    raw = row.get("raw")
    if not isinstance(raw, dict) or not raw:
        raise ProjectionError(f"{where}: the raw llama-bench row is missing")
    if row.get("switch") not in ("on", "off") or not isinstance(arm, str):
        raise ProjectionError(f"{where}: arm / switch malformed")
    for col, rawcol in (("n_prompt", "n_prompt"), ("n_gen", "n_gen"), ("n_depth", "n_depth"),
                        ("avg_ts", "avg_ts"), ("stddev_ts", "stddev_ts"), ("samples_ts", "samples_ts"),
                        ("cpu_fused_moe_upgate_field", "cpu_fused_moe_upgate")):
        if row.get(col) != raw.get(rawcol):
            raise ProjectionError(f"{where}: record column {col} {row.get(col)!r} differs from the raw llama-bench "
                                  f"row {raw.get(rawcol)!r}")
    if raw.get("cpu_fused_moe_upgate") is not (row["switch"] == "on"):
        raise ProjectionError(f"{where}: raw cpu_fused_moe_upgate disagrees with the arm switch {row['switch']}")
    for col, key in (("llama_bench_sha256", "llama_bench_sha256"), ("libggml_cpu_sha256", "libggml_cpu_sha256"),
                     ("built_from", "built_from")):
        if row.get(col) != prov.get(key):
            raise ProjectionError(f"{where}: {col} differs from provenance.json")
    bc = raw.get("build_commit")
    if not (isinstance(bc, str) and bc and str(prov.get("built_from", "")).startswith(bc)):
        raise ProjectionError(f"{where}: raw build_commit {bc!r} is not a prefix of provenance built_from")
    s = row.get("samples_ts")
    if not (isinstance(s, list) and s and all(_num(v) and v > 0 for v in s)):
        raise ProjectionError(f"{where}: samples_ts must be a non-empty list of positive numbers")
    if not _close(statistics.fmean(s), row["avg_ts"]):
        raise ProjectionError(f"{where}: avg_ts {row['avg_ts']} does not re-derive from samples_ts "
                              f"(mean {statistics.fmean(s):.6f})")
    sd = statistics.stdev(s) if len(s) > 1 else 0.0
    if not _close(sd, row["stddev_ts"], rel=5e-3):
        raise ProjectionError(f"{where}: stddev_ts {row['stddev_ts']} does not re-derive from samples_ts ({sd:.6f})")
    ns_ = raw.get("samples_ns")
    toks = (row["n_prompt"] or 0) + (row["n_gen"] or 0)
    if isinstance(ns_, list) and len(ns_) == len(s) and toks:
        for a, b in zip(s, ns_):
            if not _close(toks * 1e9 / b, a):
                raise ProjectionError(f"{where}: samples_ts {a} does not re-derive from samples_ns {b} ({toks} tokens)")
    else:
        raise ProjectionError(f"{where}: samples_ns missing or a different length than samples_ts")
    if not (_num(row["n_depth"]) and row["n_depth"] in DEPTHS or row["arm"] == "preflight-on"):
        raise ProjectionError(f"{where}: depth {row['n_depth']} is not a predeclared depth {DEPTHS}")
    # recipe the scope names
    for k, v in RECIPE_RAW.items():
        if raw.get(k) != v:
            raise ProjectionError(f"{where}: raw {k}={raw.get(k)!r} departs from the canonical recipe ({v!r})")
    if raw.get("model_filename", "").rsplit("/", 1)[-1] != EXPECT_MODEL_NAME:
        raise ProjectionError(f"{where}: model {raw.get('model_filename')!r} is not {EXPECT_MODEL_NAME}")
    if (raw.get("n_gpu_layers") not in (-1, 0)) or raw.get("gpu_info"):
        raise ProjectionError(f"{where}: a GPU is named in the raw row; the claim scope is CPU only")


def _recipe_from_log(arm: str, logs: dict) -> None:
    cmd, env = logs["cmd"], logs["env"]
    if not cmd or not env:
        raise ProjectionError(f"arm {arm}: run.log carries no canonical Cmd:/Env: lines")
    try:
        toks = shlex.split(cmd)
    except ValueError as exc:
        raise ProjectionError(f"arm {arm}: unparsable Cmd line: {exc}") from exc
    if toks[:5] != ["taskset", "-c", "0-95", "numactl", "--interleave=all"]:
        raise ProjectionError(f"arm {arm}: placement prefix of the command is not taskset -c 0-95 numactl --interleave=all")
    for flag_, val in (("-t", "96"), ("-fa", "1"), ("-mmp", "0")):
        if flag_ not in toks or toks[toks.index(flag_) + 1] != val:
            raise ProjectionError(f"arm {arm}: command lacks canonical {flag_} {val}")
    if "-b" in toks or "-ub" in toks:
        raise ProjectionError(f"arm {arm}: command overrides -b/-ub (canonical recipe uses the llama-bench defaults)")
    got = dict(t.split("=", 1) for t in env.split() if "=" in t)
    for k, v in RECIPE_ENV.items():
        if got.get(k) != v:
            raise ProjectionError(f"arm {arm}: env {k}={got.get(k)!r} departs from the canonical recipe ({v!r})")


# --- reading one screen directory ----------------------------------------------------------------------------------
def _summary_text(per_test: dict, invalid: list[str]) -> str:
    """The producer's own summary renderer, re-applied to the re-read records (exact format)."""
    out = [f"invalid arms: {len(invalid)}" + "".join("\n  " + x for x in invalid)]
    for key in sorted(per_test, key=lambda k: (k[2] or 0, k[1] or 0)):
        np_, ng, dp = key
        name = (f"pp{np_}" if np_ else f"tg{ng}") + f" @ d{dp}"
        per = per_test[key]
        ratios = [v["on"] / v["off"] for v in per.values() if "on" in v and "off" in v]
        offs = [v["off"] for v in per.values() if "off" in v]
        ons = [v["on"] for v in per.values() if "on" in v]
        if ratios:
            out.append(f"{name:16s} OFF median {statistics.median(offs):8.2f} t/s  ON median {statistics.median(ons):8.2f} "
                       f"t/s  ON/OFF median {statistics.median(ratios):.4f} (pairs={len(ratios)}, min {min(ratios):.4f}, "
                       f"max {max(ratios):.4f})")
        else:
            out.append(f"{name:16s} no complete valid pair")
    return "\n".join(out) + "\n"


def _floor(vals: list[float]) -> dict:
    """A/A-like spread of one arm's per-process avg_ts, in process order: adjacent ratios, max |r-1|, CV."""
    if len(vals) < MIN_FLOOR_PROCS:
        return {"n_processes": len(vals), "floor_rel": None}
    aa = [b / a for a, b in zip(vals, vals[1:])]
    return {"n_processes": len(vals), "aa_ratios": aa, "floor_rel": max(abs(r - 1.0) for r in aa),
            "cv": statistics.stdev(vals) / statistics.fmean(vals)}


def native_rows(unit_dir: str | Path) -> list[dict]:
    """Native rows of one T3 screen directory; ``[]`` for a directory that is not one."""
    unit = Path(unit_dir)
    if unit.is_file():
        unit = unit.parent
    rec_p, prov_p = unit / RECORDS, unit / PROVENANCE
    if not (rec_p.is_file() and prov_p.is_file()):
        return []
    # --- the producer pin
    if PRODUCER_PATH.is_file():
        got = _sha(PRODUCER_PATH)
        if got != PRODUCER_SHA256:
            raise ProjectionError(f"producer script {PRODUCER_PATH} sha256 {got[:12]} differs from the pin "
                                  f"{PRODUCER_SHA256[:12]}")
        producer_present = True
    else:
        producer_present = False
    rec_bytes = rec_p.read_bytes()
    rows = _jsonl(rec_bytes.decode(), RECORDS)
    prov = _read_json(prov_p, PROVENANCE)
    if not rows:
        raise ProjectionError("records.jsonl holds no rows")
    for k in ("built_from", "llama_bench_sha256", "libggml_cpu_sha256", "libllama_sha256", "model", "pairs", "reps",
              "depths", "start"):
        if k not in prov:
            raise ProjectionError(f"provenance.json lacks {k}")
    if str(prov["model"]).rsplit("/", 1)[-1] != EXPECT_MODEL_NAME:
        raise ProjectionError(f"provenance model {prov['model']!r} is not {EXPECT_MODEL_NAME}")
    if str(prov["depths"]) != ",".join(str(d) for d in DEPTHS):
        raise ProjectionError(f"provenance depths {prov['depths']!r} is not the predeclared {DEPTHS}")
    pairs, reps = prov["pairs"], prov["reps"]
    if not (type(pairs) is int and pairs >= 1 and type(reps) is int and reps >= 1):
        raise ProjectionError("provenance pairs / reps must be positive integers")

    # --- per-arm logs, per-row checks
    arms: list[str] = []
    for r in rows:
        if r.get("arm") not in arms:
            arms.append(r.get("arm"))
    logs = {arm: _arm_logs(unit, arm) for arm in arms}
    for arm, lg in logs.items():
        _recipe_from_log(arm, lg)
        if lg["binary"]:
            b = Path(lg["binary"])
            if b.is_file() and _sha(b.resolve()) != prov["llama_bench_sha256"]:
                raise ProjectionError(f"arm {arm}: {b} on disk no longer hashes to provenance llama_bench_sha256")
            c = b.parent / "libggml-cpu.so"
            if c.exists() and _sha(c.resolve()) != prov["libggml_cpu_sha256"]:
                raise ProjectionError(f"arm {arm}: {c} on disk no longer hashes to provenance libggml_cpu_sha256")
    tally = _lbp.RefusalTally()
    protocols: list[dict] = []
    for i, r in enumerate(rows, 1):
        if r.get("raw") == {} and r.get("valid") == 0 and r.get("why") == "no jsonl rows":
            continue  # the script's placeholder row for an arm that produced no result: INVALID, kept as a row
        _check_row(r, prov=prov, arm_logs=logs, idx=i)
        lg = logs[r["arm"]]
        protocols.append(tally.assess(row=r["raw"], argv=lg["cmd"], label=f"{r['arm']} llama-bench row {i}"))
    # arm level: bench rows = records' raw rows, marker, validity
    by_arm: dict[str, list[dict]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], []).append(r)
    for arm, grp in by_arm.items():
        lg = logs[arm]
        if [g["raw"] for g in grp] != lg["bench"] and not (len(lg["bench"]) == 0 and len(grp) == 1 and grp[0]["raw"] == {}):
            raise ProjectionError(f"arm {arm}: records.jsonl raw rows differ from {arm}/bench.jsonl")
        for field in ("switch", "wrapper_rc", "marker", "valid", "why"):
            if len({g[field] for g in grp}) != 1:
                raise ProjectionError(f"arm {arm}: rows disagree on {field}")
        g0 = grp[0]
        if int(lg["marker"]) != g0["marker"]:
            raise ProjectionError(f"arm {arm}: record marker={g0['marker']} but run.log "
                                  f"{'has' if lg['marker'] else 'lacks'} {MARK!r}")
        valid, why = _expected_validity(rc=g0["wrapper_rc"], switch=g0["switch"], has_marker=lg["marker"],
                                        n_rows=len(lg["bench"]))
        if (valid, why) != (g0["valid"], g0["why"]):
            raise ProjectionError(f"arm {arm}: record valid/why ({g0['valid']}, {g0['why']!r}) differs from the "
                                  f"script's rule over its own inputs ({valid}, {why!r})")
        pl = lg["placement"]
        if g0["valid"] == 1:
            if not (pl["present"] and pl["rc"] == 0 and pl.get("pass") and pl["max_node_share_pct"] is not None
                    and pl["max_node_share_pct"] <= THRESHOLD_PCT):
                raise ProjectionError(f"arm {arm}: marked valid but its bench_canonical placement proof is absent, "
                                      f"non-zero rc or above the {THRESHOLD_PCT:g}% node-share threshold")
    # strict ABAB order, one window
    ordered = [a for a in arms if not a.startswith("preflight")]
    expect = [f"p{p}-{x}" for p in range(1, pairs + 1) for x in ("A-off", "B-on")]
    if ordered != expect[:len(ordered)]:
        raise ProjectionError(f"arm order {ordered} is not the strict ABAB sequence {expect}")
    times = [r["raw"].get("test_time") for r in rows if r["arm"] in set(ordered)]
    if not all(isinstance(t, str) for t in times) or times != sorted(times):
        raise ProjectionError("raw test_time is missing or not monotonic in record order (ABAB order broken)")

    # --- summary.txt / end.txt
    body = [r for r in rows if not r["arm"].startswith("preflight")]
    summary_p, end_p = unit / SUMMARY, unit / END
    summary_sha = end_sha = None
    end_ts = None
    if body:
        if not (summary_p.is_file() and end_p.is_file()):
            raise ProjectionError("records.jsonl holds screen rows but summary.txt / end.txt is missing (incomplete screen)")
        if ordered != expect:
            raise ProjectionError(f"summary.txt exists but only {len(ordered)} of {len(expect)} ABAB arms are recorded")
        key = lambda r: (r["n_prompt"], r["n_gen"], r["n_depth"])  # noqa: E731
        per_test: dict = {}
        for r in body:
            if r["valid"] and r["avg_ts"] is not None:
                per_test.setdefault(key(r), {}).setdefault(r["arm"].split("-")[0], {})[r["switch"]] = r["avg_ts"]
        invalid = sorted({r["arm"] + ": " + r["why"] for r in body if not r["valid"]})
        derived = _summary_text(per_test, invalid)
        stated = _read_text(summary_p, SUMMARY)
        if derived != stated:
            raise ProjectionError("summary.txt differs from the figures re-derived from records.jsonl:\n"
                                  f"  derived: {derived!r}\n  stated:  {stated!r}")
        m = re.fullmatch(r"end=(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)\n?", _read_text(end_p, END))
        if not m:
            raise ProjectionError("end.txt is not `end=<UTC>`")
        end_ts = m.group(1)
        summary_sha, end_sha = _sha(summary_p), _sha(end_p)
    else:
        per_test = {}

    ctx = {
        "unit": unit, "unit_name": unit.name, "records_path": str(rec_p), "records_sha256": hashlib.sha256(rec_bytes).hexdigest(),
        "provenance_sha256": _sha(prov_p), "summary_sha256": summary_sha, "end_sha256": end_sha,
        "prov": prov, "start": prov["start"], "end": end_ts, "pairs": pairs, "reps": reps,
        "producer_script": str(PRODUCER_PATH), "producer_sha256": PRODUCER_SHA256, "producer_present": producer_present,
        "protocol_refusals": tally.report(),
        "protocol": {"autokernel_hardened": sorted({p["autokernel_hardened"] for p in protocols}),
                     "autokernel_harden_requested": sorted({str(p["autokernel_harden_requested"]) for p in protocols}),
                     "schema": _lbp.PROTOCOL_SCHEMA},
        "arm_run_log_sha256": {a: logs[a]["log_sha256"] for a in arms},
        "placement": {a: {k: v for k, v in logs[a]["placement"].items() if k in
                          ("present", "rc", "max_node_share_pct", "threshold_pct")} for a in arms},
        "window": {"first_test_time": times[0] if times else None, "last_test_time": times[-1] if times else None},
        "cmd": logs[ordered[0]]["cmd"] if ordered else logs[arms[0]]["cmd"],
    }
    out: list[dict] = []
    # INVALID results stay rows (one per result row, never dropped)
    for r in rows:
        if not r["valid"]:
            out.append({"kind": "invalid", "ctx": ctx, "arm": r["arm"], "switch": r["switch"], "why": r["why"],
                        "wrapper_rc": r["wrapper_rc"], "marker": r["marker"], "n_prompt": r["n_prompt"],
                        "n_gen": r["n_gen"], "n_depth": r["n_depth"], "samples_ts": r["samples_ts"],
                        "avg_ts": r["avg_ts"]})
    # per-test aggregates over the valid pairs / arms (producer statistic: avg_ts per process)
    for tkey in sorted(per_test, key=lambda k: (k[2] or 0, k[1] or 0)):
        np_, ng, dp = tkey
        proc = per_test[tkey]
        order = sorted(proc, key=lambda p: int(p[1:]))  # p1..pN
        offs = [proc[p]["off"] for p in order if "off" in proc[p]]
        ons = [proc[p]["on"] for p in order if "on" in proc[p]]
        ratios = [proc[p]["on"] / proc[p]["off"] for p in order if "on" in proc[p] and "off" in proc[p]]
        floors = {"off": _floor(offs), "on": _floor(ons)}
        base = {"ctx": ctx, "test": _tname(np_, ng), "n_prompt": np_, "n_gen": ng, "depth": dp, "floors": floors,
                "pair_ids": order}
        if ratios:
            out.append({**base, "kind": "ratio", "value": statistics.median(ratios), "ratios": ratios,
                        "n_pairs": len(ratios), "off_ts": offs, "on_ts": ons})
        for sw, vals in (("off", offs), ("on", ons)):
            if vals:
                out.append({**base, "kind": "arm_median", "switch": sw, "value": statistics.median(vals),
                            "values": vals})
    return out


# --- projection -----------------------------------------------------------------------------------------------------
def _fmt(x: float) -> str:
    return f"{x:.6g}"


def _scope(native: dict) -> dict:
    c = native["ctx"]
    prov = c["prov"]
    depth = native.get("depth", native.get("n_depth"))
    on = native.get("switch") == "on"
    knobs: dict = {"threads": 96, "flash_attn": 1, "mmap": 0, "batch": 2048, "ubatch": 512,
                   "reps_per_process": c["reps"]}
    if depth is not None:
        knobs["depth"] = int(depth)
    if native["kind"] == "invalid":
        knobs["n_prompt"], knobs["n_gen"] = int(native["n_prompt"] or 0), int(native["n_gen"] or 0)
        knobs["cpu_fused_moe_upgate"] = native["switch"]
    elif native["kind"] == "arm_median":
        knobs["cpu_fused_moe_upgate"] = "on" if on else "off"
    else:
        knobs["cpu_fused_moe_upgate"] = "on_vs_off"
    return {
        "scope_basis": "native", "model_file": str(prov["model"]), "quant": "Q8_0", "backend": "cpu",
        "build_sha": str(prov["built_from"]),
        "kernel": {"build_path": f"{prov['built_from'][:9]}:llama-bench", "execution_digest": prov["llama_bench_sha256"],
                   "libggml_cpu_sha256": prov["libggml_cpu_sha256"]},
        "run_id": f"ch19-t3-screen:{c['unit_name']}", "knob_family": KNOB_FAMILY, "knobs": knobs,
        "varied": ["cpu_fused_moe_upgate"],
        "recipe": ("canonical recipe (taskset -c 0-95 numactl --interleave=all, -t 96 -fa 1 -mmp 0, OMP spread/cores/"
                   "active, GGML_IQK=1 GGML_IQK_Q8_0=1, default -b 2048 -ub 512) via bench_canonical.sh with in-window "
                   "placement proof; same-window strict ABAB, one llama-bench process per arm, "
                   f"{c['pairs']} pairs x {c['reps']} reps; CPU only"),
    }


def _claim(native: dict, metric: str, unit: str) -> str:
    c = native["ctx"]
    if native["kind"] == "invalid":
        return (f"CH-19.2 T3 screen {c['unit_name']}: arm {native['arm']} (cpu_fused_moe_upgate {native['switch']}) is "
                f"INVALID: {native['why']} (wrapper rc {native['wrapper_rc']}, fused marker {native['marker']}); "
                "carries no measured value and is never graded as a speed number")
    where = f"CH-19.2 T3 screen {c['unit_name']}, {native['test']} @ d{native['depth']}, Qwen3.6-35B-A3B-MTP-Q8_0 CPU"
    f = native["floors"]["off"]["floor_rel"]
    floor = (f"same-window A/A-like noise floor {100 * f:.2f}% (max adjacent OFF/OFF process ratio deviation)"
             if f is not None else "same-window noise floor ABSENT (fewer than 3 valid OFF processes)")
    if native["kind"] == "ratio":
        return (f"{where}: median ON/OFF ratio {native['value']:.4f} over {native['n_pairs']} same-window ABAB pairs "
                f"(min {min(native['ratios']):.4f}, max {max(native['ratios']):.4f}); {floor}; an observation, "
                "no keep/discard verdict is derived")
    return (f"{where}: cpu_fused_moe_upgate {native['switch']} median {native['value']:.2f} t/s over "
            f"{len(native['values'])} processes; {floor}")


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    kind = native.get("kind")
    if kind not in ("ratio", "arm_median", "invalid") or "ctx" not in native:
        raise ProjectionError("CH-19.2 T3 native row must be a ratio, arm_median or invalid row with its context")
    c = native["ctx"]
    try:
        reread = hashlib.sha256(Path(c["records_path"]).read_bytes()).hexdigest()
    except OSError as exc:
        raise ProjectionError(f"{RECORDS} cannot be re-read for attestation: {exc}") from exc
    if reread != c["records_sha256"]:
        raise ProjectionError(f"{RECORDS} changed between read and projection")
    extra: dict = {
        "kind": kind, "records_sha256": c["records_sha256"], "provenance_sha256": c["provenance_sha256"],
        "summary_sha256": c["summary_sha256"], "end_sha256": c["end_sha256"],
        "producer_script": c["producer_script"], "producer_sha256": c["producer_sha256"],
        "producer_script_present_at_read": c["producer_present"],
        "llama_bench_sha256": c["prov"]["llama_bench_sha256"], "libggml_cpu_sha256": c["prov"]["libggml_cpu_sha256"],
        "libllama_sha256": c["prov"]["libllama_sha256"], "built_from": c["prov"]["built_from"],
        "window_start": c["start"], "window_end": c["end"], **c["window"],
        "llama_bench_protocol": c["protocol"], "llama_bench_protocol_assessed": c["protocol_refusals"]["assessed"],
        "command": c["cmd"],
        "write_side_gap": "the producer wrote no belief_measurements.jsonl; retrofit projection",
    }
    date = c["start"]
    if kind == "invalid":
        arm = native["arm"]
        extra.update(arm=arm, switch=native["switch"], why=native["why"], wrapper_rc=native["wrapper_rc"],
                     marker=native["marker"], samples_ts_unusable=native["samples_ts"],
                     placement=c["placement"].get(arm), run_log_sha256=c["arm_run_log_sha256"].get(arm))
        metric, unit = "ch19_t3_upgate_invalid_arm", "none (INVALID: no value)"
        t = f"{_tname(native['n_prompt'] or 0, native['n_gen'] or 0)}_d{native['n_depth']}"
        mid = f"ch19t3:v1:{c['unit_name']}:{c['records_sha256'][:16]}:invalid:{arm}:{t}"
        return ClaimTuple(
            measurement_id=mid, metric=metric, value=None, unit=unit, date=date,
            category="CANDIDATE" if native["switch"] == "on" else "BASELINE",
            claim=_claim(native, metric, unit), metric_direction="higher_better", protocol_id="", reps=None,
            reps_basis="", attestation_path=c["records_path"], attestation_sha256=c["records_sha256"],
            attestation_locator=f"ch19t3:{c['unit_name']}:{RECORDS}#{arm}:{t}", attestation_present=True,
            attestation_verified=True, source_kind=SOURCE_KIND, extra=extra, applicability=_scope(native),
            observation={})
    test, depth = native["test"], native["depth"]
    off_f, on_f = native["floors"]["off"], native["floors"]["on"]
    extra.update(test=test, depth=depth, pair_ids=native["pair_ids"], per_process_ts_off=native.get("off_ts"),
                 per_process_ts_on=native.get("on_ts"), reps_per_process=c["reps"],
                 noise_floor_basis=(
                     "A/A-like: ratios of ADJACENT OFF processes (same configuration, same window); floor_rel = max "
                     "|OFF_{i+1}/OFF_i - 1|; absent when fewer than 3 valid OFF processes"),
                 aa_off=off_f, aa_on=on_f, arm_run_log_sha256=c["arm_run_log_sha256"], placement=c["placement"])
    obs: dict = {"retrofit": True}
    if kind == "ratio":
        metric = f"ch19_t3_upgate_on_over_off_{test}_d{depth}"
        unit, cat = U_RATIO, "CANDIDATE"
        value = native["value"]
        extra.update(per_pair_ratio=native["ratios"], min_ratio=min(native["ratios"]), max_ratio=max(native["ratios"]))
        obs.update(anchor_value=1.0, effect_rel=value - 1.0, n_pairs=native["n_pairs"])
        floor_src = off_f
        reps, basis = native["n_pairs"], "valid same-window ABAB pairs (one llama-bench process per arm per pair)"
        mid_tail = f"ratio:{test}:d{depth}"
        loc = f"{RECORDS}#ratio:{test}:d{depth}"
    else:
        sw = native["switch"]
        metric = f"ch19_t3_upgate_{sw}_median_ts_{test}_d{depth}"
        unit, cat = U_TS, "CANDIDATE" if sw == "on" else "BASELINE"
        value = native["value"]
        extra.update(switch=sw, per_process_avg_ts=native["values"])
        floor_src = on_f if sw == "on" else off_f
        reps, basis = len(native["values"]), "valid llama-bench processes (avg_ts of reps_per_process reps each)"
        mid_tail = f"arm:{sw}:{test}:d{depth}"
        loc = f"{RECORDS}#arm:{sw}:{test}:d{depth}"
        extra["noise_floor_basis"] = ("A/A-like: ratios of adjacent processes of THIS arm; floor_rel = max |r - 1|; "
                                      "absent when fewer than 3 valid processes")
    if floor_src["floor_rel"] is not None:
        obs["noise_floor_rel"] = float(floor_src["floor_rel"])
    else:
        extra["noise_floor_absent"] = (f"fewer than {MIN_FLOOR_PROCS} valid processes "
                                       f"({floor_src['n_processes']}): no same-window floor is derivable")
    metric_unit = unit
    return ClaimTuple(
        measurement_id=f"ch19t3:v1:{c['unit_name']}:{c['records_sha256'][:16]}:{mid_tail}",
        metric=metric, value=value, unit=metric_unit, date=date, category=cat,
        claim=_claim(native, metric, unit), metric_direction="higher_better", protocol_id="", reps=reps,
        reps_basis=basis, attestation_path=c["records_path"], attestation_sha256=c["records_sha256"],
        attestation_locator=f"ch19t3:{c['unit_name']}:{loc}", attestation_present=True, attestation_verified=True,
        source_kind=SOURCE_KIND, extra=extra, applicability=_scope(native), observation=obs)


__all__ = ["ADAPTER_ID", "AUTHORITY", "KNOB_FAMILY", "PRODUCER_SHA256", "SOURCE_KIND", "native_rows", "project"]
