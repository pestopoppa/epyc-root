"""Per-surface accumulator card (``/loop``, AKU-18) - read-only.

Plane rule: the data contract ``epyc.autokernel.accumulator_surfaces.v1`` is owned by the
AutoKernel subsystem (``loop/accumulator_surfaces.py`` in epyc-inference-research publishes it).
This module only READS it. It never recomputes a fire decision and never edits the schema.

One rule is enforced here because it is the point of the card: a figure that is an ESTIMATE
(the product of solo keep effects, or a stale snapshot) must carry the ESTIMATE label. A record
that presents one without it is refused, never relabelled, so the page cannot launder an
estimate into a measurement.

Freshness is the record's own ``generated_at``: the publisher is a CLI run, so a record nobody
re-ran ages into stale rather than staying green.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

SCHEMA = "epyc.autokernel.accumulator_surfaces.v1"
RECORD_PATH = Path(os.environ.get(
    "AK_ACC_SURFACES_JSON", "/mnt/raid0/llm/tmp/ak-accumulator-surfaces/accumulator_surfaces.json"))
DECISIONS = ("fire", "accumulate", "cannot_decide")
KINDS = ("measured", "estimate", "none")


def _refuse(msg: str) -> dict:
    return {"present": False, "error": msg}


def _check_surface(s) -> Optional[str]:
    if not isinstance(s, dict) or not isinstance(s.get("surface"), str):
        return "surface entry malformed"
    name = s["surface"]
    fire, fig = s.get("fire"), s.get("figure")
    if not isinstance(fire, dict) or fire.get("decision") not in DECISIONS:
        return f"{name}: fire decision missing or unknown"
    if not isinstance(fig, dict) or fig.get("kind") not in KINDS:
        return f"{name}: figure kind missing or unknown"
    if fig["kind"] == "estimate" and not str(fig.get("label", "")).startswith("ESTIMATE"):
        return f"{name}: an estimate figure without the ESTIMATE label"
    for fe in s.get("fold_estimates") or []:
        if not str(fe.get("label", "")).startswith("ESTIMATE"):
            return f"{name}: a fold estimate without the ESTIMATE label"
    return None


def build(path: Path | str | None = None) -> dict:
    p = Path(path) if path else RECORD_PATH
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return _refuse(f"accumulator surfaces record unreadable: {type(exc).__name__}")
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA \
            or not isinstance(raw.get("surfaces"), list):
        return _refuse("accumulator surfaces record has an unknown schema")
    for s in raw["surfaces"]:
        bad = _check_surface(s)
        if bad:
            return _refuse(f"accumulator surfaces record refused: {bad}")
    return {"present": True, "schema": SCHEMA, "generated_at": raw.get("generated_at"),
            "surfaces": raw["surfaces"], "evidence": str(p)}
