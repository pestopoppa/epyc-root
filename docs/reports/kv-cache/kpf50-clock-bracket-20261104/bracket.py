"""Strictly check one profiled KPF-50 step against typed HSA clock captures.

This verifies record structure and a host-monotonic bracket only.
"""
import hashlib
import json
import re


UINT = lambda x: type(x) is int and 0 <= x < 2**64
SHA = re.compile(r"[0-9a-f]{64}\Z")


def _native(raw, witness, phase, window, run_id):
    if not isinstance(raw, bytes) or not isinstance(witness, dict):
        raise ValueError("missing native capture or witness")
    if witness.get("schema") != "kpf50.clock-sample.v1" or witness.get("phase") != phase or witness.get("window") != window or witness.get("run_id") != run_id:
        raise ValueError("clock witness identity mismatch")
    if type(witness.get("pid")) is not int or witness["pid"] <= 0 or not UINT(witness.get("birth_ticks")) or witness["birth_ticks"] == 0 or not UINT(witness.get("process_start_bound_ns")) or not UINT(witness.get("process_end_bound_ns")) or witness["process_start_bound_ns"] > witness["process_end_bound_ns"]:
        raise ValueError("clock producer lifetime identity missing")
    if not all(UINT(witness.get(k)) for k in ("hsa_tick", "hsa_hz", "mono_before_ns", "mono_after_ns")) or witness["hsa_hz"] == 0 or witness["mono_before_ns"] > witness["mono_after_ns"]:
        raise ValueError("malformed witness sample fields")
    if not isinstance(witness.get("producer_sha256"), str) or not SHA.fullmatch(witness["producer_sha256"]):
        raise ValueError("clock producer digest missing")
    if witness.get("native_sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("native capture digest mismatch")
    x = json.loads(raw)
    if x.get("schema") != "epyc.kpf50.hsa-clock.v1" or type(x.get("pid")) is not int or x["pid"] != witness["pid"]:
        raise ValueError("native producer identity mismatch")
    hz, rows = x.get("frequency_hz"), x.get("samples")
    if type(hz) is not int or hz <= 0 or type(witness.get("hsa_hz")) is not int or witness["hsa_hz"] != hz or not isinstance(rows, list) or len(rows) < 2:
        raise ValueError("invalid native frequency or samples")
    last = -1
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"host_before_ns", "hsa_ticks", "host_after_ns"}:
            raise ValueError("invalid native sample shape")
        b, t, e = (row[k] for k in ("host_before_ns", "hsa_ticks", "host_after_ns"))
        if not all(UINT(v) for v in (b, t, e)) or b > e or t < last or b < witness["process_start_bound_ns"] or e > witness["process_end_bound_ns"]:
            raise ValueError("invalid or unordered native sample")
        last = t
    # Deliberately do not infer a host/HSA offset or profiler epoch equivalence.
    tick = witness.get("hsa_tick")
    best = min(rows, key=lambda row: row["host_after_ns"] - row["host_before_ns"])
    if not UINT(tick) or best["hsa_ticks"] != tick or best["host_before_ns"] != witness["mono_before_ns"] or best["host_after_ns"] != witness["mono_after_ns"]:
        raise ValueError("selected witness sample is not in native capture")
    return rows


def verify(before, after, before_raw, after_raw, *, window, run_id, step_begin_ns, step_end_ns):
    """Check a host-monotonic actual step interval against same-domain clock samples."""
    br = _native(before_raw, before, "clock_before", window, run_id)
    ar = _native(after_raw, after, "clock_after", window, run_id)
    if before.get("hsa_hz") != after.get("hsa_hz") or before.get("pid") == after.get("pid"):
        raise ValueError("clock producer identity/frequency mismatch")
    if before["mono_after_ns"] > after["mono_before_ns"] or before["hsa_tick"] >= after["hsa_tick"]:
        raise ValueError("clock records are not ordered around the step")
    # Every before sample precedes the profile, and every after sample follows it.
    start, end = step_begin_ns, step_end_ns
    if not UINT(start) or not UINT(end) or end <= start:
        raise ValueError("invalid host-monotonic step interval")
    if before.get("producer_sha256") != after.get("producer_sha256") or not isinstance(before.get("producer_sha256"), str) or not SHA.fullmatch(before["producer_sha256"]):
        raise ValueError("clock producer pin mismatch")
    if before["mono_after_ns"] > start or end > after["mono_before_ns"]:
        raise ValueError("step interval is not fully inside host clock bracket")
    if any(row["host_after_ns"] > start for row in br) or any(row["host_before_ns"] < end for row in ar):
        raise ValueError("native samples overlap the actual step interval")
    return {"schema": "kpf50.clock-bracket.v1", "window": window, "run_id": run_id,
            "step_interval_monotonic_ns": [start, end],
            "clock_host_edges_ns": [before["mono_after_ns"], after["mono_before_ns"]], "verified": True}
