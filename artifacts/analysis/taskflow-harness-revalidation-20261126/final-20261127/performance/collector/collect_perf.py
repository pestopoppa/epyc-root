#!/usr/bin/env python3
"""Read-only, incremental A3B report. No inference, process control, network or pricing.
Refresh reads a prefix of each file once and records its SHA256. Re-running against
identical evidence produces identical output; concurrent append files are not an
atomic multi-file snapshot. Unknown numeric fields are None, never implicit zero.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics

LIVE = Path("/mnt/raid0/llm/tmp/ws58-a3b-frozen-revalidation-20261126/quality-runs/initial-01")
MAIN = Path("/mnt/raid0/llm/tmp/ws58-a3b-revalidate-20261126/main-comparison/runs")
OUT = Path(__file__).resolve().parent
TITLE_SYSTEM_SHA256 = 'a8382db91f60f816e5a7c3057edc771476ae817e2bd53273577e4bf4ab3add02'

class Reader:
    def __init__(self):
        self.sources, self.warnings = {}, []
    def bytes(self, path):
        path = Path(path)
        if not path.exists():
            return None
        data = path.read_bytes()
        self.sources[str(path)] = {"bytes_read": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        return data
    def obj(self, path, default=None):
        data = self.bytes(path)
        if data is None:
            return default
        try:
            return json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            self.warnings.append({"path": str(path), "error": str(exc), "partial_read": True})
            return default
    def lines(self, path):
        data = self.bytes(path)
        if data is None:
            return []
        rows = []
        for n, line in enumerate(data.splitlines(), 1):
            try:
                rows.append(json.loads(line))
            except (ValueError, UnicodeDecodeError) as exc:
                self.warnings.append({"path": str(path), "line": n, "error": str(exc), "partial_read": True})
        return rows

def numeric(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)

def known_sum(values):
    values = list(values)
    known = [v for v in values if numeric(v)]
    return {"known_sum": sum(known) if known else None, "known_count": len(known),
            "unknown_count": len(values) - len(known)}

def describe(values):
    values = [x for x in values if numeric(x)]
    return {"count": len(values), "min": min(values) if values else None,
            "median": statistics.median(values) if values else None,
            "max": max(values) if values else None}

def union_seconds(intervals):
    merged = []
    for a, b in sorted((a, b) for a, b in intervals if numeric(a) and numeric(b) and b > a):
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return sum(b-a for a,b in merged)

def wall_interval(row):
    a, wall = row.get("t0"), row.get("wall_s")
    return (a, a + wall) if numeric(a) and numeric(wall) and wall >= 0 else None

def phase_interval(row, phase):
    """Approximate native active windows, right-aligned to proxy response end.
    Native timers do not disclose exact phase boundaries. No claim of precise GPU
    occupancy or pure device rates is possible, especially with overlapping slots.
    """
    wall = wall_interval(row)
    p, d = row.get("prompt_ms"), row.get("predicted_ms")
    if wall is None or not all(numeric(v) and v >= 0 for v in (p, d)):
        return None
    if (p+d)/1000 > row["wall_s"] + .1:
        return None
    end = wall[1]
    return (end-(p+d)/1000, end-d/1000) if phase == "prompt" else (end-d/1000, end)

def request_envelope(rows, terminal=None):
    windows = [v for r in rows if (v := wall_interval(r))]
    after = [(max(a, terminal), b) for a,b in windows if numeric(terminal) and b > terminal]
    return {"first_forwarded_epoch_s": min((a for a,b in windows), default=None),
            "last_receipt_epoch_s": max((b for a,b in windows), default=None),
            "request_wall_union_s": union_seconds(windows) if windows else None,
            "unit_terminal_epoch_s": terminal,
            "receipts_ending_after_terminal": len(after) if numeric(terminal) else None,
            "post_terminal_request_wall_union_s": union_seconds(after) if numeric(terminal) else None,
            "last_receipt_after_terminal_s": max(0, max((b for a,b in windows), default=terminal)-terminal)
                if numeric(terminal) else None,
            "interpretation": "forwarded request wall envelope includes queueing, cancellation and post-task drain; never task completion latency"}

def attach_timing(row, result):
    window = wall_interval(row)
    terminal = result.get("terminal_at")
    row["forwarded_request_window"] = {"start_epoch_s": window[0] if window else None,
                                       "receipt_epoch_s": window[1] if window else None}
    end = window[1] if window else None
    row["task_terminal_epoch_s"] = terminal
    row["receipt_after_task_terminal_s"] = max(0, end-terminal) if numeric(end) and numeric(terminal) else None
    row["receipt_ends_after_task_terminal"] = end > terminal if numeric(end) and numeric(terminal) else None
    failure = row.get("http_status") != 200 or row.get("transport_error") or row.get("server_error") or row.get("generation_complete") is False
    row["failure_timing"] = {"failure_observed_at_receipt_epoch_s": end if failure else None,
        "failure_wall_s": row.get("wall_s") if failure else None,
        "failure_receipt_minus_task_terminal_s": end-terminal if failure and numeric(end) and numeric(terminal) else None,
        "scope": "transport failure observed at receipt completion; underlying error onset is unknown"}
    p,d = row.get("prompt_ms"),row.get("predicted_ms")
    outside = (p+d)/1000 > row["wall_s"] if window and all(numeric(v) and v >= 0 for v in (p,d)) else None
    row["native_phase_interval_validation"] = {"extends_outside_observed_request_wall": outside,
        "native_phase_sum_ms": p+d if all(numeric(v) for v in (p,d)) else None,
        "request_wall_ms": row["wall_s"]*1000 if window else None,
        "scope": "right-aligned inferred phases; durations over request wall flagged even when phase aggregation excludes them"}

def aggregate(rows):
    result = {"forwarded_receipts": len(rows), "tokens": {key: known_sum(r.get(key) for r in rows)
              for key in ("prompt_n", "cache_n", "predicted_n", "draft_n", "draft_accepted")}}
    result["latency"] = {key: describe(r.get(key) for r in rows) for key in
                         ("wall_s", "ttft_s", "delivered_ttft_s", "first_body_s", "prompt_tok_s", "decode_tok_s")}
    result["forwarded_request_window"] = request_envelope(rows)
    result["receipts_ending_after_own_unit_terminal"] = sum(r.get("receipt_ends_after_task_terminal") is True for r in rows)
    result["native_intervals_outside_request_wall"] = sum((r.get("native_phase_interval_validation") or {}).get("extends_outside_observed_request_wall") is True for r in rows)
    result["role_counts"] = {role: sum((r.get("role_metadata") or {}).get("observed_role", "unknown") == role for r in rows) for role in ("observed_title", "unknown")}
    result["approximate_native_phase_rates"] = {}
    for phase, tokenkey in (("prompt", "prompt_n"), ("decode", "predicted_n")):
        eligible = [(r, phase_interval(r, phase)) for r in rows if numeric(r.get(tokenkey))]
        eligible = [(r, interval) for r, interval in eligible if interval and interval[1] > interval[0]]
        intervals = [i for _,i in eligible]
        active = union_seconds(intervals)
        tokens = sum(r[tokenkey] for r,_ in eligible) if eligible else None
        result["approximate_native_phase_rates"][phase] = {
            "eligible_receipts": len(eligible), "excluded_receipts": len(rows)-len(eligible),
            "tokens": tokens, "union_active_s": active if eligible else None,
            "summed_native_phase_s": sum(b-a for a,b in intervals) if eligible else None,
            "tokens_per_union_active_s": tokens/active if active and tokens is not None else None,
            "method": "native phase durations right-aligned to proxy response end; approximate intervals, union removes concurrency double-counting; includes post-task-terminal upstream drain and is not task completion rate"}
    return result

def resources(samples, rows, backend, terminal=None):
    intervals = [i for r in rows if (i := wall_interval(r))]
    selected = [s for s in samples if numeric(s.get("epoch_s")) and any(a <= s["epoch_s"] <= b for a,b in intervals)]
    return {"scope": "host/device/process samples DURING known forwarded-request wall windows; includes queue/wait and concurrent slots; not task-attributed utilization",
            "request_windows": len(intervals), "sample_count": len(selected),
            "samples_after_task_terminal": sum(s["epoch_s"] > terminal for s in selected) if numeric(terminal) else None,
            "last_sample_minus_task_terminal_s": max((s["epoch_s"] for s in selected), default=terminal)-terminal if numeric(terminal) else None,
            "first_epoch_s": selected[0]["epoch_s"] if selected else None,
            "last_epoch_s": selected[-1]["epoch_s"] if selected else None,
            "vram_bytes": describe(s.get("vram_bytes") for s in selected),
            "gpu_busy_percent": describe(s.get("gpu_busy_percent") for s in selected),
            "process_rss_pages": describe((s.get(backend) or {}).get("rss_pages") for s in selected),
            "process_threads": describe((s.get(backend) or {}).get("threads") for s in selected),
            "cpu_ticks": describe((s.get(backend) or {}).get("cpu_ticks") for s in selected),
            "kfd_pid_sets": sorted({tuple(s.get("kfd_pids", [])) for s in selected}),
            "raw_samples": selected}

def native_log(data):
    """Keep native task IDs distinct from proxy sequence numbers: no guessed join."""
    records = {}
    for n,line in enumerate((data or b"").decode(errors="replace").splitlines(), 1):
        m = re.search(r"id\s+(\d+)\s*\| task\s+(\d+)\s*\|\s*(.*)", line)
        if not m:
            continue
        slot, task, body = m.groups()
        key = (int(slot), int(task))
        rec = records.setdefault(key, {"slot": int(slot), "native_task": int(task), "first_line": n})
        if "processing task" in body:
            rec["launch_line"] = n
        for label, name in (("prompt eval time", "prefill"), ("eval time", "decode")):
            t = re.search(r"^"+label+r"\s*=\s*([\d.]+) ms /\s*(\d+) tokens.*?([\d.]+) tokens per second", body)
            if t:
                rec[name] = {"ms": float(t[1]), "tokens": int(t[2]), "tokens_per_second": float(t[3]), "line": n}
        d = re.search(r"draft acceptance =\s*([\d.]+) \(\s*(\d+) accepted /\s*(\d+) generated", body)
        if d:
            rec["mtp"] = {"ratio": float(d[1]), "accepted": int(d[2]), "proposals": int(d[3]), "line": n}
        p = re.search(r"n_decoded =\s*(\d+), tg =\s*([\d.]+) t/s", body)
        if p:
            rec["last_decode_progress"] = {"generated_so_far": int(p[1]), "native_tg_tok_s": float(p[2]), "line": n}
        if "stop processing" in body:
            rec["release_line"] = n
    for rec in records.values():
        rec["state"] = "released" if "release_line" in rec else "timings_emitted" if "decode" in rec else "partial_in_flight_or_unreleased"
    return sorted(records.values(), key=lambda r:(r["slot"], r["native_task"]))

def request(reader, path, raw, *, epoch_title_enabled=False):
    row = dict(raw)
    body = reader.bytes(path.parent / str(raw.get("body_ref", "missing")))
    payload = None
    if body is not None:
        try:
            payload = json.loads(gzip.decompress(body))
        except (ValueError, OSError, EOFError) as exc:
            reader.warnings.append({"path": str(path), "error": str(exc), "partial_read": True})
    system = [m.get("content") for m in (payload or {}).get("messages", []) if m.get("role") == "system"]
    system_hashes = [hashlib.sha256(x.encode()).hexdigest() for x in system if isinstance(x, str)]
    row["role_metadata"] = {"observed_role": "observed_title" if epoch_title_enabled and TITLE_SYSTEM_SHA256 in system_hashes else "unknown",
        "classification": "exact pinned title-system-prompt hash, restricted to initial-01; model/tool count do not imply role",
        "model_id": (payload or {}).get("model"), "tool_count": len(payload.get("tools") or []) if payload is not None else None,
        "system_prompt_sha256": system_hashes, "epoch_title_matching_enabled": epoch_title_enabled}
    row["stream_requested"] = payload.get("stream", False) if payload is not None else None
    if row["stream_requested"] is False:
        row["ttft_s"] = row["delivered_ttft_s"] = None
    row["ttft_scope"] = "actual streaming first reasoning/content/tool delta; upstream then flushed downstream; nonstream unknown"
    row["reasoning_tokens"] = ((raw.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens")
    row["wire_receipt_path"] = str(path)
    row["failure"] = {k: raw.get(k) for k in ("http_status", "transport_error", "server_error", "generation_complete", "finish_reason")}
    return row

def collect_snapshot(live, main):
    reader = Reader()
    selected = reader.obj(live / "SELECTED-ROWS.json", [])
    if isinstance(selected, dict):
        selected = selected.get("rows", selected.get("selected", []))
    planned = {row["id"]: row for row in selected}
    unitsdir = live / "units"
    for directory in sorted(unitsdir.iterdir() if unitsdir.exists() else []):
        if directory.is_dir():
            planned.setdefault(directory.name, {"id": directory.name})
    frozen_root = live.parent.parent
    grid = reader.obj(frozen_root / "quality" / "GRID.json")
    for source in ("stock/transport.py", "stock/sandbox.py", "quality/launch.py", "quality/cases.py"):
        reader.bytes(frozen_root / source)
    samples = reader.lines(live / "resource-samples.jsonl")
    units, allrows = [], []
    for uid, controls in sorted(planned.items()):
        directory = unitsdir / uid
        result = reader.obj(directory / "RESULT.json", {})
        path = directory / "wire" / "requests.jsonl"
        rows = [request(reader, path, r, epoch_title_enabled=live.resolve() == LIVE.resolve()) for r in reader.lines(path)]
        for row in rows:
            attach_timing(row, result)
        allrows.extend(rows)
        transcript = reader.obj(directory / "OPEN-CODE-SESSION.json")
        messages = transcript.get("messages", []) if isinstance(transcript, dict) else []
        errors = [{"id": m.get("id"), "error": m.get("error"), "finish": m.get("finish")}
                  for m in messages if m.get("error")]
        known = {r.get("body_ref") for r in rows}
        pending = []
        for archive in sorted((directory / "wire").glob("*.json.gz")):
            if archive.name not in known:
                data = reader.bytes(archive)
                pending.append({"path": str(archive), "state": "forwarded_payload_archived_receipt_not_yet_present",
                                "caution": "may be in flight, transport interrupted or receipt append raced snapshot; counters and TTFT unknown"})
        status = result.get("status", "not_started" if not directory.exists() else "result_missing_or_partial")
        partial = status in ("starting", "running", "not_started", "result_missing_or_partial") or bool(pending)
        units.append({"id": uid, "controls": controls, "result": result, "status": status,
                      "partial": partial,
                      "task_latency": {"started_at": result.get("started_at"), "terminal_at": result.get("terminal_at"),
                          "model_wall_s": result.get("model_wall_s"),
                          "task_terminal_wall_s": result["terminal_at"] - result["started_at"]
                              if all(numeric(result.get(k)) for k in ("terminal_at", "started_at")) else None,
                          "elapsed_lower_bound_s_at_latest_resource_sample":
                              max(0, max((x.get("epoch_s", 0) for x in samples), default=0) - result["started_at"])
                              if partial and numeric(result.get("started_at")) else None},
                      "requests": rows, "forwarded_request_window": request_envelope(rows, result.get("terminal_at")), "unreceipted_archives": pending,
                      "summary": aggregate(rows), "resources": resources(samples, rows, result.get("backend", controls.get("backend")), result.get("terminal_at")),
                      "sdk_accounting": {"scope": "forwarded receipts only; SDK attempts/rejections/unmetered retries are not completely observed",
                                         "attempt_count": None, "locally_rejected_count": None,
                                         "export_present": transcript is not None, "export_errors": errors},
                      "local_economic_cost": 0, "currency": "USD", "reasoning_only_tokens": known_sum(r.get("reasoning_tokens") for r in rows)})
    native = {}
    for backend in ("cpu", "gpu"):
        path = live / ("out-" + backend) / "server.log"
        native[backend] = {"path": str(path), "join_policy": "native task IDs are not proxy seq IDs; no inferred per-request join", "tasks": native_log(reader.bytes(path))}
    comparator = []
    for path in sorted(main.glob("*/direct-1/measurement.json")):
        m = reader.obj(path, {})
        comparator.append({"path": str(path), "case": m.get("case"), "requested_model": m.get("requested_model"),
                           "requested_effort": m.get("requested_effort"), "wall_s": m.get("execution", {}).get("wall_s"),
                           "usage": m.get("jsonl", {}).get("usage"), "measurement": m, "economic_cost": None,
                           "ttft_s": None, "rates": None})
    return {"schema_version": 2, "live_root": str(live), "main_root": str(main), "as_of_last_resource_epoch_s": max((s.get("epoch_s", 0) for s in samples), default=None),
            "scope": "exploratory overlapping task churn; no CPU versus GPU benchmark claim",
            "snapshot_policy": "one read of each file; append-prefix hashes; no cross-file atomicity; re-run at owner boundary",
            "limitations": ["Native active intervals are timing-derived approximations, not observed phase boundaries; they include post-terminal upstream drain and are not task completion rates.",
                            "Resources are selected DURING forwarded-request wall windows, may include queueing and concurrent slots; never per-task attribution.",
                            "In-flight unreceipted generation is excluded from totals and aggregate rates; native progress is separate.",
                            "Separate reasoning-only tokens stay unknown when absent; reasoning characters are not tokens.",
                            "No SDK attempt total or unmetered retry count can be reconstructed from forwarded receipts.",
                            "First-body arrival is never substituted for streaming TTFT.",
                            "Missing main price is unknown; local token economic cost is zero.",
                            "Native log IDs are not joined to proxy receipt IDs without an explicit mapping."],
            "failure_diagnosis": reader.obj(OUT / "EPOCH-DIAGNOSIS.json") if live.resolve() == LIVE.resolve() else None,
            "epoch_lifecycle_evidence": {name: reader.obj(live / name) for name in ("OWNER-STOP.json", "CLEANUP.json", "cpu-cleanup.json", "gpu-cleanup.json")},
            "frozen_grid": grid,
            "unmeasured_states": {"cpu_thinking_on": "not present in selected/approved initial rows; no performance estimate",
                                  "sdk_local_rejections_and_retries": "unmetered; no attempt rate estimate",
                                  "main_stream_ttft_and_native_rates": "not recorded in comparator measurement schema; unknown"},
            "approval": reader.obj(live / "APPROVAL.json"),
            "guidance_approvals": {str(p): reader.obj(p) for p in sorted((live / "guidance-approvals").glob("*.json"))},
            "units": units, "by_backend": {b: aggregate([r for r in allrows if r.get("backend") == b]) for b in ("cpu", "gpu")},
            "native_logs": native, "main_comparator": comparator,
            "source_manifest": reader.sources, "read_warnings": reader.warnings}

def markdown(report):
    lines = ["# Incremental A3B performance evidence", "", report["scope"]+".", "",
             "Snapshot includes planned, in-flight and terminal states. Totals cover receipted calls only; currently running generation is incomplete.", "",
             "| Unit | Status | Partial | Task terminal wall / running lower bound s | Receipts | Pending archives | Generated known / unknown calls | Streaming TTFT median s |", "|---|---|---|---|---:|---:|---|---:|"]
    for unit in report["units"]:
        gen = unit["summary"]["tokens"]["predicted_n"]
        ttft = unit["summary"]["latency"]["ttft_s"]["median"]
        latency = unit["task_latency"]
        task_wall = latency["task_terminal_wall_s"] if latency["task_terminal_wall_s"] is not None else latency["elapsed_lower_bound_s_at_latest_resource_sample"]
        lines.append(f"| {unit['id']} | {unit['status']} | {unit['partial']} | {task_wall} | {len(unit['requests'])} | {len(unit['unreceipted_archives'])} | {gen['known_sum']} / {gen['unknown_count']} | {ttft} |")
    lines += ["", "## Approximate aggregate rates", "", "These rates use tokens divided by the union of native phase durations right-aligned to response completion. Overlapping slots are counted once in the denominator. Queueing, phase overlap and timings semantics limit interpretation. Queued upstream requests can outlive task cancellation and terminal timestamps. These rates include that drain; they are not task completion rates or device comparisons.", ""]
    for backend, summary in report["by_backend"].items():
        for phase, rate in summary["approximate_native_phase_rates"].items():
            lines.append(f"- {backend} {phase}: {rate['tokens_per_union_active_s']} tokens/s; eligible receipts {rate['eligible_receipts']}, excluded {rate['excluded_receipts']}; approximate active union {rate['union_active_s']} s.")
    lines += ["", "## Task terminal versus upstream drain", "", "Task terminal wall, forwarded-request receipt completion and resource sampling are separate clocks. A late receipt may be charged after the harness task terminated.", "", "| Unit | Last receipt minus task terminal s | Receipts ending after terminal | Post-terminal request union s | Resource samples after terminal |", "|---|---:|---:|---:|---:|"]
    for unit in report["units"]:
        window = unit["forwarded_request_window"]
        lines.append(f"| {unit['id']} | {window['last_receipt_after_terminal_s']} | {window['receipts_ending_after_terminal']} | {window['post_terminal_request_wall_union_s']} | {unit['resources']['samples_after_task_terminal']} |")
    lines += ["", "## Observed metadata and failure diagnosis", ""]
    for backend, summary in report["by_backend"].items():
        lines.append(f"- {backend}: exact title-prompt matches {summary['role_counts']['observed_title']}; other/unknown role receipts {summary['role_counts']['unknown']}; native interval excursions outside request wall {summary['native_intervals_outside_request_wall']}.")
    if report.get("failure_diagnosis"):
        lines += ["", report["failure_diagnosis"]["owner_reported_diagnosis"], "", "Diagnosis is attributed to the owning session. Per-receipt failures and timing remain separate raw observations; future metadata role identification requires explicit model IDs."]
    lines += ["", "## Main comparator", "", "| Case | Model / effort | Task wall s | Input | Cached input | Output | Reasoning output |", "|---|---|---:|---:|---:|---:|---:|"]
    for row in report["main_comparator"]:
        usage = row.get("usage") or {}
        lines.append("| " + " | ".join(str(v) for v in [row["case"], f"{row['requested_model']} / {row['requested_effort']}", row["wall_s"], *[usage.get(k) for k in ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")]]) + " |")
    lines += ["", "## Evidence and limits", ""] + ["- " + item for item in report["limitations"]]
    lines += ["", "Full per-stream latency, prompt/cache/generation counts, native prefill/decode and MTP counters, raw resource samples during requests, result controls/failures, partial archive state and hashed source manifest are in REPORT.json.", "", f"Read warnings: {len(report['read_warnings'])}.", "", "Next: owner refresh at each live controller task boundary."]
    return "\n".join(lines)+"\n"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", type=Path, default=LIVE)
    parser.add_argument("--main", type=Path, default=MAIN)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if args.out.resolve() == args.live.resolve() or args.out.resolve().is_relative_to(args.live.resolve()):
        parser.error("output must be outside live evidence")
    report = collect_snapshot(args.live, args.main)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "REPORT.json").write_text(json.dumps(report, sort_keys=True, indent=2)+"\n")
    (args.out / "REPORT.md").write_text(markdown(report))
    print(json.dumps({"units": len(report["units"]), "partial": sum(u["partial"] for u in report["units"]),
                      "receipts": sum(len(u["requests"]) for u in report["units"]), "warnings": len(report["read_warnings"])}))

if __name__ == "__main__":
    main()
