"""Prospective R18-D pp512 A/A calibration capture (VB-AK-R18D-AA-WIRE); never retrofits.

Native input: the producer's hash-chained stream `r18d-capture-<run_id>.jsonl` (schema
`epyc.autokernel.r18d.native_capture.v1`, written by the running producer, not reconstructed).
The reader re-derives the SETTLED bootstrap floor from the original eligible samples and
refuses (ProjectionError) on any pre-hook, partial, failed, retried, reordered, unbound or
unwitnessed unit. A complete campaign can still be refused as a floor. Grading is the shared
`claim_tuple.grade()`; this module carries no ladder.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

AUTHORITY = "measurement"
SOURCE_KIND = "autokernel-r18d-aa-measurement"
ADAPTER_ID = "vidya.adapters.autokernel_r18d_aa/v1"
SCHEMA = "epyc.autokernel.r18d.native_capture.v1"
MARKER = "VB-AK-R18D-AA-WIRE/v1"
CONDITIONS = (("SETTLED", 1), ("PREHEATED", 6), ("POST_BUILD", 1))
PAIRS = 20
_RESEARCH = (os.environ.get("EPYC_RESEARCH_REPO", ""), "/workspace/repos/epyc-inference-research",
             "/mnt/raid0/llm/epyc-inference-research")


def _canonical(x) -> bytes:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _bench():
    """The research repo's llama-bench row parser and bootstrap floor (the producer's own)."""
    for root in _RESEARCH:
        p = Path(root) / "scripts" / "kernel_rnd" if root else None
        if p and (p / "autokernel" / "loop" / "bench.py").is_file():
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
            from autokernel.loop import bench  # noqa: PLC0415
            return bench
    raise ProjectionError("research repo bench module unavailable; cannot rederive the floor")


def _clock_policy():
    """The research repo's ratified clock policy module and its loaded policy (band mode only).

    Fails closed: an unavailable module, a strict policy or a malformed file refuses the capture.
    """
    for root in _RESEARCH:
        p = Path(root) / "scripts" / "kernel_rnd" if root else None
        if p and (p / "autokernel" / "loop" / "clock_policy.py").is_file():
            if str(p) not in sys.path:
                sys.path.insert(0, str(p))
            from autokernel.loop import clock_policy  # noqa: PLC0415
            try:
                policy = clock_policy.load()
            except ValueError as exc:
                raise ProjectionError(f"R18-D A/A refused: clock policy unreadable: {exc}") from exc
            if not policy.is_band:
                raise ProjectionError("R18-D A/A refused: clock policy is not the ratified band")
            return clock_policy, policy
    raise ProjectionError("R18-D A/A refused: research clock_policy module unavailable")


def _require(ok, reason):
    if not ok:
        raise ProjectionError("R18-D A/A refused: " + reason)


def _derive(path) -> dict:
    path = Path(path)
    try:
        data = path.read_bytes()
        rows = [json.loads(x) for x in data.splitlines()]
    except (OSError, ValueError) as exc:
        raise ProjectionError(f"R18-D A/A refused: unreadable stream: {exc}") from exc
    try:
        return _derive_rows(path, data, rows)
    except ProjectionError:
        raise
    except (KeyError, TypeError, IndexError, ValueError, AttributeError) as exc:
        raise ProjectionError(f"R18-D A/A refused: malformed record: {type(exc).__name__}: {exc}") from exc


def _derive_rows(path, data, rows) -> dict:
    bench = _bench()
    clock_policy, band = _clock_policy()
    _require(len(rows) > 2, "unfinished stream")
    previous = None
    for i, row in enumerate(rows):
        body = dict(row)
        digest = body.pop("content_sha256")
        _require(body["schema"] == SCHEMA and body["seq"] == i and body["previous_sha256"] == previous,
                 "stream schema/order/chain mismatch")
        _require(body["run_id"] == rows[0]["run_id"] and digest == hashlib.sha256(_canonical(body)).hexdigest(),
                 "stream content mismatch")
        previous = digest
    _require(rows[0]["kind"] == "run_start" and rows[-1]["kind"] == "run_end", "missing start/end")
    context, end = rows[0]["native"], rows[-1]["native"]
    _require(context.get("prospective_capture") == MARKER, "pre-hook source")
    _require(end["disposition"] == "complete", "partial/failed/refused source is not a floor")
    ids = context["identities"]
    files = ids["files"]
    _require(all(x.get("sha256") and x.get("ino") for x in files), "missing content identities")
    model = [x for x in files if x["path"] == context["model"]]
    _require(len(model) == 1 and model[0]["sha256"] == context["model_pregrant_identity"]["sha256"],
             "model binding mismatch")
    _require(context["workload"] == {"pp": 512, "tg": 0} and context["surface"] == "pp512", "workload mismatch")
    _require(all(ids["grant"].get(k) for k in ("FILLER_ID", "FILLER_END", "FILLER_CPUS", "FILLER_THREADS")),
             "missing acquired grant context")
    claims = [r["native"] for r in rows if r["kind"] == "claim"]
    _require(len(claims) == 1 and claims[0]["owner"].get("start_ticks"), "missing actual claim witness")
    conditions = [r["native"] for r in rows if r["kind"] == "condition"]
    _require([x["condition"] for x in conditions] == [c for c, _ in CONDITIONS], "conditions missing/reordered")
    invocations = [r["native"] for r in rows if r["kind"] == "invocation"]
    values, expected_total = {}, 0
    for condition, warmup in CONDITIONS:
        events = [x for x in invocations if x["condition"] == condition]
        expected_total += (PAIRS + warmup) * 2
        _require(len(events) == (PAIRS + warmup) * 2, "missing/retried units cannot silently form a floor")
        arms = {"anchor": [], "candidate": []}
        for i, event in enumerate(events):
            phase = "warmup" if i < warmup * 2 else "scored"
            pair = i // 2 + 1 if phase == "warmup" else (i - warmup * 2) // 2 + 1
            arm = "anchor" if i % 2 == 0 else "candidate"
            _require((event["phase"], event["pair_index"], event["arm"]) == (phase, pair, arm), "unit order differs")
            _require(event["returncode"] == 0 and event["error"] is None, "failed invocation")
            _require(event["started_monotonic_s"] < event["ended_monotonic_s"], "bad invocation window")
            proof = event["residency"]
            own = proof["own_process"]
            _require(own["verified"] and own["pid"] == event["pid"],
                     "missing own-PID HIP residency")
            verdict = clock_policy.band_verdict({**proof, "backend": "gpu"}, band)
            _require(verdict["stable"], "clock outside the ratified band or no usable clock trace: "
                     + ",".join(verdict["reasons"]))
            joint = [x for x in own["joint_samples"]
                     if x.get("binary_match") and x.get("mapping", {}).get("status") == "matched"
                     and (x.get("vram_bytes") or 0) >= 1 << 30
                     and event["started_monotonic_s"] <= x["monotonic_s"] <= event["ended_monotonic_s"]]
            _require(len(joint) >= 2, "insufficient in-window observations")
            _require(all(x.get("mapped_dso_identities") for x in joint), "mapped DSO digests missing")
            for x in joint:
                _require(all(d["inode_match"] and any(f["path"] == d["path"] and f["sha256"] == d["sha256"]
                                                      for f in files) for d in x["mapped_dso_identities"]),
                         "mapped DSO identity mismatch")
            _require([f["path"] for f in files if f["path"].endswith("/llama-bench")][0] in event["argv"],
                     "executable binding mismatch")
            value = float(bench.hardened_row(event["stdout"], pp=512, tg=0, reps=9).avg_ts)
            if phase == "scored":
                arms[arm].append(value)
        native = next(x["native_result"] for x in conditions if x["condition"] == condition)
        _require(native["anchor_samples"] == arms["anchor"] and native["candidate_samples"] == arms["candidate"],
                 "native samples do not rederive from invocations")
        values[condition] = arms
    _require(len(invocations) == expected_total, "unknown condition units")
    settled = values["SETTLED"]
    floors = bench.bootstrap_floor(settled["anchor"], settled["candidate"])
    declared = end["outcome"]["bootstrap_floor_pct"]
    _require(declared == {str(k): v for k, v in floors.items()}, "settled floor mismatch")
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "run_id": rows[0]["run_id"],
            "date": rows[-1]["recorded_at_utc"], "context": context, "model": model[0], "ids": ids,
            "values": values, "floors": floors, "declared": declared,
            "protocol_id": context.get("protocol_id") or ""}


def native_rows(path):
    d = _derive(path)
    return ({"path": d["path"], "sha256": d["sha256"]},)


@register(SOURCE_KIND)
def project(row):
    d = _derive(row["path"])
    if d["sha256"] != row.get("sha256"):
        raise ProjectionError("R18-D A/A row changed")
    ctx, floors = d["context"], d["floors"]
    return ClaimTuple(
        measurement_id="r18d-aa:" + d["run_id"], metric="pp512.aa_noise_floor_pct", value=floors[PAIRS],
        unit="percent", date=d["date"], category="BASELINE",
        claim=f"SETTLED pp512 process-pair A/A bootstrap floor at {PAIRS} pairs: {floors[PAIRS]}%; calibration observation",
        metric_direction="lower_better", protocol_id=d["protocol_id"], reps=PAIRS,
        reps_basis=f"scored:{PAIRS} ordered process pairs; warmups excluded",
        attestation_path=d["path"], attestation_locator=d["path"], attestation_sha256=d["sha256"],
        attestation_present=True, attestation_verified=True, source_kind=SOURCE_KIND,
        applicability={"model_file": Path(ctx["model"]).name, "model_sha256": d["model"]["sha256"],
                       "quant": ctx["quant"], "backend": ctx["backend"], "surface": "pp512",
                       "scope_basis": "native"},
        observation={"outcome": "floor", "n_pairs": PAIRS, "noise_floor_rel": floors[PAIRS] / 100,
                     "retrofit": False},
        extra={"adapter": ADAPTER_ID, "conditions": d["values"], "bootstrap_floor_pct": d["declared"],
               "identities": d["ids"]})
