"""Serving-floor REGISTRY entries -> BASELINE ClaimTuples (VB-FLOOR-REGISTRY-WIRE).

Native source: the top-level ``serving_floors:`` section of the research MASTER model registry
(``orchestration/model_registry.yaml``, role -> list of ``epyc.autokernel.floor_registry_entry.v1``
entries; research ``scripts/kernel_rnd/autokernel/loop/floor_registry.py``; the master is the only
floor store, operator 2026-10-22). Each entry pins its sealed A/A record by ``record_sha256``.

PROJECTION ONLY. One entry -> one ``BASELINE`` tuple; ``claim_tuple.grade()`` decides (a floor cites
no protocol, so it is an observation). No ladder, no grading rule here.

Condition key. The entry's ``equivalence_key, recipe_hash, request_digest, model_sha, numerics_epoch,
claim_class, threads, co_tenancy`` are carried as the tuple's floor key. ``applicability`` is a closed
set in ``claim_tuple.APPLICABILITY_KEYS``; the floor-key names are placed in ``applicability`` exactly
when that set admits them, and ALWAYS in ``extra["floor_key"]`` (never dropped, never invented).
``recipe``, ``model_sha256`` and ``build_sha`` map onto existing applicability keys.
``observation.noise_floor_rel = floor_pct / 100``.

Refusals (loud, never repaired):
* ``grade.claim_class == "indicative"`` -- a floor that can never satisfy a decision is REFUSED as
  decision-gating: ``native_rows`` withholds it (listed by ``refusals``), ``project`` raises.
  ``decision`` requires ``co_tenancy == quiet`` (the registry's own rule) or the entry is refused.
* The sealed record is read when present: its bytes must hash to ``record_sha256`` (streamed; the
  DS41-1017 record is 336 MB) and, for v1, restate the entry's ``floor_pct`` / ``n``. A mismatch refuses
  the entry. A record that is unreadable (moved, permissions) projects a v2 entry with
  ``attestation_present=False`` and no verification (the pin is then a recorded claim only); a v1 entry
  cannot project without its record because it states no median.

v1 entries REUSE ``autokernel_serving_floor.project`` over the sealed v1 record (median, launches
re-derived there); this adapter only re-labels the identity and adds the registry key.

v2 PROJECTION RULING (matched-process floors carry no median; ``autokernel_serving_floor`` projects
nothing for them by design). The value-bearing statement of a v2 floor is the relative spread itself:
metric ``serving_floor_pct``, value ``floor_pct`` (percent), lower_better, ``reps`` = ``n`` (the
launches/processes), ``unit`` of the replicate = ``process`` (``reps_basis``), ``k`` pairs and the
95% interval recorded in ``extra``. It is the noise floor expressed as a number; a planner reads it
as ``observation.noise_floor_rel``. No anchor rate is invented.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import (APPLICABILITY_KEYS, ClaimTuple, ProjectionError, register,  # noqa: E402
                         to_frames)
from adapters import autokernel_serving_floor as v1floor  # noqa: E402

ADAPTER_ID = "vidya.adapters.floor_registry/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "floor-registry"
SECTION = "serving_floors"
ENTRY_SCHEMA = "epyc.autokernel.floor_registry_entry.v1"
V1_SCHEMA = "epyc.autokernel.serving_floor.v1"
V2_SCHEMA = "epyc.autokernel.serving_floor.v2"
MASTER_NAME = "model_registry.yaml"
MEASUREMENT_PREFIX = "floor-registry:"
_MAX_MASTER = 64 << 20
_HEX64 = re.compile(r"[0-9a-f]{64}")
KEY_FIELDS = ("equivalence_key", "recipe_hash", "request_digest", "model_sha", "numerics_epoch")
GRADE_FIELDS = ("claim_class", "threads", "co_tenancy")


def _finite(v: Any) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def master_path(path: str | Path) -> Path:
    p = Path(path)
    return p / "orchestration" / MASTER_NAME if p.is_dir() else p


def load_section(path: str | Path) -> dict[str, list]:
    """role -> entries, parsed from ONLY the top-level ``serving_floors:`` slice of the master."""
    p = master_path(path)
    if not p.is_file() or p.stat().st_size > _MAX_MASTER:
        raise ProjectionError("floor registry master is not a bounded regular file")
    lines = p.read_text(encoding="utf-8").split("\n")
    start = next((i for i, ln in enumerate(lines) if ln == f"{SECTION}:"), None)
    if start is None:
        return {}
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i] and not lines[i].startswith((" ", "#")):
            end = i
            break
    try:
        import yaml  # noqa: PLC0415
        body = yaml.safe_load("\n".join(lines[start:end])) or {}
    except ImportError as exc:
        raise ProjectionError("floor registry needs PyYAML to read the master") from exc
    except Exception as exc:  # noqa: BLE001 -- yaml raises many types
        raise ProjectionError(f"floor registry section is not YAML: {exc}") from exc
    section = body.get(SECTION) or {}
    if not isinstance(section, dict) or any(not isinstance(v, list) for v in section.values()):
        raise ProjectionError(f"`{SECTION}` must map role -> list of entries")
    return section


def _record_path(master: Path, entry: dict) -> Path:
    rec = entry.get("record")
    if not isinstance(rec, str) or not rec.strip():
        raise ProjectionError("floor entry names no sealed record")
    rp = Path(rec)
    return rp if rp.is_absolute() else master.resolve().parent.parent / rp


def _stream_sha256(path: Path) -> str | None:
    """sha256 of the exact bytes, streamed; None if the file is absent/unreadable."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def _entry_problem(entry: Any) -> str | None:
    """Why an entry cannot be admitted as a floor at all (structure), else None."""
    if not isinstance(entry, dict):
        return "entry is not a mapping"
    if entry.get("schema") not in (V1_SCHEMA, V2_SCHEMA):
        return f"entry schema {entry.get('schema')!r} is not a serving floor schema"
    for k in KEY_FIELDS:
        if not isinstance(entry.get(k), str) or not entry[k].strip():
            return f"entry states no {k}"
    for k in ("equivalence_key", "recipe_hash", "request_digest", "model_sha"):
        if not _HEX64.fullmatch(entry[k]):
            return f"entry {k} is not a sha256"
    if not isinstance(entry.get("recipe"), str) or not entry["recipe"].strip():
        return "entry states no recipe"
    if not _finite(entry.get("floor_pct")) or entry["floor_pct"] < 0:
        return "entry floor_pct is not a non-negative finite number"
    if type(entry.get("n")) is not int or entry["n"] < 1:
        return "entry states no sample count"
    if not isinstance(entry.get("record_sha256"), str) or not _HEX64.fullmatch(entry["record_sha256"]):
        return "entry pins no record_sha256"
    g = entry.get("grade")
    if not isinstance(g, dict) or g.get("claim_class") not in ("decision", "indicative") \
            or g.get("co_tenancy") not in ("quiet", "co-tenant") \
            or type(g.get("threads")) is not int or g["threads"] < 1:
        return "entry grade is malformed (claim_class / co_tenancy / threads)"
    if g["claim_class"] == "decision" and g["co_tenancy"] != "quiet":
        return "decision-class floor claims a co-tenant condition (registry rule)"
    return None


def _scan(path: str | Path) -> tuple[list[dict], list[dict]]:
    master = master_path(path)
    rows: list[dict] = []
    refused: list[dict] = []
    for role, entries in sorted(load_section(master).items()):
        for entry in entries:
            ident = (entry.get("id") if isinstance(entry, dict) else None) or "?"
            problem = _entry_problem(entry)
            if problem is None and entry["grade"]["claim_class"] == "indicative":
                problem = ("claim_class=indicative: refused as decision-gating (an indicative floor "
                           "can never satisfy a decision)")
            if problem is not None:
                refused.append({"role": role, "id": ident, "reason": problem})
                continue
            rows.append(_native(master, role, entry))
    return rows, refused


def _native(master: Path, role: str, entry: dict) -> dict:
    rpath = _record_path(master, entry)
    actual = _stream_sha256(rpath)
    if actual is not None and actual != entry["record_sha256"]:
        raise ProjectionError(f"floor {role}/{entry.get('id')}: sealed record {rpath} does not "
                              "re-derive its pinned record_sha256")
    row: dict = {"role": role, "entry": dict(entry), "master": str(master),
                 "record_path": str(rpath), "record_sha256": entry["record_sha256"],
                 "record_verified": actual is not None}
    if entry["schema"] == V1_SCHEMA:
        if actual is None:
            raise ProjectionError(f"floor {role}/{entry.get('id')}: a v1 entry states no median; "
                                  "its sealed record is unreadable")
        doc, sha = v1floor.read_floor(rpath)
        if not isinstance(doc, dict) or doc.get("schema") != V1_SCHEMA or sha != actual:
            raise ProjectionError("v1 floor entry's record is not a v1 serving floor")
        if doc.get("floor_pct") != entry["floor_pct"]:
            raise ProjectionError("v1 floor entry floor_pct differs from its sealed record")
        row["floor"] = doc
    return row


def native_rows(path: str | Path) -> tuple[dict, ...]:
    """Admissible rows; indicative / malformed entries are withheld (see ``refusals``)."""
    return tuple(_scan(path)[0])


def refusals(path: str | Path) -> list[dict]:
    """Entries refused as decision-gating or malformed: ``{role, id, reason}``."""
    return _scan(path)[1]


def units(path: Path) -> list[Path]:
    """ingest_sources unit discovery: the master registry file (or the research repo holding it)."""
    p = master_path(path)
    return [p] if p.is_file() and p.name == MASTER_NAME else []


def _floor_key(entry: dict) -> dict:
    g = entry["grade"]
    return {**{k: entry[k] for k in KEY_FIELDS}, **{k: g[k] for k in GRADE_FIELDS}}


def _split_key(entry: dict) -> tuple[dict, dict]:
    """(applicability part admitted by the closed key set, the rest)."""
    key = _floor_key(entry)
    inside = {k: v for k, v in key.items() if k in APPLICABILITY_KEYS}
    return inside, key


def _date(entry: dict) -> str:
    return str(entry.get("measured_at") or "")


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    if not isinstance(native, dict) or not isinstance(native.get("entry"), dict):
        raise ProjectionError("floor-registry native entry missing")
    entry, role = native["entry"], native.get("role")
    problem = _entry_problem(entry)
    if problem is None and entry["grade"]["claim_class"] == "indicative":
        problem = "claim_class=indicative is refused as decision-gating"
    if problem:
        raise ProjectionError(f"floor {role}/{entry.get('id')}: {problem}")
    inside, key = _split_key(entry)
    locator = f"floor-registry:{native['master']}#{role}/{entry.get('id')}"
    g = entry["grade"]
    extra = {"adapter": ADAPTER_ID, "role": role, "floor_key": key,
             "id": entry.get("id"), "schema": entry["schema"], "k": entry.get("k"),
             "interval": entry.get("interval"), "champion_tree_hash": entry.get("champion_tree_hash"),
             "content_sha256": entry.get("content_sha256"), "annotation": entry.get("annotation"),
             "record_verified": bool(native.get("record_verified"))}
    applicability = {"recipe": entry["recipe"], "model_sha256": entry["model_sha"],
                     "scope_basis": "native", "role": role, **inside}
    commit = (entry.get("build") or {}).get("commit")
    if isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{7,64}", commit):
        applicability["build_sha"] = commit
    noise = entry["floor_pct"] / 100.0
    if entry["schema"] == V1_SCHEMA:
        base = v1floor.project(v1floor.native_rows(
            native["floor"], locator=v1floor.LOCATOR_PREFIX + native["record_path"],
            sha256=native["record_sha256"])[0])
        return dataclasses.replace(
            base, measurement_id=f"{MEASUREMENT_PREFIX}{role}:{entry['id']}", source_kind=SOURCE_KIND,
            applicability={**base.applicability, **applicability},
            attestation_locator=locator, extra={**base.extra, **extra},
            observation={**base.observation, "noise_floor_rel": noise})
    claim = (f"serving floor registry [{role}] {entry['recipe']}: matched-process A/A noise floor "
             f"{entry['floor_pct']}% over n={entry['n']} process launches"
             + (f" ({entry['k']} pairs)" if type(entry.get("k")) is int else "")
             + f"; {g['claim_class']}-class, {g['co_tenancy']}, {g['threads']} threads, numerics "
             f"{entry['numerics_epoch']} -- calibration observation, protocol unqualified")
    return ClaimTuple(
        measurement_id=f"{MEASUREMENT_PREFIX}{role}:{entry['id']}", metric="serving_floor_pct",
        value=entry["floor_pct"], unit="%", date=_date(entry), category="BASELINE", claim=claim,
        metric_direction="lower_better", protocol_id="", reps=entry["n"],
        reps_basis="scored: process launches (unit=process), matched-process A/A",
        attestation_path=native["record_path"], attestation_sha256=native["record_sha256"],
        attestation_locator=locator, attestation_present=bool(native.get("record_verified")),
        attestation_verified=True if native.get("record_verified") else None,
        source_kind=SOURCE_KIND, applicability=applicability, extra=extra,
        observation={"outcome": "floor", "noise_floor_rel": noise})


def frames_for_path(path: str | Path, *, as_of: str) -> list[dict]:
    frames: list[dict] = []
    for native in native_rows(path):
        frames.extend(to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID,
                                authority=AUTHORITY))
    return frames


__all__ = ["ADAPTER_ID", "AUTHORITY", "SOURCE_KIND", "frames_for_path", "native_rows", "project",
           "refusals", "units"]
