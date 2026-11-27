#!/usr/bin/env python3
"""Reconcile the pinned W66 light canary using retained local evidence only."""

import argparse
from collections import Counter, defaultdict
import csv
import gzip
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re
from statistics import median
import subprocess


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "artifacts/analysis/ap-w66-replay-inputs/requests.json"
DEFAULT_OUTPUT = ROOT / "artifacts/analysis/ap-w66-trace"
SERVER_ROOT = Path("ws58-a3b-revalidate-20261126/coverage/persistent-serving/runs/final-01")
BENCHMARKS = {
    "S5-r2": "ak-c22-prodcfg-a3b-gpu-20261126-r2",
    "S1-r2": "ak-c22-prodcfg-27b-gpu-20261126-r2",
}
SAMPLER_FIELDS = (
    "temperature", "top_p", "top_k", "min_p", "presence_penalty", "repeat_penalty", "seed",
)
TIMERS = {"prompt": ("prompt_n", "prompt_ms"), "decode": ("predicted_n", "predicted_ms")}
WIRE_FIELDS = (
    "seq", "slot", "body_ref", "t0", "forwarded_at", "wall_s", "client_wall_s", "client_ttft_s",
    "delivered_ttft_s", "ttft_s", "prompt_n", "cache_n", "predicted_n", "prompt_ms", "predicted_ms",
    "draft_n", "draft_accepted", "finish_reason", "generation_complete", "http_status",
    "transport_error", "server_error", "first_body_s", "queue_wait_s", "reasoning_tokens",
    "reasoning_characters", "tool_calls",
)
SERVER_EVENT = re.compile(r"^(\d+)\.(\d+)\.(\d+)\.(\d+) . slot\s+(\w+): id\s+(\d+) \| task\s+(\d+) \| (.*)$")
NATIVE_TIMING = re.compile(r"(prompt eval|eval) time =\s*([\d.]+) ms /\s*(\d+) tokens")
BATCH = re.compile(r"prefill-budget: iter (\d+): decode_rows = (\d+) \(slots (\d+)\), prompt = (\d+) \(slots (\d+)\)")
PROGRESS = re.compile(r"n_decoded =\s*(\d+), tg =\s*([\d.]+) t/s, tg_3s =\s*([\d.]+) t/s")
RELEASE = re.compile(r"n_tokens = (\d+), truncated = (\d+)")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def source(path):
    return {"path": str(path), "sha256": digest(path.read_bytes())}


def jsonl(path):
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def git_blob(revision, path):
    return subprocess.check_output(["git", "show", f"{revision}:{path}"], cwd=ROOT)


def union_seconds(intervals):
    seconds = 0.0
    end = -math.inf
    for start, stop in sorted(intervals):
        if stop > end:
            seconds += stop - max(start, end)
            end = stop
    return seconds


def intersection(a, b):
    start, stop = max(a[0], b[0]), min(a[1], b[1])
    return (start, stop) if stop > start else None


def server_records(log):
    tasks = defaultdict(dict)
    batches = []
    for line_number, line in enumerate(log.read_text().splitlines(), 1):
        event = SERVER_EVENT.match(line)
        if event:
            mins, secs, ms, us, kind, slot, task_id, detail = event.groups()
            instant = int(mins) * 60 + int(secs) + int(ms) / 1e3 + int(us) / 1e6
            task = tasks[int(task_id)]
            task["slot"] = int(slot)
            if kind in {"launch_slot_", "release", "create_check"}:
                task.setdefault(kind, []).append({"at": instant, "line": line_number, "detail": detail})
            timing = NATIVE_TIMING.match(detail.lstrip())
            progress = PROGRESS.match(detail)
            if timing:
                label, duration, tokens = timing.groups()
                phase = "prompt" if label == "prompt eval" else "decode"
                task[phase] = {"at": instant, "line": line_number, "ms": duration, "n": int(tokens)}
            if progress:
                tokens, rate, window_rate = progress.groups()
                task.setdefault("decode_progress", []).append(
                    {"at": instant, "line": line_number, "n": int(tokens),
                     "tok_s": float(rate), "last_3s_tok_s": float(window_rate)}
                )
        batch = BATCH.search(line)
        if batch:
            mins, secs, ms, us = map(int, line.split()[0].split("."))
            batches.append({
                "at": mins * 60 + secs + ms / 1e3 + us / 1e6, "line": line_number,
                **dict(zip(("iteration", "decode_rows", "decode_slots", "prompt_rows", "prompt_slots"),
                           map(int, batch.groups()))),
            })
    return dict(tasks), batches


def native_intervals(task, prompt_ms, decode_ms):
    end = task["decode"]["at"]
    decode_start = end - float(decode_ms) / 1000
    return {
        "prompt": (decode_start - float(prompt_ms) / 1000, decode_start),
        "decode": (decode_start, end),
    }


def read_body(path):
    compressed = path.read_bytes()
    decoded = gzip.decompress(compressed)
    return json.loads(decoded), compressed, decoded


def body_record(path):
    body, compressed, decoded = read_body(path)
    messages = body["messages"]
    return ({
        "body_ref": path.name, "gzip_sha256": digest(compressed), "decoded_sha256": digest(decoded),
        "decoded_bytes": len(decoded), "messages": len(messages),
        "message_roles": dict(Counter(message["role"] for message in messages)),
        "tools": len(body.get("tools") or []),
        "sampling": {field: body.get(field) for field in SAMPLER_FIELDS},
        "template": body.get("chat_template_kwargs"),
        "max_completion_tokens": body.get("max_completion_tokens"),
    }, body["id_slot"])


def reconcile(pins, csv_blob, tasks):
    allowed = {(row["epoch"], row["id"], row["wire_receipt_path"]) for row in pins["requests"]}
    rows = {}
    log_keys = defaultdict(list)
    for task_id, event in tasks.items():
        if {"prompt", "decode"} <= event.keys():
            log_keys[(event["slot"], event["prompt"]["n"], event["decode"]["n"])].append(task_id)

    exports = defaultdict(dict)
    for row in csv.DictReader(io.StringIO(csv_blob.decode())):
        key = (row["epoch"], row["id"], row["wire_receipt_path"])
        if key in allowed:
            seq = int(row["seq"])
            require(seq not in exports[key], f"duplicate exported receipt {key}: {seq}")
            exports[key][seq] = row

    inputs = []
    for key in sorted(allowed):
        epoch, unit, path = key
        ledger = Path(path)
        inputs.append(source(ledger))
        native_rows = jsonl(ledger)
        require(len(native_rows) == 70 and {row["seq"] for row in native_rows} == set(range(1, 71))
                and len(exports[key]) == 70, f"receipt denominator mismatch for {unit}")
        for row in native_rows:
            seq = row["seq"]
            exported = exports[key][seq]
            wire_hash = digest(json.dumps(row, sort_keys=True, separators=(",", ":")).encode())
            require(row["label"] == unit and row["backend"] == exported["backend"] == "gpu"
                    and wire_hash == exported["receipt_sha256"], f"invalid receipt identity {unit}/{seq}")
            for field in WIRE_FIELDS:
                value = "" if row.get(field) is None else str(row[field])
                require(value == exported[field], f"wire/CSV field mismatch {unit}/{seq}/{field}")
            body, slot = body_record(ledger.parent / row["body_ref"])
            require(slot == row["slot"], f"body slot mismatch {unit}/{seq}")
            # Timing text is rounded to .01 ms by the native logger. Restrict ambiguous
            # candidates rather than assigning a task id from ordering or stream rate.
            candidates = [task_id for task_id in log_keys[(row["slot"], row["prompt_n"], row["predicted_n"])]
                          if all(abs(float(tasks[task_id][phase]["ms"]) - row[field]) <= 0.00501
                                 for phase, (_, field) in TIMERS.items())]
            require(len(candidates) == 1, f"ambiguous native log join {unit}/{seq}: {candidates}")
            task_id = candidates[0]
            timing = native_intervals(tasks[task_id], row["prompt_ms"], row["predicted_ms"])
            record = {
                **row, **body, "wire_receipt_path": path, "receipt_sha256": wire_hash,
                "epoch": epoch, "id": unit, "mode": unit.split("-")[4].upper(),
                "server_task": task_id, "native_intervals": timing,
                "request_window": tuple(json.loads(exported["forwarded_request_window"])[name]
                                        for name in ("start_epoch_s", "receipt_epoch_s")),
                "receipt_after_terminal": exported["receipt_ends_after_task_terminal"] == "True",
                "observed_role": json.loads(exported["role_metadata"])["observed_role"],
                "post_native_residual_s": row["client_wall_s"] -
                (row["prompt_ms"] + row["predicted_ms"]) / 1000,
            }
            rows[(epoch, unit, seq)] = record
    require(len(rows) == len({row["server_task"] for row in rows.values()}) == 140,
            "receipt/native cardinality mismatch")
    last_by_slot = {}
    for row in sorted(rows.values(), key=lambda item: item["forwarded_at"]):
        previous = last_by_slot.get(row["slot"])
        row["preceding_receipt_seq"] = previous["seq"] if previous else None
        row["preceding_server_task"] = previous["server_task"] if previous else None
        row["preceding_retained_tokens"] = None
        if previous:
            release = tasks[previous["server_task"]]["release"][-1]
            launch = tasks[row["server_task"]]["launch_slot_"][0]["at"]
            require(release["at"] < launch, f"slot reuse out of order {row['id']}/{row['seq']}")
            event_tokens = RELEASE.search(release["detail"])
            require(event_tokens is not None, f"missing recorded release for {previous['server_task']}")
            row["preceding_retained_tokens"] = int(event_tokens[1])
        last_by_slot[row["slot"]] = row
    return rows, inputs


def resource_stats(samples, window):
    current = [sample for sample in samples if window[0] <= sample["epoch_s"] <= window[1]]
    return {
        "samples": len(current), "vram_min_bytes": min((r["vram_bytes"] for r in current), default=None),
        "gpu_busy_median_pct": median([r["gpu_busy_percent"] for r in current]) if current else None,
        "kfd_pids": sorted({pid for sample in current for pid in sample["kfd_pids"]}),
        "samples_with_gpu_process_resident": sum(
            bool(sample["gpu"] and sample["gpu"]["pid"] in sample["kfd_pids"]
                 and sample["vram_bytes"] > 0)
            for sample in current
        ),
    }


def join_peers(rows, tasks, samples):
    lookup = {row["server_task"]: row for row in rows.values()}
    phases = {task_id: native_intervals(task, task["prompt"]["ms"], task["decode"]["ms"])
              for task_id, task in tasks.items() if {"prompt", "decode"} <= task.keys()}
    for row in rows.values():
        peers = []
        for task_id, timing in phases.items():
            native = tasks[task_id]
            if native["slot"] == row["slot"]:
                continue
            overlaps = {}
            for phase, window in row["native_intervals"].items():
                for peer_phase, peer_window in timing.items():
                    overlap = intersection(window, peer_window)
                    if overlap:
                        overlaps[f"{phase}/{peer_phase}"] = overlap
            if overlaps:
                other = lookup.get(task_id)
                peers.append({
                    "server_task": task_id, "slot": native["slot"],
                    "unit": other["id"] if other else None, "seq": other["seq"] if other else None,
                    "fresh_tokens": native["prompt"]["n"], "windows": overlaps,
                })
        row["peers"] = peers
        for phases_key in ("prompt/prompt", "prompt/decode", "decode/prompt", "decode/decode"):
            row[f"peer_{phases_key}_s"] = union_seconds(
                peer["windows"][phases_key] for peer in peers if phases_key in peer["windows"]
            )
        row["resources"] = resource_stats(samples, row["request_window"])


def rank_rows(rows):
    # Descriptive same-run reference. Retain direction and support count, even
    # if the comparison is slower than the target or the target has no peer.
    material = list(rows.values())
    for row in material:
        context = row["prompt_n"] + row["cache_n"]
        controls = [candidate for candidate in material
                    if candidate is not row
                    and candidate["mode"] == row["mode"]
                    and candidate["sampling"] == row["sampling"]
                    and candidate["template"] == row["template"]
                    and candidate["tools"] == row["tools"]
                    and candidate["finish_reason"] == row["finish_reason"]
                    and abs(candidate["prompt_n"] + candidate["cache_n"] - context) <= context * .1
                    and abs(candidate["predicted_n"] - row["predicted_n"]) <= max(64, row["predicted_n"] * .5)
                    and 0.5 <= max(candidate["prompt_n"], 64) / max(row["prompt_n"], 64) <= 2]
        row["reference_seqs"] = sorted(candidate["seq"] for candidate in controls)
        for phase, (_, field) in TIMERS.items():
            samples = [candidate[field] / 1000 for candidate in controls]
            if phase == "decode":
                samples = [candidate[field] * row["predicted_n"] / candidate["predicted_n"] / 1000
                           for candidate in controls if candidate["predicted_n"]]
            reference = median(samples) if len(samples) >= 2 else None
            row[f"{phase}_reference_s"] = reference
            row[f"{phase}_excess_s"] = row[field] / 1000 - reference if reference is not None else None
        excesses = (row["prompt_excess_s"], row["decode_excess_s"])
        row["native_excess_s"] = sum(excesses) if all(value is not None for value in excesses) else None


def tool_summary(path, request_windows):
    calls = []
    missing = 0
    for message in json.loads(path.read_bytes())["messages"]:
        for event in message.get("content", []):
            if event.get("type") != "tool":
                continue
            timing = event.get("time") or {}
            start, end = timing.get("ran"), timing.get("completed")
            if start is None or end is None or start > end:
                missing += 1
                continue
            calls.append((start / 1000, end / 1000))
    overlaps = [overlap for call in calls for request in request_windows
                if (overlap := intersection(call, request))]
    return {
        "timed_calls": len(calls), "unknown_intervals": missing,
        "sum_seconds": sum(end - start for start, end in calls),
        "union_seconds": union_seconds(calls), "overlap_request_union_s": union_seconds(overlaps),
        "source": source(path),
    }


def summarize(rows, pins):
    revision = pins["source_commit"]
    csv_path = str(Path(pins["source_csv"]).with_name("TASKS.csv"))
    blob = git_blob(revision, csv_path)
    tasks = {row["id"]: row for row in csv.DictReader(io.StringIO(blob.decode()))
             if row["epoch"] == pins["requests"][0]["epoch"]}
    report = {"task_csv": {"path": csv_path, "sha256": digest(blob)}, "by_mode": {}}
    for mode in sorted({row["mode"] for row in rows.values()}):
        group = [row for row in rows.values() if row["mode"] == mode]
        published = tasks[group[0]["id"]]
        unit_root = Path(group[0]["wire_receipt_path"]).parent.parent
        result = json.loads((unit_root / "RESULT.json").read_bytes())
        worker = float(published["reported_model_wall_s"])
        require(result["model_wall_s"] == worker, f"worker time mismatch for {mode}")
        totals = {name: sum(row[name] for row in group if row[name] is not None)
                  for name in ("prompt_n", "cache_n", "predicted_n", "draft_n", "draft_accepted")}
        published_tokens = json.loads(published["tokens"])
        require(all(value == published_tokens[name]["known_sum"] for name, value in totals.items())
                and len(group) == int(published["forwarded_receipts"]), f"published counts mismatch for {mode}")
        windows = [row["request_window"] for row in group]
        timed_tools = tool_summary(unit_root / "OPEN-CODE-SESSION.json", windows)
        seconds = {phase: sum(row[field] for row in group) / 1000
                   for phase, (_, field) in TIMERS.items()}
        published_native = json.loads(published["approximate_native_phase_rates"])
        native_union = {phase: union_seconds(row["native_intervals"][phase] for row in group)
                        for phase in TIMERS}
        require(all(math.isclose(seconds[phase], published_native[phase]["summed_native_phase_s"],
                                 abs_tol=0.00001) for phase in TIMERS), f"native times mismatch for {mode}")
        median_rate = median(row["predicted_n"] * 1000 / row["predicted_ms"] for row in group)
        require(math.isclose(median_rate, json.loads(published["latency"])["decode_tok_s"]["median"]),
                f"native median mismatch for {mode}")
        unknown = {name: sum(row.get(name) is None for row in group)
                   for name in ("predicted_n", "prompt_ms", "predicted_ms", "draft_n", "draft_accepted",
                                "client_ttft_s", "reasoning_tokens")}
        erase_path = unit_root / "SLOT-ERASE.json"
        erase = json.loads(erase_path.read_bytes())
        first = min(group, key=lambda row: row["seq"])
        require(erase["id_slot"] == first["slot"] and first["cache_n"] == 0,
                f"unverified empty-slot starting point for {mode}")
        require(result["generation_unknown_requests"] == unknown["predicted_n"],
                f"worker receipt unknowns mismatch for {mode}")
        report["by_mode"][mode] = {
            "receipts": len(group), "unknown": unknown, **totals, "native_seconds": seconds,
            "native_union_seconds": native_union, "worker_seconds": worker,
            "worker_token_rate": totals["predicted_n"] / worker,
            "decode_weighted_token_rate": totals["predicted_n"] / seconds["decode"],
            "decode_median_token_rate": median_rate, "request_wall_union_s": union_seconds(windows),
            "estimated_native_phase_union_s": union_seconds(
                window for row in group for window in row["native_intervals"].values()
            ),
            "worker_minus_native_sum_s": worker - sum(seconds.values()),
            "tools": timed_tools, "finish_reasons": Counter(row["finish_reason"] for row in group),
            "noncomplete_receipts": sum(row["generation_complete"] is not True for row in group),
            "transport_or_server_errors": sum(bool(row["transport_error"] or row["server_error"]) for row in group),
            "after_task_terminal_receipts": sum(row["receipt_after_terminal"] for row in group),
            "matched_controls_receipts": sum(len(row["reference_seqs"]) >= 2 for row in group),
            "source_worker_result": source(unit_root / "RESULT.json"),
            "source_slot_erase": source(erase_path), "slot_erase": erase,
            "first_request_cached_tokens": first["cache_n"],
        }
    report["combined"] = {}
    for phase, (count, _) in TIMERS.items():
        seconds = union_seconds(row["native_intervals"][phase] for row in rows.values())
        tokens = sum(row[count] for row in rows.values())
        report["combined"][phase] = {
            "seconds": seconds, "tokens": tokens, "tokens_per_union_active_second": tokens / seconds,
        }
    return report


def replay_manifest(pins, rows, native, batches, summary):
    targets = []
    for pin in pins["requests"]:
        key = (pin["epoch"], pin["id"], int(pin["seq"]))
        row = rows[key]
        for name in ("slot", "receipt_sha256", "gzip_sha256", "decoded_sha256", "body_ref",
                     "prompt_n", "cache_n", "prompt_ms", "predicted_n", "predicted_ms",
                     "client_ttft_s", "draft_accepted", "draft_n"):
            require(str(row[name]) == pin[name], f"target drift {key}/{name}")
        history = sorted((prior for prior in rows.values()
                          if prior["id"] == row["id"] and prior["slot"] == row["slot"]
                          and prior["forwarded_at"] < row["forwarded_at"]),
                         key=lambda prior: prior["forwarded_at"])
        task = native[row["server_task"]]
        last = history[-1]
        last_native = native[last["server_task"]]
        prior_release = last_native["release"][-1]
        wire_directory = Path(row["wire_receipt_path"]).parent
        prior_body, _, _ = read_body(wire_directory / last["body_ref"])
        target_body, _, _ = read_body(wire_directory / row["body_ref"])
        shared_prefix = 0
        for before, after in zip(prior_body["messages"], target_body["messages"]):
            if before != after:
                break
            shared_prefix += 1
        retained_tokens, truncated = map(int, RELEASE.search(prior_release["detail"]).groups())
        require(prior_release["at"] < task["launch_slot_"][0]["at"], f"predecessor order {key}")
        scans = [batch for batch in batches
                 if task["launch_slot_"][0]["at"] <= batch["at"] <= task["decode"]["at"]]
        targets.append({
            **pin, "body_path": str(Path(row["wire_receipt_path"]).parent / row["body_ref"]),
            "request_body_shape": {name: row[name] for name in ("messages", "message_roles", "tools",
                                                               "decoded_bytes", "sampling", "template",
                                                               "max_completion_tokens")},
            "server_task": row["server_task"], "server_events": task,
            "original_peers": row["peers"], "during_request_resources": row["resources"],
            "mixed_batch_iterations_while_target_active": [batch for batch in scans
                                                            if batch["prompt_slots"] and batch["decode_slots"]],
            "historical_slot_snapshot": None,
            "predecessor_reconstruction": {
                "slot_erase": summary["by_mode"][row["mode"]]["source_slot_erase"],
                "initial_slot_state": "empty by erase receipt and first request cache_n=0",
                "original_state_at_target": "historical KV/draft/checkpoint bytes unknown",
                "shared_wire_message_prefix_length": shared_prefix,
                "immediate_predecessor_message_count": len(prior_body["messages"]),
                "ordered_history": [{name: prior[name] for name in (
                    "seq", "body_ref", "receipt_sha256", "gzip_sha256", "decoded_sha256",
                    "prompt_n", "cache_n", "predicted_n", "draft_n", "draft_accepted", "server_task",
                )} for prior in history],
                "immediate_predecessor": {
                    "seq": last["seq"], "server_task": last["server_task"],
                    "release_log_line": prior_release["line"], "retained_tokens": retained_tokens,
                    "truncated": bool(truncated),
                },
                "independent_arms": "Erase the slot before each arm. Replay ordered sealed bodies without "
                "running tool calls. Compare predecessor token counts and finishes through the warmup "
                "chain and verify target native fresh/cached counts and rendered prefix identity. Historical "
                "predecessor output tokens, full KV/draft checkpoints and allocator state cannot be recovered "
                "from the saved bodies. A failed match uses independently rebuilt controlled prefixes for "
                "both arms with a reconstructed label. Retain divergent output lengths and run a fixed-length "
                "secondary decode control when the divergence confounds the comparison.",
            },
        })
    return targets


def benchmark_receipts(scratch):
    result = {}
    for label, unit in BENCHMARKS.items():
        directory = scratch / unit
        native_result = directory / "out/RESULT.json"
        verdict = scratch / "compute-flags/filing-done" / f"{unit}.verdict.json"
        receipt = source(native_result)
        require(receipt["sha256"] == json.loads(verdict.read_bytes())["verdict"]["native_result_sha256"],
                f"filing digest mismatch for {label}")
        report = json.loads(native_result.read_bytes())
        results_file = directory / "out/results.jsonl"
        visits = jsonl(results_file)
        by_kind = {}
        for kind in ("visit", "load"):
            units = [row for row in visits if row["arm"] == "C22" and row["kind"] == kind]
            requests = [request for row in units for request in row["req"]]
            by_kind[kind] = {
                "argv": units[0]["argv"], "units": len(units), "requests": len(requests),
                "prompt_sizes": sorted({row["prompt_n"] for row in requests}),
                "generation_sizes": sorted({row["predicted_n"] for row in requests}),
                "sum_tokens_per_summed_decode_second": sum(row["predicted_n"] for row in requests)
                * 1000 / sum(row["predicted_ms"] for row in requests),
                "paired_draft_accepted": sum(row["draft_n_accepted"] for row in requests),
                "paired_draft_proposed": sum(row["draft_n"] for row in requests),
            }
        result[label] = {
            "receipt": receipt, "visits_src": source(results_file), "filing": source(verdict),
            "sampler_source": source(directory / "ak_gate.py"), "native_verdict": report["native_verdict"],
            "reason": report["reason"], "aa": report["aa"], "per_arm": report["per_arm"],
            **by_kind,
        }
    return result


def write_outputs(output, rows, summary, replay):
    output.mkdir(parents=True, exist_ok=True)
    columns = (
        "epoch", "id", "mode", "seq", "slot", "server_task", "receipt_sha256", "observed_role",
        "body_ref", "gzip_sha256", "decoded_sha256", "messages", "message_roles", "tools", "decoded_bytes",
        "preceding_receipt_seq", "preceding_server_task", "preceding_retained_tokens",
        "sampling", "template", "max_completion_tokens", "prompt_n", "cache_n", "predicted_n",
        "prompt_ms", "predicted_ms", "ttft_s", "client_ttft_s", "delivered_ttft_s", "queue_wait_s",
        "first_body_s", "wall_s", "client_wall_s", "post_native_residual_s", "draft_n", "draft_accepted",
        "reasoning_tokens", "reasoning_characters", "tool_calls",
        "finish_reason", "generation_complete", "http_status", "transport_error", "server_error",
        "receipt_after_terminal", "request_window",
        "native_intervals", "peer_prompt/prompt_s", "peer_prompt/decode_s", "peer_decode/prompt_s",
        "peer_decode/decode_s", "peers", "resources", "reference_seqs", "prompt_reference_s",
        "prompt_excess_s", "decode_reference_s", "decode_excess_s", "native_excess_s", "native_seconds_rank",
        "prompt_seconds_rank", "decode_seconds_rank", "prompt_excess_rank", "decode_excess_rank",
        "native_excess_rank",
    )
    ranked_metrics = {
        "native_seconds_rank": lambda row: row["prompt_ms"] + row["predicted_ms"],
        "prompt_seconds_rank": lambda row: row["prompt_ms"],
        "decode_seconds_rank": lambda row: row["predicted_ms"],
        "prompt_excess_rank": lambda row: row["prompt_excess_s"],
        "decode_excess_rank": lambda row: row["decode_excess_s"],
        "native_excess_rank": lambda row: row["native_excess_s"],
    }
    for name, measure in ranked_metrics.items():
        members = [row for row in rows.values() if measure(row) is not None]
        for rank, row in enumerate(sorted(members, key=lambda row: (-measure(row), row["id"], row["seq"])), 1):
            row[name] = rank
    with (output / "requests.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for _, row in sorted(rows.items()):
            writer.writerow({name: json.dumps(row[name], sort_keys=True, separators=(",", ":"))
                             if isinstance(row.get(name), (list, tuple, dict)) else row.get(name)
                             for name in columns})
    for name, payload in (("summary.json", summary), ("replay-manifest.json", replay)):
        (output / name).write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")
    tracked = ("requests.csv", "summary.json", "replay-manifest.json")
    (output / "SHA256SUMS").write_text(
        "".join(f"{digest((output / name).read_bytes())}  {name}\n" for name in sorted(tracked))
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-root", type=Path, default=Path("/mnt/raid0/llm/tmp"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    pins = json.loads(INPUT.read_bytes())
    csv_blob = git_blob(pins["source_commit"], pins["source_csv"])
    require(digest(csv_blob) == pins["source_csv_sha256"], "published REQUESTS.csv digest mismatch")
    server_dir = args.scratch_root / SERVER_ROOT
    log = server_dir / "out-gpu/server.log"
    resource_log = server_dir / "resource-samples.jsonl"
    native, batches = server_records(log)
    rows, wire_sources = reconcile(pins, csv_blob, native)
    join_peers(rows, native, jsonl(resource_log))
    rank_rows(rows)
    summary = summarize(rows, pins)
    summary["benchmarks"] = benchmark_receipts(args.scratch_root)
    proofs = server_dir / "out-gpu/proofs.json"
    configuration = server_dir / "out-gpu/server.json"
    cache_directory = server_dir / "out-gpu/slot-cache"
    require(cache_directory.is_dir() and not any(cache_directory.iterdir()),
            "recorded empty slot-cache directory differs")
    replay = {
        "schema": "epyc.ap-w66.trace-replay.v1",
        "source_commit": pins["source_commit"], "source_csv": pins["source_csv"],
        "source_csv_sha256": pins["source_csv_sha256"],
        "inputs": {"pins": {"path": str(INPUT.relative_to(ROOT)), "sha256": digest(INPUT.read_bytes())},
                   "wire_ledgers": wire_sources, "server_log": source(log), "resource_log": source(resource_log),
                   "server_configuration": source(configuration),
                   "server_recipe": source(server_dir / "out-gpu/recipe-derived.json"),
                   "server_live_proof": source(server_dir / "out-gpu/live.json"), "server_proofs": source(proofs)},
        "historical_slot_cache_directory": {"path": str(cache_directory), "retained_entries": 0},
        "historical_runtime": {
            **json.loads(configuration.read_bytes()),
            "artifact_identity": json.loads(proofs.read_bytes()),
        },
        "native_overlap_scope": "Phase intervals estimated by right-aligning original native timers "
        "to the final decode log timestamp. Prefill-budget events and decode progress have observed "
        "server-relative timestamps. A mixed batch event alone does not record its slot IDs.",
        "requests": replay_manifest(pins, rows, native, batches, summary),
    }
    write_outputs(args.output, rows, summary, replay)


if __name__ == "__main__":
    main()
