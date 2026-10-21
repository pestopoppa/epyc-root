"""VB-HIL-REPLAY-WRITE write-side hook: producer-authored belief rows for the replay-flip report
(``replay_flip_report/v1``, orchestrator ``scripts/trace/replay_flip_run.py flip``) and the spectrum
report (``spectrum_report/v1``, ``scripts/trace/spectrum_replay.py report``).

Same pattern as ``l2_scan_capture`` (VB-L2-WRITE): the producer calls :func:`write_belief_measurements`
right after saving its JSON report, which emits ``<report>.beliefs.jsonl`` next to it. One
claim-tuple-shaped row per reported rate/count with its denominator in ``reps``. Never run over a
finished report to backfill it. Every row is an OBSERVATION (no protocol codified); no grading rule
lives here -- the reader projects and ``claim_tuple.grade()`` decides.

Synthetic reports are refused: only a report whose own ``label`` is exactly ``"measurement"`` is a
measurement. The committed ``replay_flip_report.example.json`` is labelled "format example, synthetic
counts, NOT a measurement", so the writer raises on it and :func:`validate_row` voids any hand-built
sidecar that claims another label (``extra.report_label``).

Claim discipline carried in the rows:
* flip: a flip-rate alone is not decisiveness. ``hil_decisive`` echoes the report's OWN ``decisive``
  (true only when the targeted rate beats no_hint, placebo and wrong_step), and contrasts carry their
  Fisher p. A report with a missing control arm emits ``hil_decisive`` = 0.
* spectrum: a ranking is co-occurrence with failure, not causation (``extra.scope``); every score row
  carries the replay denominator (labelled replays), every agreement row its flagged-run denominator.
"""
from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from adapters.l2_scan_capture import (  # noqa: F401  (shared helpers: one canonicalisation, one self-hash)
    _SHA256, _text, _utc, content_hash, file_sha256, row_digest, sidecar_path,
)

CAPTURE_SCHEMA = "epyc.vidya.hil_replay_capture.v1"
SIDECAR_SUFFIX = ".beliefs.jsonl"
KINDS = ("flip", "spectrum")
REPORT_SCHEMAS = {"flip": "replay_flip_report/v1", "spectrum": "spectrum_report/v1"}
NO_PROTOCOL = ""
MEASUREMENT_LABEL = "measurement"
_METRIC = re.compile(r"^hil_(flip_rate|flip_contrast_diff|decisive|spectrum_(pass_rate|top_k2|l2_agree|unclassified_share|"
                     r"human_overlap|join_with_steps|join_outcome_known))$")
_SIGNED = {"hil_flip_contrast_diff"}
SPECTRUM_SCOPE = "co-occurrence with failure across replays, not causation; causal claims come from the replay-flip report"
FLIP_SCOPE = "a flip is evidence of decisiveness only when hil_decisive is 1 (beats no_hint, placebo and wrong_step)"


class CaptureError(ValueError):
    """The report does not carry what a claim tuple needs."""


def measurement_identity(*, run_id: str, kind: str, locator: str, metric: str, report_sha256: str) -> str:
    return "hilrep_" + content_hash({"run_id": run_id, "kind": kind, "locator": locator,
                                     "metric": metric, "report_sha256": report_sha256})[:24]


def validate_row(row: Any) -> list[str]:
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []
    if row.get("schema") != CAPTURE_SCHEMA:
        p.append(f"schema must be {CAPTURE_SCHEMA!r}")
    for k in ("run_id", "producer", "measurement_id", "metric", "unit", "claim", "reps_basis",
              "report_path", "date", "locator"):
        if not _text(row.get(k)):
            p.append(f"{k} must be a non-empty string")
    if row.get("kind") not in KINDS:
        p.append(f"kind must be one of {KINDS}")
    if row.get("protocol_id") != NO_PROTOCOL:
        p.append("protocol_id must be empty: no protocol is codified for the replay tier")
    if row.get("category") != "CANDIDATE":
        p.append("category must be CANDIDATE")
    if row.get("metric_direction") not in ("higher_better", "lower_better"):
        p.append("metric_direction must be higher_better or lower_better")
    if not _METRIC.match(str(row.get("metric", ""))):
        p.append("metric is not a declared replay-tier metric")
    if not _utc(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    if not _SHA256.match(str(row.get("report_sha256", ""))):
        p.append("report_sha256 must be a 64-hex digest")
    v = row.get("value")
    lo = -1 if row.get("metric") in _SIGNED else 0
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= 1:
        p.append(f"value must be a finite number in [{lo}, 1]")
    reps = row.get("reps")
    if isinstance(reps, bool) or not isinstance(reps, int) or reps < 1:
        p.append("reps must be a positive integer (the denominator)")
    ex = row.get("extra")
    if not isinstance(ex, dict) or not _text(ex.get("denominator_label")) or not _text(ex.get("code_ref")) or not _text(ex.get("scope")):
        p.append("extra must carry denominator_label, code_ref and scope")
    elif ex.get("report_label") != MEASUREMENT_LABEL:
        p.append("extra.report_label must be 'measurement': synthetic or example reports are not evidence")
    if not _SHA256.match(str(row.get("row_sha256", ""))):
        p.append("row_sha256 must be a 64-hex self-hash")
    else:
        try:
            if row_digest(row) != row["row_sha256"]:
                p.append("row_sha256 does not bind the row content")
        except (ValueError, TypeError) as exc:
            p.append(f"row is not canonically hashable: {exc}")
    if all(_text(row.get(k)) for k in ("run_id", "kind", "locator", "metric")) and _SHA256.match(str(row.get("report_sha256", ""))):
        if row.get("measurement_id") != measurement_identity(
                run_id=row["run_id"], kind=row["kind"], locator=row["locator"], metric=row["metric"],
                report_sha256=row["report_sha256"]):
            p.append("measurement_id does not re-derive from (run_id, kind, locator, metric, report_sha256)")
    return p


# cell = (locator, metric, value, reps, denominator_label, direction, extra)
Cell = tuple[str, str, float, int, str, str, dict]


def _flip_cells(rep: dict) -> list[Cell]:
    cells: list[Cell] = []
    base = {"task_key": rep.get("task_key"), "original_outcome": rep.get("original_outcome")}
    for arm, a in sorted((rep.get("arms") or {}).items()):
        if a.get("flip_rate") is not None and a.get("n_started", 0) > 0:
            cells.append((f"flip:{arm}", "hil_flip_rate", a["flip_rate"], a["n_started"], "samples started (errors count as non-flips)",
                          "higher_better", {**base, "restart_turn": a.get("restart_turn"), "hint_chars": a.get("hint_chars"),
                                            "n_pass": a.get("n_pass"), "n_error": a.get("n_error"), "wilson95": a.get("wilson95")}))
    for ctl, c in sorted((rep.get("contrasts_vs_targeted") or {}).items()):
        arms = rep["arms"]
        n = min(arms["targeted"]["n_started"], arms[ctl]["n_started"])
        cells.append((f"flip:targeted-vs-{ctl}", "hil_flip_contrast_diff", c["diff"], n, "smaller arm's samples started",
                      "higher_better", {**base, "fisher_one_sided_p": c["fisher_one_sided_p"], "alpha": rep.get("alpha")}))
    tgt = (rep.get("arms") or {}).get("targeted")
    if tgt and tgt.get("n_started", 0) > 0:
        cells.append(("flip:decisive", "hil_decisive", 1.0 if rep.get("decisive") else 0.0, tgt["n_started"],
                      "targeted samples started", "higher_better",
                      {**base, "verdict": rep.get("verdict"), "claim_allowed": rep.get("claim_allowed")}))
    return cells


def _spectrum_cells(rep: dict) -> list[Cell]:
    cells: list[Cell] = []
    for t in rep.get("tasks") or []:
        rk, ag = t["ranking"], t.get("l2_agreement") or {}
        tk = rk["task_key"]
        if rk["n_runs"] > 0:
            cells.append((f"spectrum:{tk}", "hil_spectrum_pass_rate", rk["n_pass"] / rk["n_runs"], rk["n_runs"],
                          "labelled replays", "higher_better", {"task_key": tk, "n_pass": rk["n_pass"], "n_fail": rk["n_fail"], "usable": rk["usable"]}))
        if rk.get("top"):
            top = rk["top"][0]
            cells.append((f"spectrum:{tk}:top1", "hil_spectrum_top_k2", top["k2"], rk["n_runs"], "labelled replays", "higher_better",
                          {"task_key": tk, "key": top["key"], "ef": top["ef"], "nf": top["nf"], "ep": top["ep"], "ambiguous": top["ambiguous"]}))
        if ag.get("n_failed_runs"):
            cells.append((f"spectrum:{tk}:unclassified", "hil_spectrum_unclassified_share", ag["unclassified"] / ag["n_failed_runs"],
                          ag["n_failed_runs"], "failed replays", "lower_better", {"task_key": tk, "unclassified": ag["unclassified"]}))
        for cat, v in sorted((ag.get("by_category") or {}).items()):
            if v["failed_runs_flagged"] > 0:
                cells.append((f"spectrum:{tk}:{cat}", "hil_spectrum_l2_agree", v["top_key_at_flagged_step"] / v["failed_runs_flagged"],
                              v["failed_runs_flagged"], "failed replays flagged by the L2 detector", "higher_better",
                              {"task_key": tk, "category": cat, "top_m": ag.get("top_m")}))
        ho = t.get("human_overlap")
        if ho and ho.get("top_m"):
            cells.append((f"spectrum:{tk}:human", "hil_spectrum_human_overlap", ho["hits"] / ho["top_m"], ho["top_m"],
                          "top-m spectrum keys", "higher_better", {"task_key": tk, "human_n": ho["human_n"]}))
    for cat, v in sorted((rep.get("l2_agreement_pooled") or {}).items()):
        if v["failed_runs_flagged"] > 0:
            cells.append((f"spectrum:pooled:{cat}", "hil_spectrum_l2_agree", v["top_key_at_flagged_step"] / v["failed_runs_flagged"],
                          v["failed_runs_flagged"], "failed replays flagged by the L2 detector (pooled)", "higher_better",
                          {"category": cat, "top_m": rep.get("top_m"), "tasks_reported": rep.get("tasks_reported")}))
    j = rep.get("join") or {}
    if j.get("replays_started"):
        n = j["replays_started"]
        cells.append(("spectrum:join:steps", "hil_spectrum_join_with_steps", j["with_steps"] / n, n, "replays started", "higher_better",
                      {"without_steps": len(j.get("without_steps") or []), "tasks_skipped": len(rep.get("tasks_skipped") or [])}))
        cells.append(("spectrum:join:outcome", "hil_spectrum_join_outcome_known", 1 - j.get("outcome_unknown", 0) / n, n, "replays started",
                      "higher_better", {"outcome_unknown": j.get("outcome_unknown", 0)}))
    return cells


def write_belief_measurements(report_path: str | Path, *, kind: str, run_id: str, producer: str,
                              code_ref: str, emitted_at: str | None = None) -> Path:
    """Emit ``<report>.beliefs.jsonl``. Any invalid row raises :class:`CaptureError`; nothing is written."""
    if kind not in KINDS:
        raise CaptureError(f"kind must be one of {KINDS}")
    path = Path(report_path)
    rep = json.loads(path.read_text())
    if rep.get("schema") != REPORT_SCHEMAS[kind]:
        raise CaptureError(f"{path}: schema {rep.get('schema')!r} is not {REPORT_SCHEMAS[kind]!r}")
    if rep.get("label") != MEASUREMENT_LABEL:
        raise CaptureError(f"{path}: report label {rep.get('label')!r} is not {MEASUREMENT_LABEL!r}; "
                           "synthetic/example reports are never written as beliefs")
    cells = _flip_cells(rep) if kind == "flip" else _spectrum_cells(rep)
    if not cells:
        raise CaptureError(f"no reportable cells in {path}")
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sha = file_sha256(path)
    scope = FLIP_SCOPE if kind == "flip" else SPECTRUM_SCOPE
    rows = []
    for locator, metric, value, reps, denom, direction, extra in cells:
        row: dict[str, Any] = {
            "schema": CAPTURE_SCHEMA, "kind": kind, "run_id": run_id, "producer": producer,
            "emitted_at": when, "date": when[:10], "locator": locator, "metric": metric,
            "measurement_id": measurement_identity(run_id=run_id, kind=kind, locator=locator, metric=metric, report_sha256=sha),
            "value": value, "unit": "fraction" if metric not in _SIGNED else "rate difference",
            "metric_direction": direction, "category": "CANDIDATE",
            "claim": f"replay {kind} {run_id}: {locator} {metric} = {value:.4f} (n={reps} {denom})",
            "protocol_id": NO_PROTOCOL, "reps": reps, "reps_basis": f"denominator:{denom}",
            "report_path": str(path), "report_sha256": sha,
            "extra": {"denominator_label": denom, "code_ref": code_ref, "scope": scope, "report_label": rep["label"], **extra},
        }
        row["row_sha256"] = row_digest(row)
        problems = validate_row(row)
        if problems:
            raise CaptureError(f"{locator}/{metric}: refusing an invalid row: " + "; ".join(problems))
        rows.append(row)
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate measurement ids")
    out = sidecar_path(path)
    tmp = out.with_suffix(".tmp")
    with open(tmp, "w") as h:
        for r in rows:
            h.write(json.dumps(r, sort_keys=True) + "\n")
    os.replace(tmp, out)
    return out


__all__ = ["CAPTURE_SCHEMA", "SIDECAR_SUFFIX", "KINDS", "CaptureError", "validate_row", "row_digest",
           "file_sha256", "sidecar_path", "write_belief_measurements"]
