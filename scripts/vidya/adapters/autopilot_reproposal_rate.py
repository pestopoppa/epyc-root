"""Project VB-AP53-RATE per-window AutoPilot re-proposal rates into ``ClaimTuple``.

Write side (producer): epyc-orchestrator ``scripts/autopilot/reproposal_rate.py``.
At each trial boundary, AutoPilot calls ``record_closed_windows(journal)``, which
appends one ``epyc.autopilot.reproposal_rate.v1`` line per closed trial-id window to
``orchestration/autopilot_reproposal_rates.jsonl``. Each line carries its counts,
the key/rejection-class definitions (plus a sha256 over their source), the journal
and mutation-ledger prefix identities, and producer-authored
``belief_measurements`` rows. Three metrics can appear:

* ``autopilot.reproposal_rate.all_trials``: re-proposals / every trial in the window;
* ``autopilot.reproposal_rate.keyed_trials``: re-proposals / trials with a config key;
* ``autopilot.rejected_mutation.diff_repeat_rate``: AP-53 ledger records repeating an
  already-rejected exact diff / ledger records in the window.

This adapter PROJECTS those rows. Every tuple is graded by ``claim_tuple.grade()``,
and the rows cite no protocol, so each is an OBSERVATION. The reader is strict:

* **Locator = the window**, never a single trial or rejection record.
* **Pre-hook data projects nothing.** The file's first record is ``armed``. A window
  line that starts before ``armed_from_trial``, or appears before any ``armed``
  record, voids the file. A ``retrospective`` line (the offline ``backfill``) is
  accepted only with ZERO belief rows, and it contributes none: pilot spec section
  4.7, "a row that predates a producer's provenance hook is skipped rather than
  back-filled".
* **Everything re-derives.** Each line's sha256 is checked, each row's sha256 is
  checked, ``value == numerator / denominator``, ``reps == denominator``, and every
  numerator and denominator must match the line's own counts. One bad line voids the
  file, so it is refused whole, never partly projected.
* The journal grows, so no whole-file digest is claimed. The prefix digests stay in
  the line and are never lifted into ``attestation_sha256``.
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

ADAPTER_ID = "vidya.adapters.autopilot_reproposal_rate/v1"
#: Frame authority scope: a protocol-less loop observation in the measurement class.
AUTHORITY = "measurement"
PROJECTION_NAME = "autopilot_reproposal_rate"
LINE_SCHEMA = "epyc.autopilot.reproposal_rate.v1"
BELIEF_SCHEMA = "epyc.autopilot.reproposal_rate_belief.v1"
METRIC_ALL = "autopilot.reproposal_rate.all_trials"
METRIC_KEYED = "autopilot.reproposal_rate.keyed_trials"
METRIC_DIFF_REPEAT = "autopilot.rejected_mutation.diff_repeat_rate"
METRICS = frozenset({METRIC_ALL, METRIC_KEYED, METRIC_DIFF_REPEAT})
_FIELDS = frozenset(ClaimTuple.__dataclass_fields__)


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _row_digest(row: Mapping[str, Any]) -> str:
    body = json.loads(_canon(row))
    body.get("extra", {}).pop("row_sha256", None)
    return _sha(_canon(body))


def _expected(line: Mapping[str, Any], metric: str) -> tuple[int, int]:
    counts, ledger = line["counts"], line["ledger_counts"]
    if metric == METRIC_ALL:
        return counts["reproposals"], counts["all_trials"]
    if metric == METRIC_KEYED:
        return counts["reproposals"], counts["keyed_trials"]
    return ledger["diff_repeats"], ledger["records"]


def _check_line(line: Mapping[str, Any], armed_from: int, size: int) -> None:
    body = dict(line)
    if body.pop("line_sha256", None) != _sha(_canon(body)):
        raise ProjectionError("rate line does not hash to its line_sha256 (edited after writing)")
    window = line.get("window") or {}
    start, wsize = window.get("start"), window.get("size")
    if not isinstance(start, int) or wsize != size or window.get("end_exclusive") != start + size:
        raise ProjectionError(f"window {window!r} does not match the armed window size {size}")
    if start < armed_from or line.get("armed_from_trial") != armed_from:
        raise ProjectionError(
            f"pre-hook window {start} (armed from trial {armed_from}); pre-hook data is never "
            "projected (vidya-pilot-spec section 4.7)")
    c = line.get("counts") or {}
    if not (0 <= c.get("reproposals", -1) <= c.get("keyed_trials", -1) <= c.get("all_trials", -1)):
        raise ProjectionError("counts are incoherent: need reproposals <= keyed <= all")
    if sum((c.get("reproposals_by_action_type") or {}).values()) != c["reproposals"]:
        raise ProjectionError("reproposals_by_action_type does not sum to reproposals")
    rows = line.get("belief_measurements")
    if not isinstance(rows, list):
        raise ProjectionError("window line carries no belief_measurements list")
    metrics = [r.get("metric") for r in rows]
    if len(metrics) != len(set(metrics)):
        raise ProjectionError("a window line repeats a metric")
    for row in rows:
        extra = row.get("extra") or {}
        num, den = _expected(line, row.get("metric"))
        if (extra.get("numerator"), extra.get("denominator")) != (num, den) or den < 1:
            raise ProjectionError(
                f"{row.get('metric')}: numerator/denominator do not match the line's counts")
        if extra.get("window") != dict(window):
            raise ProjectionError("row window differs from its line's window")
        if extra.get("fold_sha256") != c.get("fold_sha256"):
            raise ProjectionError("row fold_sha256 differs from its line's fold")
        if extra.get("definition_sha256") != line.get("definition_sha256"):
            raise ProjectionError("row definition_sha256 differs from its line's")
    # A denominator > 0 with no row is a silently dropped rate.
    present = set(metrics)
    for metric in METRICS:
        if _expected(line, metric)[1] > 0 and metric not in present:
            raise ProjectionError(f"window {start}: {metric} has a denominator but no row")


def native_rows(path: str | Path) -> tuple[dict[str, Any], ...]:
    """Read one rate file strictly. Returns producer rows from post-hook windows only."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ProjectionError(f"re-proposal rate file unreadable: {exc}") from exc
    raw_lines = text.splitlines()
    if raw_lines and not text.endswith("\n"):
        # An fsync'd append interrupted mid-write leaves an unterminated tail. It is not a
        # record; skip it only if it does not parse. Any other malformed line voids the file.
        try:
            json.loads(raw_lines[-1])
        except ValueError:
            raw_lines = raw_lines[:-1]
    lines = []
    for n, raw in enumerate(raw_lines, 1):
        if not raw.strip():
            continue
        try:
            line = json.loads(raw)
        except ValueError as exc:
            raise ProjectionError(f"line {n}: not JSON ({exc}); a torn file is refused") from exc
        if not isinstance(line, dict) or line.get("schema") != LINE_SCHEMA:
            raise ProjectionError(f"line {n}: not a {LINE_SCHEMA} record")
        lines.append(line)
    if not lines:
        raise ProjectionError(f"not a {LINE_SCHEMA} file (no records)")

    armed_from: int | None = None
    size: int | None = None
    seen: set[int] = set()
    out: list[dict[str, Any]] = []
    for line in lines:
        kind = line.get("record")
        if kind == "armed":
            if armed_from is None:
                armed_from, size = int(line["armed_from_trial"]), int(line["window_size"])
            continue
        if line.get("retrospective") is True or kind == "retrospective_window":
            if kind != "retrospective_window" or line.get("retrospective") is not True:
                raise ProjectionError("a retrospective line must say so in both fields")
            if line.get("belief_measurements"):
                raise ProjectionError(
                    "retrospective line carries belief rows; pre-hook windows get zero rows "
                    "(vidya-pilot-spec section 4.7)")
            continue
        if kind != "window":
            raise ProjectionError(f"unknown record kind {kind!r}")
        if armed_from is None or size is None:
            raise ProjectionError("window line before any armed record: pre-hook, refused")
        _check_line(line, armed_from, size)
        start = line["window"]["start"]
        if start in seen:
            raise ProjectionError(f"window {start} recorded twice")
        seen.add(start)
        out.extend(dict(r) for r in line["belief_measurements"])
    return tuple(out)


@register(PROJECTION_NAME)
def project(native: Mapping[str, Any]) -> ClaimTuple:
    """Project one producer row. Grading stays in ``claim_tuple.grade()``."""
    if not isinstance(native, Mapping):
        raise ProjectionError("re-proposal rate row must be a mapping")
    extra = native.get("extra")
    if not isinstance(extra, Mapping) or extra.get("belief_schema") != BELIEF_SCHEMA:
        raise ProjectionError(f"row is not a {BELIEF_SCHEMA} row")
    if native.get("metric") not in METRICS:
        raise ProjectionError(f"unknown re-proposal metric {native.get('metric')!r}")
    if native.get("metric_direction") != "lower_better":
        raise ProjectionError("metric_direction must be the producer-recorded lower_better")
    if str(native.get("protocol_id") or "").strip():
        raise ProjectionError("no codified protocol covers the loop re-proposal rate; a row "
                              "citing one was not written by this producer")
    if native.get("attestation_sha256"):
        raise ProjectionError("the journal grows, so a whole-file digest cannot be true")
    if extra.get("row_sha256") != _row_digest(native):
        raise ProjectionError("row does not hash to its row_sha256 (edited after writing)")
    num, den = extra.get("numerator"), extra.get("denominator")
    if not (isinstance(num, int) and isinstance(den, int) and 0 <= num <= den and den >= 1):
        raise ProjectionError("numerator/denominator must be integers with 0 <= num <= den, den >= 1")
    if native.get("reps") != den:
        raise ProjectionError("reps must equal the stated denominator")
    value = native.get("value")
    if not isinstance(value, (int, float)) or not math.isclose(value, num / den, abs_tol=1e-12):
        raise ProjectionError(f"value {value!r} is not numerator/denominator = {num}/{den}")
    window = extra.get("window") or {}
    if not isinstance(window.get("start"), int) or not str(native.get("measurement_id", "")).startswith(
            f"ap53-rate-w{window.get('size')}-{window['start']:07d}-"):
        raise ProjectionError("measurement_id does not name the row's window")
    unknown = set(native) - _FIELDS
    if unknown:
        raise ProjectionError(f"row carries non-ClaimTuple fields: {sorted(unknown)}")
    try:
        return ClaimTuple(**dict(native))
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"re-proposal rate ClaimTuple grammar mismatch: {exc}") from exc


__all__ = ["ADAPTER_ID", "AUTHORITY", "BELIEF_SCHEMA", "LINE_SCHEMA", "METRICS",
           "native_rows", "project"]
