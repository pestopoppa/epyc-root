#!/usr/bin/env python3
"""Prototype AKX §7 screen over *verified, normalized* evidence.

This pure classifier does not capture evidence, verify file bytes, establish the
loaded-object inventory, or append to the campaign journal. Callers must prove
those properties before supplying a record; it is not a runnable P1c replay.
Missing or malformed proof always maps to UNKNOWN (and decision TOUCHED).
"""
from __future__ import annotations

import re
from typing import Any

_SHA = re.compile(r"^[0-9a-f]{64}$")


def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA.fullmatch(value))


def _row(classification: str, tier: str = "none", *, reason: str | None = None,
         witnesses: dict | None = None, detail: dict | None = None) -> dict:
    result = {"classification": classification,
              "decision_class": "INERT" if classification == "INERT" else "TOUCHED",
              "tier": tier, "witnesses": witnesses or {},
              "touched_detail": detail or {}}
    if reason:
        result["unknown_reason"] = reason
    return result


def classify(record: dict) -> dict:
    """Classify one already-verified footprint/census pair; never infer missing proof.

    Required input is documented in test_screen.py. `verified` flags are a trust
    boundary for the future capture adapter, not proof of verification themselves.
    No consumer should use this prototype to excuse a workload until that adapter
    validates digests, source bindings, inventories, shape completeness and paths.
    """
    try:
        return _classify(record)
    except (KeyError, TypeError, ValueError, AttributeError):
        return _row("UNKNOWN", reason="missing or malformed evidence")


def _classify(r: dict) -> dict:
    if r.get("author_target") is True:
        return _row("TOUCHED", detail={"author_target": True})
    c, f = r["census"], r["footprint"]
    shapes = c["shapes"]
    if (c["verified"] is not True or c["fresh"] is not True or c["observed"] is not True
            or not _sha(c["freshness_key"]) or not _sha(c["envelope_hash"])
            or not isinstance(shapes, list) or not shapes
            or not all(isinstance(s, str) and s for s in shapes)
            or len(set(shapes)) != len(shapes)
            or type(c["nodes_total"]) is not int or c["nodes_total"] <= 1000
            or c["expected_ops_present"] is not True or c["device_seen"] is not True):
        return _row("UNKNOWN", reason="census missing, stale, or vacuous")
    hunks, knobs = f["hunks"], f["knobs"]
    if (f["verified"] is not True or not _sha(f["sha256"]) or
            not isinstance(hunks, dict) or not isinstance(knobs, dict)):
        return _row("UNKNOWN", reason="invalid footprint")
    if f["nonempty_diff"] is True and not hunks:
        raise ValueError("empty footprint on nonempty diff")
    if type(f["nonempty_diff"]) is not bool:
        raise ValueError("unknown diff state")
    if any(not isinstance(k, str) or not k or v not in ("body", "table", "predicate", "comment")
           for k, v in hunks.items()):
        return _row("UNKNOWN", reason="unsupported hunk kind")
    if f["opaque_reasons"]:
        return _row("UNKNOWN", reason="opaque footprint")

    t0 = r.get("t0")
    if isinstance(t0, dict) and t0.get("verified") is True:
        a, b = t0.get("anchor_objects"), t0.get("candidate_objects")
        if (isinstance(a, dict) and a and isinstance(b, dict)
                and all(isinstance(k, str) and k and _sha(v) for k, v in a.items())
                and all(isinstance(k, str) and k and _sha(v) for k, v in b.items())
                and a == b and _sha(t0.get("anchor_recipe"))
                and t0["anchor_recipe"] == t0.get("candidate_recipe")
                and _sha(t0.get("anchor_env")) and t0["anchor_env"] == t0.get("candidate_env")):
            return _row("INERT", "T0", witnesses={"anchor_objects": a,
                "candidate_objects": b, "recipe": t0["anchor_recipe"], "env": t0["anchor_env"]})
    if f.get("change_class") == "build" and r["variant"] in f["variants_affected"]:
        return _row("TOUCHED", detail={"affected_variant": r["variant"]})
    t1 = r.get("t1")
    if any(not isinstance(name, str) or not name or not isinstance(k, dict)
           or not isinstance(k.get("before"), str) or not isinstance(k.get("after"), str)
           for name, k in knobs.items()):
        raise ValueError("knob defaults unknown")
    flips = [name for name, k in knobs.items() if k["before"] != k["after"]]
    if not isinstance(t1, dict) or t1.get("verified") is not True:
        if flips:
            return _row("TOUCHED", detail={"potential_knob_reads": flips, "coverage_unavailable": True})
        return _row("UNKNOWN", reason="coverage unavailable")
    if (not _sha(t1["anchor_profile_sha256"]) or not _sha(t1["candidate_profile_sha256"])
            or t1["envelope_hash"] != c["envelope_hash"] or set(t1["shapes"]) != set(shapes)):
        return _row("UNKNOWN", reason="unbound coverage or incomplete shape envelope")
    changed_hunks, changed_branches, changed_routes, changed_knobs = set(), set(), set(), set()
    for shape in shapes:
        s = t1["shapes"][shape]
        if (type(s["anchor_lines"]) is not int or s["anchor_lines"] <= 0 or
                type(s["candidate_lines"]) is not int or s["candidate_lines"] <= 0
                or set(s["hunks"]) != set(hunks) or set(s["knobs"]) != set(knobs)):
            return _row("UNKNOWN", reason="vacuous or incomplete coverage")
        for h, kind in hunks.items():
            evidence = s["hunks"][h]
            if type(evidence["executed"]) is not bool:
                raise ValueError("hunk execution unknown")
            if kind in ("body", "table") and evidence["executed"]:
                changed_hunks.add(h)
            if kind == "predicate" and evidence["executed"]:
                a, b = evidence["anchor_branches"], evidence["candidate_branches"]
                if not isinstance(a, list) or not a or not isinstance(b, list) or not b:
                    raise ValueError("branch vectors missing")
                if any(type(v) is not int or v < 0 for v in a + b):
                    raise ValueError("invalid branch counts")
                if a != b:
                    changed_branches.add(h)
        for name in knobs:
            k = s["knobs"][name]
            if type(k["executed"]) is not bool:
                raise ValueError("knob read unknown")
            if k["executed"]:
                if not all(isinstance(k[x], str) for x in ("anchor_value", "candidate_value")):
                    raise ValueError("knob value unknown")
                if name in flips or k["anchor_value"] != k["candidate_value"]:
                    changed_knobs.add(name)
        for key in ("hip_matmul_routes", "op_backend"):
            a, b = s["anchor_" + key], s["candidate_" + key]
            if not isinstance(a, dict) or not isinstance(b, dict):
                raise ValueError("histogram unknown")
            if key == "op_backend" and (not a or not b):
                raise ValueError("vacuous op/backend histogram")
            if any(not isinstance(k, str) or not k or type(v) is not int or v < 0
                   for hist in (a, b) for k, v in hist.items()):
                raise ValueError("invalid histogram")
            if a != b:
                changed_routes.add(shape + ":" + key)
    detail = {"executed_hunks": sorted(changed_hunks), "changed_branches": sorted(changed_branches),
              "changed_routes": sorted(changed_routes), "knob_reads": sorted(changed_knobs)}
    witnesses = {"anchor_profile_sha256": t1["anchor_profile_sha256"],
                 "candidate_profile_sha256": t1["candidate_profile_sha256"],
                 "shape_envelope_hash": c["envelope_hash"]}
    if any(detail.values()):
        return _row("TOUCHED", "T1", detail=detail, witnesses=witnesses)
    return _row("INERT", "T1", witnesses=witnesses)
