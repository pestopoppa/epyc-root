"""SC45 / RVP-C5-6: strict read side (plus the collect-time derive hook) for ParEval.

ParEval (`intake-1225`, MIT, HPDC'24; checkout pinned at
``9e2a9afafa2c9686fdd3310defde0f9a8c3731c1``) emits per-problem measurements
(``pass@k``, ``build@k``, ``speedup_n@k``, ``efficiency_n@k``) against a LOCALLY
measured ``best_sequential_runtime``. The runner (`drivers/run-all.py`) writes the
whole prompt dataset back with per-output result dicts; `analysis/metrics.py`
aggregates to (execution model, problem type) groups at HARDCODED processor counts.
Neither file is a claim tuple. This module defines the ONE driver record the write
hook must emit at collect time — one record per (problem, parallelism_model, k, n)
cell, derived from the run's own output by ``derive_driver_records()`` — and the
strict reader that projects those records. It never recomputes a metric on read
(the DF2-4 / ``benchmarks/results`` precedent: a tuple invented on read claims
warrant the original run never captured).

Doctrine, following the strict-reader family (SC19 / SC37 / SC21 precedents):

* **One claim per CELL, never per sample.** A run evaluates N LLM outputs per
  problem; the cell (problem, parallelism_model, k, n) is one witness, never N.
* **The O0 caveat is load-bearing and rides IN the tuple.** ParEval wraps its
  timed region in ``__attribute__((optimize("O0")))`` at a fixed
  ``DRIVER_PROBLEM_SIZE``, so absolute numbers are NOT comparable to the
  llama-bench protocol and must never be graded against it. The reader REFUSES a
  record whose claim does not state the caveat verbatim, so no tuple can be
  emitted without it. ``grade()``'s reasons stay the ladder's own; the claim text
  (which carries the caveat) accompanies those reasons in every emitted frame.
* **Category is the arm rule, enforced:** the serial arm IS the baseline
  (its ``best_sequential_runtime`` is the reference the parallel arms' speedup
  is computed against) so a ``serial`` record must be ``BASELINE`` and every
  parallel-model record must be ``CANDIDATE`` — a mislabeled record is malformed.
* **Direction is recorded per field** (pass@k/build@k/speedup_n@k/efficiency_n@k
  higher_better; best_sequential_runtime lower_better) in ``extra``; the tuple's
  own metric/value pair is pass@k.
* **Attestation is collect-time, and the level is honest.** The record carries a
  sha256 over the run's output file computed at collect time. When that file sits
  inside a git tree whose HEAD equals the recorded pinned revision the artifact
  is pin-verifiable and the tuple reaches ``Witnessed/Attested``; otherwise —
  out-of-tree, or a tree moved off its pin — the honest answer is
  ``Witnessed/Anchored`` (re-derivable, not pinned). A RECOMPUTED hash that
  disagrees with the recorded one is tampering, not decay: the whole records file
  is refused (fail closed). A MISSING artifact is decay: the tuple still projects
  and the ladder grades it down itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

ADAPTER_ID = "vidya.adapters.pareval/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "pareval-measurement"
SCHEMA = "epyc.vidya.pareval_driver_record.v1"

# The pinned checkout the C5-6 run executes against (rocm-verify-profile-backend.md
# RVP-C5-6 / intake-1225 notes). A driver record from any other revision is refused:
# the pin is part of the record's identity.
PAREVAL_REVISION = "9e2a9afafa2c9686fdd3310defde0f9a8c3731c1"
PAREVAL_REVISION_SHORT = PAREVAL_REVISION[:12]

PARALLELISM_MODELS = frozenset({"serial", "omp", "mpi", "mpi+omp", "kokkos", "cuda", "hip"})
CATEGORIES = frozenset({"CANDIDATE", "BASELINE"})
CPU_ARMS = frozenset({"serial", "omp"})  # v1 derive scope (RVP-C5-6); HIP arm = C5-7 hook

# Load-bearing caveat (handoff RVP-C5-6, verbatim clause). The reader requires it in
# every record's claim, so it rides in every tuple and its emitted frames.
CAVEAT = (
    'ParEval wraps its timed region in __attribute__((optimize("O0"))) at a fixed '
    "problem size (DRIVER_PROBLEM_SIZE), so absolute numbers are NOT comparable to "
    "the llama-bench protocol and must never be graded against it."
)

# Metric direction, recorded per field (the tuple's own metric/value is pass@k).
PRIMARY_METRIC = "pass@k"
FIELD_DIRECTIONS = {
    "pass@k": "higher_better",
    "build@k": "higher_better",
    "speedup_n@k": "higher_better",
    "efficiency_n@k": "higher_better",
    "best_sequential_runtime": "lower_better",
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CaptureError(ValueError):
    """The collect-time hook was asked for a driver record the run did not measure."""


# ── shared vocabulary helpers (one definition of well-formed, hook + reader) ──


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonneg_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _finite(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head(directory: Path) -> str | None:
    """The HEAD revision of the git tree containing ``directory``, else None."""
    try:
        out = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    head = out.stdout.strip()
    return head if _SHA256.match(head) else None


def _canonical_claim(*, problem: str, problem_type: str, model: str, run_id: str, k: int,
                     n: int, passk: float, buildk: float, speedup: float, efficiency: float,
                     baseline: float, hardware: str, revision_short: str,
                     num_valid: int, num_samples: int, serial_baseline_note: bool) -> str:
    parts = [
        f"ParEval {model} arm, problem {problem!r} ({problem_type}), run {run_id} "
        f"(pareval @ {revision_short}):",
        f"pass@{k}={passk:.3f} (k={k}, {num_valid}/{num_samples} outputs valid), "
        f"build@{k}={buildk:.3f},",
        f"speedup_{n}@{k}={speedup:.3f} against the LOCALLY measured best-sequential "
        f"baseline {baseline:.6f}s on {hardware},",
        f"efficiency_{n}@{k}={efficiency:.3f} per thread.",
    ]
    if serial_baseline_note:
        parts.append(
            " This serial record is the BASELINE arm: its best_sequential_runtime is "
            "the locally measured reference the parallel arms' speedup is computed "
            "against.")
    parts.append(f" {CAVEAT}")
    return " ".join(parts)


# ── the driver record: validation (shared by hook and reader) ─────────────────


def validate_record(record: Any) -> list[str]:
    """Every structural problem in one driver record. Empty list == producer-authored.

    One definition of well-formed, shared by ``derive_driver_records`` (refuse to
    emit) and the reader (refuse to project) — the 2026-08-10 two-dialects lesson.
    """
    if not isinstance(record, dict):
        return ["driver record is not a JSON object"]
    p: list[str] = []

    if record.get("schema") != SCHEMA:
        p.append(f"schema must be {SCHEMA!r}")
    if record.get("pareval_revision") != PAREVAL_REVISION:
        p.append(f"pareval_revision must be the pinned {PAREVAL_REVISION!r}")
    for key in ("run_id", "problem", "problem_type", "hardware", "problem_size", "claim"):
        if not _text(record.get(key)):
            p.append(f"{key} must be a non-empty string")
    if not _utc_timestamp(record.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")

    model = record.get("parallelism_model")
    if model not in PARALLELISM_MODELS:
        p.append(f"parallelism_model must be one of {sorted(PARALLELISM_MODELS)}")
    category = record.get("category")
    if category not in CATEGORIES:
        p.append(f"category must be exactly one of {sorted(CATEGORIES)}")
    elif model == "serial" and category != "BASELINE":
        p.append("the serial arm IS the baseline: a serial record must be category "
                 "BASELINE (its best_sequential_runtime is the reference the parallel "
                 "arms are measured against)")
    elif model != "serial" and category != "CANDIDATE":
        p.append(f"a {model} record must be category CANDIDATE (the arm under test), "
                 "never BASELINE")

    for key in ("k", "n", "num_samples", "num_valid"):
        if not _nonneg_int(record.get(key)):
            p.append(f"{key} must be a non-negative integer")
    k = record.get("k")
    n = record.get("n")
    if _nonneg_int(k) and k < 1:
        p.append("k must be >= 1 (the pass@k/build@k horizon)")
    if _nonneg_int(n) and n < 1:
        p.append("n must be >= 1 (the resource count of speedup_n@k)")
    if model == "serial" and _nonneg_int(n) and n != 1:
        p.append("a serial record must have n=1 (the serial sweep is config-less; its "
                 "speedup is baseline-over-baseline)")
    num_samples = record.get("num_samples")
    num_valid = record.get("num_valid")
    if _nonneg_int(num_samples) and num_samples < 1:
        p.append("num_samples must be >= 1 (a run that evaluated no outputs is not a run)")
    if _nonneg_int(num_samples) and _nonneg_int(num_valid) and num_valid > num_samples:
        p.append("num_valid cannot exceed num_samples")

    for key in ("pass@k", "build@k", "speedup_n@k", "efficiency_n@k"):
        if not _finite(record.get(key)):
            p.append(f"{key} must be a finite number")
    if _finite(record.get("pass@k")) and not 0.0 <= record["pass@k"] <= 1.0:
        p.append("pass@k must lie in [0, 1] (an estimator over output validity)")
    if _finite(record.get("build@k")) and not 0.0 <= record["build@k"] <= 1.0:
        p.append("build@k must lie in [0, 1]")
    if _finite(record.get("speedup_n@k")) and record["speedup_n@k"] < 0.0:
        p.append("speedup_n@k must be >= 0")
    if _finite(record.get("efficiency_n@k")) and record["efficiency_n@k"] < 0.0:
        p.append("efficiency_n@k must be >= 0")
    if not _finite(record.get("best_sequential_runtime")):
        p.append("best_sequential_runtime must be a finite number")
    elif record["best_sequential_runtime"] <= 0.0:
        p.append("best_sequential_runtime must be > 0 — the runner itself warns on a "
                 "zero baseline ('Try increasing the problem size') and a 0 baseline "
                 "makes speedup_n@k meaningless")

    if not _text(record.get("run_output_path")):
        p.append("run_output_path must be a non-empty string")
    if not _SHA256.match(str(record.get("run_output_sha256", ""))):
        p.append("run_output_sha256 must be a 64-hex digest recorded at collect time")
    claim = str(record.get("claim", ""))
    if CAVEAT not in claim:
        p.append("claim must state the O0-fixed-problem-size caveat verbatim (absolute "
                 "numbers are NOT comparable to the llama-bench protocol)")
    return p


# ── collect-time write side: derive_driver_records ─────────────────────────────
#
# The hook the C5-6 run calls AFTER run-all.py has written its output JSON. It ports
# the upstream metric definitions verbatim (analysis/metrics.py: `_passk`,
# `_speedupk`, the validity aggregation and the fixed-n config selection) so the
# record carries exactly what the run measured — never what a later reader wishes it
# had measured.


def _passk(total: int, correct: int, k: int) -> float:
    """Upstream ``analysis/metrics.py _passk``: the chance a k-draw is all-correct."""
    if total - correct < k:
        return 1.0
    acc = 1.0
    for j in range(total - correct + 1, total + 1):
        acc *= 1.0 - k / j
    return 1.0 - acc


def _ncr(n: int, r: int) -> float:
    if n < r:
        return 1.0
    return float(math.comb(n, r))


def _speedupk(runtimes: list[float], baseline: float, k: int) -> float:
    """Upstream ``_speedupk``: expected speedup of the best of k samples."""
    rt = sorted(runtimes)
    m = len(rt)
    total = 0.0
    for j in range(1, m + 1):
        total += (_ncr(j - 1, k - 1) * baseline) / (_ncr(m, k) * max(rt[j - 1], 1e-8))
    return total


def _select_run(output: dict, model: str, n: int) -> dict | None:
    """The run row of one output matching resource count ``n`` (upstream's fixed-n
    config selection). Serial/cuda/hip carry a single config-less row; omp/kokkos
    key on num_threads; mpi on num_procs; mpi+omp on the product."""
    runs = output.get("runs")
    if not isinstance(runs, list) or not runs:
        return None
    if model in ("serial", "cuda", "hip"):
        return runs[0] if n == 1 else None
    if model in ("omp", "kokkos"):
        for row in runs:
            if row.get("num_threads") == n:
                return row
        return None
    if model == "mpi":
        for row in runs:
            if row.get("num_procs") == n:
                return row
        return None
    if model == "mpi+omp":
        for row in runs:
            if row.get("num_procs") and row.get("num_threads") \
                    and row["num_procs"] * row["num_threads"] == n:
                return row
        return None
    return None


def derive_driver_records(
    run_json: str | Path | list,
    *,
    run_id: str,
    emitted_at: str,
    hardware: str,
    problem_sizes: str | Path | dict,
    k_values: Iterable[int] = (1, 5, 10, 20),
    n: int = 1,
    run_output_path: str | Path | None = None,
    revision: str = PAREVAL_REVISION,
) -> list[dict]:
    """Derive ONE driver record per (problem, parallelism_model, k) cell at resource
    count ``n`` from the run's own output — the C5-6 post-hook, called at collect time.

    ``run_json`` is the ``run-all.py -o`` output (a list of prompts, each with the
    per-output result dicts the runner attached). ``problem_sizes`` is the
    ``drivers/problem-sizes.json`` mapping (or its path) — the fixed
    ``DRIVER_PROBLEM_SIZE`` is part of the O0 caveat and rides in every record.
    ``n`` is the resource count for the PARALLEL arms' speedup_n@k/efficiency_n@k;
    serial cells are always derived at n=1 (the serial sweep is config-less).
    Refusals: a cell with no measured baseline (no valid run emitted
    ``best_sequential_runtime``), a model outside the CPU serial+omp scope, or a
    parallel arm whose launch sweep never ran at the requested ``n`` — each is a
    cell the run did not measure, so no record is emitted for it (fail closed at
    collect time).
    """
    if isinstance(run_json, (str, Path)):
        run_path = Path(run_json)
        data = json.loads(run_path.read_text())
        out_path = Path(run_output_path) if run_output_path else run_path
    else:
        data = run_json
        if run_output_path is None:
            raise CaptureError("run_json is in-memory: run_output_path must name the "
                               "final run output file to hash at collect time")
        out_path = Path(run_output_path)
    if not isinstance(data, list):
        raise CaptureError("run JSON must be the run-all.py output list of prompts")
    if not out_path.is_file():
        raise CaptureError(f"run output file not found at {out_path} — hash it AFTER "
                           "run-all.py has written it")
    if revision != PAREVAL_REVISION:
        raise CaptureError(f"revision must be the pinned {PAREVAL_REVISION!r}")
    if n < 1:
        raise CaptureError("n must be >= 1")
    if not _utc_timestamp(emitted_at):
        raise CaptureError("emitted_at must be a UTC timestamp")

    if isinstance(problem_sizes, (str, Path)):
        sizes: dict = json.loads(Path(problem_sizes).read_text())
    else:
        sizes = dict(problem_sizes)

    out_digest = _file_sha256(out_path)
    records: list[dict] = []
    for prompt in data:
        if not isinstance(prompt, dict):
            raise CaptureError("every prompt entry must be an object")
        model = prompt.get("parallelism_model")
        name = prompt.get("name")
        problem_type = prompt.get("problem_type")
        outputs = prompt.get("outputs")
        if not _text(name) or not _text(problem_type) or not isinstance(outputs, list):
            raise CaptureError(f"prompt {name!r} lacks name/problem_type/outputs — is "
                               "this the post-run output of run-all.py?")
        if model not in CPU_ARMS:
            raise CaptureError(
                f"v1 derive covers the CPU serial+omp arms (RVP-C5-6); a {model} record "
                "must be authored by the C5-7 HIP-arm hook")
        if not outputs:
            raise CaptureError(f"problem {name!r} has no evaluated outputs")

        cell_n = 1 if model == "serial" else n
        totals: list[dict] = []
        for output in outputs:
            totals.append({
                "did_build": bool(output.get("did_build")),
                "all_valid": bool(output.get("are_all_valid")),
                "baseline": output.get("best_sequential_runtime"),
                "row": _select_run(output, model, cell_n),
            })
        num_samples = len(totals)
        num_valid = sum(1 for t in totals if t["all_valid"])
        built = sum(1 for t in totals if t["did_build"])
        baselines = [t["baseline"] for t in totals
                     if isinstance(t["baseline"], (int, float))]
        if not baselines:
            raise CaptureError(
                f"problem {name!r} ({model}) measured NO best_sequential_runtime — "
                "nothing was valid enough to time, so no baseline exists to derive a "
                "cell from (refusing rather than fabricating)")
        baseline = min(baselines)
        if not any(t["row"] is not None for t in totals):
            raise CaptureError(
                f"problem {name!r} ({model}): the launch sweep never ran at n={cell_n} — "
                "no cell was measured at that resource count (refusing rather than "
                "inventing a speedup_n@k)")
        valid_at_n = [t["row"]["runtime"] for t in totals
                      if t["row"] is not None and t["row"].get("is_valid")
                      and isinstance(t["row"].get("runtime"), (int, float))]
        num_valid_at_n = len(valid_at_n)
        size = sizes.get(name, {}).get(model)
        if not _text(size):
            raise CaptureError(
                f"problem-sizes.json has no {model} size for {name!r} — the fixed "
                "DRIVER_PROBLEM_SIZE is part of the O0 caveat and must ride in the record")

        for k in k_values:
            if not isinstance(k, int) or k < 1:
                raise CaptureError(f"k must be an integer >= 1 (got {k!r})")
            passk = _passk(num_samples, num_valid, k)
            buildk = _passk(num_samples, built, k)
            speedup = _speedupk(valid_at_n, baseline, k) if valid_at_n else 0.0
            efficiency = speedup / cell_n
            claim = _canonical_claim(
                problem=name, problem_type=problem_type, model=model, run_id=run_id,
                k=k, n=cell_n, passk=passk, buildk=buildk, speedup=speedup,
                efficiency=efficiency, baseline=baseline, hardware=hardware,
                revision_short=revision[:12], num_valid=num_valid,
                num_samples=num_samples, serial_baseline_note=model == "serial")
            record = {
                "schema": SCHEMA,
                "run_id": run_id,
                "emitted_at": emitted_at,
                "pareval_revision": revision,
                "problem": name,
                "problem_type": problem_type,
                "parallelism_model": model,
                "category": "BASELINE" if model == "serial" else "CANDIDATE",
                "k": k,
                "n": cell_n,
                "num_samples": num_samples,
                "num_valid": num_valid,
                "num_valid_at_n": num_valid_at_n,
                "pass@k": passk,
                "build@k": buildk,
                "speedup_n@k": speedup,
                "efficiency_n@k": efficiency,
                "best_sequential_runtime": baseline,
                "hardware": hardware,
                "problem_size": size,
                "claim": claim,
                "run_output_path": str(out_path),
                "run_output_sha256": out_digest,
            }
            problems = validate_record(record)
            if problems:
                raise CaptureError("refusing to emit an invalid driver record: "
                                   + "; ".join(problems))
            records.append(record)
    if not records:
        raise CaptureError("no driver records derived — the run measured no cells")
    return records


def write_records(records: list[dict], out_path: str | Path) -> Path:
    """Append-safe JSONL emission of derived driver records (one record per line)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, out)
    return out


# ── the strict reader ──────────────────────────────────────────────────────────


def _resolve_run_output(record: dict, records_file: Path) -> Path | None:
    """The run output file a record attests, resolved against the records file."""
    raw = record.get("run_output_path")
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = records_file.parent / path
    return path


def refusal_reason(records_path: str | Path) -> str | None:
    """Why a driver-records file yields zero rows: ``"no emissions"`` /
    ``"malformed: ..."`` / ``"tampered: ..."``, else None."""
    path = Path(records_path)
    if not path.is_file():
        return "no emissions"
    try:
        lines = path.read_text().splitlines()
    except OSError as exc:
        return f"malformed: unreadable records file ({exc})"
    if not any(line.strip() for line in lines):
        return "no emissions"
    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            return f"malformed: non-JSON line {lineno} ({exc})"
        problems = validate_record(record)
        if problems:
            return f"malformed: line {lineno}: " + "; ".join(problems)
        run_output = _resolve_run_output(record, path)
        if run_output is None or not run_output.is_file():
            continue  # absent artifact decays the grade; it is not corruption
        try:
            recomputed = _file_sha256(run_output)
        except OSError as exc:
            return f"malformed: unreadable attested run output ({exc})"
        if recomputed != record["run_output_sha256"]:
            return (f"tampered: run output {run_output} no longer matches the "
                    f"collect-time sha256 (recorded {record['run_output_sha256'][:12]}…, "
                    f"recomputed {recomputed[:12]}…) — fail closed, zero rows")
    return None


def native_rows(records_path: str | Path) -> tuple[dict, ...]:
    """Admissible driver records from one records file. Missing/empty/malformed/
    tampered -> zero rows."""
    path = Path(records_path)
    if not path.is_file():
        return ()
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return ()
    natives: list[dict] = []
    pinned_cache: dict[str, bool] = {}
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return ()
        if validate_record(record):
            return ()
        run_output = _resolve_run_output(record, path)
        if run_output is None or not run_output.is_file():
            # Absent artifact: the tuple still projects and the ladder grades it down
            # (a hash over a file that no longer exists proves nothing).
            pinned = False
        else:
            try:
                recomputed = _file_sha256(run_output)
            except OSError:
                return ()
            if recomputed != record["run_output_sha256"]:
                return ()
            pinned = pinned_cache.get(str(run_output))
            if pinned is None:
                head = _git_head(run_output.parent)
                pinned = head is not None and head == record["pareval_revision"]
                pinned_cache[str(run_output)] = pinned
        natives.append({
            "record": record,
            "record_path": str(path),
            "run_output_path": str(run_output) if run_output is not None else "",
            "run_output_sha256_recomputed": _file_sha256(run_output) if (
                run_output is not None and run_output.is_file()) else None,
            "git_pinned": pinned,
        })
    return tuple(natives)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    """Projection only. One claim per (problem, parallelism_model, k, n) cell."""
    if not isinstance(native, dict) or not isinstance(native.get("record"), dict):
        raise ProjectionError("pareval native must retain the driver record")
    record = native["record"]
    problems = validate_record(record)
    if problems:
        raise ProjectionError("driver record is not a producer-authored post-hook "
                              "record: " + "; ".join(problems))
    if not _text(native.get("record_path")):
        raise ProjectionError("pareval native must retain the records-file path "
                              "(callers cannot bypass native_rows)")
    model = record["parallelism_model"]
    k = record["k"]
    n = record["n"]
    measurement_id = f"pareval_{record['run_id']}_{record['problem']}_{model}_k{k}_n{n}"
    pinned = bool(native.get("git_pinned"))
    return ClaimTuple(
        measurement_id=measurement_id,
        metric=PRIMARY_METRIC,
        value=record[PRIMARY_METRIC],
        date=str(record["emitted_at"])[:10],
        category=record["category"],
        claim=record["claim"],
        # pass@k higher is better; per-field directions ride in extra.
        metric_direction=FIELD_DIRECTIONS[PRIMARY_METRIC],
        # Protocol id = the native schema version (the SC19 precedent): the driver
        # record IS the protocol this measurement is admissible under.
        protocol_id=record["schema"],
        reps=record["num_samples"],
        reps_basis=(f"evaluated:LLM outputs (pass@k over the k={k} horizon; "
                    f"{record['num_valid']} of {record['num_samples']} valid)"),
        unit="fraction_0_1",
        attestation_path=str(native.get("run_output_path") or ""),
        attestation_sha256=record["run_output_sha256"],
        attestation_locator=(
            f"pareval@{record['pareval_revision'][:12]}:{record['run_id']}:"
            f"{record['problem']}:{model}:k{k}:n{n}"),
        # Presence is decided by the reader, not the ladder's containment root: the
        # attested artifact is the run output file, verified on disk AND inside a git
        # tree whose HEAD equals the recorded pinned revision. Out-of-tree or unpinned
        # -> False -> the ladder's honest Witnessed/Anchored.
        attestation_present=pinned,
        source_kind=SOURCE_KIND,
        extra={
            "schema": record["schema"],
            "run_id": record["run_id"],
            "problem": record["problem"],
            "problem_type": record["problem_type"],
            "parallelism_model": model,
            "k": k,
            "n": n,
            "num_samples": record["num_samples"],
            "num_valid": record["num_valid"],
            "num_valid_at_n": record.get("num_valid_at_n"),
            "pass@k": record["pass@k"],
            "build@k": record["build@k"],
            "speedup_n@k": record["speedup_n@k"],
            "efficiency_n@k": record["efficiency_n@k"],
            "best_sequential_runtime": record["best_sequential_runtime"],
            "hardware": record["hardware"],
            "problem_size": record["problem_size"],
            "pareval_revision": record["pareval_revision"],
            "metric_directions": dict(FIELD_DIRECTIONS),
            "run_output_path": record["run_output_path"],
            "run_output_sha256": record["run_output_sha256"],
            "run_output_sha256_recomputed": native.get("run_output_sha256_recomputed"),
            "git_pinned": pinned,
            "caveat": CAVEAT,
        },
    )


def frames_for_records(records_path: str | Path, *, as_of: str) -> list[dict]:
    """Uniform frame emission through the shared carrier (``claim_tuple.to_frames``)."""
    frames: list[dict] = []
    for native in native_rows(records_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


# ── CLI: the collect-time post-hook invocation staged for RVP-C5-6 ─────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pareval.py",
        description="SC45 collect-time hook: derive ParEval driver records from a "
                    "run-all.py output JSON (RVP-C5-6).")
    sub = parser.add_subparsers(dest="command", required=True)

    derive = sub.add_parser("derive", help="derive + write driver records (post-hook)")
    derive.add_argument("--run-json", required=True, help="run-all.py -o output JSON")
    derive.add_argument("--run-id", required=True)
    derive.add_argument("--emitted-at", required=True, help="UTC timestamp (ISO8601)")
    derive.add_argument("--hardware", required=True, help="host identity, e.g. "
                        "'AMD EPYC 9655 (96C/192T) CPU-only, g++ 15.2 -fopenmp'")
    derive.add_argument("--problem-sizes", required=True,
                        help="drivers/problem-sizes.json path")
    derive.add_argument("--n", type=int, default=1,
                        help="resource count for speedup_n@k/efficiency_n@k (default 1)")
    derive.add_argument("--k", type=int, nargs="+", default=[1, 5, 10, 20])
    derive.add_argument("--records-out", required=True,
                        help="JSONL path for the derived driver records")
    derive.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "derive":
        records = derive_driver_records(
            args.run_json, run_id=args.run_id, emitted_at=args.emitted_at,
            hardware=args.hardware, problem_sizes=args.problem_sizes,
            k_values=args.k, n=args.n)
        if not args.dry_run:
            write_records(records, args.records_out)
        print(f"derived {len(records)} driver record(s) -> {args.records_out}")
        return 0
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "SCHEMA", "PAREVAL_REVISION", "CAVEAT",
    "FIELD_DIRECTIONS", "PRIMARY_METRIC", "CPU_ARMS", "CaptureError",
    "validate_record", "derive_driver_records", "write_records", "refusal_reason",
    "native_rows", "project", "frames_for_records", "main",
]
