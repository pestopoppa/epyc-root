#!/usr/bin/env python3
"""Prospective isolated pytest entry; sealed paths and zero ambient plugin loading."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--stage", choices=("focused", "full"), required=True)
    parser.add_argument("--results", required=True)
    args, selectors = parser.parse_known_args()
    body = Path(args.approval).read_bytes()
    if hashlib.sha256(body).hexdigest() != args.sha:
        raise SystemExit("approval changed before pytest entry")
    approval = json.loads(body)
    if (approval.get("status") != "MAIN_APPROVED_NATIVE" or approval.get("approved") is not True
            or approval.get("native_launch_approved") is not True or approval.get("source_review_approved") is not True):
        raise SystemExit("UNARMED")
    own = Path(__file__).resolve().parent
    sys.path.insert(0, str(own))
    from runner import Runtime, FOCUSED, digest, grant_cpus, grant_fields
    # Stage child must not allocate a second run directory or reinterpret native authority.
    expected = (["scripts/kernel_rnd/autokernel/loop/" + name for name in FOCUSED]
                if args.stage == "focused" else ["scripts/kernel_rnd/autokernel/loop"])
    if selectors != expected:
        raise SystemExit("exact focused/full selectors changed")
    if os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD") != "1":
        raise SystemExit("ambient plugin autoload enabled")
    runtime = object.__new__(Runtime)
    runtime.approval_path = Path(args.approval)
    runtime.approval_sha = args.sha
    runtime.approval = approval
    runtime.verify_sources()
    runtime.flags = Path("/mnt/raid0/llm/tmp/compute-flags")
    runtime.grant = runtime.flags / "grants" / (approval["row_id"] + ".grant")
    runtime.grant_sha = digest(runtime.grant)
    context = json.loads(Path(approval["acquired_owner_context"]).read_text())
    if (context["row_id"] != approval["row_id"] or context["approval_sha256"] != args.sha
            or context["canonical_grant_sha256"] != runtime.grant_sha
            or context["producer_sha256"] != approval["runner_files"]["capture_native"]["sha256"]):
        raise SystemExit("stage owner context changed")
    runtime.owner = tuple(context["captured_owner_identity"])
    runtime.cancelled = None
    if os.environ.get("FILLER_ID") != approval["row_id"] or approval["declared_cpu_policy"] != "first-n-canonical":
        raise SystemExit("stage outside exact official row")
    runtime.declared = set(sorted(grant_cpus(grant_fields(runtime.grant.read_text())["regions"]))[:approval["declared_cpu_count"]])
    runtime.boundary()
    roots = os.environ["PYTHONPATH"].split(os.pathsep)
    # -S retains stdlib only; explicitly add approved source/site roots, never .pth imports.
    sys.path = [str(own), *roots, *[p for p in sys.path if p and p != str(own)]]
    result = Path(args.results).resolve()
    if not result.is_relative_to(Path(approval["own_state_root"]).resolve()):
        raise SystemExit("stage result path escapes own state")
    base = result / "tmp" / (args.stage + "-pytest")
    if base.exists():
        raise SystemExit("basetemp must be unique")
    sys.argv = ["pytest", "-q", "-p", "no:cacheprovider", "-p", "no:xdist",
        "-c", str(Path(approval["materialized"]["research"]["root"]) / "pyproject.toml"),
        "--rootdir=" + approval["materialized"]["research"]["root"],
        "--basetemp=" + str(base), "--junitxml=" + str(result / (args.stage + ".junit.xml")), *selectors]
    runpy.run_module("pytest", run_name="__main__", alter_sys=True)

if __name__ == "__main__":
    main()
