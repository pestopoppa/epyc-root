"""Prospective, bounded fixture execution receipts. No scientific warrant or backfill."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

SCHEMA = "epyc.ci.fixture_execution.v1"
EXCLUSIONS = ["inference", "performance", "promotion", "live_host_corpus",
              "unselected_cases", "undeclared_dependency_completeness"]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular_bytes(path):
    """Never follow a nonregular leaf (including FIFOs and symlinks)."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("artifact is not a regular file")
        with os.fdopen(fd, "rb", closefd=False) as handle:
            return handle.read()
    finally:
        os.close(fd)


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def git_identity(path):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(path), *args], text=True).strip()
    sha = git("rev-parse", "HEAD")
    if len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
        raise ValueError("invalid tested repository SHA")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tested repository has tracked changes")
    return sha


def junit_summary(data):
    """Re-derive identities and counts from the original JUnit bytes, not suite labels."""
    root = ET.fromstring(data)
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("not JUnit")
    cases = []
    for item in root.iter("testcase"):
        name, classname = item.get("name", ""), item.get("classname", "")
        if not name or not classname:
            raise ValueError("unnamed JUnit case")
        duration = float(item.get("time", "0"))
        if not math.isfinite(duration) or duration < 0:
            raise ValueError("invalid case duration")
        statuses = [tag for tag in ("failure", "error", "skipped") if item.find(tag) is not None]
        if len(statuses) > 1:
            raise ValueError("ambiguous case status")
        cases.append({"classname": classname, "name": name,
                      "status": statuses[0] if statuses else "passed"})
    if not cases:
        raise ValueError("no collected cases")
    identities = [(c["classname"], c["name"]) for c in cases]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate JUnit case identity")
    # Validate every suite, including nested suites, against its descendant cases.
    for suite in root.iter("testsuite"):
        items = list(suite.iter("testcase"))
        expected = {"tests": len(items), "failures": sum(i.find("failure") is not None for i in items),
                    "errors": sum(i.find("error") is not None for i in items),
                    "skipped": sum(i.find("skipped") is not None for i in items)}
        for key, count in expected.items():
            if key not in suite.attrib or int(suite.attrib[key]) != count:
                raise ValueError("inconsistent JUnit suite counts")
    counts = {key: sum(c["status"] == key for c in cases)
              for key in ("passed", "failure", "error", "skipped")}
    counts["collected"] = len(cases)
    counts["executed"] = len(cases) - counts["skipped"]
    return {"cases": cases, "counts": counts}


def decide(summary, exit_code):
    counts = summary["counts"]
    if counts["executed"] == 0:
        return None, "all collected cases skipped"
    if exit_code < 0:
        return None, "command interrupted"
    if exit_code == 0 and (counts["failure"] or counts["error"]):
        return None, "exit zero contradicts JUnit failures/errors"
    if exit_code != 0 and not (counts["failure"] or counts["error"]):
        return None, "nonzero exit without JUnit failure/error"
    return exit_code == 0, ""


def proposition(record):
    """Only the producer calls this to author the original bounded assertion."""
    return ("In captured runner " + json.dumps(record["runner"], sort_keys=True)
            + ", argv " + json.dumps(record["argv"])
            + " at tested repository SHAs " + json.dumps(record["repositories"], sort_keys=True)
            + " reported these named collected JUnit cases and statuses "
            + json.dumps(record["summary"]["cases"], sort_keys=True)
            + "; executed cases passed and command exited zero: "
            + str(record["fixture_execution_conformant"]).lower()
            + ". Skipped cases and " + ", ".join(EXCLUSIONS) + " are excluded.")


def artifact(directory, name, data):
    path = directory / name
    with path.open("xb") as handle:
        handle.write(data)
    return {"name": name, "sha256": digest(data)}


def capture_fixture_execution(*, argv, cwd, junit, output, repositories, read_paths, selections):
    if not argv or not selections or not repositories or not read_paths:
        raise ValueError("argv, explicit selections, repositories and readset required")
    producer = Path(__file__).resolve()
    read_paths = list(dict.fromkeys([producer, *[Path(path).resolve() for path in read_paths]]))
    cwd, junit, output = Path(cwd).resolve(), Path(junit), Path(output)
    if not junit.is_absolute():
        junit = cwd / junit
    if os.path.lexists(junit):
        raise ValueError("JUnit output already exists; no old-run capture")
    output.mkdir(parents=True, exist_ok=False)
    identities = {name: git_identity(path) for name, path in repositories.items()}
    readset = []
    for index, source in enumerate(read_paths):
        data = regular_bytes(source)
        leaf = f"read-{index:03d}.bin"
        pin = artifact(output, leaf, data)
        readset.append({"name": str(source), "role": "producer" if source == producer else "declared_read",
                        "artifact": pin})
    runner = {"run_id": os.environ.get("GITHUB_RUN_ID", ""),
              "job": os.environ.get("GITHUB_JOB", ""),
              "attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
              "os": platform.platform(), "python": platform.python_version()}
    record = {"schema": SCHEMA, "started_utc": utc(), "runner": runner,
              "argv": list(argv), "cwd": str(cwd), "selections": list(selections),
              "repositories": identities, "readset": readset, "exclusions": EXCLUSIONS,
              "metric": "fixture_execution_conformant", "metric_direction": "higher_better",
              "category": "CANDIDATE", "protocol_id": ""}
    # Persist the original recipe before launch; later readers never author its identity.
    record["request"] = artifact(output, "execution-request.json", canonical(record))
    # Exclusive log creation happens before the command. No ambient environment is persisted.
    with (output / "command.log").open("xb") as log:
        process = subprocess.Popen(argv, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
        record["exit_code"] = process.wait()
    record["ended_utc"] = utc()
    record["log"] = {"name": "command.log", "sha256": digest(regular_bytes(output / "command.log"))}
    record["summary"] = None
    record["junit"] = None
    record["fixture_execution_conformant"] = None
    record["diagnostic"] = ""
    try:
        data = regular_bytes(junit)
        record["junit"] = artifact(output, "original-junit.xml", data)
        record["summary"] = junit_summary(data)
        record["fixture_execution_conformant"], record["diagnostic"] = decide(record["summary"], record["exit_code"])
        if identities != {name: git_identity(path) for name, path in repositories.items()}:
            raise ValueError("tested repository identity changed during execution")
        if any(digest(regular_bytes(source)) != pin["artifact"]["sha256"]
               for source, pin in zip(read_paths, readset)):
            raise ValueError("declared readset changed during execution")
    except (OSError, ValueError, ET.ParseError) as exc:
        record["fixture_execution_conformant"] = None
        record["diagnostic"] = str(exc)
    record["decided_proposition"] = (proposition(record)
                                     if record["fixture_execution_conformant"] is not None else "")
    record["receipt_sha256"] = digest(canonical(record))
    artifact(output, "receipt.json", canonical(record) + b"\n")
    return record


def read_receipt(path):
    """Strictly reopen captured sidecars; never create a historical native record."""
    path = Path(path)
    original = regular_bytes(path)
    record = json.loads(original)
    if not isinstance(record, dict) or record.get("schema") != SCHEMA:
        raise ValueError("not a prospective fixture receipt")
    unsigned = dict(record)
    seal = unsigned.pop("receipt_sha256", None)
    if seal != digest(canonical(unsigned)):
        raise ValueError("receipt seal mismatch")
    if set(record["runner"]) != {"run_id", "job", "attempt", "os", "python"}:
        raise ValueError("unexpected runner facts")
    for key in ("started_utc", "ended_utc"):
        if not isinstance(record[key], str) or not record[key].endswith("Z"):
            raise ValueError("execution time must be UTC")
    started = datetime.fromisoformat(record["started_utc"].replace("Z", "+00:00"))
    ended = datetime.fromisoformat(record["ended_utc"].replace("Z", "+00:00"))
    if ended < started:
        raise ValueError("execution time reversed")
    if type(record["exit_code"]) is not int:
        raise ValueError("exit code must be an integer")
    for sha in record["repositories"].values():
        if not isinstance(sha, str) or len(sha) != 40 or any(c not in "0123456789abcdef" for c in sha):
            raise ValueError("invalid tested repository SHA")
    for pin in [record["request"], record["log"], *[item["artifact"] for item in record["readset"]],
                *([record["junit"]] if record["junit"] else [])]:
        name = pin["name"]
        if not name or Path(name).name != name or name in {".", ".."}:
            raise ValueError("nonlocal artifact")
        if digest(regular_bytes(path.parent / name)) != pin["sha256"]:
            raise ValueError("original artifact digest mismatch")
    request = json.loads(regular_bytes(path.parent / record["request"]["name"]))
    expected_fields = {"schema", "started_utc", "runner", "argv", "cwd", "selections",
                       "repositories", "readset", "exclusions", "metric", "metric_direction",
                       "category", "protocol_id"}
    if set(request) != expected_fields or any(record[key] != value for key, value in request.items()):
        raise ValueError("receipt differs from original pre-execution request")
    if not record["argv"] or not record["selections"] or not record["repositories"] or not record["readset"]:
        raise ValueError("missing original execution identity")
    if sum(item.get("role") == "producer" for item in record["readset"]) != 1:
        raise ValueError("missing original producer source proof")
    if record["fixture_execution_conformant"] is None:
        if not record["diagnostic"] or record["decided_proposition"]:
            raise ValueError("diagnostic receipt cannot assert conformance")
        return record, digest(original)
    summary = junit_summary(regular_bytes(path.parent / record["junit"]["name"]))
    result, diagnostic = decide(summary, record["exit_code"])
    if summary != record["summary"] or result is not record["fixture_execution_conformant"] or diagnostic:
        raise ValueError("native decision contradicts original JUnit/exit")
    if record["metric"] != "fixture_execution_conformant" or record["metric_direction"] != "higher_better":
        raise ValueError("unexpected native boolean metric")
    if record["protocol_id"] or record["exclusions"] != EXCLUSIONS:
        raise ValueError("unsupported warrant or scope")
    if record["decided_proposition"] != proposition(record):
        raise ValueError("native proposition contradicts execution")
    return record, digest(original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True)
    parser.add_argument("--junit", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo", action="append", required=True, help="label=path")
    parser.add_argument("--read-path", action="append", required=True)
    parser.add_argument("--select", action="append", required=True)
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
    repos = dict(item.split("=", 1) for item in args.repo)
    record = capture_fixture_execution(argv=argv, cwd=args.cwd, junit=args.junit,
        output=args.output, repositories=repos, read_paths=args.read_path, selections=args.select)
    print(json.dumps({"receipt": str(Path(args.output) / "receipt.json"),
                      "conformant": record["fixture_execution_conformant"],
                      "diagnostic": record["diagnostic"]}))
    return record["exit_code"] if record["exit_code"] > 0 else (0 if record["fixture_execution_conformant"] is True else 1)


if __name__ == "__main__":
    sys.exit(main())
