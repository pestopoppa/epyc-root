#!/usr/bin/env python3
"""Extract aggregate cache-read trajectories from one Claude Code project snapshot."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from dh_sources import _claude_usage


FIELDS = ("cache_read_input_tokens", "cache_creation_input_tokens", "input_tokens", "output_tokens")
COUNT_KEYS = ("cache_read", "cache_creation", "uncached_input", "output")


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def profile(totals):
    read, created, uncached, output = totals
    inclusive = read + created + uncached
    return dict(zip(COUNT_KEYS, totals)) | {
        "inclusive_input": inclusive,
        "token_intensity": inclusive + output,
        "h": ratio(read, inclusive),
        "cache_creation_share": ratio(created, inclusive),
        "uncached_input_share": ratio(uncached, inclusive),
        "input_output_ratio": ratio(inclusive, output),
    }


def add_totals(records):
    return [sum(column) for column in zip(*records)] if records else [0] * len(FIELDS)


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, OverflowError):
        return None


def read_session(path):
    digest = sha256()
    records = {}
    counters = Counter()
    raw = []
    first_stat = path.stat()
    with path.open("rb") as source:
        for ordinal, line in enumerate(source, 1):
            digest.update(line)
            counters["bytes"] += len(line)
            counters["lines"] += 1
            if not line.strip():
                counters["blank_lines"] += 1
                continue
            try:
                record = json.loads(line)
            except (ValueError, UnicodeError):
                counters["invalid_json_lines"] += 1
                continue
            if not isinstance(record, dict):
                counters["non_object_lines"] += 1
                continue
            if record.get("type") != "assistant":
                continue
            counters["assistant_lines"] += 1
            message = record.get("message")
            usage = message.get("usage") if isinstance(message, dict) else None
            if not isinstance(usage, dict):
                counters["assistant_lines_without_usage"] += 1
                continue
            counters["raw_usage_records"] += 1
            fields = [key for key in FIELDS if type(usage.get(key)) is not int or usage[key] < 0]
            for key in fields:
                counters[f"missing_or_invalid_{key}"] += 1
            normalized = _claude_usage(usage) if not fields else None
            totals = (
                normalized["cache_read"], normalized["cache_creation"],
                normalized["raw"]["input_tokens"], normalized["output"],
            ) if normalized else None
            if totals is not None:
                raw.append(totals)
            else:
                counters["raw_usage_records_with_invalid_counters"] += 1
            message_id = message.get("id")
            if not isinstance(message_id, str) or not message_id:
                counters["raw_usage_records_without_message_id"] += 1
                continue
            if message_id in records:
                counters["repeated_message_id_records"] += 1
            records[message_id] = (timestamp(record.get("timestamp")), ordinal, totals)
    last_stat = path.stat()
    identity = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    if identity(first_stat) != identity(last_stat) or counters["bytes"] != last_stat.st_size:
        raise ValueError("input file changed during scan")

    timed = []
    deduplicated = []
    for ts, ordinal, totals in records.values():
        if totals is None:
            counters["messages_excluded_for_invalid_counters"] += 1
            continue
        deduplicated.append(totals)
        if ts is None:
            counters["messages_without_valid_timestamp"] += 1
            continue
        timed.append((ts, ordinal, totals))
    timed.sort()
    counters["complete_messages"] = len(deduplicated)
    counters["timed_messages"] = len(timed)
    bins = []
    bucket_count = min(10, len(timed))
    for i in range(bucket_count):
        start = i * len(timed) // bucket_count
        end = (i + 1) * len(timed) // bucket_count
        bucket = timed[start:end]
        totals = add_totals([row[2] for row in bucket])
        read, created, uncached, output = totals
        bins.append([start + 1, end, (bucket[0][0] - timed[0][0]).total_seconds(),
                     (bucket[-1][0] - timed[0][0]).total_seconds(), read, created, uncached,
                     output, ratio(read, read + created + uncached)])
    return {
        "source_sha256": digest.hexdigest(),
        "counts": dict(counters),
        "raw_usage": profile(add_totals(raw)),
        "deduplicated_usage": profile(add_totals(deduplicated)),
        "trajectory": bins,
    }


def analyze(directory, expected_files, max_bytes):
    paths = sorted(directory.glob("*.jsonl"))
    if len(paths) != expected_files or not paths:
        raise ValueError(f"expected {expected_files} JSONL files, found {len(paths)}")
    if any(path.is_symlink() or not path.is_file() for path in paths):
        raise ValueError("all input files must be regular and cannot be symlinks")
    if sum(path.stat().st_size for path in paths) > max_bytes:
        raise ValueError("input exceeds the declared byte budget")
    sessions = sorted((read_session(path) for path in paths), key=lambda row: row["source_sha256"])
    if paths != sorted(directory.glob("*.jsonl")):
        raise ValueError("input file membership changed during scan")
    digests = [row["source_sha256"] for row in sessions]
    counts = Counter()
    for row in sessions:
        counts.update(row["counts"])
    if counts["bytes"] > max_bytes:
        raise ValueError("input grew beyond the declared byte budget")
    summary = {}
    for key in ("raw_usage", "deduplicated_usage"):
        summary[key] = profile([sum(row[key][metric] for row in sessions) for metric in COUNT_KEYS])
    return {
        "schema": "epyc.dcp9a.cache-trajectory.v1",
        "extractor_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "usage_normalizer_sha256": sha256(Path(__file__).with_name("dh_sources.py").read_bytes()).hexdigest(),
        "source_selection": "top_level_jsonl_only",
        "source_file_count": len(sessions),
        "source_duplicate_digest_count": len(digests) - len(set(digests)),
        "source_multiset_sha256": sha256("".join(f"{digest}\n" for digest in digests).encode()).hexdigest(),
        "counts": dict(counts),
        "summary": summary,
        "definition_1": {"verdict": None, "missing": ["comparable_completed_task_token_intensity_by_release",
                                                     "fixed_judge_task_quality_by_release"]},
        "trajectory_columns": ["first_timed_message_ordinal", "last_timed_message_ordinal",
                               "first_elapsed_seconds", "last_elapsed_seconds", *COUNT_KEYS, "h"],
        "sessions": sessions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="one immutable Claude Code project directory")
    parser.add_argument("--expect-files", type=int, required=True)
    parser.add_argument("--max-bytes", type=int, required=True)
    args = parser.parse_args()
    try:
        report = analyze(args.directory, args.expect_files, args.max_bytes)
    except (OSError, ValueError) as error:
        parser.exit(1, f"analysis refused: {error.strerror if isinstance(error, OSError) else error}\n")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
