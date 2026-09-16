#!/usr/bin/env python3
"""VB-EVCONF2 write-side hook: producer-authored belief rows for EV-CONF-2 confidence-source reports.

The EV-CONF-2 GPU runner calls this once per arm, right after
``confidence_source_compare.py --out <report>`` (orchestrator) has read that arm's
``question_results.<arm>.jsonl``. The runner passes:

* the report (``epyc.confidence_source_compare.v1``)
* the probe's ``serving_identity.<arm>.json`` (``epyc.ev_conf2_probe_identity.v1``, written by
  orchestrator ``scripts/analysis/confidence_probe.py``)
* the served binary's recorded identity

It emits ``<report>.beliefs.jsonl``: one claim-tuple-shaped row per
arm x confidence source x metric.

Metrics per source (a row exists only where the report computed the value):

* ``confidence_auroc``            auroc                  higher_better  CI95 + paired delta in ``extra``
* ``confidence_ece``              ece_closed_top_bin_10  lower_better
* ``confidence_ece_reweighted``   ece_closed_top_bin_10  lower_better   prevalence in ``extra``

``neg_length`` is not a probability, so it carries AUROC only; the report already gives it no ECE.

**Speculative-decoding state is part of the measurement, not a footnote.** llama.cpp reports
``prob=1.0`` with no top-k for every draft-accepted token, so under MTP the geomean saturates and
every token-probability source is void. ``extra.spec`` records the resolved state (``on`` / ``off``
/ ``unknown``) and its evidence: the placeholder census from the report's ``token_trace``, plus the
``/slots`` declaration from the serving identity. A contradiction refuses the write. An
``A-specoff`` arm must resolve to ``off`` and a ``B-mtp`` arm to ``on``. A spec-on or
spec-unknown row states the contamination in its claim text, because ``to_frames`` carries the
claim, not ``extra``.

**Grade.** The compare tool stamps its own report ``claim_grade: "observation"``, and no codified
protocol names this probe instrument. P-CAL (``measurement/protocols/quality-eval.md``) names the E7c
math re-baseline and the EV-4c calibration baseline, and keeps math AUROC an observation pending
EV-CONF-2. So ``protocol_id`` is empty, and the shared ladder returns ``Judged/Located``. This
module does not decide that: ``claim_tuple.grade()`` does, from the empty protocol. The row
refuses a non-empty ``protocol_id`` while the report says ``observation`` or while spec state is
not ``off``. Lifting it takes a human P-CAL amendment and a producer that stops self-labelling as
observation. A new schema version then projects the same reports with no re-read of the sidecars.

Pre-hook reports stay pre-hook. The E7c and EV-4c aggregates in the ESC-7 draft and P-CAL emit zero
rows, and this module is never run over them to backfill. The strict read side is
``confidence_source.py``; it imports ``validate_row`` from here, so writer and reader share one
definition of well-formed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAPTURE_SCHEMA = "epyc.vidya.confidence_source_capture.v1"
REPORT_SCHEMA = "epyc.confidence_source_compare.v1"
IDENTITY_SCHEMA = "epyc.ev_conf2_probe_identity.v1"
SIDECAR_SUFFIX = ".beliefs.jsonl"
SERVING_MODES = frozenset({"test_port", "live_production"})
SPEC_STATES = ("on", "off", "unknown")
ECE_UNIT = "ece_closed_top_bin_10"
#: arm label -> the spec state that arm must resolve to (other labels accept any state)
ARM_SPEC_CONTRACT = {"A-specoff": "off", "B-mtp": "on"}

#: metric -> (unit, direction, report-entry key)
METRICS: dict[str, tuple[str, str, str]] = {
    "confidence_auroc": ("auroc", "higher_better", "auroc"),
    "confidence_ece": (ECE_UNIT, "lower_better", "ece"),
    "confidence_ece_reweighted": (ECE_UNIT, "lower_better", "ece_reweighted"),
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CaptureError(ValueError):
    """The runner asked for rows whose identity the run did not capture."""


# ── canonical hashing (same contract as the other *_capture producers) ────


def _canonical_json(value: Any) -> str:
    def check(obj: Any, path: str) -> None:
        if obj is None or isinstance(obj, (bool, int, str)):
            return
        if isinstance(obj, float):
            if not math.isfinite(obj):
                raise CaptureError(f"{path}: non-finite float is not canonical JSON")
            return
        if isinstance(obj, list):
            for index, item in enumerate(obj):
                check(item, f"{path}[{index}]")
            return
        if isinstance(obj, dict):
            for key, item in obj.items():
                if not isinstance(key, str):
                    raise CaptureError(f"{path}: canonical JSON keys must be strings")
                check(item, f"{path}.{key}")
            return
        raise CaptureError(f"{path}: {type(obj).__name__} is not canonical JSON")

    check(value, "$")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def content_hash(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def row_digest(row: Mapping[str, Any]) -> str:
    return content_hash({k: v for k, v in row.items() if k != "row_sha256"})


def file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def measurement_identity(*, run_id: str, arm: str, source: str, metric: str,
                         report_sha256: str) -> str:
    digest = content_hash({"run_id": run_id, "arm": arm, "source": source, "metric": metric,
                           "report_sha256": report_sha256})
    return f"evconf_{digest[:24]}"


def sidecar_path(report_path: str | Path) -> Path:
    path = Path(report_path)
    return path.with_name(path.stem + SIDECAR_SUFFIX)


# ── validation ────────────────────────────────────────────────────────────


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _pos_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value > 0


def _nonneg_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def _unit_float(value: Any) -> bool:
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value) and 0.0 <= value <= 1.0)


def _utc(value: Any) -> bool:
    if not _text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.utcoffset() is not None


def spec_caveat(state: str) -> str:
    if state == "on":
        return ("CONTAMINATED: speculative decoding ON (draft-accepted tokens carry placeholder "
                "p=1.0), so token-probability confidence is void; ")
    if state == "unknown":
        return "UNVERIFIED speculative-decoding state; token-probability confidence may be void; "
    return ""


def validate_row(row: Any) -> list[str]:
    """Every structural problem in one producer-authored row. Empty list == valid."""
    if not isinstance(row, dict):
        return ["row is not a JSON object"]
    p: list[str] = []
    if row.get("schema") != CAPTURE_SCHEMA:
        p.append(f"schema must be {CAPTURE_SCHEMA!r}")
    for key in ("run_id", "producer", "measurement_id", "metric", "unit", "claim", "reps_basis",
                "report_path", "identity_path", "date"):
        if not _text(row.get(key)):
            p.append(f"{key} must be a non-empty string")
    if not isinstance(row.get("protocol_id"), str):
        p.append("protocol_id must be a string (empty = observation)")
    if not _utc(row.get("emitted_at")):
        p.append("emitted_at must be a UTC timestamp")
    for key in ("report_sha256", "identity_sha256"):
        if not _SHA256.match(str(row.get(key, ""))):
            p.append(f"{key} must be a 64-hex digest")
    metric = row.get("metric")
    if metric not in METRICS:
        p.append(f"metric must be one of {sorted(METRICS)}")
    else:
        unit, direction, _ = METRICS[metric]
        if row.get("unit") != unit:
            p.append(f"unit for {metric} must be {unit!r}")
        if row.get("metric_direction") != direction:
            p.append(f"metric_direction for {metric} must be {direction!r}")
    if not _unit_float(row.get("value")):
        p.append("value must be a finite number in [0, 1]")
    if not _pos_int(row.get("reps")):
        p.append("reps must be a positive integer")
    extra = row.get("extra")
    if not isinstance(extra, dict):
        return p + ["extra must be an object carrying the run identity"]

    for key in ("arm", "source", "role", "baseline_source", "claim_grade", "ece_binning"):
        if not _text(extra.get(key)):
            p.append(f"extra.{key} must be a non-empty string")
    if _text(extra.get("source")) and _text(extra.get("baseline_source")):
        want = "BASELINE" if extra["source"] == extra["baseline_source"] else "CANDIDATE"
        if row.get("category") != want:
            p.append(f"category must be {want} for source {extra['source']!r}")
    n, n_scored = extra.get("n"), extra.get("n_scored")
    if not _pos_int(n) or not _pos_int(n_scored) or n > n_scored:
        p.append("extra.n must be positive and within extra.n_scored")
    else:
        if row.get("reps") != n:
            p.append("reps must equal extra.n (rows where this source is defined)")
        want_basis = ("scored:questions" if n == n_scored else
                      f"scored:questions ({n_scored - n} without this source excluded)")
        if row.get("reps_basis") != want_basis:
            p.append(f"reps_basis must be {want_basis!r}")
    if metric == "confidence_auroc":
        ci = extra.get("ci95")
        if ci is not None and not (isinstance(ci, list) and len(ci) == 2
                                   and all(_unit_float(v) for v in ci) and ci[0] <= ci[1]):
            p.append("extra.ci95 must be null or [lo, hi] within [0, 1]")
    if metric == "confidence_ece_reweighted" and not _unit_float(extra.get("reweight_prevalence")):
        p.append("extra.reweight_prevalence must be recorded for a reweighted ECE")
    for key in ("dataset_sha256", "sample_sha256"):
        if not _SHA256.match(str(extra.get(key, ""))):
            p.append(f"extra.{key} must be a 64-hex digest")
    if not _nonneg_int(extra.get("seed")):
        p.append("extra.seed must be a non-negative integer")
    sidecars = extra.get("sidecars")
    if not isinstance(sidecars, list) or not sidecars or not all(
            isinstance(s, dict) and _text(s.get("path")) and _SHA256.match(str(s.get("sha256", "")))
            for s in sidecars):
        p.append("extra.sidecars must list every input sidecar with its sha256")
    served = extra.get("served")
    if not isinstance(served, dict) or not _text(served.get("model_path")) \
            or not _text(served.get("build_info")):
        p.append("extra.served must name model_path and build_info (from /props)")
    serving = extra.get("serving")
    if not isinstance(serving, dict) or serving.get("mode") not in SERVING_MODES \
            or not _text(serving.get("endpoint")):
        p.append(f"extra.serving must carry endpoint and mode in {sorted(SERVING_MODES)}")
    kernel = extra.get("kernel")
    if not isinstance(kernel, dict) or not _SHA256.match(str(kernel.get("binary_sha256", ""))) \
            or not _text(kernel.get("binary_path")):
        p.append("extra.kernel must carry the served binary_path and its binary_sha256")
    sampling = extra.get("sampling")
    if not isinstance(sampling, dict) or "temperature" not in sampling \
            or not _nonneg_int(sampling.get("seed")):
        p.append("extra.sampling must record the request temperature and seed")

    spec = extra.get("spec")
    state = spec.get("state") if isinstance(spec, dict) else None
    if state not in SPEC_STATES:
        p.append(f"extra.spec.state must be one of {SPEC_STATES}")
    else:
        if not isinstance(spec.get("evidence"), list) or not spec["evidence"]:
            p.append("extra.spec.evidence must name what the state was resolved from")
        arm_state = ARM_SPEC_CONTRACT.get(str(extra.get("arm")))
        if arm_state and state != arm_state:
            p.append(f"arm {extra.get('arm')!r} must resolve to spec {arm_state!r}, not {state!r}")
        if extra.get("confidence_is_real") is not (state == "off"):
            p.append("extra.confidence_is_real must be true exactly when spec state is 'off'")
        if _text(row.get("claim")) and not row["claim"].startswith(
                f"EV-CONF-2 {row.get('run_id')}: " + spec_caveat(state)):
            p.append("claim must lead with the run id and the spec-state caveat")
    if _text(row.get("protocol_id")) and (extra.get("claim_grade") == "observation"
                                          or state != "off"):
        p.append("protocol_id must be empty while the report is observation-grade or spec is "
                 "not verified off")

    if all(_text(row.get(k)) for k in ("run_id", "metric")) and _text(extra.get("arm")) \
            and _text(extra.get("source")) and _SHA256.match(str(row.get("report_sha256", ""))):
        expected = measurement_identity(run_id=row["run_id"], arm=extra["arm"],
                                        source=extra["source"], metric=row["metric"],
                                        report_sha256=row["report_sha256"])
        if row.get("measurement_id") != expected:
            p.append("measurement_id does not re-derive from (run_id, arm, source, metric, "
                     "report_sha256)")
    if not _SHA256.match(str(row.get("row_sha256", ""))):
        p.append("row_sha256 must be a 64-hex self-hash")
    else:
        try:
            if row_digest(row) != row["row_sha256"]:
                p.append("row_sha256 does not bind the row content")
        except CaptureError as exc:
            p.append(f"row is not canonically hashable: {exc}")
    return p


# ── write side ────────────────────────────────────────────────────────────


def _load_identity(identity_path: Path, arm: str) -> dict[str, Any]:
    data = json.loads(identity_path.read_text())
    segments = data.get("segments") if isinstance(data, dict) else None
    if not isinstance(segments, list) or not segments:
        raise CaptureError(f"{identity_path}: no serving-identity segments")
    for seg in segments:
        if not isinstance(seg, dict) or seg.get("schema") != IDENTITY_SCHEMA:
            raise CaptureError(f"{identity_path}: segment schema must be {IDENTITY_SCHEMA!r}")
        if seg.get("arm") != arm:
            raise CaptureError(f"{identity_path}: segment arm {seg.get('arm')!r} != {arm!r}")
    first = segments[0]
    for key in ("dataset_sha256", "sample_sha256", "eval_batch_id"):
        values = {seg.get(key) for seg in segments}
        if len(values) != 1:
            raise CaptureError(f"{identity_path}: {key} differs across segments: {sorted(map(str, values))}")
    for key in ("model_path", "build_info"):
        values = {((seg.get("serving") or {}).get("props") or {}).get(key) for seg in segments}
        if len(values) != 1 or not _text(next(iter(values))):
            raise CaptureError(f"{identity_path}: /props {key} missing or changed across segments")
    declared = [(seg.get("serving") or {}).get("spec_declared") for seg in segments]
    return {"first": first, "segments": segments, "declared": declared}


def resolve_spec_state(report: Mapping[str, Any], declared: list[Any]) -> tuple[str, list[str]]:
    """Resolve spec state from the placeholder census and the ``/slots`` declaration.

    Contradictions raise, because a row that cannot say whether its confidence was real is not
    written.
    """
    tt = report.get("token_trace") or {}
    with_trace = int(tt.get("rows_with_trace") or 0)
    with_ph = int(tt.get("rows_with_any_placeholder") or 0)
    n_scored = int(report.get("n_scored") or 0)
    evidence = [
        f"token_trace.rows_with_trace={with_trace}/{n_scored}",
        f"token_trace.rows_with_any_placeholder={with_ph}",
        f"token_trace.placeholder_fraction_median={tt.get('placeholder_fraction_median')}",
        f"slots.speculative per segment={declared}",
    ]
    declared_on = any(d is True for d in declared)
    declared_off = bool(declared) and all(d is False for d in declared)
    if with_ph > 0 and declared_off:
        raise CaptureError("placeholders observed while /slots declared speculative=false; "
                           "the identity does not describe the server that produced these rows")
    if with_ph > 0 or declared_on:
        return "on", evidence
    if with_trace == 0 or with_trace < n_scored:
        return "unknown", evidence
    return "off", evidence


def build_rows(
    report_path: str | Path, *,
    identity_path: str | Path,
    arm: str,
    run_id: str,
    producer: str,
    kernel: Mapping[str, Any],
    serving_mode: str = "test_port",
    emitted_at: str | None = None,
) -> list[dict[str, Any]]:
    report_file, identity_file = Path(report_path), Path(identity_path)
    if not report_file.is_file() or not identity_file.is_file():
        raise CaptureError(f"report or identity missing: {report_file}, {identity_file}")
    report = json.loads(report_file.read_text())
    if not isinstance(report, dict) or report.get("schema") != REPORT_SCHEMA:
        raise CaptureError(f"{report_file}: schema must be {REPORT_SCHEMA!r}")
    inputs = (report.get("inputs") or {}).get("files")
    if not isinstance(inputs, list) or not inputs:
        raise CaptureError("report.inputs.files is missing: write the report with --out, not stdout")
    sidecars = []
    for entry in inputs:
        path = Path(str(entry.get("path", "")))
        if not path.is_file() or file_sha256(path) != entry.get("sha256"):
            raise CaptureError(f"input sidecar {path} changed or vanished since the report was computed")
        sidecars.append({"path": str(path), "sha256": entry["sha256"]})
    ident = _load_identity(identity_file, arm)
    first = ident["first"]
    # Bind the identity to the report. Every question row in every input sidecar must come from
    # the batch this identity describes. Only the batch id is read here, never a value, so this
    # checks the pairing and does not reconstruct anything.
    batch_ids: set[str] = set()
    for entry in sidecars:
        for line in Path(entry["path"]).read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    batch_ids.add(str(json.loads(line).get("eval_batch_id")))
                except json.JSONDecodeError as exc:
                    raise CaptureError(f"input sidecar {entry['path']} is not JSONL") from exc
    if batch_ids != {str(first.get("eval_batch_id"))}:
        raise CaptureError(
            f"identity batch {first.get('eval_batch_id')!r} does not describe the report's "
            f"sidecars (batches {sorted(batch_ids)}); pass the identity written by the same probe run")
    state, evidence = resolve_spec_state(report, ident["declared"])
    sampling = (first.get("sampling") or {})
    payload = sampling.get("payload") or {}
    props = (first.get("serving") or {}).get("props") or {}
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report_sha, identity_sha = file_sha256(report_file), file_sha256(identity_file)
    baseline = str(report.get("baseline_source") or "")
    claim_grade = str(report.get("claim_grade") or "")
    n_scored = int(report.get("n_scored") or 0)
    tt = report.get("token_trace") or {}
    rows: list[dict[str, Any]] = []
    for source, entry in sorted((report.get("sources") or {}).items()):
        n = entry.get("n") if isinstance(entry, dict) else None
        if not _pos_int(n):
            continue  # a source undefined on every row has nothing to project
        for metric, (unit, direction, key) in METRICS.items():
            value = entry.get(key)
            if value is None:
                continue  # never computed (e.g. ECE of a non-probability) -> no row
            extra: dict[str, Any] = {
                "arm": arm, "source": source, "baseline_source": baseline,
                "role": sampling.get("role"), "n": n, "n_scored": n_scored,
                "accuracy": entry.get("accuracy"),
                "claim_grade": claim_grade, "ece_binning": report.get("ece_binning"),
                "dataset_sha256": first.get("dataset_sha256"),
                "sample_sha256": first.get("sample_sha256"),
                "eval_batch_id": first.get("eval_batch_id"),
                # the request sampling seed; the bootstrap seed rides inside `bootstrap`
                "seed": payload.get("seed"),
                "bootstrap": report.get("bootstrap"),
                "sidecars": sidecars,
                "served": {"model_path": props.get("model_path"), "build_info": props.get("build_info"),
                           "model_alias": props.get("model_alias"), "n_ctx": props.get("n_ctx"),
                           "registry_model_path": sampling.get("model_path")},
                "serving": {"mode": serving_mode, "endpoint": (first.get("serving") or {}).get("endpoint")},
                "kernel": dict(kernel),
                "sampling": {k: payload.get(k) for k in ("temperature", "top_k", "top_p",
                                                         "repeat_penalty", "seed")}
                | {"top_logprobs": (first.get("request") or {}).get("top_logprobs"),
                   "max_tokens": (first.get("request") or {}).get("max_tokens")},
                "orchestrator_head": first.get("orchestrator_head"),
                "spec": {"state": state, "evidence": evidence,
                         "placeholder_fraction_median": tt.get("placeholder_fraction_median"),
                         "placeholder_fraction_max": tt.get("placeholder_fraction_max"),
                         "rows_with_any_placeholder": tt.get("rows_with_any_placeholder"),
                         "rows_with_trace": tt.get("rows_with_trace")},
                "confidence_is_real": state == "off",
                "metric_direction_note": "AUROC higher is better; ECE lower is better",
            }
            if metric == "confidence_auroc":
                ci = entry.get("auroc_ci95")
                extra["ci95"] = list(ci) if ci else None
                extra["paired_vs_baseline"] = entry.get("paired_vs_baseline")
            if metric == "confidence_ece_reweighted":
                extra["reweight_prevalence"] = report.get("reweight_prevalence")
            ci_txt = (f" (95% CI [{extra['ci95'][0]}, {extra['ci95'][1]}])"
                      if metric == "confidence_auroc" and extra.get("ci95") else "")
            row: dict[str, Any] = {
                "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
                "emitted_at": when, "date": when[:10],
                "measurement_id": measurement_identity(run_id=run_id, arm=arm, source=source,
                                                       metric=metric, report_sha256=report_sha),
                "metric": metric, "value": value, "unit": unit, "metric_direction": direction,
                "category": "BASELINE" if source == baseline else "CANDIDATE",
                "claim": (f"EV-CONF-2 {run_id}: {spec_caveat(state)}arm {arm}, source {source}: "
                          f"{metric} = {float(value):.4f}{ci_txt} over n={n} scored "
                          f"{sampling.get('role')} math rows ({direction.replace('_', ' ')})"),
                "protocol_id": "",
                "reps": n,
                "reps_basis": ("scored:questions" if n == n_scored else
                               f"scored:questions ({n_scored - n} without this source excluded)"),
                "report_path": str(report_file), "report_sha256": report_sha,
                "identity_path": str(identity_file), "identity_sha256": identity_sha,
                "extra": extra,
            }
            row["row_sha256"] = row_digest(row)
            problems = validate_row(row)
            if problems:
                raise CaptureError(f"{source}/{metric}: refusing an invalid row: " + "; ".join(problems))
            rows.append(row)
    if not rows:
        raise CaptureError(f"{report_file}: no source carries a computed metric")
    return rows


def write_belief_measurements(report_path: str | Path, **kwargs: Any) -> Path:
    """Emit ``<report>.beliefs.jsonl`` atomically. Any invalid row raises and nothing is written."""
    rows = build_rows(report_path, **kwargs)
    out = sidecar_path(report_path)
    tmp = out.with_suffix(".tmp")
    with open(tmp, "w") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    os.replace(tmp, out)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--report", required=True, type=Path, help="confidence_source_compare.py --out file")
    ap.add_argument("--identity", required=True, type=Path, help="probe serving_identity.<arm>.json")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--producer", default="orchestrator:scripts/analysis/confidence_source_compare.py")
    ap.add_argument("--binary-path", required=True)
    ap.add_argument("--binary-sha256", default=None,
                    help="recorded at launch; if omitted the binary is hashed now")
    ap.add_argument("--serving-mode", default="test_port", choices=sorted(SERVING_MODES))
    args = ap.parse_args(argv)
    binary_sha = args.binary_sha256 or file_sha256(args.binary_path)
    try:
        out = write_belief_measurements(
            args.report, identity_path=args.identity, arm=args.arm, run_id=args.run_id,
            producer=args.producer, serving_mode=args.serving_mode,
            kernel={"binary_path": args.binary_path, "binary_sha256": binary_sha,
                    "binary_sha256_source": "argument" if args.binary_sha256 else "hashed_at_capture"},
        )
    except CaptureError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(out)
    return 0


__all__ = ["CAPTURE_SCHEMA", "REPORT_SCHEMA", "IDENTITY_SCHEMA", "SIDECAR_SUFFIX", "METRICS",
           "SPEC_STATES", "ARM_SPEC_CONTRACT", "CaptureError", "content_hash", "row_digest",
           "file_sha256", "measurement_identity", "sidecar_path", "spec_caveat", "validate_row",
           "resolve_spec_state", "build_rows", "write_belief_measurements"]


if __name__ == "__main__":
    raise SystemExit(main())
