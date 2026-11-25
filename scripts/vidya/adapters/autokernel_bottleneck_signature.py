"""AutoKernel bottleneck signatures as Located observations (VB-AK-BNSIG-WIRE, AK-BNSIG-P3).

Native source: the bandwidth census `mi210_bandwidth_census.json` (schema `epyc.autokernel.bw_census.v1`),
`records[k].signature` -- written by research `scripts/kernel_rnd/autokernel/loop/census_update.py`
`apply_signature` (AK-BNSIG P1) from a counter-diag row RESULT classified by `bottleneck_signature.py`
against the stream references S16 (healthy) / S64 (over-subscribed).

PROJECTION ONLY. One tuple per (kernel record x build x fired class): the class's evidence axis is the
value (over_fetch -> fetch_over_bytes, over_subscribed -> mem_stalled band position, issue_bound ->
issue_busy, latency_bound -> wait_any, not_in_flight / healthy_bw -> achieved GB/s over S16). BASELINE,
no protocol, so `claim_tuple.grade()` says `Judged/Located`: an observation, never decision-gating.
No ladder and no grade here.

Warrant: the signature's OWN `source_row`, `result_sha256`, `measured_at` (it may come from a different
row than the record's timing). Missing any of the three -> UNKNOWN, dropped, never filled. The row must
be in the census `signature_applied` ledger and its sha must agree with that entry, else REFUSED
(`extra.applied_bound` records the binding). A signature whose
reference self-check failed (`reference_check.ok` false, classes harness / reference_incoherent) states
no limiter and is REFUSED by name. `build` is carried when the write side recorded it and is otherwise
`unknown` -- never invented.

Write-side, not retrofit: the warrant is captured by `apply_signature` at write time, so
`observation.retrofit` is False.
"""
from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402
from adapters.autokernel_bw_census import (  # noqa: E402
    _HEX64, _ISO_DATE, CENSUS_SCHEMA, LIVE_CENSUS, _text, read_census)

ADAPTER_ID = "vidya.adapters.autokernel_bottleneck_signature/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "autokernel-bottleneck-signature"
SIGNATURE_SCHEMA = "epyc.autokernel.bottleneck_signature.v1"
MEASUREMENT_PREFIX = "ak-bnsig:v1:"
LOCATOR_PREFIX = "autokernel-bottleneck-signature:"
#: class -> (axis source, axis name, direction). "band" reads band_position, "axes" the raw axis,
#: "bw" the signature's achieved GB/s over S16.
CLASS_AXIS = {
    "over_fetch": ("axes", "fetch_over_bytes", "lower_better"),
    "over_subscribed": ("band", "mem_stalled", "lower_better"),
    "issue_bound": ("axes", "issue_busy", "lower_better"),
    "latency_bound": ("axes", "wait_any", "lower_better"),
    "not_in_flight": ("bw", "bw_frac_of_s16", "higher_better"),
    "healthy_bw": ("bw", "bw_frac_of_s16", "higher_better"),
}
NON_LIMITER = frozenset({"harness", "reference_incoherent", "unclassified"})


def _finite(v: Any) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def _warrant_missing(sig: dict) -> list[str]:
    return [n for n in ("source_row", "result_sha256", "measured_at") if not _text(sig.get(n))]


def _sig_applied(document: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for e in document.get("signature_applied") or []:
        if isinstance(e, dict) and _text(e.get("row")) and _text(e.get("sha256")):
            out.setdefault(_text(e["row"]), set()).add(_text(e["sha256"]))
    return out


def _checked(key: str, rec: dict, applied: set[str] | None) -> dict:
    sig = rec.get("signature") if isinstance(rec, dict) else None
    if not isinstance(sig, dict):
        raise ProjectionError(f"census record {key!r} carries no signature object")
    missing = _warrant_missing(sig)
    if missing:
        raise ProjectionError(f"signature of {key!r} carries no {'/'.join(missing)}: UNKNOWN warrant")
    row, sha, at = _text(sig["source_row"]), _text(sig["result_sha256"]), _text(sig["measured_at"])
    if not _HEX64.fullmatch(sha):
        raise ProjectionError(f"signature of {key!r} result_sha256 is not a 64-hex digest")
    if not _ISO_DATE.fullmatch(at):
        raise ProjectionError(f"signature of {key!r} measured_at {at!r} is not an ISO date")
    if not applied:
        raise ProjectionError(f"signature of {key!r} row {row!r} is absent from the census `signature_applied` "
                              "ledger: the write side never applied it")
    if sha not in applied:
        raise ProjectionError(f"signature of {key!r} result_sha256 differs from the census "
                              f"`signature_applied` ledger for row {row!r}")
    if sig.get("schema") not in (None, SIGNATURE_SCHEMA):
        raise ProjectionError(f"signature of {key!r} schema {sig.get('schema')!r} != {SIGNATURE_SCHEMA}")
    primary = _text(sig.get("class"))
    if primary in NON_LIMITER or not (sig.get("reference_check") or {}).get("ok", False):
        raise ProjectionError(f"signature of {key!r} states no limiter (class {primary!r}, "
                              f"reference_check {sig.get('reference_check')!r})")
    classes = [c for c in sig.get("classes") or [] if c in CLASS_AXIS]
    if not classes or primary not in classes:
        raise ProjectionError(f"signature of {key!r} classes {sig.get('classes')!r} do not include primary {primary!r}")
    for n in ("model", "kernel_class", "shape"):
        if not _text(rec.get(n)):
            raise ProjectionError(f"census record {key!r} names no {n}")
    return {"key": key, "row": row, "sha": sha, "at": at, "primary": primary, "classes": classes,
            "marginal": [c for c in sig.get("marginal") or [] if c in classes],
            "ruled_out": [c for c in sig.get("ruled_out") or [] if c not in classes],
            "axes": sig.get("axes") or {}, "band": sig.get("band_position") or {},
            "bw": {"bw_frac_of_s16": sig.get("bw_frac_of_s16")}, "build": _text(sig.get("build")),
            "model": rec["model"].strip(), "kernel_class": rec["kernel_class"].strip(),
            "shape": rec["shape"].strip(), "n": rec.get("n"), "device": "mi210",
            "stale_vs_timing": bool(sig.get("stale_vs_timing")),
            "counter_set_sha256": sig.get("counter_set_sha256"), "refs": sig.get("refs") or {},
            "applied_bound": True}


def classify(document: Any, *, locator: str, sha256: str) -> dict:
    """Split signed census records into projectable `rows` (one per fired class), `unknown` (missing
    warrant) and `refused`. Unsigned records are not this source's and are not reported."""
    if not isinstance(locator, str) or not locator.startswith(LOCATOR_PREFIX):
        raise ProjectionError("bottleneck signature needs its original census locator")
    if not isinstance(sha256, str) or not _HEX64.fullmatch(sha256):
        raise ProjectionError("bottleneck signature needs the sha256 of the census bytes")
    out: dict = {"rows": [], "unknown": [], "refused": []}
    if not isinstance(document, dict) or document.get("schema") != CENSUS_SCHEMA:
        return out
    records = document.get("records")
    if not isinstance(records, dict):
        raise ProjectionError("bandwidth census `records` is not an object")
    applied = _sig_applied(document)
    for key, rec in records.items():
        sig = rec.get("signature") if isinstance(rec, dict) else None
        if not sig:
            continue
        if isinstance(sig, dict) and _warrant_missing(sig):
            out["unknown"].append({"key": key, "missing": _warrant_missing(sig)})
            continue
        try:
            f = _checked(key, rec, applied.get(_text(sig.get("source_row"))))
        except ProjectionError as exc:
            out["refused"].append({"key": key, "reason": str(exc)})
            continue
        for cls in f["classes"]:
            out["rows"].append({"key": key, "class": cls, "record": rec,
                                "applied_sha256": sorted(applied.get(f["row"], ())) or None,
                                "locator": locator, "census_sha256": sha256})
    return out


def native_rows(unit: str | Path) -> list[dict]:
    path = Path(unit)
    document, digest = read_census(path)
    return classify(document, locator=f"{LOCATOR_PREFIX}{path}", sha256=digest)["rows"]


def dropped(unit: str | Path) -> dict:
    path = Path(unit)
    document, digest = read_census(path)
    got = classify(document, locator=f"{LOCATOR_PREFIX}{path}", sha256=digest)
    return {"unknown": got["unknown"], "refused": got["refused"]}


def claim_text(f: dict, cls: str, value: float) -> str:
    src, axis, _d = CLASS_AXIS[cls]
    return (f"{f['device']} bottleneck signature [{f['model']} {f['kernel_class']} {f['shape']} n={f['n']} "
            f"build {f['build'] or 'unknown'}]: {cls}{' (marginal)' if cls in f['marginal'] else ''}"
            f"{' primary' if cls == f['primary'] else ''}, {axis} {value:.4g}"
            f"{' band position (0=S16, 1=S64)' if src == 'band' else ''}; ruled out "
            f"{', '.join(f['ruled_out']) or 'none'}; refs S16/S64 row {f['row']} -- diagnostic observation, "
            "counter-classified, protocol unqualified")


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    if not isinstance(native, dict) or set(native) != {
            "key", "class", "record", "applied_sha256", "locator", "census_sha256"}:
        raise ProjectionError("bottleneck signature native row has the wrong shape")
    if not isinstance(native["locator"], str) or not native["locator"].startswith(LOCATOR_PREFIX):
        raise ProjectionError("bottleneck signature needs its original census locator")
    applied = set(native["applied_sha256"]) if native["applied_sha256"] else None
    try:
        f = _checked(native["key"], native["record"], applied)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        if isinstance(exc, ProjectionError):
            raise
        raise ProjectionError(f"bottleneck signature refused: {exc}") from exc
    cls = native["class"]
    if cls not in f["classes"]:
        raise ProjectionError(f"class {cls!r} did not fire for {native['key']!r}")
    src, axis, direction = CLASS_AXIS[cls]
    value = f[src].get(axis)
    if not _finite(value):
        raise ProjectionError(f"signature of {native['key']!r} has no finite {axis} for class {cls!r}")
    build = f["build"] or "unknown"
    ident = hashlib.sha256(f"{f['key']}|{build}|{cls}".encode()).hexdigest()[:12]
    scope = {"device": f["device"], "kernel": f["kernel_class"], "shape": f["shape"],
             "surface": "autokernel-bottleneck-signature",
             "config_key": f"model={f['model']};n={f['n']};build={build};class={cls}", "scope_basis": "native"}
    return ClaimTuple(
        measurement_id=f"{MEASUREMENT_PREFIX}{ident}:{f['sha'][:16]}",
        metric=f"bottleneck_{cls}_{axis}", value=value, unit="fraction" if src != "axes" or axis != "fetch_over_bytes"
        else "ratio", date=f["at"], category="BASELINE", claim=claim_text(f, cls, value),
        metric_direction=direction, protocol_id="", reps=None,
        reps_basis="unknown: a signature is a mean over the diag row's shapes; dispatch counts are not carried",
        attestation_locator=f"{LOCATOR_PREFIX}{f['key']}@{f['sha']}", attestation_sha256=f["sha"],
        source_kind=SOURCE_KIND,
        extra={"source_row": f["row"], "census_key": f["key"], "class": cls, "primary": f["primary"],
               "classes": f["classes"], "marginal": f["marginal"], "ruled_out": f["ruled_out"],
               "build": build, "build_basis": "record" if f["build"] else "unknown",
               "stale_vs_timing": f["stale_vs_timing"], "applied_bound": f["applied_bound"], "counter_set_sha256": f["counter_set_sha256"],
               "census_locator": native["locator"], "census_sha256": native["census_sha256"]},
        applicability=scope, observation={"retrofit": False, "outcome_native": cls})


__all__ = ["ADAPTER_ID", "AUTHORITY", "CLASS_AXIS", "LIVE_CENSUS", "MEASUREMENT_PREFIX", "SOURCE_KIND",
           "classify", "claim_text", "dropped", "native_rows", "project"]
