#!/usr/bin/env python3
"""Behavior fixtures for the reviewed SPEC-GRAM.3 relocatable-CPU repair."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timedelta, timezone

CHECKER = Path(__file__).parents[1] / "engine" / "dryrun_check.py"
spec = importlib.util.spec_from_file_location("canonical_dryrun_check", CHECKER)
dc = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(dc)
ROOT = Path("/mnt/raid0/llm/tmp/codex-ni-specgram3-repair-20261101")
ID = "codex-ni-specgram3-llg101-cpu-r2-20261101"
SCRATCH = ROOT / "fixture-scratch"
SCRATCH.mkdir(exist_ok=True)


def row(claim="dynamic", window=21600):
    notes = (f"requested_window_s={window}; claimed_cpus={claim}; est_output_GiB=1; "
             f"scratch_root={SCRATCH}; process_limit_GiB=48; launcher_path=/fixture/launch.sh; "
             "job_path=/fixture/job.py; source_manifest=/fixture/SOURCES.sha256")
    cells = [ID, "codex-ni", "/fixture/launch.sh", "any-cpu-quarter", "1200 s", "56",
             "/fixture/STOP", "BACKLOG", "block-correctness", f"{window} s", "1200 s",
             "n", "y", "/fixture/out/RESULT.json",
             "SPEC-GRAM3 original native1.0.1 cost arm plus actual autoregressive greedy and 5450-call replay; no parent completion",
             "n/a (combined diagnostic; original acceptance retained)", "cpu", notes]
    return "| " + " | ".join(cells) + " |\n"


def call_admit(row_path, grant_path, min_window_s=1200):
    args = argparse.Namespace(row_file=str(row_path), id=ID, grant=str(grant_path),
                              min_window_s=min_window_s, scoped_pf=False,
                              require_proof=False, engine="/fixture/engine",
                              policy=str(CHECKER.with_name("dryrun_disk_policy.json")))
    return dc.admission(args)


def grant(path, regions, end_delta=21600):
    start = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    end = start + timedelta(seconds=end_delta)
    path.write_text(f"regions={regions} start={start:%Y-%m-%dT%H:%MZ} end={end:%Y-%m-%dT%H:%MZ}\n")


def must_refuse(fn, text):
    try:
        fn()
    except dc.Refused as exc:
        assert text in str(exc), (text, str(exc))
    else:
        raise AssertionError(f"expected refusal containing {text!r}")


def main():
    proposed = ROOT / "proposed-r2-row.md"
    # The real proposal must already satisfy the canonical row contract.
    proposed_row = dc.row_record(proposed, ID)
    assert proposed_row["notes"]["claimed_cpus"] == "dynamic"
    assert proposed_row["cpus"] == set() and proposed_row["cells"][3] == "any-cpu-quarter"
    manifest = json.loads((ROOT / "manifest-producer-draft.json").read_text())
    assert manifest["claimed_cpus"] == "dynamic" and not manifest["ready_manifest"]

    row_path = ROOT / "fixture-row.md"
    row_path.write_text(row())
    parsed = dc.row_record(row_path, ID)
    assert parsed["cpus"] == set(), "dynamic claim must defer CPU authority to actual grant"

    # Actual ended-run CPU shape and a valid relocation both resolve from the grant.
    for name, cpus in (("actual-24-47", "24-47"), ("relocated-72-95", "72-95")):
        grant_path = ROOT / f"{name}.grant"
        grant(grant_path, cpus)
        admitted = call_admit(row_path, grant_path)
        assert admitted["window"] == 21600
        # These are the same region-list and taskset CPU-list values the keeper
        # exports as WS58_REGIONS and FILLER_CPUS for the in-claim checker.
        old_regions = os.environ.get("WS58_REGIONS")
        os.environ["WS58_REGIONS"] = cpus
        observed_grant = dc.grant_cpus(os.environ["WS58_REGIONS"])
        if old_regions is None: os.environ.pop("WS58_REGIONS", None)
        else: os.environ["WS58_REGIONS"] = old_regions
        expected = set(range(int(cpus.split("-")[0]), int(cpus.split("-")[1]) + 1))
        assert observed_grant == expected
        parsed_regions, _, _ = dc.parse_grant(grant_path)
        assert dc.grant_cpus(parsed_regions) == expected
        assert dc.row_record(row_path, ID)["cpus"] == set()

    # Prove resources() uses the real allowed grant CPU set, not a hardcoded quarter.
    old_affinity = dc.os.sched_getaffinity
    old_limits = dc.limits_record
    try:
        for allowed in ("24-47", "72-95"):
            target = dc.cpus(allowed)
            old_fill = os.environ.get("FILLER_CPUS")
            os.environ["FILLER_CPUS"] = allowed
            dc.os.sched_getaffinity = lambda _pid, target=target: target
            observed = {}
            def fake_limits(ram, process, required, allowed_set):
                observed.update(required=required, allowed=allowed_set)
                return {"affinity": sorted(target)}
            dc.limits_record = fake_limits
            dc.resources(argparse.Namespace(row_file=str(row_path), id=ID,
                                            allowed_cpus=os.environ["FILLER_CPUS"], scoped_pf=False))
            assert observed == {"required": target, "allowed": target}
            if old_fill is None: os.environ.pop("FILLER_CPUS", None)
            else: os.environ["FILLER_CPUS"] = old_fill
    finally:
        dc.os.sched_getaffinity = old_affinity
        dc.limits_record = old_limits

    # A symbolic alias in the claim field is invalid; only canonical dynamic is accepted.
    row_path.write_text(row(claim="any-cpu-quarter"))
    must_refuse(lambda: dc.row_record(row_path, ID), "malformed claimed_cpus")
    row_path.write_text(row(claim="dynamic") .replace("requested_window_s=21600; claimed_cpus=dynamic;", "requested_window_s=21600; est_output_GiB=1;"))
    must_refuse(lambda: dc.row_record(row_path, ID), "missing notes keys")

    # Window reserve and expired-grant checks remain fail-closed.
    row_path.write_text(row())
    short = ROOT / "short-window.grant"
    row_path.write_text(row(window=1200))
    grant(short, "24-47", end_delta=1200)
    # The shortened row matches the grant; only the reserve guard should fail.
    must_refuse(lambda: call_admit(row_path, short, 1200), "min_window 1200s + 300s exceeds booked")
    row_path.write_text(row())
    expired = ROOT / "expired.grant"
    expired.write_text("regions=24-47 start=2026-10-31T00:00Z end=2026-10-31T06:00Z\n")
    must_refuse(lambda: call_admit(row_path, expired), "grant expired")

    # Atomic native boundary receipt writer, with host resource observation stubbed.
    job = ROOT / "fixture-job.py"
    job.write_text("# pinned fixture\n")
    receipt = ROOT / "receipt.json"
    env = {
        "FILLER_PREFLIGHT": "1", "DRYRUN_NONCE": "a" * 48,
        "DRYRUN_RECEIPT": str(receipt), "DRYRUN_JOB_SHA256": dc.sha(job),
        "DRYRUN_RAM_GIB": "56", "DRYRUN_PROCESS_LIMIT_GIB": "48",
        "DRYRUN_REQUIRED_CPUS": "24-25", "DRYRUN_ALLOWED_CPUS": "24-47",
        "DRYRUN_LAUNCHER_SHA256": "b" * 64,
    }
    before = {key: os.environ.get(key) for key in env}
    try:
        os.environ.update(env)
        dc.limits_record = lambda ram, process, required, allowed: {
            "affinity": sorted(required), "reserved_ram_gib": ram,
            "process_limit_gib": process,
        }
        dc.boundary(argparse.Namespace(job=str(job), effect="fixture-before-effect"))
    finally:
        for key, value in before.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value
        dc.limits_record = old_limits
    record = json.loads(receipt.read_text())
    assert record["effect"] == "fixture-before-effect" and record["job_sha256"] == dc.sha(job)
    assert record["nonce"] == "a" * 48 and not list(ROOT.glob("receipt.json.tmp.*"))
    print("PASS dynamic actual/relocated CPU grants, malformed metadata, deadline reserve, expired grant, atomic receipt")


def test_all() -> None:
    main()


if __name__ == "__main__":
    main()
