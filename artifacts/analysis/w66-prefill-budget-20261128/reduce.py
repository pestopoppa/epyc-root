"""Verify and reduce the C22 W66 prefill-budget timing receipts."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def delivery_gaps(path, first_delta):
    chunks = []
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        if any(any(choice.get("delta", {}).get(field) for field in
                   ("content", "reasoning_content", "tool_calls"))
               for choice in entry["event"].get("choices", [])):
            chunks.append(entry["at_ns"])
    if not chunks or chunks[0] != first_delta["at_ns"]:
        raise ValueError(f"streamed delivery start disagrees with first-delta receipt for {path.name}")
    gaps = sorted((end - start) / 1e6 for start, end in zip(chunks, chunks[1:]))
    return {"events": len(chunks), "gaps": len(gaps),
            "nearest_rank_p99_ms": gaps[math.ceil(.99 * len(gaps)) - 1] if gaps else None,
            "worst_ms": gaps[-1] if gaps else None}


def item(run, visit, prior_exit):
    directory = run / visit["name"]
    launch = read(directory / "launch.json")
    cleanup = read(directory / "cleanup.json")
    slots = read(directory / "slots.json")
    if not (launch["pid"] == cleanup["owned_server_pid"]
            and cleanup["server_rc"] == 0
            and not cleanup["kfd_after"] and not cleanup["exists_after"]
            and launch["started_unix"] >= prior_exit):
        raise ValueError(f"independent process lifecycle failed {visit['name']}")
    if launch["argv"][-4:] != visit["controller_argv"]:
        raise ValueError(f"applied flags differ {visit['name']}")
    if not (len(slots["slots"]) == 4 and not slots["kv_unified"] and
            all(slot["n_ctx"] == 131072 for slot in slots["slots"])):
        raise ValueError(f"unexpected slot configuration {visit['name']}")
    mixed = visit["mixed"]
    times = sorted(row["iteration_ms"] for row in mixed["rows"] if row["mixed"])
    if len(times) != mixed["count"]:
        raise ValueError(f"mixed iteration count differs {visit['name']}")
    gaps = {}
    for label, stream in visit["streams"].items():
        if stream["resource_sample_count"] <= 0 or not stream["min_vram_b"]:
            raise ValueError(f"missing residency for {label} in {visit['name']}")
        for ending, field in ((".sse.jsonl", "private_sse_sha256"),
                               (".message.json", "private_message_sha256")):
            if sha(directory / "private" / (stream["name"] + ending)) != stream[field]:
                raise ValueError(f"stream proof differs for {label} in {visit['name']}")
        sse = directory / "private" / (stream["name"] + ".sse.jsonl")
        gaps[label] = delivery_gaps(sse, stream["first_delta"])
    baseline_argv = launch["argv"][:-4]
    baseline_argv[baseline_argv.index("--slot-save-path") + 1] = "<per-visit-slot-path>"
    reduced = {k: v for k, v in visit.items() if k != "mixed"}
    reduced.update({"launch": launch, "cleanup": cleanup, "slots": slots,
                    "baseline_argv": baseline_argv,
                    "delivered_sse_gaps_ms": gaps,
                    "server_log_sha256": sha(directory / "private/server.log"),
                    "resources_sha256": sha(directory / "resources.jsonl"),
                    "linkage_sha256": sha(directory / "linkage.txt"),
                    "native_iterations": {**mixed, "historical_rounded_index_p99_ms": times[round(.99 * (len(times) - 1))]}})
    return reduced


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    cli = parser.parse_args()
    native_path = cli.run / "RESULT.json"
    raw = read(native_path)
    if not raw["complete"] or not 2 <= len(raw["pairs"]) <= 3:
        raise ValueError("measured row incomplete")
    pairs = []
    ref_argv = None
    ref_source = None
    ref_body = None
    last_exit = 0
    server_pids = set()
    for pair in raw["pairs"]:
        block = {"pair": pair["pair"], "order": pair["order"]}
        for arm in pair["order"]:
            row = item(cli.run, pair[arm], last_exit)
            server = row["launch"]["pid"]
            if server in server_pids:
                raise ValueError("a server process was reused")
            server_pids.add(server)
            last_exit = row["cleanup"]["ended_unix"]
            sources = row["launch"]["hashes"]
            bodies = {k: v["request_body_sha256"] for k, v in row["streams"].items()}
            if ref_argv is not None and (row["baseline_argv"] != ref_argv or sources != ref_source or bodies != ref_body):
                raise ValueError("baseline argv, loaded artifact pin or request body changed")
            ref_argv, ref_source, ref_body = row["baseline_argv"], sources, bodies
            block[arm] = row
        a, b = [block[arm]["metrics"] for arm in ("control", "budget")]
        block["paired_seconds"] = {"on28_decode_recovered": a["on28_decode_s"] - b["on28_decode_s"],
                                   "off56_ttft_change": b["off56_ttft_s"] - a["off56_ttft_s"],
                                   "both_finish_change": b["both_finish_s_since_on28_forward"] - a["both_finish_s_since_on28_forward"]}
        pairs.append(block)
    reduced = {k: v for k, v in raw.items() if k != "pairs"}
    reduced.update({"pairs": pairs, "row_result_sha256": sha(native_path),
                    "p99_method_for_900_ms_target": "nearest rank ceil(0.99*n)-1",
                    "comparison_p99_method": "prior 27B rounded index round(0.99*(n-1))",
                    "all_variants_same_rendered_input_and_request": True,
                    "no_model_proposed_tool_effects": True})
    cli.output.write_text(json.dumps(reduced, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
