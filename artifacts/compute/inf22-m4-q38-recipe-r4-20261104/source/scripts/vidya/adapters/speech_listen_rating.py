"""Project a human speech listen/rating aggregate (VB-SPEECH-LISTEN-1).

First record: `artifacts/stt-cs8/cs8l-italian-listen-20261022.json` (CS-8.L, Italian cascade TTS,
60 clips, single labelled rater). Reusable: any aggregate with schema `epyc.<item>_listen.v<N>`
and the same field set (e.g. the re-listen after the TTS normalizer) projects the same way.

Projection only: `claim_tuple.grade()` decides, no grading rule lives here. `protocol_id` is
EMPTY, so every tuple is an observation; a single-rater rating never gates a decision alone.
One tuple per metric: naturalness mean (higher_better), intelligibility rate (higher_better),
and one count per error category (lower_better). The ASR WER cross-check is NOT projected: same
clips, so it is not an independent witness. The record is re-derived before projection (mean and
rate recomputed from the distribution/clips, category counts from their clip lists); a record
that does not re-derive is refused.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.speech_listen_rating/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "speech-listen-rating"
SCHEMA_RE = re.compile(r"^epyc\.[a-z0-9_]+_listen\.v\d+$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _problems(d: Any) -> list[str]:
    if not isinstance(d, dict):
        return ["record is not an object"]
    p: list[str] = []
    if not (isinstance(d.get("schema"), str) and SCHEMA_RE.match(d["schema"])):
        p.append("schema must match epyc.<item>_listen.v<N>")
    if d.get("protocol_id") != "":
        p.append("protocol_id must be empty (observation)")
    for k in ("item", "date", "rater", "subject"):
        if not (isinstance(d.get(k), str) and d[k].strip()):
            p.append(f"{k} missing")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(d.get("date", ""))):
        p.append("date must be YYYY-MM-DD")
    for k in ("rating_docs_sha256", "kit_manifest_sha256"):
        if not (isinstance(d.get(k), str) and _HEX64.match(d[k])):
            p.append(f"{k} must be 64 hex chars")
    n = d.get("n")
    if not (isinstance(n, int) and not isinstance(n, bool) and n > 0):
        return p + ["n must be a positive int"]
    if d.get("rating_docs_count") != n:
        p.append("rating_docs_count != n")
    clips = d.get("clips")
    if not isinstance(clips, list) or len(clips) != n:
        return p + ["clips must list exactly n entries"]
    dist = d.get("naturalness_distribution")
    try:
        if sorted(dist) != ["1", "2", "3", "4", "5"] or sum(dist.values()) != n:
            p.append("naturalness_distribution must cover 1..5 and sum to n")
        else:
            mean = sum(int(k) * v for k, v in dist.items()) / n
            if abs(mean - d.get("naturalness_mean", -1)) > 0.005:
                p.append("naturalness_mean does not re-derive from the distribution")
            got = [0] * 5
            for c in clips:
                got[c["naturalness"] - 1] += 1
            if got != [dist[str(i)] for i in range(1, 6)]:
                p.append("clip naturalness ratings disagree with the distribution")
    except (TypeError, KeyError, ValueError, IndexError, AttributeError):
        p.append("naturalness_distribution / clips malformed")
    try:
        yes = sum(1 for c in clips if c["intelligible"] == "yes")
        if d.get("intelligible_yes") != yes or abs(d.get("intelligibility_rate", -1) - yes / n) > 0.005:
            p.append("intelligibility does not re-derive from clips")
    except (TypeError, KeyError):
        p.append("clips malformed")
    cats = d.get("error_categories")
    if not isinstance(cats, dict):
        p.append("error_categories missing")
    else:
        for name, c in cats.items():
            if not (isinstance(c, dict) and isinstance(c.get("clips"), list)
                    and c.get("count") == len(c["clips"])):
                p.append(f"error_categories.{name}.count != len(clips)")
    return p


def native_rows(path: str | Path) -> tuple[dict, ...]:
    """One native per metric of one aggregate; a record that does not re-derive refuses the file."""
    p = Path(path)
    if not p.is_file():
        return ()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f"listen aggregate unreadable: {exc}") from exc
    problems = _problems(d)
    if problems:
        raise ProjectionError("listen aggregate refused: " + "; ".join(problems))
    base = {"record": d, "path": str(p), "sha256": _sha256(p)}
    out = [{**base, "metric": "naturalness_mean"}, {**base, "metric": "intelligibility_rate"}]
    out += [{**base, "metric": f"error_count:{name}"} for name in d["error_categories"]]
    return tuple(out)


@register(SOURCE_KIND)
def project(native: Any) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("record"), dict):
        raise ProjectionError("listen native row missing")
    d = native["record"]
    problems = _problems(d)
    if problems:
        raise ProjectionError("listen aggregate refused: " + "; ".join(problems))
    metric = native.get("metric", "")
    if metric == "naturalness_mean":
        value, direction, unit = d["naturalness_mean"], "higher_better", "score_1_5"
    elif metric == "intelligibility_rate":
        value, direction, unit = d["intelligibility_rate"], "higher_better", "fraction"
    elif metric.startswith("error_count:") and metric[12:] in d["error_categories"]:
        value, direction, unit = d["error_categories"][metric[12:]]["count"], "lower_better", "clips"
    else:
        raise ProjectionError(f"unknown listen metric {metric!r}")
    path = Path(native.get("path", ""))
    present = path.is_file()
    recorded = native.get("sha256", "")
    verified = present and bool(recorded) and _sha256(path) == recorded
    n = d["n"]
    mid = hashlib.sha256(f"{d['schema']}|{d['rating_docs_sha256']}|{metric}".encode()).hexdigest()[:24]
    return ClaimTuple(
        measurement_id=f"{d['item']}-listen-{d['date']}-{mid}",
        metric=f"listen_{metric.replace(':', '_')}", value=value, date=d["date"],
        category="BASELINE",
        claim=(f"{metric} = {value} {unit} ({direction}); {d['item']} human listen check, n={n} clips, "
               f"{d['rater']} [{d['date']}, observation: single-rater, no ratified protocol route]"),
        metric_direction=direction, protocol_id="", reps=n, reps_basis="scored", unit=unit,
        attestation_path=str(path) if present else "",
        attestation_sha256=recorded if verified else "",
        attestation_locator=f"{d['item']}:{metric}|{path}",
        attestation_present=present, attestation_verified=True if verified else None,
        source_kind=SOURCE_KIND,
        applicability={"surface": "human_listen"},
        extra={"schema": d["schema"], "rater": d["rater"], "subject": d["subject"],
               "n_clips": n, "item": d["item"],
               "rating_docs_sha256": d["rating_docs_sha256"],
               "kit_manifest_sha256": d["kit_manifest_sha256"], "adapter": ADAPTER_ID},
    )
