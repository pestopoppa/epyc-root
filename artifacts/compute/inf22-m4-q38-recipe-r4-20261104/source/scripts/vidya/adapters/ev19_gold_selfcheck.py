"""VB-EV19-GOLD-SELFCHECK-WIRE: EV-19 scorer gold self-check as a measurement of the SCORER and POOL.

Producer: ``src/autopilot_core/gold_self_check.py`` + ``scripts/autopilot/gold_self_check.py`` in
epyc-orchestrator (zero inference). It runs each suite's own scorer on that suite's own gold answers
and writes ``data/autopilot/gold_self_check.json``: per suite ``n / checkable / ok_bare / ok_wrapped /
wrong / scorer_error / not_checkable / rate``, plus run-level ``pool``, ``pool_size_bytes``,
``max_per_suite`` (0 = every row, else a deterministic stride sample), ``self_check_version``.

The claim is about the SCORER and the POOL, never a model: ``rate = (wrong + scorer_error) /
checkable`` for one suite on one pool. Doctrine:

* PROJECTION ONLY. The writer copies counts out of the report; ``claim_tuple.grade()`` decides.
* SAMPLE MODE IS PART OF THE CLAIM. ``max_per_suite == 0`` is ``full_pool``; anything else is
  ``sampled`` and a sampled run can NEVER ground a pool-gate claim: the writer refuses a protocol
  citation for it (``protocol_id`` stays empty, so the ladder yields an OBSERVATION by itself).
  No grade rule is added here.
* A full-pool run carries a protocol only when the caller cites a ratified one (none is ratified for
  scorer self-checks today, so the default is also an OBSERVATION).
* POOL IDENTITY. The report records only the pool PATH and byte size, not a digest: the writer
  hashes the pool file at capture time, refuses a path/size mismatch against the report, and refuses
  a caller-supplied expected digest that differs. The pool digest rides in the measurement identity.
* Suites with no checkable row (``rate`` null) emit no row; they are never given a rate.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.ev19_gold_selfcheck_capture.v1"
SIDECAR_NAME = "ev19_gold_selfcheck.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.ev19_gold_selfcheck/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "ev19-gold-selfcheck"
METRIC = "gold_self_check_wrong_rate"
UNIT = "fraction of checkable gold rows the suite's own scorer marks wrong or errors on"
SCOPE_LIMIT = "scorer and pool validity only, not a model claim"
FULL, SAMPLED = "full_pool", "sampled"
COUNTS = ("n", "checkable", "ok_bare", "ok_wrapped", "wrong", "scorer_error", "not_checkable")
RUN_FIELDS = ("self_check_version", "suites", "flagged", "pool", "pool_size_bytes",
              "max_per_suite", "method")


def sample_mode(max_per_suite: int) -> str:
    return FULL if max_per_suite == 0 else SAMPLED


def _load_report(path: Path) -> dict:
    try:
        rep = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"gold self-check report unreadable: {exc}") from exc
    if not isinstance(rep, dict):
        raise CaptureError("gold self-check report must be an object")
    for key in RUN_FIELDS:
        if key not in rep:
            raise CaptureError(f"report lacks producer field {key!r}")
    if not isinstance(rep["suites"], dict) or not rep["suites"]:
        raise CaptureError("report.suites must be a non-empty object")
    if not ns.nonneg_int(rep["max_per_suite"]) or not ns.nonneg_int(rep["pool_size_bytes"]):
        raise CaptureError("report max_per_suite/pool_size_bytes must be non-negative integers")
    return rep


def suite_problems(s: Any, where: str = "extra.suite") -> list[str]:
    if not isinstance(s, dict):
        return [f"{where} must be an object"]
    p = [f"{where}.{k} must be a non-negative integer" for k in COUNTS if not ns.nonneg_int(s.get(k))]
    if p:
        return p
    if s["ok_bare"] + s["ok_wrapped"] + s["wrong"] + s["scorer_error"] != s["checkable"]:
        p.append(f"{where}: checkable must equal ok_bare+ok_wrapped+wrong+scorer_error")
    if s["checkable"] + s["not_checkable"] != s["n"]:
        p.append(f"{where}: n must equal checkable+not_checkable")
    if s["checkable"] == 0:
        p.append(f"{where}: no checkable row, no rate may be projected")
    return p


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("metric") != METRIC:
        p.append(f"metric must be {METRIC!r}")
    if row.get("metric_direction") != "lower_better":
        p.append("metric_direction must be lower_better")
    if SCOPE_LIMIT not in str(row.get("claim", "")):
        p.append("claim must state the scorer/pool-only scope limit")
    for k in ("suite_id", "pool", "pool_id", "eval_era_row"):
        if not ns.text(e.get(k)):
            p.append(f"extra.{k} must be a non-empty string")
    if not ns.SHA256.match(str(e.get("pool_sha256", ""))):
        p.append("extra.pool_sha256 must be a 64-hex digest over the pool file")
    if not ns.nonneg_int(e.get("pool_size_bytes")) or not ns.nonneg_int(e.get("max_per_suite")):
        p.append("extra.pool_size_bytes/max_per_suite must be non-negative integers")
        return p + ns.self_hash_problems(row)
    if e.get("sample_mode") != sample_mode(e["max_per_suite"]):
        p.append("extra.sample_mode must be derived from max_per_suite (0 = full_pool)")
    if e.get("sample_mode") == SAMPLED and row.get("protocol_id") != "":
        p.append("a sampled run cannot cite a protocol: it cannot ground a pool-gate claim")
    p += suite_problems(e.get("suite"))
    s = e.get("suite")
    if isinstance(s, dict) and not suite_problems(s):
        bad = s["wrong"] + s["scorer_error"]
        if row.get("reps") != s["checkable"] or row.get("reps_basis") != "checkable:gold rows":
            p.append("reps must equal checkable with basis 'checkable:gold rows'")
        if not ns.finite(row.get("value")) or abs(row["value"] - bad / s["checkable"]) > 1e-9:
            p.append("value must equal (wrong+scorer_error)/checkable")
        if not p:
            p += ns.check_identity(row, {
                "run_id": row["run_id"], "suite": e["suite_id"], "pool_sha256": e["pool_sha256"],
                "max_per_suite": e["max_per_suite"], "results": row["results_sha256"]}, "ev19gs")
    return p + ns.self_hash_problems(row)


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, report_path: str | Path,
    pool_path: str | Path, pool_id: str, eval_era_row: str,
    expected_pool_sha256: str | None = None, protocol_id: str = "",
    emitted_at: str | None = None,
) -> Path:
    """Emit ``ev19_gold_selfcheck.beliefs.jsonl`` from a finished gold_self_check report.

    ``pool_path`` must be the pool the report scored (same path string and byte size as the
    report's own ``pool`` / ``pool_size_bytes``). Raises :class:`CaptureError`.
    """
    raw, pool = Path(report_path), Path(pool_path)
    rep = _load_report(raw)
    if not pool.is_file():
        raise CaptureError(f"pool file missing: {pool}")
    if str(pool) != rep["pool"]:
        raise CaptureError(f"report scored pool {rep['pool']!r}, not {str(pool)!r}")
    if pool.stat().st_size != rep["pool_size_bytes"]:
        raise CaptureError("pool byte size differs from the report's pool_size_bytes")
    pool_sha = ns.file_sha256(pool)
    if expected_pool_sha256 is not None and expected_pool_sha256 != pool_sha:
        raise CaptureError("pool sha256 differs from the expected digest")
    mode = sample_mode(rep["max_per_suite"])
    if mode == SAMPLED and protocol_id:
        raise CaptureError("a sampled run cannot cite a protocol; it cannot ground a pool-gate claim")
    digest = ns.file_sha256(raw)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for suite_id, s in sorted(rep["suites"].items()):
        if isinstance(s, dict) and s.get("rate") is None and s.get("checkable") == 0:
            continue  # no checkable row: no rate, never invented
        bad = suite_problems(s)
        if bad:
            raise CaptureError(f"suite {suite_id!r} malformed: " + "; ".join(bad))
        wrong = s["wrong"] + s["scorer_error"]
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
            "emitted_at": when, "date": when[:10], "metric": METRIC,
            "value": wrong / s["checkable"], "unit": UNIT, "metric_direction": "lower_better",
            "category": "BASELINE",
            "claim": (f"EV-19 {run_id}: suite {suite_id} scorer marks {wrong}/{s['checkable']} of "
                      f"its own checkable gold rows wrong ({mode}, max_per_suite="
                      f"{rep['max_per_suite']}, pool {pool_id} sha256 {pool_sha[:12]}, era "
                      f"{eval_era_row}); {SCOPE_LIMIT}"),
            "protocol_id": protocol_id, "reps": s["checkable"], "reps_basis": "checkable:gold rows",
            "results_path": str(raw), "results_sha256": digest,
            "extra": {"suite_id": suite_id, "suite": {k: s[k] for k in COUNTS},
                      "pool": rep["pool"], "pool_id": pool_id, "pool_sha256": pool_sha,
                      "pool_size_bytes": rep["pool_size_bytes"],
                      "max_per_suite": rep["max_per_suite"], "sample_mode": mode,
                      "self_check_version": rep["self_check_version"], "method": rep["method"],
                      "eval_era_row": eval_era_row, "scope_limit": SCOPE_LIMIT},
        }
        row["measurement_id"] = "ev19gs_" + ns.content_hash({
            "run_id": run_id, "suite": suite_id, "pool_sha256": pool_sha,
            "max_per_suite": rep["max_per_suite"], "results": digest})[:24]
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
    if not rows:
        raise CaptureError("report has no suite with a checkable row")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("EV-19 native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("EV-19 row is not a producer-authored capture: " + "; ".join(problems))
    x = row["extra"]
    locator = f"ev19-gold-selfcheck:{row['run_id']}:{x['suite_id']}:{row['results_path']}"
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
