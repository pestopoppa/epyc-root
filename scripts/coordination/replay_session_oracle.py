#!/usr/bin/env python3
"""Replay the session oracle on hash-verified frozen transcript copies."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import session_oracle

DEFAULT_BASELINE = Path(__file__).resolve().parents[2] / "data/fanout_timing/session_oracle.v1.jsonl"
PRESERVED_VERDICTS = {"success", "failure", "partial"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot_path(manifest_path, entry):
    """Resolve only the prescribed path beneath the frozen snapshot directory."""
    relative = Path(entry["path"])
    backend = entry["backend"]
    if backend not in {"claude", "codex"} or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"invalid snapshot identity for {entry['original_path']}")
    inputs = manifest_path.parent
    expected = inputs / backend / relative
    if (inputs.parent / entry["snapshot_path"]) != expected or expected.resolve() != expected:
        raise ValueError(f"invalid snapshot path for {entry['original_path']}")
    return expected


def verify_input(manifest_path, entry):
    if entry["status"] != "matched":
        return None, entry["status"]
    try:
        path = snapshot_path(manifest_path, entry)
        if path.stat().st_size != entry["bytes"]:
            return None, "snapshot_changed"
        if digest(path) != entry["sha256"] or entry["frozen_sha256"] != entry["sha256"]:
            return None, "snapshot_changed"
    except FileNotFoundError:
        return None, "snapshot_missing"
    except (OSError, ValueError, KeyError):
        return None, "snapshot_refused"
    return path, "verified"


def replay(manifest_path, out, summary_path, baseline_path=DEFAULT_BASELINE):
    manifest_path = Path(manifest_path).resolve()
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest["schema"] != "fm4.frozen_replay_inputs.v1":
        raise ValueError("unexpected replay manifest schema")
    original_manifest = manifest_path.with_name("original-manifest.json")
    original_raw = original_manifest.read_bytes()
    original_sha = hashlib.sha256(original_raw).hexdigest()
    if manifest["frozen_original_manifest_sha256"] != original_sha:
        raise ValueError("original manifest digest mismatch")
    entries = manifest["entries"]
    original = json.loads(original_raw)
    if original["cutoff"] != manifest["cutoff"]:
        raise ValueError("replay cutoff differs from original manifest")
    frozen_entries = original["entries"]
    fields = ("backend", "path", "root", "bytes", "sha256")
    if [tuple(row[key] for key in fields) for row in entries] != [
        tuple(row[key] for key in fields) for row in frozen_entries
    ]:
        raise ValueError("replay manifest entries differ from original manifest")
    if len({row["original_path"] for row in entries}) != len(entries):
        raise ValueError("duplicate original paths in replay manifest")
    baseline_raw = Path(baseline_path).read_bytes()
    baseline_sha = hashlib.sha256(baseline_raw).hexdigest()
    if baseline_sha != manifest["historical_verdicts_sha256"]:
        raise ValueError("historical verdict baseline digest mismatch")
    baseline = {}
    for line in baseline_raw.splitlines():
        row = json.loads(line)
        path = row["path"]
        if path in baseline:
            raise ValueError(f"duplicate historical verdict for {path}")
        baseline[path] = row["verdict"]
    for entry in entries:
        if entry.get("historical_verdict") != baseline.get(entry["original_path"]):
            raise ValueError(f"historical verdict differs from baseline for {entry['original_path']}")
        if entry["original_path"] != str(Path(entry["root"], entry["path"])):
            raise ValueError("original transcript path does not match frozen identity")

    parents = {}
    parent_cache = {}
    for entry in entries:
        if entry["kind"] == "claude_parent":
            parents[entry["path"]] = verify_input(manifest_path, entry)

    statuses, before, before_assessed, after, joins, outcomes = (Counter() for _ in range(6))
    unchanged, changed = Counter(), Counter()
    native_before, native_unchanged, native_changed = Counter(), Counter(), Counter()
    statuses_by_kind = {entry["kind"]: Counter() for entry in entries}
    with Path(out).open("w", encoding="utf-8") as output:
        for entry in entries:
            kind = entry["kind"]
            if kind == "claude_parent":
                path, status = parents[entry["path"]]
            else:
                path, status = verify_input(manifest_path, entry)
            old = entry.get("historical_verdict")
            before[old or "unavailable"] += 1
            result = {
                "original_path": entry["original_path"],
                "snapshot_path": entry.get("snapshot_path"),
                "original_sha256": entry["sha256"],
                "snapshot_sha256": entry.get("frozen_sha256"),
                "historical_verdict": old,
                "kind": kind,
            }
            if path is not None:
                parent_path = None
                if kind == "claude_subagent":
                    parent_name = Path(entry["path"]).parent.parent.with_suffix(".jsonl")
                    parent_path, _ = parents.get(str(parent_name), (None, None))
                    if parent_path is None:
                        # Have the oracle see no parent result without consulting
                        # any file that was missing or refused at verification.
                        parent_path = manifest_path.parent / "unavailable-parent" / parent_name
                        parent_cache[parent_path] = {}
                try:
                    row = session_oracle.assess(path, parent_path=parent_path, parent_cache=parent_cache)
                except OSError:
                    status = "assessment_refused"
                else:
                    new = row["verdict"]
                    signals = row["signals"]
                    local = signals["local_verdict"]
                    native_before[local] += 1
                    if local in PRESERVED_VERDICTS:
                        (native_unchanged if local == new else native_changed)[local] += 1
                    before_assessed[old or "unavailable"] += 1
                    after[new] += 1
                    if old in PRESERVED_VERDICTS:
                        (unchanged if old == local else changed)[old] += 1
                    if kind == "claude_subagent":
                        joins[signals.get("parent_join", "not_joined")] += 1
                    if (evidence := signals.get("parent_result")) is not None:
                        outcomes[evidence.get("outcome") or "no_outcome"] += 1
                    result["native_before_verdict"] = local
                    result["native_assessment"] = {
                        **row, "verdict": local,
                        "signals": {key: value for key, value in signals.items()
                                    if key not in {"parent_join", "parent_result"}},
                    }
                    result["assessment"] = row
            statuses[status] += 1
            statuses_by_kind[kind][status] += 1
            result["input_status"] = status
            output.write(json.dumps(result, sort_keys=True) + "\n")

    summary = {
        "schema": "fm4.session_oracle_replay.v1",
        "manifest_entries": len(entries),
        "cutoff": manifest["cutoff"],
        "original_manifest_sha256": original_sha,
        "replay_manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "historical_verdicts_sha256": baseline_sha,
        "runner_sha256": digest(Path(__file__)),
        "oracle_sha256": digest(Path(session_oracle.__file__)),
        "rows_sha256": digest(Path(out)),
        "input_status": dict(statuses),
        "input_status_by_kind": statuses_by_kind,
        "matched_assessments": sum(after.values()),
        "missing_inputs": statuses["missing"] + statuses["snapshot_missing"],
        "changed_inputs": statuses["changed"] + statuses["short"] + statuses["snapshot_changed"],
        "refused_inputs": (statuses["unreadable"] + statuses["snapshot_refused"]
                           + statuses["assessment_refused"]),
        "historical_verdicts": dict(before),
        "historical_verdicts_for_assessed": dict(before_assessed),
        "native_before_verdicts": dict(native_before),
        "assessed_verdicts": dict(after),
        "preserved_native_verdicts": dict(native_unchanged),
        "changed_native_verdicts": dict(native_changed),
        "parent_join_dispositions": dict(joins),
        "parent_result_outcomes": dict(outcomes),
        "preserved_historical_verdicts": dict(unchanged),
        "changed_historical_verdicts": dict(changed),
    }
    Path(summary_path).write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    args = parser.parse_args(argv)
    summary = replay(args.manifest, args.out, args.summary, baseline_path=args.baseline)
    return int(bool(summary["changed_native_verdicts"]))


if __name__ == "__main__":
    raise SystemExit(main())
