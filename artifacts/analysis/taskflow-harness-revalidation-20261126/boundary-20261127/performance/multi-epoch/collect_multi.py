#!/usr/bin/env python3
"""Hash and summarize existing A3B receipts across serving epochs. No inference."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import collect_perf as v1

MEASURES = ("seq", "slot", "t0", "wall_s", "forwarded_at", "queue_wait_s", "client_wall_s", "client_ttft_s",
            "http_status", "first_body_s", "ttft_s", "delivered_ttft_s", "prompt_n", "cache_n", "predicted_n",
            "prompt_ms", "predicted_ms", "prompt_tok_s", "decode_tok_s", "draft_n", "draft_accepted",
            "reasoning_characters", "tool_calls")
RUNNING = {"not_started", "starting", "running", "result_missing_or_partial"}
TERMINAL = ("terminal_at", "ended_at")
UNIT_KEYS = ("id", "case", "backend", "profile", "slot", "thinking", "sampling", "wall_s", "request_cap",
             "generated_ceiling", "session", "started_at", "terminal_at", "ended_at", "model_wall_s",
             "generation_observed", "generated_observed", "generation_charged", "charged_toward_ceiling",
             "generation_unknown_requests", "generation_unknown", "reserved_at_terminal",
             "config_sha256", "opencode_config_sha256", "manifest_sha256", "job_sha256",
             "patch_sha256", "candidate_patch_sha256", "worker_receipt_sha256",
             "candidate_status", "status", "worker_status", "worker_rc", "wire_failures",
             "oracle_sha256", "acceptance_version")
REVIEW_STATES = {"accepted", "rejected", "pending"}


def digest(value):
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def number(value):
    return value if v1.numeric(value) and math.isfinite(value) else None


def summary(rows):
    result = v1.aggregate(rows)
    for key, field in (("sdk_input", "sdk_input_tokens"), ("sdk_cached_input", "sdk_cached_input_tokens"),
                       ("sdk_output", "sdk_output_tokens"), ("reasoning_output", "reasoning_tokens")):
        result["tokens"][key] = v1.known_sum(row.get(field) for row in rows)
    for key in ("queue_wait_s", "client_wall_s", "client_ttft_s"):
        result["latency"][key] = v1.describe(row.get(key) for row in rows)
    paired = [(r["draft_accepted"], r["draft_n"]) for r in rows
              if number(r["draft_accepted"]) is not None and number(r["draft_n"]) is not None]
    proposed = sum(n for _, n in paired) if paired else None
    accepted = sum(a for a, _ in paired) if paired else None
    result["mtp_paired"] = {"receipts": len(paired), "unknown_receipts": len(rows) - len(paired),
                            "accepted": accepted, "proposed": proposed,
                            "acceptance_ratio": accepted / proposed if proposed else None}
    return result


def error_metadata(value):
    return {"present": True, "sha256": digest(canonical(value))} if value else None


def object_lines(reader, path):
    for row in reader.lines(path):
        if isinstance(row, dict):
            yield row
        else:
            reader.warnings.append({"path": str(path), "error": "JSONL row is not an object", "partial_read": True})


def wire_request(reader, path, raw, result):
    row = {key: number(raw.get(key)) for key in MEASURES}
    row.update({key: raw.get(key) for key in ("body_ref", "backend", "upstream_attempted",
                                             "finish_reason", "generation_complete")})
    if row["body_ref"] and Path(str(row["body_ref"])).name != row["body_ref"]:
        reader.warnings.append({"path": str(path), "error": "nonlocal request archive reference"})
        row["body_ref"] = None
    row["server_error"] = error_metadata(raw.get("server_error"))
    row["transport_error"] = error_metadata(raw.get("transport_error"))
    observed = v1.request(reader, path, dict(row, usage=raw.get("usage") or {}))
    observed.pop("usage")
    if observed["stream_requested"] is not True:
        for key in ("ttft_s", "delivered_ttft_s", "client_ttft_s"):
            observed[key] = None
    sdk = raw.get("usage") or {}
    observed.update(sdk_input_tokens=number(sdk.get("prompt_tokens")),
                    sdk_cached_input_tokens=number((sdk.get("prompt_tokens_details") or {}).get("cached_tokens")),
                    sdk_output_tokens=number(sdk.get("completion_tokens")),
                    reasoning_tokens=number(observed["reasoning_tokens"]))
    projected = raw.get("digest") or {}
    observed["sealed_wire_controls"] = {key: projected[key] for key in
                                       ("sdk_model", "thinking", "preserve_thinking", "cap_agent", "upstream_requested_cap",
                                        "role", "tools") if key in projected}
    if projected.get("sdk_model") == "q35-a3b-title" and projected.get("role") == "title":
        observed["role_metadata"]["observed_role"] = "observed_title"
        observed["role_metadata"]["classification"] = "explicit upstream adapter SDK title alias and role"
    if observed["upstream_attempted"] is not False:
        v1.attach_timing(observed, result)
    observed["ttft_scope"] = {
        "upstream": "Streaming first native delta after forwarding.",
        "delivered": ("Streaming delta delivered from client arrival, including queue wait." if "client_ttft_s" in raw
                      else "Streaming delta delivered from the older proxy timing origin."),
        "client": "Explicit client-relative streaming delta, including queue wait when the adapter supplies it.",
        "unknown": "Nonstream, native log-only or unknown stream framing has no measured TTFT.",
    }
    observed["receipt_sha256"] = digest(canonical(raw))
    return observed


def read_wires(reader, unit, result, seen):
    requests, pending, duplicates, rejected = [], [], [], []
    for wire in (unit / "wire", unit / "worker" / "wire"):
        path = wire / "requests.jsonl"
        known = set()
        for raw in object_lines(reader, path):
            known.add(raw.get("body_ref"))
            fingerprint = digest(canonical(raw))
            evidence = {"unit_path": str(unit), "receipt_path": str(path), "seq": raw.get("seq")}
            if fingerprint in seen:
                duplicates.append({**evidence, "receipt_sha256": fingerprint,
                                   "first_seen": seen[fingerprint], "reason": "identical recorded request"})
                continue
            seen[fingerprint] = evidence
            requests.append(wire_request(reader, path, raw, result))
        for archive in sorted(wire.glob("*.json.gz")):
            if archive.name not in known:
                reader.bytes(archive)
                pending.append({"path": str(archive), "state": "archive_without_request_receipt",
                                "generated_tokens": None, "ttft_s": None, "upstream_attempted": None})
        for row in object_lines(reader, wire / "adapter-rejections.jsonl"):
            rejected.append({"path": str(wire / "adapter-rejections.jsonl"),
                             **{key: row.get(key) for key in ("http_status", "seq", "at", "queue_wait_s", "stage")},
                             "reason": error_metadata(row.get("reason"))})
    return requests, pending, duplicates, rejected


def planned_rows(reader, spec):
    plan = reader.obj(Path(spec["plan"]), {}) or {}
    if spec["layout"] == "quality":
        return {row["id"]: row for row in plan}
    rows = {name: {"id": name} for name in plan.get("legacy_rows", plan.get("initial_rows", []))}
    for item in plan.get("quality_resume_rows", []):
        name = item["initial_row"] + "-numa-resume-1"
        rows[name] = {"id": name, "resume": item}
    return rows


def binding(item, data):
    observed = digest(data) if data is not None else None
    expected = item.get("sha256")
    return {**item, "observed_sha256": observed,
            "state": "missing" if observed is None else "matched" if observed == expected else
                     "hash_mismatch" if expected else "observed"}


def review(reader, attempt, config):
    patch = attempt["patch_sha256"]
    score = attempt["oracle"]
    entry = config.get(attempt["source_path"])
    if entry is not None:
        data = reader.bytes(Path(entry["path"]))
        evidence = binding(entry, data)
        record = json.loads(data) if evidence["state"] == "matched" else {}
        if (isinstance(record, dict) and patch and record.get("candidate_patch_sha256") == patch
                and record.get("decision") in REVIEW_STATES):
            return {"state": record["decision"], "evidence": evidence, "raw_automated_score": score}
        return {"state": "unverified_review_record", "evidence": evidence, "raw_automated_score": score}
    return {"state": "pending_independent_review" if patch else "no_candidate_review_record",
            "raw_automated_score": score}


def ancestry(result, worker, plan):
    spec = result.get("resume") or result.get("feedback") or worker.get("resume") or plan.get("resume") or {}
    source = spec.get("prior") or spec.get("prior_attempt") or spec.get("prior_run")
    if not isinstance(source, str) or not source.startswith("/"):
        return None
    path = Path(source)
    return {"prior_unit_path": str(path.parent if path.name == "worker" else path),
            "prior_result_sha256": spec.get("prior_result_sha256") or spec.get("owner_result_sha256"),
            "prior_worker_receipt_sha256": spec.get("prior_receipt_sha256") or spec.get("receipt_sha256"),
            "prior_session_sha256": spec.get("prior_session_sha256") or spec.get("session_sha256"),
            "prior_declared_tokens_at_resume": spec.get("previous_generated_observed"),
            "prior_declared_wall_s_at_resume": spec.get("previous_model_wall_s")}


def collect_unit(reader, epoch, unit, plan, samples, seen, reviews):
    raw_path = unit / "RESULT.json"
    worker_path = unit / "worker/receipt.json"
    result = reader.obj(raw_path, {}) or {}
    worker = reader.obj(worker_path, {}) or {}
    job = reader.obj(unit / "JOB.json", {}) or {}
    status = result.get("status", worker.get("status", "result_missing_or_partial" if unit.exists() else "not_started"))
    backend = result.get("backend") or job.get("backend") or plan.get("backend") or epoch.get("default_backend")
    started = number(result.get("started_at") if result else worker.get("started_at"))
    terminal = next((value for rec in (result, worker) for key in TERMINAL if (value := number(rec.get(key))) is not None), None)
    task_wall = terminal - started if all(v1.numeric(x) for x in (terminal, started)) and terminal >= started else None
    normalized = {"started_at": started, "terminal_at": terminal}
    requests, pending, duplicates, rejected = read_wires(reader, unit, normalized, seen)
    forwarded = [r for r in requests if r["upstream_attempted"] is not False]
    partial = status in RUNNING or terminal is None or bool(pending)
    # One epoch copy of resource samples, with per-attempt references into it.
    res = v1.resources(samples, forwarded, backend, terminal)
    selected = {id(sample) for sample in res.pop("raw_samples")}
    res["sample_indices"] = [i for i, sample in enumerate(samples) if id(sample) in selected]
    patch = result.get("patch_sha256") or result.get("candidate_patch_sha256") or worker.get("patch_sha256")
    separate_oracle = reader.obj(unit / "independent/oracle-result.json", {}) or {}
    oracle = result.get("oracle") or separate_oracle or None
    tags = list(epoch.get("profile_tags", []))
    for overlay in epoch.get("overlays", []):
        if backend == overlay.get("backend") and (not overlay.get("ids") or unit.name in overlay["ids"]):
            tags.append(overlay["tag"])
    if str(status).startswith(("interrupted", "harness_")):
        tags.append("harness_interrupted_or_environment_affected")
    if result.get("wire_failures") or any(r["transport_error"] or r["server_error"] for r in requests):
        tags.append("transport_failures_observed")
    paths = (unit / "OPEN-CODE-SESSION.json", unit / "worker/session.json")
    session_hashes = {str(path): digest(data) for path in paths if (data := reader.bytes(path)) is not None}
    attempt = {
        "epoch": epoch["id"], "id": unit.name, "source_path": str(unit), "case": result.get("case") or worker.get("case") or plan.get("case"),
        "backend": backend, "status": status, "partial": partial, "qualification_tags": sorted(set(tags)),
        "controls": {key: item for key in UNIT_KEYS if (item := result.get(key, job.get(key, plan.get(key)))) is not None},
        "raw_result_metrics": {key: result[key] for key in UNIT_KEYS if key in result},
        "worker_receipt_metrics": {key: worker[key] for key in UNIT_KEYS if key in worker},
        "raw_result_source": reader.sources.get(str(raw_path)), "worker_receipt_source": reader.sources.get(str(worker_path)),
        "session_export_sha256": session_hashes, "patch_sha256": patch,
        "oracle": None if oracle is None else {key: oracle.get(key) for key in ("rc", "oracle_sha256", "acceptance_version", "semantic_review_required")},
        "failure_metadata": {key: error_metadata(result.get(key) or worker.get(key))
                             for key in ("error", "assistant_errors", "stop_reason", "interrupt_receipt", "interrupt")},
        "task_latency": {**normalized, "phase_wall_s": task_wall, "reported_model_wall_s": number(result.get("model_wall_s")),
                         "worker_started_at": number(worker.get("started_at")), "worker_ended_at": number(worker.get("ended_at")),
                         "elapsed_lower_bound_if_running_s": max(0, max(s["epoch_s"] for s in samples) - started)
                         if partial and terminal is None and v1.numeric(started) and samples else None},
        "requests": requests, "unreceipted_archives": pending, "duplicate_receipts": duplicates,
        "local_adapter_rejections": rejected, "forwarded_request_window": v1.request_envelope(forwarded, terminal),
        "summary": summary(forwarded), "resources": res, "ancestry": ancestry(result, worker, plan),
    }
    attempt["acceptance"] = review(reader, attempt, reviews)
    return attempt


def self_receipt(attempt):
    return {"epoch": attempt["epoch"], "id": attempt["id"], "raw_status": attempt["status"],
            "qualification_tags": attempt["qualification_tags"], "phase_wall_s": attempt["task_latency"]["phase_wall_s"],
            "generated": attempt["summary"]["tokens"]["predicted_n"],
            "unreceipted_archives": len(attempt["unreceipted_archives"])}


def continuation_costs(attempt, indexed):
    lineage, cursor = [attempt], attempt
    reason = None
    while spec := cursor["ancestry"]:
        parent = indexed.get(spec["prior_unit_path"])
        if parent is None or parent in lineage:
            reason = "missing or cyclic prior attempt"
            break
        if ((spec["prior_result_sha256"] and spec["prior_result_sha256"] != (parent["raw_result_source"] or {}).get("sha256"))
                or (spec["prior_worker_receipt_sha256"] and spec["prior_worker_receipt_sha256"] != (parent["worker_receipt_source"] or {}).get("sha256"))
                or (spec["prior_session_sha256"] and spec["prior_session_sha256"] not in parent["session_export_sha256"].values())
                or not (spec["prior_result_sha256"] or spec["prior_worker_receipt_sha256"])):
            reason = "prior receipt or session hash not established"
            break
        lineage.append(parent)
        cursor = parent
    rows = [request for item in lineage for request in item["requests"] if request["upstream_attempted"] is not False]
    return {"current_phase": self_receipt(attempt), "previous_phases": [self_receipt(item) for item in reversed(lineage[1:])],
            "captured_cumulative": {"summary": summary(rows), "request_windows": v1.request_envelope(rows),
                                   "task_phase_wall_known": v1.known_sum(item["task_latency"]["phase_wall_s"] for item in lineage),
                                   "unreceipted_archives": sum(len(item["unreceipted_archives"]) for item in lineage)},
            "complete_bound_chain": reason is None, "unresolved_ancestry": reason}


def serving(reader, root, backend):
    config = reader.obj(root / f"CONFIG-{backend}.json", {}) or {}
    native = root / f"out-{backend}"
    launch = reader.obj(native / "server.json", {}) or {}
    live = reader.obj(native / "live.json", {}) or {}
    build = reader.obj(native / "proofs.json", {}) or {}
    argv = launch.get("argv", live.get("argv", []))
    pairs = [(item, argv[i+1] if i + 1 < len(argv) else None) for i, item in enumerate(argv)
             if item in ("--cache-ram", "-cram")]
    return {"config": reader.sources.get(str(root / f"CONFIG-{backend}.json")),
            "argv_evidence": reader.sources.get(str(native / "server.json")),
            "live_receipt": reader.sources.get(str(native / "live.json")),
            "build_proof": reader.sources.get(str(native / "proofs.json")),
            "source_commit": build.get("source_sha"), "native_pid": launch.get("pid", live.get("pid")),
            "model_path": config.get("model"), "slot_context": live.get("n_ctx_slot"), "parallel_slots": live.get("n_parallel"),
            "shared_ram_cache_argv": pairs, "shared_ram_cache_disabled": all(str(value) == "0" for _, value in pairs) if pairs else None,
            "cache_scope": "Shared RAM snapshot cache setting is separate from the receipt's in-slot cache-hit counters."}


def main_comparators(reader, roots):
    output = []
    for root in roots:
        for path in sorted(Path(root).glob("*/direct-1/measurement.json")):
            value = reader.obj(path, {}) or {}
            info = value.get("jsonl") or {}
            output.append({"case": value.get("case"), "path": str(path), "model": value.get("requested_model"),
                           "effort": value.get("requested_effort"), "wall_s": (value.get("execution") or {}).get("wall_s"),
                           "usage": {key: number(num) for key, num in (info.get("usage") or {}).items()},
                           "ttft_s": None, "native_rates": None, "economic_cost": None})
    return output


def collect(config):
    reader, seen, attempts, epochs = v1.Reader(), {}, [], []
    for spec in config["epochs"]:
        root, units = Path(spec["serving_root"]), Path(spec["units_root"])
        samples = sorted((row for row in object_lines(reader, root / "resource-samples.jsonl") if number(row.get("epoch_s")) is not None),
                         key=lambda row: row["epoch_s"])
        planned = planned_rows(reader, spec)
        actual = {item.name for item in units.iterdir() if item.is_dir()} if units.is_dir() else set()
        parts = [collect_unit(reader, spec, units / name, planned.get(name, {}), samples, seen, config.get("reviews", {}))
                 for name in sorted(actual | set(planned))]
        attempts.extend(parts)
        bound = [binding(item, reader.bytes(Path(item["path"]))) for item in spec.get("bindings", [])]
        if any(item["state"] == "hash_mismatch" for item in bound):
            for attempt in parts:
                attempt["qualification_tags"].append("serving_provenance_hash_mismatch")
        native, server = {}, {}
        for side in spec["backends"]:
            path = root / f"out-{side}/server.log"
            native[side] = {"path": str(path), "tasks": v1.native_log(reader.bytes(path)),
                            "ttft_s": None, "join_policy": "Native task IDs lack an explicit proxy sequence join."}
            server[side] = serving(reader, root, side)
        rows = [r for item in parts for r in item["requests"] if r["upstream_attempted"] is not False]
        epochs.append({"id": spec["id"], "layout": spec["layout"], "serving_root": str(root), "units_root": str(units),
                       "state": "observed" if root.is_dir() else "not_started", "native_logs": native,
                       "server_identity": server, "bindings": bound, "overlays": spec.get("overlays", []),
                       "resource_samples": samples, "summary": summary(rows), "attempts": len(parts)})
    indexed = {attempt["source_path"]: attempt for attempt in attempts}
    for attempt in attempts:
        if attempt["ancestry"]:
            attempt["continuation_costs"] = continuation_costs(attempt, indexed)
    all_rows = [r for item in attempts for r in item["requests"] if r["upstream_attempted"] is not False]
    return {"schema": "a3b.multi-epoch-performance.v2",
            "scope": "Exploratory task observations across serving epochs. CPU and GPU were not compared as a benchmark.",
            "snapshot_policy": "Append prefixes are independently read and hashed. In-flight data and cross-file races remain explicit.",
            "epochs": epochs, "attempts": attempts, "main_comparators": main_comparators(reader, config.get("main_roots", [])),
            "rollup": summary(all_rows), "unreceipted_archives": sum(len(item["unreceipted_archives"]) for item in attempts),
            "accepted_count": sum(item["acceptance"]["state"] == "accepted" for item in attempts),
            "source_manifest": reader.sources, "read_warnings": reader.warnings}


def markdown(report):
    lines = ["# A3B performance evidence across serving epochs", "", report["scope"], "",
             "TTFT, token counts and resource samples are observational. Missing values stay unknown.",
             "Oracle verdicts and independent acceptance are separate.", "",
             "| Epoch / attempt | Raw status | Review | Wall s | Streaming TTFT median s | Prefill / decode median tok/s | Generated known / unknown receipts | Cached input known | MTP accepted / proposed | Resource samples |",
             "|---|---|---|---:|---:|---|---|---:|---|---:|"]
    for item in report["attempts"]:
        s, sample = item["summary"], item["resources"]
        m = s["mtp_paired"]
        gen = s["tokens"]["predicted_n"]
        latency = s["latency"]
        wall = item["task_latency"]["phase_wall_s"]
        lines.append(f"| {item['epoch']} / {item['id']} | {item['status']} | {item['acceptance']['state']} | "
                     f"{wall} | {latency['ttft_s']['median']} | {latency['prompt_tok_s']['median']} / {latency['decode_tok_s']['median']} | "
                     f"{gen['known_sum']} / {gen['unknown_count']} | {s['tokens']['sdk_cached_input']['known_sum']} | "
                     f"{m['accepted']} / {m['proposed']} | {sample['sample_count']} |")
    lines += ["", "## Qualification and accounting", "",
              "- The CPU placement incident remains tagged on the original affected attempts. Their raw observations remain available.",
              "- Continuations retain each parent phase and this phase separately. Cumulative counters use only hash-bound observed ancestry.",
              "- Elapsed request intervals are unioned by recorded timestamps. Native prefill and decode phase envelopes are timing-derived estimates.",
              "- Resource references index the serving epoch's samples during forwarded windows. Samples include overlapping slots and shared host activity.",
              "- The adapter's upstream, delivered and client TTFT measures retain their distinct clocks. First-body and nonstream measurements supply no TTFT.",
              "- Unreceipted archives, pre-forward rejections and missing counters are retained separately. A partial attempt is insufficient for a complete cost.",
              "- Shared RAM cache settings do not remove ordinary in-slot reuse counters.",
              "", f"Independent acceptance records counted: {report['accepted_count']}.", "Next: owner refresh at the next evidence boundary."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=HERE / "INPUTS.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = args.out.resolve()
    if not output.is_relative_to(HERE) or output == HERE or output.exists():
        parser.error("use a new private output directory beneath multi-epoch")
    raw = args.input.read_bytes()
    report = collect(json.loads(raw))
    report["input_manifest_sha256"] = digest(raw)
    report["collector_sha256"] = digest(Path(__file__).read_bytes())
    report["metric_math_sha256"] = digest(Path(v1.__file__).read_bytes())
    output.mkdir(mode=0o700)
    (output / "REPORT.json").write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")
    (output / "REPORT.md").write_text(markdown(report))
    print(json.dumps({"epochs": len(report["epochs"]), "attempts": len(report["attempts"]),
                      "receipted": report["rollup"]["forwarded_receipts"], "unreceipted": report["unreceipted_archives"],
                      "warnings": len(report["read_warnings"])}))


if __name__ == "__main__":
    main()
