"""AutoKernel served-kernel bandwidth census records as BASELINE observations (VB-AK-BW-CENSUS-WIRE).

Native source: `mi210_bandwidth_census.json` (schema `epyc.autokernel.bw_census.v1`; written by the
research `scripts/kernel_rnd/autokernel/loop/census_update.py`, run on every AutoKernel row end by
root `scripts/coordination/akloop/ak_runend.py`; live copy
`/mnt/raid0/llm/tmp/ak-bw-census/mi210_bandwidth_census.json`). `records` maps a census key
(`<model>|<kernel_class>|<shape>|n<N>`, CPU rows prefixed `cpu|`) to one measured effective
bandwidth.

PROJECTION ONLY. One census record -> one `BASELINE` tuple: value = `gbps`, unit `GB/s`,
`higher_better`, no protocol. `claim_tuple.grade()` decides; a census record cites no protocol, so
it grades `Judged/Located` -- an observation, never decision-gating, which is what it is. There is
no ladder here and no grade here.

The warrant is the three fields the write side recorded with the figure: `source_row` (the AK row
that produced it), `result_sha256` (the digest of that row's RESULT.json, the artifact the figure
was computed from) and `measured_at`. A record missing ANY of the three is UNKNOWN and is dropped
at read, never repaired and never filled: a warrant invented after the fact claims provenance the
run never captured (spec §4.7). Live today: 6 `a3b-cpu-gap-census-20261121` records carry an empty
`measured_at` and the q38fn CPU record carries `result_sha256: null`; none of them project.

Strict where the record lets it be: `gbps` must re-derive from `bytes_per_call` / `us_per_call`
(rounded to 0.1 GB/s upstream), and when `source_row` is in the census's own `applied` ledger its
sha256 must equal the record's `result_sha256`. A record that does not re-derive is REFUSED (named
in `classify()`), never repaired.

Two traps this adapter keeps honest:

* `n` in a census record is the matmul batch width (N columns), NOT a repetition count. `reps` is
  therefore left unset with `reps_basis` saying so; the n goes into the measurement id and scope.
* The attestation digest is the producing row's RESULT.json digest, which this adapter cannot
  re-read (no path in the record). `attestation_verified` stays unclaimed.

Retrofit (DP-1 (a)): the census writer has no belief hook, so every record projected today is a
retrofit and says so (`observation.retrofit`, and `provenance.retrofit` on its source frame).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_bw_census/v1"
AUTHORITY = "measurement"
SOURCE_KIND = "autokernel-bw-census"
CENSUS_SCHEMA = "epyc.autokernel.bw_census.v1"
MEASUREMENT_PREFIX = "ak-bw-census:v1:"
LOCATOR_PREFIX = "autokernel-bw-census:"
METRIC = "effective_bandwidth_gbps"
LIVE_CENSUS = Path("/mnt/raid0/llm/tmp/ak-bw-census/mi210_bandwidth_census.json")
_MAX_BYTES = 64 << 20
_HEX64 = re.compile(r"[0-9a-f]{64}")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(T[0-9:.]+(Z|[+-]\d{2}:\d{2})?)?")
_DEVICES = frozenset({"mi210", "cpu"})
# The census producer writes the generic word "gpu" on its MI210 records (the host has exactly one
# GPU, and the file is mi210_bandwidth_census.json). It is the same device as mi210, so it is
# normalized to mi210 and the basis says so; any other device word is still refused by name.
_DEVICE_ALIASES = {"gpu": "mi210"}


def read_census(path: str | Path) -> tuple[Any, str]:
    """(document, sha256 of the exact bytes read). Bounded, no symlinks, stable during read."""
    path = Path(path)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as exc:
        raise ProjectionError(f"bandwidth census cannot be opened: {exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= _MAX_BYTES:
            raise ProjectionError("bandwidth census is not a bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(_MAX_BYTES + 1)
        after = os.fstat(fd)
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (
                after.st_ino, after.st_size, after.st_mtime_ns) or len(raw) != before.st_size:
            raise ProjectionError("bandwidth census changed during read")
    finally:
        os.close(fd)
    try:
        return json.loads(raw), hashlib.sha256(raw).hexdigest()
    except (ValueError, RecursionError) as exc:
        raise ProjectionError(f"bandwidth census is not JSON: {exc}") from exc


def _finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _warrant_missing(rec: dict) -> list[str]:
    """The warrant fields the write-time record does not carry (empty / null / absent)."""
    return [name for name in ("source_row", "result_sha256", "measured_at")
            if not _text(rec.get(name))]


def _checked(key: str, rec: dict, applied_sha: str | None) -> dict:
    """The fields the tuple is built from, after the record re-derives. ProjectionError = refuse."""
    if not isinstance(rec, dict):
        raise ProjectionError(f"census record {key!r} is not an object")
    missing = _warrant_missing(rec)
    if missing:
        raise ProjectionError(f"census record {key!r} carries no {'/'.join(missing)}: UNKNOWN warrant")
    source_row, sha, at = _text(rec["source_row"]), _text(rec["result_sha256"]), _text(rec["measured_at"])
    if not _HEX64.fullmatch(sha):
        raise ProjectionError(f"census record {key!r} result_sha256 is not a 64-hex digest")
    if not _ISO_DATE.fullmatch(at):
        raise ProjectionError(f"census record {key!r} measured_at {at!r} is not an ISO date")
    if applied_sha is not None and applied_sha != sha:
        raise ProjectionError(
            f"census record {key!r} result_sha256 differs from the census `applied` ledger entry "
            f"for row {source_row!r}")
    gbps = rec.get("gbps")
    if not _finite(gbps) or gbps <= 0:
        raise ProjectionError(f"census record {key!r} gbps is not a positive finite number")
    nbytes, us = rec.get("bytes_per_call"), rec.get("us_per_call")
    if not (_finite(nbytes) and nbytes > 0 and _finite(us) and us > 0):
        raise ProjectionError(
            f"census record {key!r} states no bytes_per_call/us_per_call to re-derive gbps from")
    derived = nbytes / us / 1e3
    if abs(derived - gbps) > 0.06 + 1e-3 * derived:  # upstream rounds to 0.1 GB/s
        raise ProjectionError(
            f"census record {key!r} gbps {gbps} does not re-derive from bytes/us ({derived:.1f})")
    n = rec.get("n")
    if type(n) is not int or n < 0:
        raise ProjectionError(f"census record {key!r} states no batch width n")
    for name in ("model", "kernel_class", "shape"):
        if not _text(rec.get(name)):
            raise ProjectionError(f"census record {key!r} names no {name}")
    device = rec.get("device")
    device_basis = "record" if device else "file_default"
    if device in _DEVICE_ALIASES:
        device, device_basis = _DEVICE_ALIASES[device], f"record_alias:{device}"
    if device is not None and device not in _DEVICES:
        raise ProjectionError(
            f"census record {key!r} device {device!r} is not a census device "
            f"(known: {sorted(_DEVICES)}; alias: {_DEVICE_ALIASES})")
    return {"key": key, "source_row": source_row, "sha": sha, "at": at, "gbps": gbps,
            "bytes": nbytes, "us": us, "n": n, "model": rec["model"].strip(),
            "kernel_class": rec["kernel_class"].strip(), "shape": rec["shape"].strip(),
            "arm": _text(rec.get("arm")), "op": _text(rec.get("op")),
            "status": _text(rec.get("status")), "device": device or "mi210",
            "device_basis": device_basis,
            "config": _text(rec.get("config")), "applied_bound": applied_sha is not None,
            "stale": bool(rec.get("stale")), "quiet_host": rec.get("quiet_host")}


def _applied(document: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for entry in document.get("applied") or []:
        if isinstance(entry, dict) and _text(entry.get("row")) and _text(entry.get("sha256")):
            out[_text(entry["row"])] = _text(entry["sha256"])
    return out


def classify(document: Any, *, locator: str, sha256: str) -> dict:
    """Split a census into `rows` (projectable), `unknown` (missing warrant: dropped) and
    `refused` (present but does not re-derive). Reported by key with the reason, never silent."""
    if not isinstance(locator, str) or not locator.startswith(LOCATOR_PREFIX):
        raise ProjectionError("bandwidth census needs its original file locator")
    if not isinstance(sha256, str) or not _HEX64.fullmatch(sha256):
        raise ProjectionError("bandwidth census needs the sha256 of the bytes it was read from")
    out: dict = {"rows": [], "unknown": [], "refused": []}
    if not isinstance(document, dict) or document.get("schema") != CENSUS_SCHEMA:
        return out
    records = document.get("records")
    if not isinstance(records, dict):
        raise ProjectionError("bandwidth census `records` is not an object")
    applied = _applied(document)
    for key, rec in records.items():
        if isinstance(rec, dict):
            missing = _warrant_missing(rec)
            if missing:
                out["unknown"].append({"key": key, "missing": missing})
                continue
            sr = _text(rec["source_row"])
            try:
                _checked(key, rec, applied.get(sr))
            except ProjectionError as exc:
                out["refused"].append({"key": key, "reason": str(exc)})
                continue
            out["rows"].append({"key": key, "record": rec, "applied_sha256": applied.get(sr),
                                "locator": locator, "census_sha256": sha256})
        else:
            out["refused"].append({"key": str(key), "reason": "census record is not an object"})
    return out


def native_rows(unit: str | Path) -> list[dict]:
    """Projectable native rows of one census file; [] for a file that is not a v1 census."""
    path = Path(unit)
    document, digest = read_census(path)
    return classify(document, locator=f"{LOCATOR_PREFIX}{path}", sha256=digest)["rows"]


def dropped(unit: str | Path) -> dict:
    """What `native_rows` did not project, by key and reason (`unknown` warrant / `refused`)."""
    path = Path(unit)
    document, digest = read_census(path)
    got = classify(document, locator=f"{LOCATOR_PREFIX}{path}", sha256=digest)
    return {"unknown": got["unknown"], "refused": got["refused"]}


def _claim(f: dict) -> str:
    return (f"{f['device']} served-kernel bandwidth [{f['model']} {f['kernel_class']} {f['shape']} "
            f"n={f['n']}{' arm ' + f['arm'] if f['arm'] else ''}]: {f['gbps']} GB/s effective "
            f"({f['bytes']:.0f} B in {f['us']} us per call) measured {f['at']} by row "
            f"{f['source_row']}; census status {f['status'] or 'unstated'} -- diagnostic "
            "observation, protocol unqualified; n is the matmul batch width and the repetition "
            "count is not recorded")


@register(SOURCE_KIND)
def project(native: dict) -> ClaimTuple:
    if not isinstance(native, dict) or set(native) != {
            "key", "record", "applied_sha256", "locator", "census_sha256"}:
        raise ProjectionError("bandwidth census native row has the wrong shape")
    locator = native["locator"]
    if not isinstance(locator, str) or not locator.startswith(LOCATOR_PREFIX):
        raise ProjectionError("bandwidth census needs its original file locator")
    try:
        f = _checked(native["key"], native["record"], native["applied_sha256"])
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError) as exc:
        if isinstance(exc, ProjectionError):
            raise
        raise ProjectionError(f"bandwidth census record refused: {exc}") from exc
    ident = hashlib.sha256(f["key"].encode()).hexdigest()[:12]
    scope = {"device": f["device"], "kernel": f["kernel_class"], "shape": f["shape"],
             "surface": "autokernel-bw-census",
             "config_key": ";".join(p for p in (
                 f"model={f['model']}", f"n={f['n']}", f"arm={f['arm']}" if f["arm"] else "",
                 f"config={f['config']}" if f["config"] else "") if p),
             "scope_basis": "native"}
    if f["op"]:
        scope["op"] = f["op"]
    return ClaimTuple(
        measurement_id=f"{MEASUREMENT_PREFIX}{ident}:{f['sha'][:16]}",
        metric=METRIC, value=f["gbps"], unit="GB/s", date=f["at"], category="BASELINE",
        claim=_claim(f), metric_direction="higher_better", protocol_id="", reps=None,
        reps_basis="unknown: the census records no repetition count (its n is the matmul batch width)",
        attestation_locator=f"{LOCATOR_PREFIX}{f['key']}@{f['sha']}", attestation_sha256=f["sha"],
        source_kind=SOURCE_KIND,
        extra={"source_row": f["source_row"], "census_key": f["key"], "batch_n": f["n"],
               "bytes_per_call": f["bytes"], "us_per_call": f["us"], "status": f["status"],
               "applied_bound": f["applied_bound"], "device_basis": f["device_basis"],
               "stale": f["stale"], "quiet_host": f["quiet_host"],
               "census_locator": locator, "census_sha256": native["census_sha256"]},
        applicability=scope, observation={"retrofit": True})


__all__ = ["ADAPTER_ID", "AUTHORITY", "CENSUS_SCHEMA", "LIVE_CENSUS", "MEASUREMENT_PREFIX",
           "SOURCE_KIND", "classify", "dropped", "native_rows", "project", "read_census"]
