"""Regrade terminal PFXC candidates without changing their saved scores."""

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

from oracle import DOC, LOG, LOG_SHA, PROBE, PROBE_SHA

HERE = Path(__file__).resolve().parent
EPOCH = HERE.parent.parent / "ws58-a3b-frozen-revalidation-20261126/quality-runs/cache-safe-01"
MAIN = HERE.parent / "main-comparison/runs/PFXC-A3/direct-1"
CASE = "PFXC-A3"
CASE_NAME = re.compile(r"(?:cpu|gpu)-PFXC-A3-[a-z0-9-]+")


@dataclass(frozen=True)
class Candidate:
    name: str
    raw_status: str
    raw_score: dict
    document: Path
    document_sha: str
    patch: Path
    patch_sha: str
    logs: tuple[Path, Path]
    records: dict[Path, bytes]
    terminal_at: float | None = None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def checked_read(path, expected):
    if path.is_symlink():
        raise ValueError(f"unexpected link: {path}")
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError(f"saved artifact differs from its receipt: {path}")
    return data


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n")


def load(path):
    return json.loads(path.read_bytes())


def read_main():
    raw = {MAIN / name: (MAIN / name).read_bytes() for name in
           ("execution.json", "measurement.json", "oracle-result.json")}
    execution, report, score = (json.loads(data) for data in raw.values())
    if (execution["rc"] != 0 or report["execution"] != execution or not report["path_scope_pass"]
            or report["jsonl"]["completed_turn_count"] != 1 or report["case"] != CASE
            or report["arm"] != "direct" or report["final_changes"] != [DOC] or report["oracle"] != score):
        raise ValueError("main comparator terminal or custody receipts do not agree")
    return Candidate(
        "main-direct-1", "completed", score, MAIN / "lane" / DOC,
        score["checked_candidate_files"][DOC]["sha256"], MAIN / "delta.patch", report["patch_sha256"],
        (MAIN / "oracle.stdout.log", MAIN / "oracle.stderr.log"), raw,
    )


def read_epoch(approved_sha):
    candidates = []
    excluded = []
    for unit in sorted((EPOCH / "units").iterdir()):
        if not unit.is_dir() or not CASE_NAME.fullmatch(unit.name):
            continue
        path = unit / "RESULT.json"
        if not path.is_file():
            excluded.append({"id": unit.name, "reason": "no_result_receipt"})
            continue
        raw = path.read_bytes()
        result = json.loads(raw)
        status = result["status"]
        observed = {"id": unit.name, "raw_status": status, "result_sha256": sha(raw)}
        if result["case"] != CASE or result["id"] != unit.name or result["manifest_sha256"] != approved_sha:
            raise ValueError(f"saved result does not match approved case or epoch: {unit.name}")
        terminal = result.get("terminal_at")
        if not isinstance(terminal, (int, float)) or not math.isfinite(terminal) or terminal <= 0:
            excluded.append({**observed, "reason": "nonterminal"})
            continue
        if status not in {"oracle_pass", "oracle_fail"}:
            excluded.append({**observed, "reason": "terminal_without_scoped_graded_candidate", "terminal_at": terminal})
            continue
        if (result["outside_scope"] or result["unsafe_paths"] or list(result["changed_files"]) != [DOC]
                or result["oracle"]["rc"] != (0 if status == "oracle_pass" else 1)):
            raise ValueError(f"terminal grade has inconsistent path or score receipts: {unit.name}")
        document_sha = result["changed_files"][DOC]["sha256"]
        checked_read(unit / "sandbox/work" / DOC, document_sha)
        candidates.append(Candidate(
            unit.name, status, result["oracle"], unit / "independent/work" / DOC, document_sha,
            unit / "independent/candidate.patch", result["patch_sha256"],
            (unit / "ORACLE.stdout.log", unit / "ORACLE.stderr.log"), {path: raw}, terminal,
        ))
    return candidates, excluded


def assess(candidate, root, oracle, migration):
    source_sha = candidate.raw_score["oracle_sha256"]
    if source_sha not in {migration["original_oracle_sha256"], migration["oracle_sha256"]}:
        raise ValueError(f"raw checker identity is unknown: {candidate.name}")
    destination = root / candidate.name
    metadata = destination / "raw"
    metadata.mkdir(parents=True)
    collected = dict(candidate.records)
    collected[candidate.document] = checked_read(candidate.document, candidate.document_sha)
    collected[candidate.patch] = checked_read(candidate.patch, candidate.patch_sha)
    for stream, path in zip(("stdout", "stderr"), candidate.logs, strict=True):
        collected[path] = checked_read(path, candidate.raw_score[f"{stream}_sha256"])
    lane = destination / "candidate"
    target = lane / DOC
    target.parent.mkdir(parents=True)
    target.write_bytes(collected[candidate.document])
    for path, data in collected.items():
        if path != candidate.document:
            (metadata / path.name).write_bytes(data)

    proc = subprocess.run([sys.executable, "-IB", str(oracle), str(lane)],
                          capture_output=True, timeout=30)
    if proc.returncode not in (0, 1) or proc.stderr.startswith(b"Traceback"):
        raise RuntimeError(f"revised verifier failed unexpectedly: {candidate.name}: {proc.stderr.decode()}")
    (destination / "v4.stdout.log").write_bytes(proc.stdout)
    (destination / "v4.stderr.log").write_bytes(proc.stderr)
    for path, data in collected.items():
        checked_read(path, sha(data))
    return {
        "id": candidate.name,
        "input_artifact_sha256": {str(path): sha(data) for path, data in collected.items()},
        "candidate_sha256": candidate.document_sha,
        "source_terminal_at": candidate.terminal_at,
        "raw_status_preserved": candidate.raw_status,
        "original_automated_score": candidate.raw_score,
        "reassessment": {
            "acceptance_version": migration["version"],
            "oracle_sha256": migration["oracle_sha256"],
            "rc": proc.returncode,
            "stdout_sha256": sha(proc.stdout),
            "stderr_sha256": sha(proc.stderr),
            "diagnostic": proc.stderr.decode().strip() or None,
        },
        "semantic_review": "unreviewed in this offline snapshot",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot_name", help="new directory name beneath this assessment workspace")
    args = parser.parse_args()
    if not re.fullmatch(r"assessment-[a-z0-9-]+", args.snapshot_name):
        parser.error("snapshot name must start with assessment- and contain only lowercase letters, digits or hyphens")
    root = HERE / args.snapshot_name
    migration_path = HERE / "acceptance-migration.json"
    migration = load(migration_path)
    oracle = HERE / migration["oracle"]
    checked_read(oracle, migration["oracle_sha256"])
    checked_read(LOG, LOG_SHA)
    checked_read(PROBE, PROBE_SHA)
    approval_path = EPOCH / "APPROVAL.json"
    approval = approval_path.read_bytes()
    approved_sha = json.loads(approval)["quality_manifest_sha256"]
    candidates, excluded = read_epoch(approved_sha)
    selected = [read_main(), *candidates]
    root.mkdir(mode=0o700)
    (root / "APPROVAL.raw.json").write_bytes(approval)
    results = [assess(candidate, root, oracle, migration) for candidate in selected]
    checked_read(approval_path, sha(approval))
    report = {
        "schema": "pfxc.terminal-reassessment.v1",
        "case": CASE,
        "quality_epoch": str(EPOCH),
        "quality_manifest_sha256": approved_sha,
        "approval_sha256": sha(approval),
        "assessment_migration_sha256": sha(migration_path.read_bytes()),
        "driver_sha256": sha(Path(__file__).read_bytes()),
        "capture_sha256": {str(LOG): LOG_SHA, str(PROBE): PROBE_SHA},
        "graded": results,
        "excluded_observed_units": excluded,
        "counts": {"main_terminal_candidates": 1, "local_terminal_candidates": len(candidates),
                   "excluded_units": len(excluded)},
        "raw_scores_changed": False,
        "model_calls": 0,
        "semantic_review_performed": False,
    }
    write(root / "REPORT.json", report)
    print(json.dumps(report["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
