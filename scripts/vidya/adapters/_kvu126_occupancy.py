"""Strict projection input verification for the existing np-ctx-kvu source.

No new source class or grading rule. Only original plan-bound paired records
can provide an occupancy-gap observation; incomplete records refuse.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from pathlib import Path

from claim_tuple import ProjectionError


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(root, ref):
    path = root / ref["path"]
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 64 << 20:
        raise ProjectionError(f"invalid evidence path: {path}")
    raw = path.read_bytes()
    if sha(raw) != ref["sha256"]:
        raise ProjectionError(f"evidence hash mismatch: {path}")
    return raw


def obj(root, ref):
    value = json.loads(pinned(root, ref))
    if not isinstance(value, dict):
        raise ProjectionError("expected evidence object")
    return value


def producer_hash(row):
    return sha(json.dumps({k: v for k, v in row.items() if k != "row_sha256"},
                          sort_keys=True, separators=(",", ":"), default=str).encode())


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def verify(carrier, strict_row):
    if carrier.get("schema") != "epyc.kvu126.occupancy_gap.v1" or carrier.get("row_sha256") != producer_hash(carrier):
        raise ProjectionError("invalid or tampered occupancy carrier")
    plan_path, records_path = Path(carrier["plan_path"]), Path(carrier["evidence_index_path"])
    plan = obj(plan_path.parent, {"path": plan_path.name, "sha256": carrier["plan_sha256"]})
    records = obj(records_path.parent, {"path": records_path.name, "sha256": carrier["evidence_index_sha256"]})
    if plan.get("schema") != "epyc.kvu126.prospective_plan.v1" or records.get("schema") != "epyc.kvu126.evidence_index.v1":
        raise ProjectionError("invalid plan or evidence-index schema")
    expected_arms = {"np8_32k": (8, 32768), "np8_48k": (8, 49152), "np8_64k": (8, 65536), "np4_96k": (4, 98304)}
    pairs = [(x["left"], x["right"]) for x in plan["comparisons"]]
    if set(plan["arms"]) != set(expected_arms) or set(records["arms"]) != set(expected_arms) or len(pairs) != 2 or set(pairs) != {("np8_32k", "np8_64k"), ("np8_48k", "np4_96k")}:
        raise ProjectionError("incomplete arm/comparison declaration")
    if (carrier.get("left_arm"), carrier.get("right_arm")) != ("np8_48k", "np4_96k"):
        raise ProjectionError("occupancy gap is not the equal-nominal-token pair")
    minimum_samples, minimum_waves = plan.get("min_occupancy_samples"), plan.get("min_waves_per_arm")
    tolerance = plan.get("max_occupancy_fraction_gap")
    if type(minimum_samples) is not int or minimum_samples < 2 or type(minimum_waves) is not int or minimum_waves < 1 or not number(tolerance) or tolerance > 1 or not plan.get("noise_rule"):
        raise ProjectionError("pre-run decision inputs are missing")
    identity, pins = plan["expected_identity"], plan["producer_pins"]
    if set(pins) != {"kvu_cpu_matrix.py", "kvu126_capture.py", "kvu126_identity.py", "kvu126_compare.py", "kvu126_build.py", "kvu126_finalize.py"} or any(not re.fullmatch(r"[0-9a-f]{64}", x) for x in pins.values()):
        raise ProjectionError("invalid producer pins")
    for key, count in (("source_commit", 40), ("model_sha256", 64), ("binary_sha256", 64)):
        if not re.fullmatch(rf"[0-9a-f]{{{count}}}", identity.get(key, "")):
            raise ProjectionError("invalid expected identity")
    root = records_path.parent
    build = obj(root, records["build_receipt"])
    dsos = build.get("dso_sha256")
    if (build.get("schema") != "epyc.kvu126.build_identity.v1" or build.get("source_tree_clean") is not True or
        build.get("source_commit") != identity["source_commit"] or build.get("binary_sha256") != identity["binary_sha256"] or
        not isinstance(dsos, dict) or not dsos or any(not re.fullmatch(r"[0-9a-f]{64}", v) for v in dsos.values())):
        raise ProjectionError("build identity missing or inconsistent")
    medians, representative, evidence = {}, None, []
    for name, (np, length) in expected_arms.items():
        spec = plan["arms"][name]
        if (spec.get("np"), spec.get("L"), spec.get("c")) != (np, length, 524288):
            raise ProjectionError("arm geometry mismatch")
        entries = records["arms"][name]
        if len(entries) < minimum_waves:
            raise ProjectionError("incomplete wave denominator")
        seen, per_wave = set(), []
        for item in entries:
            rows = [json.loads(line) for line in pinned(root, item["wave_file"]).splitlines() if line.strip()]
            matches = [r for r in rows if r.get("wave") == item["wave"]]
            if len(matches) != 1:
                raise ProjectionError("missing or ambiguous original wave")
            wave = matches[0]
            strict_row(wave, f"occupancy wave {name}")
            if (wave.get("np"), wave.get("L"), wave.get("c")) != (np, length, 524288) or wave.get("result") != "OK" or wave.get("kv_unified_from_log") != "true" or type(wave.get("wave")) is not int or wave["wave"] < 1:
                raise ProjectionError("invalid target wave")
            for key in ("binary_sha256", "model", "cpu_list", "threads", "prompt_mode", "mtp", "draft_depth", "cache_idle_slots_argv"):
                if wave.get(key) != identity.get(key) or wave.get(key) is None:
                    raise ProjectionError("wave identity differs from pre-run plan")
            for field in ("prompt_n", "cache_n", "decode_tps_per_stream"):
                vals = wave.get(field)
                if not isinstance(vals, list) or len(vals) != np or not all(number(v) for v in vals):
                    raise ProjectionError("missing per-stream original data")
            if wave["row_sha256"] in seen:
                raise ProjectionError("duplicate original wave")
            seen.add(wave["row_sha256"])
            runtime = obj(root, item["runtime_receipt"])
            if (runtime.get("schema") != "epyc.kvu126.runtime_identity.v1" or runtime.get("row_sha256") != wave["row_sha256"] or
                runtime.get("plan_sha256") != carrier["plan_sha256"] or runtime.get("producer_pins") != pins or
                runtime.get("binary_sha256") != identity["binary_sha256"] or runtime.get("model_sha256") != identity["model_sha256"] or
                runtime.get("mapped_dso_sha256") != dsos or not runtime.get("pid_birth_identity")):
                raise ProjectionError("original runtime receipt missing or mismatched")
            before, after = runtime.get("before", {}), runtime.get("after", {})
            for key in ("pid_birth_identity", "binary_sha256", "model_sha256", "mapped_dso_sha256"):
                if before.get(key) != runtime.get(key) or after.get(key) != runtime.get(key):
                    raise ProjectionError("runtime snapshots differ")
            occ = obj(root, item["occupancy_file"])
            if occ.get("schema") != "epyc.kvu126.native_unique_cells.v1" or occ.get("row_sha256") != wave["row_sha256"]:
                raise ProjectionError("occupancy not bound to wave")
            occ_dir = (root / item["occupancy_file"]["path"]).parent
            raw = obj(occ_dir, {"path": occ["native_source"], "sha256": occ["native_source_sha256"]})
            if any(raw.get(k) != occ.get(k) for k in ("row_sha256", "decode_start_monotonic_s", "decode_end_monotonic_s", "samples")):
                raise ProjectionError("native occupancy source differs")
            start, end = occ.get("decode_start_monotonic_s"), occ.get("decode_end_monotonic_s")
            samples = occ.get("samples")
            if not number(start) or not number(end) or end <= start or not isinstance(samples, list) or len(samples) < minimum_samples:
                raise ProjectionError("occupancy window incomplete")
            values, last = [], None
            for sample in samples:
                ts, req, cells = sample.get("monotonic_s"), sample.get("request_start_monotonic_s"), sample.get("unique_cells")
                if (not number(ts) or not number(req) or type(cells) is not int or not 0 <= cells <= 524288 or
                    not start <= req <= ts <= end or (last is not None and ts <= last) or
                    sample.get("pid_birth_identity") != runtime["pid_birth_identity"]):
                    raise ProjectionError("invalid in-window native occupancy sample")
                text = sample.get("metrics_text")
                if not isinstance(text, str):
                    raise ProjectionError("missing raw native metric response")
                metric = "llamacpp:kv_cache_used_cells"
                metric_values = re.findall(rf"^{re.escape(metric)}\s+(\S+)\s*$", text, re.M)
                types = re.findall(rf"^# TYPE {re.escape(metric)} (\w+)\s*$", text, re.M)
                helps = re.findall(rf"^# HELP {re.escape(metric)} (.+)\s*$", text, re.M)
                try:
                    parsed = float(metric_values[0]) if len(metric_values) == 1 else float("nan")
                except ValueError as exc:
                    raise ProjectionError("invalid native metric value") from exc
                if types != ["gauge"] or helps != ["Number of occupied unique KV cache cells."] or not math.isfinite(parsed) or parsed != cells:
                    raise ProjectionError("native metric response does not support sample")
                values.append(cells); last = ts
            if not number(before.get("captured_monotonic_s")) or not number(after.get("captured_monotonic_s")) or not before["captured_monotonic_s"] < samples[0]["monotonic_s"] <= samples[-1]["monotonic_s"] < after["captured_monotonic_s"]:
                raise ProjectionError("runtime identity does not span samples")
            per_wave.append(statistics.median(values))
            evidence.append({"arm": name, "wave_sha256": wave["row_sha256"], "runtime_sha256": item["runtime_receipt"]["sha256"],
                             "occupancy_sha256": item["occupancy_file"]["sha256"], "window": [start, end],
                             "pid_birth_identity": runtime["pid_birth_identity"], "binary_sha256": runtime["binary_sha256"],
                             "model_sha256": runtime["model_sha256"], "mapped_dso_sha256": runtime["mapped_dso_sha256"],
                             "producer_pins": runtime["producer_pins"],
                             "samples": values, "prompt_n": wave["prompt_n"], "cache_n": wave["cache_n"],
                             "recurrent_checkpoint_position": None})
            if name == "np8_48k":
                representative = wave
        medians[name] = statistics.median(per_wave)
    left, right = medians["np8_48k"], medians["np4_96k"]
    if carrier.get("left_median_cells") != left or carrier.get("right_median_cells") != right or carrier.get("absolute_gap_cells") != abs(left - right):
        raise ProjectionError("stated occupancy gap does not rederive")
    return representative, abs(left - right), evidence
