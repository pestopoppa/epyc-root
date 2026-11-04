#!/usr/bin/env python3
"""Correlate V2 dispatches with independently supplied invocation/tensor layer bindings.

Bindings are assertions supplied by the caller, not produced by the V2 patch.
Each binding has exactly invocation (positive int), tensor (non-null hex pointer),
layer (nonnegative int), and evidence (nonempty source reference). The source
must independently establish that tensor's layer in that invocation; pointer
addresses alone or layer order are not evidence. The caller must also establish
binary identity, complete event delivery, backend/HIP residency and correctness.
This function checks neither those prerequisites nor the truth of the bindings.
"""
import re

from invocation_trace_v2 import parse_invocation_trace_v2

_POINTER = re.compile(r"0x[0-9a-fA-F]+\Z")
_KERNELS = {100: "VEC", 200: "TILE", 300: "WMMA_F16", 400: "MMA_F16"}


def classify_native_trace(text, *, expected_layer_ids, layer_bindings):
    """Return observed call classifications; missing/ambiguous evidence is UNKNOWN.

    expected_layer_ids comes from independently verified model metadata. Mapping
    records must be invocation-specific; stale or extra bindings invalidate the
    entire capture. Malformed trace/binding input raises ValueError. An UNKNOWN
    result never means absence of VEC, including for a partial invocation.
    """
    if (not isinstance(expected_layer_ids, (list, tuple)) or not expected_layer_ids
            or any(type(x) is not int or x < 0 for x in expected_layer_ids)
            or len(set(expected_layer_ids)) != len(expected_layer_ids)):
        raise ValueError("unique nonnegative expected layer IDs required")
    if not isinstance(layer_bindings, list):
        raise ValueError("layer bindings must be a list")
    trace = parse_invocation_trace_v2(text)
    bindings = {}
    duplicate = set()
    for binding in layer_bindings:
        if not isinstance(binding, dict) or set(binding) != {"invocation", "tensor", "layer", "evidence"}:
            raise ValueError("invalid layer binding")
        inv, tensor, layer, evidence = (binding[k] for k in ("invocation", "tensor", "layer", "evidence"))
        if (type(inv) is not int or inv <= 0 or not isinstance(tensor, str)
                or not _POINTER.fullmatch(tensor) or int(tensor, 16) == 0
                or type(layer) is not int or layer < 0 or not isinstance(evidence, str)
                or not evidence.strip()):
            raise ValueError("invalid layer binding values")
        key = (inv, int(tensor, 16))
        if key in bindings:
            duplicate.add(key)
        bindings[key] = binding
    seen_keys = set()
    all_unknown = bool(trace["uncorrelated_dispatch_counts"])
    calls = []
    for call in trace["calls"]:
        reasons = []
        if call["status"] != "CORRELATED_CANDIDATE" or call["drafts"] <= 0:
            reasons.append("incomplete, unsuccessful or non-verify target invocation")
        events, layers = [], []
        for event in call["dispatches"]:
            key = (call["invocation"], int(event["tensor"], 16))
            if key in seen_keys or key in duplicate or key[1] == 0:
                reasons.append("ambiguous tensor identity or layer binding")
            seen_keys.add(key)
            binding = bindings.get(key)
            if binding is None:
                reasons.append("missing invocation-specific layer binding")
                continue
            layers.append(binding["layer"])
            kernel = _KERNELS.get(event["kernel"])
            kv = event["k_type"].upper()
            if kernel is None or kv not in ("Q8_0", "Q4_0") or event["v_type"].upper() != kv:
                reasons.append("unsupported kernel or KV types")
            events.append({"layer": binding["layer"], "kernel": kernel,
                           "q_len": event["q"][1], "kv_type": kv,
                           "device": event["device"], "evidence": binding["evidence"]})
        if len(layers) != len(expected_layer_ids) or set(layers) != set(expected_layer_ids):
            reasons.append("attention layer coverage is incomplete or ambiguous")
        if all_unknown:
            reasons.append("uncorrelated dispatch in capture")
        calls.append({"invocation": call["invocation"], "draft_length": call["drafts"],
                      "status": "UNKNOWN" if reasons else "OBSERVED",
                      "reasons": sorted(set(reasons)), "dispatches": events,
                      "vec_observed": None if reasons else any(e["kernel"] == "VEC" for e in events)})
    if set(bindings) - seen_keys:
        for call in calls:
            call.update(status="UNKNOWN", vec_observed=None)
            call["reasons"].append("unmatched layer binding in capture")
    return {"calls": calls, "status": "OBSERVED" if calls and all(c["status"] == "OBSERVED" for c in calls) else "UNKNOWN",
            "uncorrelated_dispatch_counts": trace["uncorrelated_dispatch_counts"],
            "limitations": ["layer binding truth, event delivery, source and binary identity unverified",
                            "HIP residency and output correctness unverified",
                            "observations cover only captured calls; no performance conclusion"]}
