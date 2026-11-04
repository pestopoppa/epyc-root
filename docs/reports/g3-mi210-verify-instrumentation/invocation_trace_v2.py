#!/usr/bin/env python3
"""Bounded, fail-closed reader for the G3 invocation-correlation V2 trace.

This parses log syntax and correlates dispatch records by the explicit ID in
v10-invocation-correlation-v2.patch. It does not prove the patch is present in
the running binary, that all dispatches were delivered, or that execution was
on HIP/a particular device. An incomplete or unsuccessful invocation remains
UNKNOWN.
"""
from collections import Counter
import re

_MARKER = re.compile(r"\b(G3_[A-Z0-9_]+)\b")
_INT = re.compile(r"-?[0-9]+\Z")
_UINT = re.compile(r"[0-9]+\Z")
_HEX_PTR = re.compile(r"0x[0-9a-fA-F]+\Z")
_BEGIN = {"invocation", "class", "slot", "off", "tokens", "drafts", "correlation"}
_END = {"invocation", "rc", "correlation"}
_DISPATCH = {"invocation", "correlation", "device", "kernel", "tensor", "q",
             "k_type", "k", "v_type", "v"}
_KERNELS = {0, 100, 200, 300, 400}
MAX_TRACE_BYTES = 8 * 1024 * 1024
MAX_TRACE_LINES = 100_000


def _fields(payload, required):
    result = {}
    for item in payload.split():
        key, sep, value = item.partition("=")
        if not sep or not key or not value or key in result:
            raise ValueError("malformed or duplicate V2 trace field")
        result[key] = value
    if set(result) != required:
        raise ValueError("unexpected V2 trace fields")
    return result


def _int(value):
    if not _INT.fullmatch(value):
        raise ValueError("invalid V2 trace integer")
    return int(value)


def _uint(value):
    if not _UINT.fullmatch(value):
        raise ValueError("invalid V2 trace unsigned integer")
    return int(value)


def _dims(value):
    parts = value.split(",")
    if len(parts) != 4:
        raise ValueError("V2 tensor must have four dimensions")
    values = tuple(_uint(part) for part in parts)
    if any(value == 0 for value in values):
        raise ValueError("V2 tensor dimensions must be positive")
    return values


def parse_invocation_trace_v2(text):
    """Parse a bounded trace and return per-call attribution plus raw counts.

    Non-G3 server lines are ignored. Unknown G3 markers and malformed records
    fail closed with ValueError. Dispatches with invocation=0/correlation=unknown
    are counted as uncorrelated and never attached to a target invocation.
    """
    if not isinstance(text, str):
        raise ValueError("trace text required")
    if len(text.encode("utf-8")) > MAX_TRACE_BYTES:
        raise ValueError("V2 trace exceeds byte limit")
    lines = text.splitlines()
    if len(lines) > MAX_TRACE_LINES:
        raise ValueError("V2 trace exceeds line limit")

    calls, by_id, seen = [], {}, set()
    active = None
    uncorrelated = Counter()
    dispatch_count = 0
    for line in lines:
        marker = _MARKER.search(line)
        if marker is None:
            continue
        kind = marker.group(1)
        fields = _fields(line[marker.end():].strip(),
                         _BEGIN if kind == "G3_TARGET_BEGIN_V2" else
                         _END if kind == "G3_TARGET_END_V2" else
                         _DISPATCH if kind == "G3_FATTN_DISPATCH_V2" else set())
        if kind == "G3_TARGET_BEGIN_V2":
            ident = _uint(fields["invocation"])
            slot, off, tokens, drafts = (_int(fields[k]) for k in ("slot", "off", "tokens", "drafts"))
            if (active is not None or ident == 0 or ident in seen or off < 0 or tokens <= 0 or drafts < 0
                    or slot < -1 or fields["class"] not in ("parallel_verify_candidate", "unclassified")
                    or fields["correlation"] != "host_scope"):
                raise ValueError("invalid or ambiguous V2 target begin")
            if fields["class"] == "parallel_verify_candidate" and (slot < 0 or tokens != drafts + 1):
                raise ValueError("invalid V2 verify-candidate slot or token count")
            call = {"invocation": ident, "class": fields["class"], "slot": slot,
                    "off": off, "tokens": tokens, "drafts": drafts, "rc": None,
                    "complete": False, "dispatches": [], "status": "UNKNOWN",
                    "reason": "target boundary is incomplete"}
            calls.append(call)
            by_id[ident] = call
            seen.add(ident)
            active = call
        elif kind == "G3_TARGET_END_V2":
            ident, rc = _uint(fields["invocation"]), _int(fields["rc"])
            if (active is None or active["invocation"] != ident
                    or fields["correlation"] != "host_scope"):
                raise ValueError("unmatched or ambiguous V2 target end")
            active["rc"], active["complete"] = rc, True
            if rc != 0:
                active["reason"] = "target decode returned nonzero"
            elif active["class"] != "parallel_verify_candidate":
                active["reason"] = "target call was not classified as a verify candidate"
            elif not active["dispatches"]:
                active["reason"] = "no correlated flash-attention dispatch observed"
            else:
                active["status"] = "CORRELATED_CANDIDATE"
                active["reason"] = "explicit V2 invocation ID links observed dispatches"
            active = None
        elif kind == "G3_FATTN_DISPATCH_V2":
            ident = _uint(fields["invocation"])
            device, kernel = _int(fields["device"]), _int(fields["kernel"])
            if device < 0 or kernel not in _KERNELS or not _HEX_PTR.fullmatch(fields["tensor"]):
                raise ValueError("invalid V2 dispatch metadata")
            q, k, v = (_dims(fields[name]) for name in ("q", "k", "v"))
            if not fields["k_type"] or not fields["v_type"]:
                raise ValueError("empty V2 tensor type")
            event = {"invocation": ident, "device": device, "kernel": kernel,
                     "tensor": fields["tensor"], "q": q, "k_type": fields["k_type"],
                     "k": k, "v_type": fields["v_type"], "v": v}
            dispatch_count += 1
            if fields["correlation"] == "unknown":
                if ident != 0:
                    raise ValueError("unknown V2 correlation must use invocation zero")
                uncorrelated[kernel] += 1
            elif fields["correlation"] == "host_scope":
                if ident == 0 or ident not in by_id or active is None or active["invocation"] != ident:
                    raise ValueError("V2 dispatch references an inactive or unknown invocation")
                by_id[ident]["dispatches"].append(event)
            else:
                raise ValueError("unsupported V2 dispatch correlation")
        else:
            raise ValueError("unsupported G3 trace marker")

    return {"calls": calls, "uncorrelated_dispatch_counts": dict(uncorrelated),
            "dispatch_records": dispatch_count,
            "correlated_dispatch_records": sum(len(call["dispatches"]) for call in calls),
            "overall_status": "UNKNOWN" if uncorrelated or any(c["status"] == "UNKNOWN" for c in calls)
                             or not calls else "CORRELATED_CANDIDATE"}
