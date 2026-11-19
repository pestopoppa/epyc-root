#!/usr/bin/env python3
"""Report TOC-SP-5 evidence from the fixed, legacy BEP sandbox trace cohort."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

COHORT = 62
MAX_FILE_BYTES = 64 * 1024
ROLES = ("architect_coding", "coder_escalation")
WINDOWS = {":8070 slot": 65_536, ":8083 request cap": 262_144}
THRESHOLDS = (50, 60, 85)
BLOCKED = "blocked on the TOC-SP-6 artifact build"
HEADER = re.compile(r"\[Output: \d+ chars, \d+ lines → |chars truncated; exact [^\n]+ span:")
SPILL_PATH = re.compile(r"(?:/[^/\s\"'<>]+)*/(?:spills?/[^\s\"'<>]+|turn_\d+\.txt)")


def read_trace(path):
    """Bound the read and retain an invalid trajectory in the cohort."""
    if path.is_symlink():
        return None, None
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
    except OSError:
        return None, None
    if len(raw) > MAX_FILE_BYTES:
        return None, None
    digest = hashlib.sha256(raw).hexdigest()
    try:
        turns = [json.loads(line) for line in raw.decode().splitlines() if line.strip()]
    except (ValueError, RecursionError):
        return digest, None
    if not turns or any(
        not isinstance(turn, dict)
        or turn.get("role") not in ROLES
        or type(turn.get("turn")) is not int
        for turn in turns
    ):
        return digest, None
    return digest, turns


def char_count(turn):
    value = turn.get("prompt_chars")
    return value if type(value) is int and value >= 0 else None


def occupancy_bounds(traces, role, window):
    """Use characters only for an explicitly assumption-dependent exclusion."""
    peaks = []
    role_absent = 0
    for trace in traces:
        if trace is None:
            continue
        counts = [char_count(turn) for turn in trace if turn["role"] == role]
        if not counts:  # Role absence is observed in this parsed trajectory.
            role_absent += 1
        elif None not in counts:
            peaks.append(max(counts))
    bounds = {}
    for threshold in THRESHOLDS:
        excluded = role_absent + sum(peak * 100 <= threshold * window for peak in peaks)
        bounds[f"0.{threshold}"] = {
            "role_absent": role_absent,
            "conditional_excluded": excluded,
            "conditional_unknown": COHORT - excluded,
            "conditional_share_interval": [0, (COHORT - excluded) / COHORT],
        }
    return bounds


def analyze_sp5_corpus(root):
    # Fixed depth and file-name shape of the standing corpus. Refuse expansion.
    paths = []
    for path in root.glob("*/traces/*.jsonl"):
        if len(paths) == COHORT:
            raise ValueError(f"expected at most {COHORT} legacy traces")
        paths.append(path)

    manifest = {}
    traces = []
    task_counts = Counter()
    for path in sorted(paths):
        digest, trace = read_trace(path)
        manifest[path.relative_to(root).as_posix()] = digest
        traces.append(trace)
        task_counts[path.stem.split("-", 1)[0]] += 1

    parsed = [trace for trace in traces if trace is not None]
    turns = [turn for trace in parsed for turn in trace]
    chars = [count for turn in turns if (count := char_count(turn)) is not None]
    metrics = {}
    for role in ROLES:
        metrics[role] = {
            "traces_with_role": sum(any(turn["role"] == role for turn in trace) for trace in parsed),
            "turns_with_role": sum(turn["role"] == role for turn in turns),
            "threshold_shares": "UNKNOWN",
            "status": BLOCKED,
            "windows": {
                name: {"tokens": window, "bounds": occupancy_bounds(traces, role, window)}
                for name, window in WINDOWS.items()
            },
        }

    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return {
        "cohort_denominator": COHORT,
        "character_bound_assumption": "The full served prompt has no more tokens than recorded prompt characters.",
        "role_to_served_window": "UNKNOWN",
        "present_traces": len(paths),
        "unparsable_traces": len(paths) - len(parsed),
        "missing_traces": COHORT - len(paths),
        "task_trace_counts": dict(sorted(task_counts.items())),
        "turns": len(turns),
        "prompt_chars_turns": len(chars),
        "complete_prompt_chars_traces": sum(all(char_count(turn) is not None for turn in trace) for trace in parsed),
        "no_prompt_chars_traces": sum(all(char_count(turn) is None for turn in trace) for trace in parsed),
        "max_prompt_chars": max(chars, default=None),
        "prompt_tokens_turns": sum(type(turn.get("prompt_tokens")) is int for turn in turns),
        "n_ctx_turns": sum(type(turn.get("n_ctx")) is int for turn in turns),
        "occupancy": metrics,
        "spill": {
            "prompt_tail_turns": sum(isinstance(turn.get("prompt_tail"), str) for turn in turns),
            "header_turns": sum(bool(HEADER.search(str(turn.get("prompt_tail", "")))) for turn in turns),
            "spill_path_reference_turns": sum(
                any(SPILL_PATH.search(str(turn.get(field, ""))) for field in ("raw_output", "extracted_code"))
                for turn in turns
            ),
            "traces_with_spill_ledger": sum(any("spill_follows" in turn for turn in trace) for trace in parsed),
            "task_follow_rate": {"value": "UNKNOWN", "status": BLOCKED},
            "size_decile_follows_per_spill": {"value": "UNKNOWN", "status": BLOCKED},
            "post_elision_rereads": {"value": "UNKNOWN", "status": BLOCKED},
            "post_elision_reruns": {"value": "UNKNOWN", "status": BLOCKED},
        },
        "trace_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "trace_sha256_by_path": manifest,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path, help="legacy data/bep_sandbox directory")
    args = parser.parse_args()
    try:
        result = analyze_sp5_corpus(args.corpus)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
