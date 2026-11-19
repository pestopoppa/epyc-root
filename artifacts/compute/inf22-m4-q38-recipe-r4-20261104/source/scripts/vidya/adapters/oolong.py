"""VB-OOLONG-WIRE: Oolong long-context suite (OOL-1) per-question JSONL as a measurement source.

Producer: research ``scripts/benchmark/oolong_adapter.py`` (lane ``lane/dpf-sample-yarn-ool``, commit
``a1ed3633a``), whose ``make_record`` writes one JSONL record per question. This module is the root
WRITE side: :func:`write_belief_measurements` is called once per finished results file (inside a
window runner, after ``run_arm``) and turns the per-question records into one self-hashed row per
CELL ``(model, arm, family, source_revision, context_len)``. The strict reader reopens the results
file digest, projects authored facts to the existing ``measurement`` ``ClaimTuple`` and
``claim_tuple.grade()`` decides. No second ladder, no retrospective tuple (a missing sidecar is zero
rows; there is no function that reads an old ``oolong-*.jsonl`` into rows).

Claim scope = model pin, context length, thinking arm, pinned dataset revision, vendored scorer pin.
``value`` is the mean score; ``reps`` is the number of CONTEXTS (the producer clusters its CI by
``context_window_id`` because a context's questions share one prefill), ``reps_basis`` says so, and
the context-clustered CI (same percentile-bootstrap rule as the producer's ``cluster_ci``) rides in
``extra``. Items are in ``extra.n_items``.

``labels_given`` records (labelled-text ablation) are NEVER gate evidence. They are dropped before
any cell is formed (counted in ``extra.labels_given_excluded``), a file with only such records is
refused, and a cell row can not carry ``labels_given`` true. The ladder has no "non-gating but
projected" state other than an empty ``protocol_id`` (an OBSERVATION); we pick exclusion because a
labelled-text number must not even be a Located observation next to the labels-blind one.

Protocol: a protocol id is carried only if the caller names one that already applies; otherwise the
row stores the literal ``observation:none`` and the projection maps it to the empty string the
ladder reads as "no protocol" (so grading is Judged/Located, never Witnessed).

Producer fields REQUIRED per record (absent -> CaptureError naming file and field, never back-filled):
``model, arm, family, labels_given, source_revision, upstream_sha, vendored_sha256, context_len,
context_window_id, id, attempted, answered, no_answer, parse_confidence, score, failure_class``
(``failure_class`` may be null only when ``score >= 1``).
"""

from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.oolong_capture.v1"
SIDECAR_NAME = "oolong.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.oolong/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "oolong-measurement"
NO_PROTOCOL = "observation:none"
METRIC = "oolong_mean_score"

#: Producer pins (research oolong_adapter.py). A different scorer is a different measurand.
UPSTREAM_SHA_PREFIX = "0bb7eabe8"
VENDORED_SHA256 = "247583a3b653b91c39fb88a102460802f1493175b23d05a7217aead0d685c64c"
SOURCE_REVISIONS = {
    "oolongbench/oolong-synth": "81d2f8d9349f6ff329d695f9be494051e9f05cb9",
    "oolongbench/oolong-real": "3ae6ab58ffcc4253ed52daeb58e02ed4cfea5784",
}
ARMS = frozenset({"thinking_on", "thinking_off"})
FAILURE_CLASSES = ("wrong", "no_answer_budget", "refusal", "unparsable")
PARSE_CONFIDENCE = frozenset({"vhigh", "high", "med", "low"})
REQUIRED = ("model", "arm", "family", "labels_given", "source_revision", "upstream_sha",
            "vendored_sha256", "context_len", "context_window_id", "id", "attempted", "answered",
            "no_answer", "parse_confidence", "score", "failure_class")


def cluster_ci(scores_by_context: dict[Any, list[float]], n_boot: int = 2000, seed: int = 0,
               alpha: float = 0.05) -> dict:
    """Context-clustered percentile bootstrap of the mean (same rule as the producer's)."""
    ctxs = [scores_by_context[k] for k in sorted(scores_by_context, key=str)]
    n = sum(len(c) for c in ctxs)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        pick = [ctxs[rng.randrange(len(ctxs))] for _ in ctxs]
        boots.append(sum(sum(c) for c in pick) / sum(len(c) for c in pick))
    boots.sort()
    return {"lo": boots[int(math.floor(alpha / 2 * (n_boot - 1)))],
            "hi": boots[int(math.ceil((1 - alpha / 2) * (n_boot - 1)))],
            "method": "context-clustered percentile bootstrap", "n_boot": n_boot, "seed": seed,
            "alpha": alpha, "n_contexts": len(ctxs), "n_items": n}


def _bad_record(rec: Any, where: str) -> list[str]:
    if not isinstance(rec, dict):
        return [f"{where}: not a JSON object"]
    p = [f"{where}: field {k!r} absent (producer gap)" for k in REQUIRED if k not in rec]
    if p:
        return p
    if not isinstance(rec["labels_given"], bool):
        p.append(f"{where}: labels_given must be a boolean")
    if rec["arm"] not in ARMS and not (rec["labels_given"] and str(rec["arm"]).startswith("labels_given_")):
        p.append(f"{where}: arm {rec['arm']!r} not thinking_on/thinking_off")
    if not ns.text(rec["model"]):
        p.append(f"{where}: model must be a non-empty string")
    if not ns.nonneg_int(rec["context_len"]) or rec["context_len"] == 0:
        p.append(f"{where}: context_len must be a positive integer")
    if not ns.finite(rec["score"]) or not 0 <= rec["score"] <= 1:
        p.append(f"{where}: score must be a finite number in [0,1]")
    for k in ("attempted", "answered", "no_answer"):
        if not isinstance(rec[k], bool):
            p.append(f"{where}: {k} must be a boolean")
    if rec["parse_confidence"] not in PARSE_CONFIDENCE:
        p.append(f"{where}: parse_confidence {rec['parse_confidence']!r} unrecognised")
    fc = rec["failure_class"]
    if fc is None:
        if ns.finite(rec["score"]) and rec["score"] < 1:
            p.append(f"{where}: failure_class null on an incorrect item")
    elif fc not in FAILURE_CLASSES:
        p.append(f"{where}: failure_class {fc!r} not in {FAILURE_CLASSES}")
    src = str(rec["source_revision"])
    name, _, rev = src.partition("@")
    if SOURCE_REVISIONS.get(name) != rev:
        p.append(f"{where}: source_revision {src!r} is not a pinned revision")
    if rec["vendored_sha256"] != VENDORED_SHA256 or rec["upstream_sha"] != UPSTREAM_SHA_PREFIX:
        p.append(f"{where}: scorer pin is not the vendored upstream 0bb7eabe8 / {VENDORED_SHA256[:8]}")
    return p


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA)
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("metric") != METRIC or row.get("metric_direction") != "higher_better":
        p.append(f"metric must be {METRIC} / higher_better")
    if e.get("labels_given") is not False:
        p.append("extra.labels_given must be false: labels_given records are never gate evidence")
    for k in ("model_pin", "arm", "family", "source_revision", "upstream_sha", "vendored_sha256",
              "results_basename"):
        if not ns.text(e.get(k)):
            p.append(f"extra.{k} must be a non-empty string")
    if e.get("arm") not in ARMS:
        p.append("extra.arm must be thinking_on or thinking_off")
    if not ns.nonneg_int(e.get("context_len")) or not e.get("context_len"):
        p.append("extra.context_len must be a positive integer")
    for k in ("n_items", "n_contexts"):
        if not ns.nonneg_int(e.get(k)) or not e.get(k):
            p.append(f"extra.{k} must be a positive integer")
    if row.get("category") not in ns.CATEGORIES:
        p.append("category invalid")
    elif ns.nonneg_int(e.get("n_contexts")):
        if row.get("reps") != e["n_contexts"]:
            p.append("reps must equal extra.n_contexts (clustered basis is contexts)")
        want = f"contexts (clustered; {e.get('n_items')} items)"
        if row.get("reps_basis") != want:
            p.append(f"reps_basis must be {want!r}")
    ci = e.get("ci")
    if not isinstance(ci, dict) or not all(ns.finite(ci.get(k)) for k in ("lo", "hi")) \
            or ci.get("method") != "context-clustered percentile bootstrap":
        p.append("extra.ci must be a context-clustered interval")
    if not p:
        p += ns.check_identity(row, {
            "run_id": row["run_id"], "model": e["model_pin"], "arm": e["arm"],
            "family": e["family"], "source": e["source_revision"], "ctx": e["context_len"],
            "results": row["results_sha256"]}, "ool")
    return p + ns.self_hash_problems(row)


def write_belief_measurements(
    out_dir: str | Path, *, run_id: str, producer: str, results_path: str | Path,
    protocol_id: str | None = None, emitted_at: str | None = None, n_boot: int = 2000,
) -> Path:
    """Emit ``oolong.beliefs.jsonl`` from one finished ``oolong-*.jsonl`` results file.

    Call at the end of the window runner, after ``run_arm`` returns::

        write_belief_measurements(run_dir, run_id=..., producer="oolong-window-runner",
                                  results_path=run_dir / "oolong-<arm>.jsonl")

    Raises :class:`CaptureError` naming file + field for any producer gap.
    """
    raw = Path(results_path)
    if not raw.is_file():
        raise CaptureError(f"raw result file missing: {raw}")
    digest = ns.file_sha256(raw)
    recs: list[dict] = []
    problems: list[str] = []
    for i, line in enumerate(raw.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            problems.append(f"{raw.name}:{i}: not JSON")
            continue
        problems += _bad_record(rec, f"{raw.name}:{i}")
        recs.append(rec)
    if problems:
        raise CaptureError("producer record gaps (never back-filled): " + "; ".join(problems[:12])
                           + (f" (+{len(problems) - 12} more)" if len(problems) > 12 else ""))
    gate = [r for r in recs if not r["labels_given"]]
    if not gate:
        raise CaptureError(f"{raw.name}: no gate-eligible record (labels_given records are never "
                           "gate evidence and are not projected)")
    excluded = len(recs) - len(gate)
    ids = [(r["id"], r["model"], r["arm"], r["source_revision"]) for r in gate]
    if len(set(map(str, ids))) != len(ids):
        raise CaptureError(f"{raw.name}: duplicate question id within a cell")
    cells: dict[tuple, list[dict]] = defaultdict(list)
    for r in gate:
        cells[(r["model"], r["arm"], r["family"], r["source_revision"], r["context_len"])].append(r)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for (model, arm, family, source, clen), rs in sorted(cells.items(), key=str):
        by_ctx: dict[Any, list[float]] = defaultdict(list)
        for r in rs:
            by_ctx[r["context_window_id"]].append(float(r["score"]))
        n_items, n_ctx = len(rs), len(by_ctx)
        mean = sum(sum(v) for v in by_ctx.values()) / n_items
        fc = {k: sum(1 for r in rs if r["failure_class"] == k) for k in FAILURE_CLASSES}
        e = {
            "model_pin": model, "arm": arm, "family": family, "labels_given": False,
            "source_revision": source, "upstream_sha": UPSTREAM_SHA_PREFIX,
            "vendored_sha256": VENDORED_SHA256, "context_len": clen, "n_items": n_items,
            "n_contexts": n_ctx, "ci": cluster_ci(by_ctx, n_boot=n_boot),
            "attempted_rate": sum(r["attempted"] for r in rs) / n_items,
            "answered_rate": sum(r["answered"] for r in rs) / n_items,
            "no_answer_rate": sum(r["no_answer"] for r in rs) / n_items,
            "failure_classes": fc,
            "low_parse_confidence": sum(1 for r in rs if r["parse_confidence"] == "low"),
            "labels_given_excluded": excluded, "results_basename": raw.name,
        }
        row = {
            "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer,
            "emitted_at": when, "date": when[:10], "metric": METRIC, "value": mean,
            "unit": "score", "metric_direction": "higher_better", "category": "OPTIMUM",
            "claim": (f"Oolong {run_id}: {model} {arm} {source.split('@')[0]} ctx={clen} "
                      f"mean score={mean:.4f} over {n_ctx} contexts / {n_items} items"),
            "protocol_id": protocol_id or NO_PROTOCOL,
            "reps": n_ctx, "reps_basis": f"contexts (clustered; {n_items} items)",
            "results_path": str(raw), "results_sha256": digest, "extra": e,
        }
        row["measurement_id"] = "ool_" + ns.content_hash({
            "run_id": run_id, "model": model, "arm": arm, "family": family, "source": source,
            "ctx": clen, "results": digest})[:24]
        ns.seal(row)
        bad = validate_row(row)
        if bad:
            raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
        rows.append(row)
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


def rows_for_run(run_dir: str | Path) -> tuple[dict, ...]:
    return native_rows(Path(run_dir) / SIDECAR_NAME)


@register(SOURCE_KIND)
def project(native: Any):
    import dataclasses
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("Oolong native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("Oolong row is not a producer-authored capture: " + "; ".join(problems))
    x = row["extra"]
    locator = (f"oolong:{row['run_id']}:{x['model_pin']}:{x['arm']}:{x['context_len']}:"
               f"{row['results_path']}")
    tup = ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                            sidecar_path=native.get("sidecar_path", ""))
    if tup.protocol_id == NO_PROTOCOL:  # the ladder reads any non-empty id as a protocol
        tup = dataclasses.replace(tup, protocol_id="")
    return tup


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
