"""VB-HIL17-WRITE: HIL-17 attribution-ladder tables as measurement OBSERVATIONS.

Source: the orchestrator driver ``scripts/trace/attribution_ladder.py`` (``src/trace/attribution/``)
writes ONE report JSON per run: a per-rung accuracy / token table (``rungs``) and, unless
``--no-aggregate``, an aggregated nDCG@5 table (``aggregate``: k-sample vs temperature-0 vs the
random baselines). The report JSON is the attested artifact; every number is copied from it.

Doctrine, in the order it bites:

* PROJECTION ONLY. The writer copies values out of the report (the caller authors no number); the
  reader re-validates and projects into a ``ClaimTuple``; ``claim_tuple.grade()`` decides. No ladder.
* ``protocol_id`` is ALWAYS the empty string. No ratified protocol applies to an attribution-ladder
  table, and the literal ``"observation:none"`` is a known bug pattern (it is a non-empty string that
  reads as a citation). An empty id lets ``grade()`` downgrade the tuple to an OBSERVATION itself.
* A ``mock: true`` report (the ``--dry-run`` fixture + heuristic fake judge) is REFUSED, as is any
  report that does not say ``"mock": false`` explicitly, one with no labelled case, and one without
  the slice-manifest sha256, the code ref and the judge identities (name, family, quantised flag).
* The judge identity, ``policy``, ``with_reference``, ``k`` and ``temperature`` are part of the
  measurand and of ``measurement_id``: two judges (or the reference-on setting) are two claims.
* ``metric_direction`` is the natural one (accuracy and nDCG higher_better; abstain rate and tokens
  lower_better). ``category`` is a carrier label only: rung0 (the existing L2 scan) and the random /
  temperature-0 aggregate arms are BASELINE, the LLM rungs, the ladder's final answer and the
  k-sample arm are CANDIDATE.
* Rungs that ran on zero cases and rates that are ``None`` yield no row, never a zero.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ProjectionError, register, to_frames  # noqa: E402

from adapters import _native_sidecar as ns  # noqa: E402
from adapters._native_sidecar import CaptureError  # noqa: E402,F401

CAPTURE_SCHEMA = "epyc.vidya.hil17_attribution_capture.v1"
SIDECAR_NAME = "hil17_attribution.beliefs.jsonl"
ADAPTER_ID = "vidya.adapters.hil17_attribution/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "hil17-attribution-ladder"
GIT_SHA = re.compile(r"^[0-9a-f]{40}$")

RUNG_BASELINE = frozenset({"rung0_l2"})
#: rung-table metric -> (direction, unit, count field of the rung row that is its n)
RUNG_METRICS = {
    "exact": ("higher_better", "fraction of labelled cases, pick = a top-consensus step", "N"),
    "within1": ("higher_better", "fraction of labelled cases, pick within 1 step of consensus", "N"),
    "hit": ("higher_better", "fraction of labelled cases, pick = any flagged step", "N"),
    "abstain": ("lower_better", "fraction of labelled cases with no pick", "N"),
    "agent_acc": ("higher_better", "fraction of cases with a gold agent set, pick's agent correct",
                  "agent_N"),
    "tokens_per_case_all": ("lower_better", "mean tokens per labelled case, all cases", "@n_labelled"),
}
AGG_ARMS = {  # aggregate key stem -> category
    "ksample": "CANDIDATE", "temp0": "BASELINE",
    "random_expected": "BASELINE", "random_mc": "BASELINE",
}
AGG_KINDS = ("exp", "linear")
RUNG_FIELDS = ("rung", "N", "ran_on", "ran_share", "exact", "within1", "hit", "abstain",
               "agent_acc", "agent_N", "calls", "prompt_tokens", "completion_tokens",
               "total_tokens", "calls_without_usage", "tokens_per_case_ran", "tokens_per_case_all")


def _load_report(path: Path) -> dict:
    try:
        rep = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CaptureError(f"HIL-17 report unreadable: {exc}") from exc
    if not isinstance(rep, dict):
        raise CaptureError("HIL-17 report must be a JSON object")
    if rep.get("mock") is not False:
        raise CaptureError("refusing a report that does not carry \"mock\": false (the --dry-run "
                           "fixture + fake judge measures plumbing only)")
    for key in ("scope", "judges", "ladder_judge", "policy", "with_reference", "code_ref",
                "n_cases", "n_labelled", "rungs"):
        if key not in rep:
            raise CaptureError(f"HIL-17 report lacks producer field {key!r}")
    if not (ns.nonneg_int(rep["n_labelled"]) and rep["n_labelled"] > 0):
        raise CaptureError("HIL-17 report has no labelled case: picks and tokens only, no accuracy")
    if not (isinstance(rep["scope"], dict) and ns.SHA256.match(str(rep["scope"].get("sha256", "")))):
        raise CaptureError("HIL-17 report scope lacks the slice-manifest sha256 (--cases / --step-db "
                           "sets carry no digest, so they cannot be attested)")
    if not GIT_SHA.match(str(rep["code_ref"])):
        raise CaptureError("HIL-17 report code_ref must be a 40-hex commit")
    return rep


def judge_problems(judges: Any, ladder: Any, where: str = "extra.judges") -> list[str]:
    if not (isinstance(judges, list) and judges):
        return [f"{where} must be a non-empty list"]
    p = []
    for j in judges:
        if not (isinstance(j, dict) and ns.text(j.get("name")) and ns.text(j.get("family"))
                and "quantised" in j and (j["quantised"] is None or isinstance(j["quantised"], bool))):
            p.append(f"{where} entries need name, family and a quantised flag")
            break
    if not any(isinstance(j, dict) and j.get("name") == ladder for j in judges):
        p.append("extra.ladder_judge must be one of extra.judges")
    if any(isinstance(j, dict) and j.get("family") == "fake" for j in judges):
        p.append("a fake (dry-run) judge can never be attested")
    return p


def _common_extra(rep: dict) -> dict:
    scope = rep["scope"]
    return {
        "set": rep.get("set"), "scope_sha256": scope["sha256"], "scope_path": scope.get("path"),
        "slice": scope.get("slice"), "skipped": scope.get("skipped"),
        "judges": rep["judges"], "ladder_judge": rep["ladder_judge"], "policy": rep["policy"],
        "with_reference": rep["with_reference"], "code_ref": rep["code_ref"],
        "n_cases": rep["n_cases"], "n_labelled": rep["n_labelled"],
    }


def validate_row(row: Any) -> list[str]:
    p = ns.common_problems(row, schema=CAPTURE_SCHEMA, optional_text=("protocol_id",))
    if not isinstance(row, dict) or not isinstance(row.get("extra"), dict):
        return p
    e = row["extra"]
    if row.get("protocol_id") != "":
        p.append("protocol_id must be empty: no ratified protocol applies, the tuple is an "
                 "OBSERVATION (\"observation:none\" is a known bug pattern)")
    if e.get("part") not in ("rung", "aggregate"):
        return p + ["extra.part must be rung or aggregate"] + ns.self_hash_problems(row)
    if not ns.SHA256.match(str(e.get("scope_sha256", ""))):
        p.append("extra.scope_sha256 must be a 64-hex slice-manifest digest")
    if not GIT_SHA.match(str(e.get("code_ref", ""))):
        p.append("extra.code_ref must be a 40-hex commit")
    p += judge_problems(e.get("judges"), e.get("ladder_judge"))
    if e.get("policy") not in ("calibrate", "escalate"):
        p.append("extra.policy must be calibrate or escalate")
    if not isinstance(e.get("with_reference"), bool):
        p.append("extra.with_reference must be a boolean")
    if not (ns.nonneg_int(e.get("n_labelled")) and e["n_labelled"] > 0):
        p.append("extra.n_labelled must be a positive integer")
    if e["part"] == "rung":
        cell = e.get("cell")
        if not isinstance(cell, dict) or set(cell) != set(RUNG_FIELDS):
            return p + ["extra.cell must be exactly the rung-table row fields"] + \
                ns.self_hash_problems(row)
        if row.get("metric") not in {f"hil17_{m}" for m in RUNG_METRICS}:
            p.append("metric is not a rung metric")
        else:
            m = row["metric"][len("hil17_"):]
            direction, _, nfield = RUNG_METRICS[m]
            if cell.get(m) is None or row.get("value") != cell[m]:
                p.append(f"value must equal extra.cell.{m} (non-null)")
            want_n = e.get("n_labelled") if nfield == "@n_labelled" else cell[nfield]
            if row.get("reps") != want_n or not want_n:
                p.append(f"reps must equal {nfield} (> 0)")
            if row.get("metric_direction") != direction:
                p.append(f"metric_direction must be {direction}")
        want = "BASELINE" if cell.get("rung") in RUNG_BASELINE else "CANDIDATE"
        if row.get("category") != want:
            p.append(f"category must be {want} for rung {cell.get('rung')}")
        ident = {"rung": cell.get("rung")}
    else:
        agg = e.get("arm")
        m = re.fullmatch(r"hil17_ndcg5_(ksample|temp0|random_expected|random_mc)_(exp|linear)",
                         str(row.get("metric")))
        if not m:
            p.append("metric is not an aggregate nDCG@5 metric")
        else:
            if row.get("category") != AGG_ARMS[m.group(1)]:
                p.append(f"category must be {AGG_ARMS[m.group(1)]}")
            if row.get("metric_direction") != "higher_better":
                p.append("metric_direction must be higher_better")
        if not (ns.finite(e.get("k_per_family")) and ns.finite(e.get("temperature"))):
            p.append("extra.k_per_family and extra.temperature must be numbers")
        if not ns.nonneg_int(row.get("reps")) or not row.get("reps"):
            p.append("reps must be the positive case count behind the metric")
        ident = {"arm": f"{agg}_{e.get('kind')}"}
    if not p:
        p += ns.check_identity(row, {
            "run_id": row["run_id"], "part": e["part"], **ident, "metric": row["metric"],
            "judges": e["judges"], "policy": e["policy"], "with_reference": e["with_reference"],
            "results": row["results_sha256"]}, "hil17")
    return p + ns.self_hash_problems(row)


def _row(rep, raw, digest, when, *, run_id, producer, part, metric, value, unit, direction,
         category, reps, reps_basis, extra, ident) -> dict:
    row = {
        "schema": CAPTURE_SCHEMA, "run_id": run_id, "producer": producer, "emitted_at": when,
        "date": when[:10], "metric": metric, "value": value, "unit": unit,
        "metric_direction": direction, "category": category,
        "claim": (f"HIL-17 {run_id}: {ident.get('rung') or ident.get('arm')} {metric}={value} on "
                  f"{rep.get('set')} (n_labelled={rep['n_labelled']}, ladder judge "
                  f"{rep['ladder_judge']}, policy {rep['policy']}, with_reference="
                  f"{rep['with_reference']}); descriptive table, no ratified protocol"),
        "protocol_id": "", "reps": reps, "reps_basis": reps_basis,
        "results_path": str(raw), "results_sha256": digest,
        "extra": {"part": part, **_common_extra(rep), **extra},
    }
    row["measurement_id"] = "hil17_" + ns.content_hash({
        "run_id": run_id, "part": part, **ident, "metric": metric, "judges": rep["judges"],
        "policy": rep["policy"], "with_reference": rep["with_reference"], "results": digest})[:24]
    ns.seal(row)
    bad = validate_row(row)
    if bad:
        raise CaptureError("refusing to emit an invalid row: " + "; ".join(bad))
    return row


def write_belief_measurements(out_dir: str | Path, *, run_id: str, producer: str,
                              results_path: str | Path, emitted_at: str | None = None) -> Path:
    """Emit ``hil17_attribution.beliefs.jsonl`` from a finished (non-mock, labelled) report."""
    raw = Path(results_path)
    rep = _load_report(raw)
    bad = judge_problems(rep["judges"], rep["ladder_judge"])
    if bad:
        raise CaptureError("; ".join(bad))
    digest = ns.file_sha256(raw)
    when = emitted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for cell in rep["rungs"]:
        if not (isinstance(cell, dict) and set(cell) == set(RUNG_FIELDS)):
            raise CaptureError("rung row must carry exactly the producer rung-table fields")
        for m, (direction, unit, nfield) in RUNG_METRICS.items():
            n = rep["n_labelled"] if nfield == "@n_labelled" else cell[nfield]
            if cell[m] is None or not n:
                continue
            if m == "tokens_per_case_all" and not cell["calls"]:
                continue  # rung0 makes no model call: a tokens row would be a vacuous zero
            rows.append(_row(
                rep, raw, digest, when, run_id=run_id, producer=producer, part="rung",
                metric=f"hil17_{m}", value=cell[m], unit=unit, direction=direction,
                category="BASELINE" if cell["rung"] in RUNG_BASELINE else "CANDIDATE",
                reps=n, reps_basis="scored:cases with a gold agent set" if nfield == "agent_N"
                else "scored:labelled cases",
                extra={"cell": {k: cell[k] for k in RUNG_FIELDS}}, ident={"rung": cell["rung"]}))
    agg = rep.get("aggregate")
    if isinstance(agg, dict):
        for stem, cat in AGG_ARMS.items():
            for kind in AGG_KINDS:
                key = f"{stem}_{kind}"
                if agg.get(key) is None or not agg.get(f"{key}_N"):
                    continue
                rows.append(_row(
                    rep, raw, digest, when, run_id=run_id, producer=producer, part="aggregate",
                    metric=f"hil17_ndcg5_{key}", value=agg[key], unit=f"nDCG@5 ({kind} gain), mean over cases",
                    direction="higher_better", category=cat, reps=agg[f"{key}_N"],
                    reps_basis="scored:labelled cases",
                    extra={"arm": stem, "kind": kind, "k_per_family": agg.get("k_per_family"),
                           "temperature": agg.get("temperature"), "per_family": agg.get("per_family"),
                           "tokens_ksample_per_case": agg.get("tokens_ksample_per_case"),
                           "tokens_temp0_per_case": agg.get("tokens_temp0_per_case")},
                    ident={"arm": f"{stem}_{kind}"}))
    if len({r["measurement_id"] for r in rows}) != len(rows):
        raise CaptureError("duplicate rung/arm x metric observation")
    if not rows:
        raise CaptureError("the report yields no gradeable row")
    return ns.write_rows_atomic(Path(out_dir) / SIDECAR_NAME, rows)


def native_rows(sidecar_path: str | Path) -> tuple[dict, ...]:
    return ns.native_rows(sidecar_path, validate_row)


@register(SOURCE_KIND)
def project(native: Any):
    if not isinstance(native, dict) or not isinstance(native.get("row"), dict):
        raise ProjectionError("HIL-17 native row must retain the producer row")
    row = native["row"]
    problems = validate_row(row)
    if problems:
        raise ProjectionError("HIL-17 row is not a producer-authored capture: " + "; ".join(problems))
    e = row["extra"]
    unit_id = e["cell"]["rung"] if e["part"] == "rung" else f"{e['arm']}_{e['kind']}"
    locator = f"hil17:{row['run_id']}:{unit_id}:{row['metric']}:{row['results_path']}"
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator=locator,
                             sidecar_path=native.get("sidecar_path", ""))


def frames_for_sidecar(sidecar_path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(sidecar_path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames
