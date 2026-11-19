"""VB-CF3C-POLICY-WIRE (first slice): ``epyc.cf3c.native.v1`` from the ``cf3c-live`` producer.

Member of the ``toc_ab`` source family (same ``claim_tuple`` carrier, same shared sealed-file
plumbing, same refusal discipline). The unit is ONE ``RESULT.json`` plus the sealed ``window-*``
directory it names. ``claim_tuple.grade()`` decides every grade; this module holds no ladder.

The reader REFUSES THE WHOLE UNIT (raises :class:`ProjectionError`, which the ingest report lists
under ``refused`` and which writes nothing) on any of:

* a sealed file missing, or whose sha256 differs from ``window_sha256``; a file in the window that
  the manifest does not seal;
* a per-cell ``TRAJECTORY.json`` that disagrees with the sealed ``WINDOW.json`` schedule, with the
  ``paired`` record in RESULT, or whose ``evidence_sha256`` map names a file the window does not
  seal under the same digest;
* a per-arm summary (``correct`` / ``graded`` / ``abstained`` / accuracy / mean tokens / mean
  wall) that does not re-derive from the per-cell trajectories (the summary is never trusted);
* an incomplete, errored, smoke or server-still-running record. A partial window is not projected
  (its denominators would be a different experiment); that is a later slice, never a backfill.

Projection: per arm, three tuples (accuracy, mean total tokens, mean wall seconds). Accuracy is
``correct / scheduled`` -- an abstention or UNKNOWN cell is NOT silently dropped from the
denominator, and the abstention count rides in the claim text. ``reps`` is the number of cells for
that arm (3 in the first real window, one per case), so the grade shows the small n. There is NO
protocol id: the record is ``diagnostic_only`` and no codified protocol covers it, so every tuple is
an OBSERVATION (``Judged``), exactly as ``claim_tuple.grade()`` computes. A diagnostic matrix does
not establish the parent 1-percentage-point accuracy adoption rule, and nothing here claims it.

Scope (``applicability``) is only what the sealed window names: ``model_file`` and
``model_sha256`` (``WINDOW.json`` inputs), ``quant`` (``SERVER.json`` ``ftype``), ``backend``
(``--n-gpu-layers 0`` in the sealed server argv => ``cpu``). A server argv that offloads layers
declares no backend. ``context_tokens`` is deliberately NOT scoped: the cell's 12288 is the case
budget, not the served context regime. No ``stack_regime`` is claimed (the record names no lineup
digest).
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path, PurePath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters import toc_ab  # noqa: E402

SCHEMA = "epyc.cf3c.native.v1"
ADAPTER_ID = "vidya.adapters.toc_ab_cf3c/v1"
AUTHORITY = toc_ab.AUTHORITY
SOURCE_KIND = "toc-ab-cf3c-measurement"
PRODUCER = "cf3c-live"
M_ACC = "cf3c_arm_accuracy_over_scheduled"
M_TOK = "cf3c_arm_mean_total_tokens"
M_WALL = "cf3c_arm_mean_wall_s"
METRICS = (M_ACC, M_TOK, M_WALL)
TERMINAL = frozenset({"graded", "abstained"})  # anything else is carried as UNKNOWN, not dropped
_TOL = 1e-9


def _refuse(msg: str):
    raise ProjectionError(f"cf3c native unit refused: {msg}")


def _load(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        _refuse(f"{path.name} unreadable ({exc})")


def _sha(path: Path) -> str:
    try:
        return ns.file_sha256(path)
    except OSError as exc:
        _refuse(f"sealed file {path} unreadable ({exc})")


def _window(result_path: Path, result: dict) -> Path:
    name = PurePath(str(result.get("window") or "")).name
    if not name or name in (".", ".."):
        _refuse("RESULT.json names no window directory")
    window = result_path.parent / name
    if not window.is_dir():
        _refuse(f"window directory {name!r} is not beside RESULT.json")
    return window


def _verify_seal(window: Path, sealed: Any) -> None:
    if not isinstance(sealed, dict) or not sealed:
        _refuse("window_sha256 must be a non-empty map")
    for rel, digest in sealed.items():
        parts = PurePath(rel).parts
        if (not isinstance(rel, str) or not parts or PurePath(rel).is_absolute() or ".." in parts
                or not ns.SHA256.fullmatch(str(digest))):
            _refuse(f"malformed sealed entry {rel!r}")
        target = window / rel
        if not target.is_file():
            _refuse(f"sealed file missing: {rel}")
        if _sha(target) != digest:
            _refuse(f"sealed file hash mismatch: {rel}")
    on_disk = {p.relative_to(window).as_posix() for p in window.rglob("*") if p.is_file()}
    extra = sorted(on_disk - set(sealed))
    if extra:
        _refuse(f"window holds files the manifest does not seal: {extra[:3]}")


def _close(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is b
    return ns.finite(a) and ns.finite(b) and math.isclose(a, b, rel_tol=_TOL, abs_tol=_TOL)


def _derive(cells: list[dict]) -> dict:
    """Per-arm summary from per-cell trajectories ONLY."""
    out: dict[str, dict] = {}
    for c in cells:
        a = out.setdefault(c["arm"], {"scheduled": 0, "correct": 0, "graded": 0, "abstained": 0,
                                      "UNKNOWN": 0, "NA": 0, "non_termination": 0, "attempted": 0,
                                      "tokens": [], "walls": []})
        a["scheduled"] += 1
        status = c["status"]
        if status == "graded":
            a["graded"] += 1
            a["correct"] += 1 if c["correct"] is True else 0
        elif status == "abstained":
            a["abstained"] += 1
        else:
            a["UNKNOWN" if status != "NA" else "NA"] += 1
        a["attempted"] += 1 if status in TERMINAL else 0
        a["non_termination"] += int(c.get("non_termination") or 0)
        u = c.get("usage")
        if isinstance(u, dict) and ns.nonneg_int(u.get("total_tokens")):
            a["tokens"].append(u["total_tokens"])
        if ns.finite(c.get("wall_s")):
            a["walls"].append(c["wall_s"])
    for a in out.values():
        a["accuracy_among_graded"] = a["correct"] / a["graded"] if a["graded"] else None
        a["accuracy_over_attempted"] = a["correct"] / a["attempted"] if a["attempted"] else None
        a["accuracy_over_scheduled"] = a["correct"] / a["scheduled"]
        a["tokens_cases"] = len(a["tokens"])
        a["mean_total_tokens"] = sum(a["tokens"]) / len(a["tokens"]) if a["tokens"] else None
        a["wall_cases"] = len(a["walls"])
        a["mean_wall_s"] = sum(a["walls"]) / len(a["walls"]) if a["walls"] else None
    return out


def _scope(window: Path, inputs: dict, argv: Any) -> dict:
    scope: dict[str, Any] = {}
    model = str(inputs.get("model_path") or "")
    sha = str(inputs.get("model_sha256") or "")
    if model:
        scope["model_file"] = PurePath(model).name
    if ns.SHA256.fullmatch(sha):
        scope["model_sha256"] = sha
    try:
        ftype = _load(window / "SERVER.json")["model"]["meta"]["ftype"]
    except (KeyError, TypeError, ProjectionError):
        ftype = None
    if isinstance(ftype, str) and ftype.strip():
        scope["quant"] = ftype.strip()
    if isinstance(argv, list) and "--n-gpu-layers" in argv:
        i = argv.index("--n-gpu-layers")
        if i + 1 < len(argv) and str(argv[i + 1]) == "0":
            scope["backend"] = "cpu"
    return scope


def read_unit(result_path: str | Path) -> dict:
    """Strict reader. Returns the verified, re-derived unit or raises :class:`ProjectionError`."""
    path = Path(result_path)
    result = _load(path)
    if not isinstance(result, dict) or result.get("schema") != SCHEMA:
        raise ProjectionError("not an epyc.cf3c.native.v1 RESULT")
    if result.get("error") is not None:
        _refuse(f"record carries an error: {str(result['error'])[:80]}")
    if (result.get("coverage_complete") is not True or result.get("server_exited") is not True
            or result.get("completed") != result.get("scheduled")
            or result.get("recorded") != result.get("scheduled")):
        _refuse("incomplete window (coverage / completed / recorded / server_exited)")
    if result.get("category") not in ns.CATEGORIES or not ns.SHA256.fullmatch(str(result.get("packet_sha256"))):
        _refuse("category or packet_sha256 malformed")
    window = _window(path, result)
    _verify_seal(window, result.get("window_sha256"))
    wjson = _load(window / "WINDOW.json")
    if wjson.get("smoke") is not False:
        _refuse("smoke window is not a measurement")
    if wjson.get("packet_sha256") != result["packet_sha256"] or wjson.get("source") != result.get("source"):
        _refuse("WINDOW.json packet/source disagree with RESULT")
    schedule = wjson.get("schedule")
    if not isinstance(schedule, list) or len(schedule) != result["scheduled"] or not schedule:
        _refuse("sealed schedule does not match the scheduled count")
    sealed = result["window_sha256"]
    paired = result.get("paired") or {}
    cells: list[dict] = []
    for entry in schedule:
        ordinal = entry.get("ordinal")
        rel = f"cell-{ordinal:02d}/TRAJECTORY.json" if ns.nonneg_int(ordinal) else ""
        if rel not in sealed:
            _refuse(f"schedule ordinal {ordinal!r} has no sealed trajectory")
        cell = _load(window / rel)
        for key in ("arm", "case", "ordinal", "seed", "unit"):
            if cell.get(key) != entry.get(key):
                _refuse(f"{rel}: {key} disagrees with the sealed schedule")
        if (cell.get("schema") != SCHEMA or cell.get("packet_sha256") != result["packet_sha256"]
                or cell.get("source") != result.get("source")
                or cell.get("category") != result["category"]):
            _refuse(f"{rel}: schema/packet/source/category disagree with RESULT")
        if cell.get("status") == "graded" and not isinstance(cell.get("correct"), bool):
            _refuse(f"{rel}: graded cell without a boolean verdict")
        if cell.get("status") == "abstained" and cell.get("correct") is not None:
            _refuse(f"{rel}: abstained cell carries a verdict")
        ev = cell.get("evidence_sha256")
        if not isinstance(ev, dict) or not ev:
            _refuse(f"{rel}: no evidence map")
        prefix = rel.rsplit("/", 1)[0]
        for name, digest in ev.items():
            if sealed.get(f"{prefix}/{name}") != digest:
                _refuse(f"{rel}: evidence {name} is not sealed under the same digest")
        if (paired.get(cell["case"], {}).get("arms", {}).get(cell["arm"])) != cell:
            _refuse(f"{rel}: RESULT.paired disagrees with the sealed trajectory")
        cells.append(cell)
    if sum(len(v.get("arms", {})) for v in paired.values()) != len(cells):
        _refuse("RESULT.paired holds cells the sealed schedule does not")
    derived = _derive(cells)
    summary = result.get("arms")
    if not isinstance(summary, dict) or set(summary) != set(derived):
        _refuse("per-arm summary arms differ from the trajectories' arms")
    for arm, d in derived.items():
        s = summary[arm]
        for key in ("scheduled", "correct", "graded", "abstained", "UNKNOWN", "NA", "attempted",
                    "non_termination", "tokens_cases"):
            if s.get(key) != d[key]:
                _refuse(f"arm {arm}: summary {key}={s.get(key)!r} does not re-derive ({d[key]!r})")
        for key in ("accuracy_among_graded", "accuracy_over_attempted", "mean_total_tokens", "mean_wall_s"):
            if not _close(s.get(key), d[key]):
                _refuse(f"arm {arm}: summary {key}={s.get(key)!r} does not re-derive ({d[key]!r})")
    return {"result_path": str(path), "result_sha256": ns.file_sha256(path), "result": result,
            "window": str(window), "derived": derived, "cells": cells,
            "scope": _scope(window, wjson.get("inputs") or {}, wjson.get("argv"))}


def native_rows(result_path: str | Path) -> tuple[dict, ...]:
    """One native per (arm, metric). A non-cf3c ``RESULT.json`` declines; a bad cf3c one refuses."""
    path = Path(result_path)
    if not path.is_file():
        return ()
    try:
        head = json.loads(path.read_text())
    except (OSError, ValueError):
        raise ProjectionError("cf3c native unit refused: RESULT.json is not JSON") from None
    if not isinstance(head, dict) or head.get("schema") != SCHEMA:
        return ()
    unit = read_unit(path)
    return tuple({"result_path": unit["result_path"], "arm": arm, "metric": metric}
                 for arm in sorted(unit["derived"]) for metric in METRICS)


def _fmt(x: Any, nd: int = 3) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or native.get("metric") not in METRICS or not native.get("arm"):
        raise ProjectionError("cf3c native must name a result_path, arm and metric")
    unit = read_unit(native["result_path"])  # re-open and re-verify on every projection
    arm, metric, d = native["arm"], native["metric"], unit["derived"].get(native["arm"])
    if d is None:
        raise ProjectionError(f"cf3c arm {arm!r} is not in the verified unit")
    r = unit["result"]
    cases = sorted(c["case"] for c in unit["cells"] if c["arm"] == arm)
    ident = ns.content_hash({"packet": r["packet_sha256"], "result": unit["result_sha256"],
                             "arm": arm, "metric": metric})[:24]
    head = (f"cf3c deterministic-policy pilot (diagnostic_only; n={d['scheduled']} cells for arm "
            f"{arm}, one per case {cases}; no adoption claim)")
    if metric == M_ACC:
        value, unit_name, direction = d["accuracy_over_scheduled"], "fraction_correct", "higher_better"
        reps = d["scheduled"]
        basis = "scored:cells" if d["graded"] + d["abstained"] == d["scheduled"] else "attempted:cells"
        claim = (f"{head}: correct {d['correct']}/{d['scheduled']} (graded {d['graded']}, abstained "
                 f"{d['abstained']}, UNKNOWN {d['UNKNOWN']}, NA {d['NA']}); accuracy over scheduled "
                 f"{_fmt(value)}, among graded {_fmt(d['accuracy_among_graded'])}")
    elif metric == M_TOK:
        value, unit_name, direction = d["mean_total_tokens"], "tokens", "lower_better"
        reps, basis = d["tokens_cases"], "observed:cells"
        claim = f"{head}: mean native total tokens {_fmt(value, 1)} over {reps} cells"
    else:
        value, unit_name, direction = d["mean_wall_s"], "seconds", "lower_better"
        reps, basis = d["wall_cases"], "observed:cells"
        claim = f"{head}: mean wall {_fmt(value, 1)} s over {reps} cells"
    if value is None:
        raise ProjectionError(f"cf3c arm {arm!r} has no observation for {metric}")
    locator = f"cf3c-live:{r['packet_sha256'][:16]}:{arm}:{PurePath(native['result_path']).name}"
    return ClaimTuple(
        measurement_id=f"cf3c_{ident}", metric=metric, value=value, date="",
        category=r["category"], claim=claim, metric_direction=direction, protocol_id="",
        reps=reps, reps_basis=basis, unit=unit_name,
        attestation_sha256=unit["result_sha256"], attestation_locator=locator,
        # RESULT.json was re-opened and hashed now, but the producer recorded no external digest of
        # it, so "verified against a recorded digest" is not claimable; the 223 sealed files ARE.
        attestation_present=True, attestation_verified=None, source_kind=SOURCE_KIND,
        extra={"schema": SCHEMA, "producer": PRODUCER, "arm": arm,
               "packet_sha256": r["packet_sha256"], "source": r["source"],
               "diagnostic_only": r.get("diagnostic_only"), "instrument_class": r.get("instrument_class"),
               "sealed_files_verified": len(r["window_sha256"]), "n_cells": d["scheduled"],
               "result_path": unit["result_path"]},
        applicability=dict(unit["scope"]))


def frames_for_result(result_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(result_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
