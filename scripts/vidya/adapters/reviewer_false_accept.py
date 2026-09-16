"""Project SC83 reviewer negative-control false-accept rates into ``ClaimTuple``.

Write side (producer): epyc-orchestrator ``src/proactive_delegation/false_accept_record.py``,
driven by ``scripts/review/score_false_accept.py``. Each scoring run (one reviewer
configuration against one RA-9 gold-corpus version) appends one
``epyc.reviewer.false_accept_run.v1`` line to
``data/reviewer_eval/false_accept_runs.jsonl``. The line carries:

* the ``FalseAcceptResult`` with its denominator stated;
* the stale verdicts dropped by the RA-12 ``check_binding`` write-side filter;
* the sha256 of every input;
* at most one producer-authored belief row.

This adapter PROJECTS that row. ``claim_tuple.grade()`` decides the grade. The rules:

* **Rates only.** Single verdicts and machine objections never become tuples.
  Objections stay ``unverified_lead`` in the orchestrator.
* **Observation only.** RC-6a has not merged, so a row that cites a protocol is
  refused. The shared ladder grades these ``Judged/Located``.
* **Locator = the scoring run** (reviewer config x corpus version), never the decoy.
* **The denominator is accounted for.** ``n_decoys == scored + unscored +
  excluded_for_arbitration``, and every stale id must sit in ``unscored``. A rate
  whose denominator silently dropped decoys is refused.
* **Staleness is never re-bound on read.** A verdict the writer dropped stays
  dropped. A run with no scored decoy has no row, and none is invented here.
* **Input decay is recorded, not repaired.** An input file that still exists at
  its recorded path is re-hashed. If it no longer matches, the tuple carries
  ``attestation_present=False``. A missing input is not asserted either way.
* Every self-hash re-derives: the line's ``line_sha256`` and the row's
  ``row_sha256``. A mismatch refuses the whole file.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.reviewer_false_accept/v1"
#: Frame authority scope: an observation-grade measurement until RC-6a merges.
AUTHORITY = "measurement"
PROJECTION_NAME = "reviewer_false_accept"
LINE_SCHEMA = "epyc.reviewer.false_accept_run.v1"
BELIEF_SCHEMA = "epyc.reviewer.false_accept_belief.v1"
METRIC = "reviewer.negative_control_false_accept_rate"
#: Keys this reader may set on a native row; they are outside the writer's row hash.
_READER_KEYS = ("attestation_present",)
_FIELDS = frozenset(ClaimTuple.__dataclass_fields__)


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _row_digest(row: Mapping[str, Any]) -> str:
    body = json.loads(_canon({k: v for k, v in row.items() if k not in _READER_KEYS}))
    body.get("extra", {}).pop("row_sha256", None)
    return _sha(_canon(body).encode())


def _inputs_match(inputs: Mapping[str, Any]) -> bool | None:
    """False if an input still on disk no longer matches; None when nothing is checkable."""
    verdict: bool | None = None
    for spec in inputs.values():
        path = Path(str(spec.get("path") or ""))
        if not path.is_absolute() or not path.is_file():
            continue
        if _sha(path.read_bytes()) != spec.get("sha256"):
            return False
        verdict = True
    return verdict


def _check_line(line: Mapping[str, Any]) -> None:
    body = dict(line)
    if body.pop("line_sha256", None) != _sha(_canon(body).encode()):
        raise ProjectionError("run line does not hash to its line_sha256 (edited after writing)")
    if line.get("record") != "scoring_run":
        raise ProjectionError(f"unknown record kind {line.get('record')!r}")
    res = line.get("result") or {}
    if res.get("metric") != "negative_control_false_accept_rate":
        raise ProjectionError("result is not a negative-control false-accept result")
    unscored = res.get("unscored") or []
    excluded = res.get("excluded_for_arbitration") or []
    den, num, n_decoys = res.get("denominator"), res.get("numerator"), res.get("n_decoys")
    if not all(isinstance(x, int) for x in (den, num, n_decoys)):
        raise ProjectionError("result counts must be integers")
    if den + len(unscored) + len(excluded) != n_decoys:
        raise ProjectionError(
            f"denominator dropped decoys: {n_decoys} decoys, "
            f"{den + len(unscored) + len(excluded)} accounted for")
    if not set(line.get("stale") or {}) <= set(unscored):
        raise ProjectionError("a stale verdict is not listed as unscored; it was re-bound")
    rows = line.get("belief_measurements")
    if not isinstance(rows, list) or len(rows) > 1:
        raise ProjectionError("a scoring run carries at most one belief row")
    if (res.get("rate") is None) != (not rows):
        raise ProjectionError("a row exists iff the run scored at least one decoy")
    for row in rows:
        extra = row.get("extra") or {}
        if (extra.get("numerator"), extra.get("denominator")) != (num, den):
            raise ProjectionError("row numerator/denominator differ from the run result")
        if extra.get("run_id") != line.get("run_id"):
            raise ProjectionError("row run_id differs from its line")
        if extra.get("corpus_sha256") != ((line.get("inputs") or {}).get("corpus") or {}).get("sha256"):
            raise ProjectionError("row corpus_sha256 differs from the line's corpus input")
        if sorted(extra.get("stale") or []) != sorted(line.get("stale") or {}):
            raise ProjectionError("row stale list differs from its line")


def native_rows(path: str | Path) -> tuple[dict[str, Any], ...]:
    """Read one runs file strictly. Returns one producer row per scored run."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectionError(f"false-accept runs file unreadable: {exc}") from exc
    raw_lines = text.splitlines()
    if raw_lines and not text.endswith("\n"):
        # An fsync'd append interrupted mid-write leaves an unterminated tail. It is not a
        # record; skip it only if it does not parse. Any other malformed line voids the file.
        try:
            json.loads(raw_lines[-1])
        except ValueError:
            raw_lines = raw_lines[:-1]
    out: list[dict[str, Any]] = []
    run_ids: set[str] = set()
    for n, raw in enumerate(raw_lines, 1):
        if not raw.strip():
            continue
        try:
            line = json.loads(raw)
        except ValueError as exc:
            raise ProjectionError(f"line {n}: not JSON ({exc}); a torn file is refused") from exc
        if not isinstance(line, dict) or line.get("schema") != LINE_SCHEMA:
            raise ProjectionError(f"line {n}: not a {LINE_SCHEMA} record")
        _check_line(line)
        if line["run_id"] in run_ids:
            raise ProjectionError(f"run_id {line['run_id']!r} recorded twice")
        run_ids.add(line["run_id"])
        match = _inputs_match(line.get("inputs") or {})
        for row in line["belief_measurements"]:
            native = dict(row)
            if match is False:
                native["attestation_present"] = False
            out.append(native)
    if not run_ids:
        raise ProjectionError(f"not a {LINE_SCHEMA} file (no records)")
    return tuple(out)


@register(PROJECTION_NAME)
def project(native: Mapping[str, Any]) -> ClaimTuple:
    """Project one producer row. Grading stays in ``claim_tuple.grade()``."""
    if not isinstance(native, Mapping):
        raise ProjectionError("false-accept row must be a mapping")
    extra = native.get("extra")
    if not isinstance(extra, Mapping) or extra.get("belief_schema") != BELIEF_SCHEMA:
        raise ProjectionError(f"row is not a {BELIEF_SCHEMA} row")
    if native.get("metric") != METRIC:
        raise ProjectionError(f"unknown false-accept metric {native.get('metric')!r}")
    if native.get("metric_direction") != "lower_better":
        raise ProjectionError("metric_direction must be the producer-recorded lower_better")
    if str(native.get("protocol_id") or "").strip():
        raise ProjectionError("RC-6a has not merged: a false-accept rate is an observation and "
                              "may not cite a protocol")
    if native.get("attestation_sha256"):
        raise ProjectionError("the runs file is append-only; a whole-file digest cannot be true")
    if extra.get("row_sha256") != _row_digest(native):
        raise ProjectionError("row does not hash to its row_sha256 (edited after writing)")
    if extra.get("objections_projected") is not False:
        raise ProjectionError("machine objections are never projected (unverified_lead)")
    num, den = extra.get("numerator"), extra.get("denominator")
    if not (isinstance(num, int) and isinstance(den, int) and 0 <= num <= den and den >= 1):
        raise ProjectionError("numerator/denominator must be integers with 0 <= num <= den, den >= 1")
    if native.get("reps") != den:
        raise ProjectionError("reps must equal the stated denominator (scored decoys)")
    value = native.get("value")
    if not isinstance(value, (int, float)) or not math.isclose(value, num / den, abs_tol=1e-12):
        raise ProjectionError(f"value {value!r} is not numerator/denominator = {num}/{den}")
    if not str(native.get("attestation_locator", "")).endswith(f"#run={extra.get('run_id')}"):
        raise ProjectionError("locator must be the scoring run")
    unknown = set(native) - _FIELDS
    if unknown:
        raise ProjectionError(f"row carries non-ClaimTuple fields: {sorted(unknown)}")
    try:
        return ClaimTuple(**dict(native))
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"false-accept ClaimTuple grammar mismatch: {exc}") from exc


__all__ = ["ADAPTER_ID", "AUTHORITY", "BELIEF_SCHEMA", "LINE_SCHEMA", "METRIC",
           "native_rows", "project"]
