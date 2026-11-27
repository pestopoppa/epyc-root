"""Reduce private W66 rowflow evidence to shareable numeric paired receipts."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import statistics

TASK = re.compile(r"id\s+(\d+)\s+\| task\s+(\d+)\s+\|")
PREFILL = re.compile(r"prompt eval time\s*=\s*([0-9.]+) ms /\s*(\d+) tokens")
DECODE = re.compile(r"\|\s+eval time\s*=\s*([0-9.]+) ms /\s*(\d+) tokens")
BATCH = re.compile(r"iter (\d+): decode_rows = (\d+) \(slots (\d+)\), prompt = (\d+) \(slots (\d+)\)")
EMITTER = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.(\d+)")
PHASES = {"prefill": ("prompt_n", "prompt_ms"), "decode": ("predicted_n", "predicted_ms")}
GRADE_LINE = re.compile(r"^\| (ON|OFF) (\d+) \| (\d+) \| (Alone|Peer|Preserved) \| ([^|]+) \|")
ACCEPTED_JUDGMENTS = {"Accepted continuation", "Accepted summary", "Substantively accepted summary"}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def local_seconds(line):
    m, s, ms, us = EMITTER.match(line).groups()
    return int(m) * 60 + int(s) + int(ms) / 1000 + int(us) / 1000_000


def server_records(path):
    rows, batches = {}, []
    with path.open() as handle:
        for i, line in enumerate(handle, 1):
            if "prefill-budget:" in line:
                m = BATCH.search(line)
                if m:
                    iteration, decode, decode_slots, prefill, prefill_slots = map(int, m.groups())
                    if decode_slots and prefill_slots:
                        batches.append((local_seconds(line), iteration, decode, decode_slots,
                                        prefill, prefill_slots))
                continue
            task = TASK.search(line)
            if not task:
                continue
            slot, task = map(int, task.groups())
            if "launch_slot_:" in line:
                rows[task] = {"task": task, "slot": slot, "launch_log_line": i,
                              "launch_s_from_server_start": local_seconds(line)}
            if task not in rows:
                continue
            for key, pattern in (("prefill", PREFILL), ("decode", DECODE)):
                match = pattern.search(line)
                if match:
                    ms, n = match.groups()
                    rows[task][key] = [float(ms), int(n), i, local_seconds(line)]
    return rows, batches


def native_match(receipt, rows, batches):
    native = receipt["native"]
    matches = [row for row in rows.values() if row["slot"] == receipt["slot"] and
               all(phase in row and row[phase][1] == native[n]
                   and abs(row[phase][0] - native[ms]) <= .006
                   for phase, (n, ms) in PHASES.items())]
    if not matches:
        return {"match": "missing"}
    if len(matches) > 1:
        return {"match": "ambiguous", "candidate_task_ids": [x["task"] for x in matches]}
    row = matches[0].copy()
    decode_end = row["decode"][3]
    decode_start = decode_end - native["predicted_ms"] / 1000
    prefill_start = decode_start - native["prompt_ms"] / 1000
    for name, lo, hi in (("decode", decode_start, decode_end), ("prefill", prefill_start, decode_start)):
        during = [b for b in batches if lo <= b[0] <= hi]
        row[f"mixed_batches_{name}"] = len(during)
        row[f"mixed_batch_prompt_tokens_{name}"] = sum(b[4] for b in during)
        row[f"mixed_batch_decode_rows_{name}"] = sum(b[2] for b in during)
    row["match"] = "unique"
    return row


def compact(receipt, log_rows, batches):
    n = receipt["native"]
    return {"name": receipt["name"], "slot": receipt["slot"], "fresh": n["prompt_n"],
            "cached": n["cache_n"], "generated": n["predicted_n"],
            "prefill_s": n["prompt_ms"] / 1000, "decode_s": n["predicted_ms"] / 1000,
            "decode_tps": n["predicted_per_second"], "ttft_s": receipt["ttft_s"], "wall_s": receipt["wall_s"],
            "mtp_draft": n.get("draft_n"), "mtp_accepted": n.get("draft_n_accepted"),
            "finish": receipt["finish_reason"], "sse_sha256": receipt["private_sse_sha256"],
            "body_sha256": receipt["request_body_sha256"], "resource_samples": receipt["resource_sample_count"],
            "min_vram_b": receipt["min_vram_b"], "gpu_busy_pct": receipt["gpu_busy_pct"],
            "server_log": native_match(receipt, log_rows, batches)}


def resource_window(resources, windows):
    begin = max(window[0] for window in windows)
    end = min(window[1] for window in windows)
    observations = [sample for sample in resources if begin * 1e9 <= sample["mono_ns"] <= end * 1e9]
    if not observations:
        return {"samples": 0}
    return {"samples": len(observations),
            "gpu_busy_median_pct": statistics.median(r["gpu_busy_pct"] for r in observations),
            "vram_min_b": min(r["vram_b"] for r in observations),
            "vram_max_b": max(r["vram_b"] for r in observations),
            "all_owned_pid_resident": all(r["pid_in_kfd"] and r["store_hip"] for r in observations),
            "server_cpu_ticks_delta": observations[-1]["cpu_ticks"] - observations[0]["cpu_ticks"]}


def arm_view(arm, log_rows, batches, resources):
    control = {k: arm[k] for k in ("historical_cache_count_match", "historical_token_counts", "simultaneous")}
    control["target_reconstruction"] = arm["target_reconstruction"]
    control["target"] = compact(arm["target"], log_rows, batches)
    if arm["peer"]:
        control["peer"] = compact(arm["peer"], log_rows, batches)
        control["overlap"] = {k: arm[k] for k in
                              ("observed_peer_forward_offset_s", "historical_peer",
                               "peer_prefill_during_target_decode_s", "peer_decode_during_target_decode_s",
                               "peer_decode_during_target_prefill_s")}
        phases = arm["simultaneous"]["monotonic_s"]
        target, peer = phases[arm["target"]["name"]], phases[arm["peer"]["name"]]
        control["overlap_resource_samples"] = {
            f"target_{a}_with_peer_{b}": resource_window(resources, [target[a], peer[b]])
            for a, b in (("decode", "prefill"), ("decode", "decode"), ("prefill", "decode"))}
    return control


def effect_rows(pairs, arm_a, arm_b):
    rows = []
    for pair in pairs:
        a, b = pair[arm_a]["target"], pair[arm_b]["target"]
        rows.append({"ordinal": pair["ordinal"], "order": pair["order"],
                     "arm_a": a["name"], "arm_b": b["name"],
                     **{f"{key}_b_minus_a": b[key] - a[key] if None not in (a[key], b[key]) else None
                        for key in ("fresh", "cached", "generated", "prefill_s", "decode_s", "ttft_s", "wall_s")}})
    return rows


def quality_receipts(quality_dir, pairs):
    judgments = quality_dir / "README.md"
    custody = quality_dir / "output-custody.json"
    verdicts = {}
    for line in judgments.read_text().splitlines():
        match = GRADE_LINE.match(line)
        if match:
            mode, seq, ordinal, arm, quality = match.groups()
            verdicts[f"{mode}{seq}-p{ordinal}-{arm.lower()}-target"] = quality.strip()
    custody_by_name = {row["name"]: row for row in read(custody)}
    by_target = {}
    rows = []
    for label, target_pairs in pairs.items():
        by_target[label] = {}
        for arm in ("alone", "peer", "preserved"):
            streams = [pair[arm]["target"] for pair in target_pairs if arm in pair]
            if not streams:
                continue
            for stream in streams:
                name = stream["name"]
                bind = custody_by_name[name]
                if (stream["body_sha256"] != bind["request_body_sha256"]
                        or stream["sse_sha256"] != bind["private_sse_sha256"]
                        or stream["generated"] != bind["output_tokens"]):
                    raise ValueError(f"timing and quality custody mismatch for {name}")
                row = {"name": name, "turn_judgment": verdicts[name]}
                if "strictformat_compliant" in bind:
                    row["strictformat_compliant"] = bind["strictformat_compliant"]
                rows.append(row)
            count = Counter(verdicts[s["name"]] for s in streams)
            accepted = sum(count[key] for key in ACCEPTED_JUDGMENTS)
            wall_s = sum(stream["wall_s"] for stream in streams)
            by_target[label][arm] = {"observations": len(streams), "accepted_immediate_turns": accepted,
                                     "by_judgment": dict(count), "sum_target_wall_s": wall_s,
                                     "accepted_immediate_turns_per_target_request_hour": 3600 * accepted / wall_s}
    if not {x["name"] for x in rows} == verdicts.keys() == custody_by_name.keys():
        raise ValueError("timing, natural quality and stream custody sets differ")
    format_checks = [row["strictformat_compliant"] for row in rows if "strictformat_compliant" in row]
    return {"judgments_path": "../ap-w66-pair-quality/README.md", "judgments_sha256": sha(judgments),
            "custody_path": "../ap-w66-pair-quality/output-custody.json", "custody_sha256": sha(custody),
            "immediate_turns_only": True, "judged_targets": len(rows),
            "judgment_counts": dict(Counter(x["turn_judgment"] for x in rows)),
            "strict_format": {"checked": len(format_checks),
                              "compliant": format_checks.count(True)},
            "by_target": by_target, "joined": rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--quality-dir", type=Path)
    cli = p.parse_args()
    run = cli.run.resolve()
    ledger = read(run / "RESULT.json")
    log = run / "private" / "server.log"
    log_rows, batches = server_records(log)
    resources_path = run / "resources.jsonl"
    with resources_path.open() as handle:
        resources = [json.loads(line) for line in handle]

    def reduce(pairs):
        return [{"ordinal": pair["ordinal"], "order": pair["order"],
                 "fixed_token_cap": pair.get("fixed_token_cap"),
                 **{kind: arm_view(pair[kind], log_rows, batches, resources) for kind in pair["order"]
                    if kind in pair}} for pair in pairs]

    pairs = {label: reduce(items) for label, items in ledger["pairs"].items()}
    preservation = reduce(ledger["preserve_thinking"])
    summary = {
        "schema": "epyc.ap-w66-pair-summary.v1", "complete": ledger["complete"],
        "numeric_receipt_sha256": sha(run / "RESULT.json"), "private_log_sha256": sha(log),
        "resources_sha256": sha(resources_path),
        "launch": read(run / "launch.json"), "slots": read(run / "slots.json"),
        "loaded_llama_maps": read(run / "loaded-llama-maps.json"),
        "cleanup": read(run / "cleanup.json"), "attribution": ledger["attribution"],
        "pairs": pairs,
        "paired_effects": {label: effect_rows(items, "alone", "peer") for label, items in pairs.items()},
        "fixed_control": {label: reduce([record])[0] for label, record in ledger["fixed_controls"].items()},
        "preservation": preservation,
        "preservation_effects": effect_rows(preservation, "alone", "preserved"),
        "native_mixed_batch_window": "Approximate boundaries from server timing-print time minus reported native durations.",
        "source": {k: ledger[k] for k in ("source_csv_sha256", "sealed_input_manifest_sha256",
                                        "state_plan_sha256", "private_prefix_receipt_sha256")},
    }
    if summary["preservation_effects"]:
        vals = [x["prefill_s_b_minus_a"] for x in summary["preservation_effects"]]
        summary["median_off56_preserve_prefill_delta_s"] = statistics.median(vals)
    if cli.quality_dir:
        summary["quality"] = quality_receipts(cli.quality_dir, pairs)
    cli.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
