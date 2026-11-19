#!/usr/bin/env python3
"""Capture one model-free C5 CPU property case through an isolated AutoKernel journal."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
ROW = "ni-sc18-cpu-softmax-property-20261118-v1"
FLAGS = Path("/mnt/raid0/llm/tmp/compute-flags")
BINARY = HERE / "candidate/bin/test-backend-ops"
CPU_THREADS = {40, 41, 42, 43}
SEED = 4711
OP = "SOFT_MAX"
PARAMS = ("type=f32,ne=[16,16,1,1],mask=0,sinks=0,m_prec=f32,nr23=[1,1],"
          "scale=1.000000,max_bias=0.000000,inplace=0")
METRIC = "softmax_invariants/v1"
COMMIT = "c72ec82f5417bb2937310326120f149b665e8400"
ANCHOR_COMMIT = "cdb4d8c77c2300f61c404a3df6d1950934b39c98"
RESEARCH_COMMIT = "6decaeda4481a841b3a85b55b0be87a6963b3042"
ENV = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC",
       "LD_LIBRARY_PATH": str(BINARY.parent), "OMP_NUM_THREADS": "1",
       "AUTOKERNEL_CPU_N_THREADS": "1", "AUTOKERNEL_BACKEND_THREADS": "1"}
ARGV = [str(BINARY), "test", "-b", "CPU", "-o", OP, "-p", "^" + re.escape(PARAMS) + "$",
        "-j", "1", "--suite-seed", str(SEED), "--autokernel-properties"]
sys.path[:0] = [str(HERE / "research/scripts/kernel_rnd"), str(HERE / "scripts/vidya")]

from autokernel import journal, schemas
from autokernel.evaluator import api, correctness
from autokernel.execution import t0_provider
from adapters import autokernel_property as property_adapter
from fold import FT_SUPPORT
from ledger import Ledger


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reference(path):
    return f"{path}#sha256={sha(path)}"


def now(epoch=None):
    return datetime.fromtimestamp(epoch if epoch is not None else time.time(), timezone.utc).isoformat()


def canonical(data):
    return schemas.content_hash(data)


def write_json(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_json(path):
    return json.loads(path.read_bytes())


def input_check():
    subprocess.run(["/usr/bin/sha256sum", "--quiet", "-c", "PINNED.sha256"],
                   cwd=HERE, check=True, env=ENV)
    with BINARY.open("rb") as stream:
        binary = stream.read()
    for name in (b"AK_PROP_V2 metric=", b"--autokernel-properties", b"--suite-seed"):
        require(name in binary, f"missing compiled property capability {name}")
    manifests = {}
    for label in ("candidate", "anchor"):
        checksum = HERE / f"source/{label}-SHA256SUMS"
        inventory = dict((name, digest) for digest, name in
                         (line.split("  ", 1) for line in checksum.read_text().splitlines()))
        ggml_names = [path.name for path in BINARY.parent.glob("libggml*.so.*.*.*")]
        names = ["test-backend-ops", *sorted(ggml_names)]
        require(len(names) == 4, "expected one CPU executable and three CPU ggml DSOs")
        manifests[label] = {name: inventory[f"./{name}"] for name in names}
    for label in ("candidate", "anchor"):
        actual = {name: sha(HERE / label / "bin" / name) for name in manifests[label]}
        require(actual == manifests[label], f"{label} CPU instrument differs from its manifest")
    check = subprocess.run(["/bin/bash", str(HERE / "verify_ggml_linkage.sh"), str(BINARY),
                            str(BINARY.parent)], capture_output=True, text=True, env=ENV, check=True)
    require("PASS:" in check.stdout and "libggml-hip" not in check.stdout, "CPU linkage check failed")
    return manifests, check.stdout + check.stderr


def output_root():
    if os.environ.get("FILLER_DRYRUN") == "1":
        return Path(os.environ["FILLER_DRYRUN_DIR"]) / f"property-{os.environ['FILLER_SMOKE_T0']}"
    return HERE / "native"


def cpu_set(text):
    cpus = set()
    for part in text.split(","):
        require(re.fullmatch(r"\d+(?:-\d+)?", part), "non-CPU token in grant")
        low, _, high = part.partition("-")
        require(0 <= int(low) <= int(high or low) < 192, "invalid CPU span")
        cpus.update(range(int(low), int(high or low) + 1))
    return cpus


def grant():
    require(os.environ["FILLER_ID"] == ROW, "wrong filler identity")
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    flag_root = Path(os.environ["FILLER_DRYRUN_DIR"]) if smoke else FLAGS
    stop = Path(os.environ["FILLER_STOPFILE"])
    require(stop == (flag_root / "stop" if smoke else HERE / "STOP"), "wrong STOP path")
    path = flag_root / "grants" / f"{ROW}.grant"
    raw = path.read_text()
    grant_fields = dict(token.split("=", 1) for token in raw.split() if "=" in token)
    start, end = (datetime.fromisoformat(grant_fields[key]).timestamp() for key in ("start", "end"))
    granted = cpu_set(grant_fields["regions"])
    physical = {cpu % 96 for cpu in granted}
    require(len(physical) == 4 and (smoke or physical == CPU_THREADS)
            and start <= time.time() < end, "invalid four-core CPU grant")
    require(os.sched_getaffinity(0) == cpu_set(os.environ["FILLER_CPUS"]) == granted,
            "wrong effective CPU affinity")
    deadline = min(float(os.environ["FILLER_DEADLINE"]), end - 90)
    require(start < deadline <= end - 90, "invalid grant deadline")
    return path, raw, stop, deadline


def guard(stop, deadline):
    require(not stop.exists() and not list(FLAGS.glob("HOLD_*")), "STOP or host HOLD")
    require(time.time() < deadline, "capture deadline reached")


def invoke_native(out, stop, deadline):
    start = time.time()
    local_deadline = min(deadline, start + 30)
    with (out / "stdout.log").open("xb") as stdout, (out / "stderr.log").open("xb") as stderr:
        child = subprocess.Popen(
            ARGV, cwd=BINARY.parent, stdout=stdout, stderr=stderr,
            env={**ENV, "FILLER_ID": ROW, "FILLER_STOPFILE": str(stop)})
        try:
            with open(os.environ["FILLER_PIDFILE"], "a") as stream:
                stream.write(f"{child.pid}\n")
            while child.poll() is None:
                guard(stop, local_deadline)
                time.sleep(0.02)
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
            for stream in (stdout, stderr):
                stream.flush()
                os.fsync(stream.fileno())
    return child.pid, child.returncode, start, time.time()


def gate_from_output(stdout, stderr, rc, evidence_ref):
    require(rc in (0, 1), f"invalid native exit {rc}")
    require(len(stdout) + len(stderr) <= 64 * 1024, "native output exceeded bound")
    output = stdout.decode("utf-8")
    diagnostics = stderr.decode("utf-8")
    controls = [line for line in diagnostics.splitlines()
                if line.startswith("AUTOKERNEL_PROPERTY_SELF_TEST ")]
    require(len(controls) == 1, "missing or repeated property self-test")
    t0_provider.parse_backend_ops_property_self_test(controls[0], expected_suite_seed=SEED)
    parsed = t0_provider.parse_backend_ops_console(output)
    parsed.reconcile()
    overall = "OK" if rc == 0 else "FAIL"
    require(parsed.overall == overall and parsed.devices_expected == parsed.backends_total == 1
            and parsed.backends_passed == (1 if rc == 0 else 0)
            and len(parsed.backends) == len(parsed.cases) == 1, "wrong CPU terminal census")
    backend = parsed.backends[0]
    case = parsed.cases[0]
    require(backend.name == "CPU" and not backend.skipped and backend.status == overall
            and backend.reported_total == 1 and case.op == OP and case.params == PARAMS
            and case.status == ("ok" if rc == 0 else "fail") and len(case.properties) == 1,
            "missing or wrong selected CPU property case")
    property_result = case.properties[0]
    require((property_result.metric_id, property_result.suite_seed, property_result.transform,
             property_result.receipt_version, property_result.passed) ==
            (METRIC, SEED, "identity", 2, rc == 0), "wrong V2 metric, seed, transform or verdict")
    measurement = correctness.PropertyMeasurement(
        shape_id=f"{case.op}({case.params})#0", op=case.op, backend=backend.name,
        metric_id=property_result.metric_id, residual=property_result.residual,
        tolerance=property_result.tolerance, suite_seed=property_result.suite_seed,
        passed=property_result.passed, input_transform=property_result.transform)
    return api.GateResult(correctness.GID_OP_UNITS, api.GATE_CORRECTNESS,
                          schemas.Check(schemas.PASS if rc == 0 else schemas.FAIL, ()),
                          evidence_ref=evidence_ref, measurements=(measurement.to_dict(),)).to_dict()


def make_event(out, request, manifests, gate):
    """Build the v5 carrier for this finite diagnostic. The Journal validates it before append."""
    campaign = request["campaign"]
    event_id = f"ake-{campaign[3:]}"
    linkage = {key: canonical({name: digest for name, digest in inventory.items()
                               if name.startswith("libggml")})
               for key, inventory in manifests.items()}
    evidence = gate["evidence_ref"]
    return {
        "schema": schemas.SCHEMA_EVALUATION_EVENT, "event_id": event_id,
        "campaign_id": campaign, "candidate_id": "akc-c5-c72ec82f5-cpu-property",
        "tier": "T0", "backend": "llama_cpu", "device_state": None,
        "change_class": "arithmetic", "anchor_tier": "T0", "transfer_ratio_to": [],
        "claim_grammar": {"category": "CANDIDATE", "protocol_id": property_adapter.DIAGNOSTIC_RECIPE_ID,
                          "metric": METRIC, "metric_direction": "lower_better", "reps": 1,
                          "attestation_ref": evidence},
        "evaluator": {"id": property_adapter.DIAGNOSTIC_RECIPE_ID,
                      "bundle_sha256": sha(HERE / "PINNED.sha256")},
        "artifact": {"source_sha256": sha(HERE / "source/c5-test-backend-ops.cpp"),
                     "binary_sha256": manifests["candidate"]["test-backend-ops"],
                     "linkage_sha256": linkage["candidate"]},
        "anchor": {"source_commit": ANCHOR_COMMIT,
                   "binary_sha256": manifests["anchor"]["test-backend-ops"], "linkage_sha256": linkage["anchor"],
                   "measurement_event_ids": [], "tool": "test-backend-ops"},
        "scope_manifest_sha256": sha(out / "request.json"),
        "host_receipt": reference(out / "host.json"), "resource_claim_receipt": reference(out / "grant.txt"),
        "co_residency": "single", "correctness": {correctness.GID_OP_UNITS: gate},
        "quality": {}, "stability": {}, "mechanism": {},
        "scope_denominator": {"machine_subset": "partial", "numa_nodes": [], "devices": ["CPU"],
                              "cores": len(CPU_THREADS)},
        "determinism": {"class": "not_measured", "same_seed_repeat_runs": 0},
        "performance": {"raw_samples": [], "paired_blocks": 0, "estimate": None, "uncertainty": None,
                        "search_discipline": {"suite_seed": SEED, "raw_evidence_ref": evidence,
                                              "record_class": property_adapter.DIAGNOSTIC_RECORD_CLASS,
                                              "speed_rank_admissible": False,
                                              "publisher_smoke": request["purpose"] == "publisher_smoke",
                                              "gates_not_run": ["remaining T0 correctness", "quality",
                                                                "stability", "mechanism", "performance"]}},
        "integrity_flags": [], "status": "inconclusive", "supersedes": [],
        "created_at": request["created_at"],
    }


def append_event(out, event):
    store = journal.Journal(str(out / "journal"), campaign_id=event["campaign_id"])
    store.initialize()
    return store.append(journal.KIND_EVALUATION_EVENT, event, record_id=event["event_id"])


def ingest(out, timestamp, action):
    args = [sys.executable, "-BI", str(HERE / "scripts/vidya/cli.py"), "--json", "ingest",
            "autokernel-property", "--root", str(out / "journal"), "--as-of", timestamp,
            "--ledger", str(out / "isolated-ledger.jsonl"), "--only-new"]
    if action == "dry-run":
        args.append("--dry-run")
    result = subprocess.run(args, env=ENV, capture_output=True, text=True, check=True, timeout=30)
    return json.loads(result.stdout)


def assert_ingest(report, expected_frames):
    require(report["documents_matched"] == report["rows_projected"] == 1
            and report["refused"] == report["documents_yielding_no_rows"] == 0
            and report["by_adapter"] == {"autokernel_property": 1}
            and report["frames_emitted"] == expected_frames, "wrong registered ingest outcome")


def result_for(out, request, entry, gate):
    ledger_path = out / "isolated-ledger.jsonl"
    receipts = Ledger(ledger_path).read_all()
    evidence = [item.frame["assertion"] for item in receipts if item.frame["frame_type"] == FT_SUPPORT]
    require(len(receipts) == 3 and len(evidence) == 1, "wrong isolated ledger census")
    grade = {"Q": "Judged", "T": "Located"}
    require(evidence[0]["grade"] == grade and evidence[0]["protocol_id"] == ""
            and evidence[0]["category"] == "CANDIDATE", "diagnostic acquired a protocol warrant")
    return {"completed": True, "purpose": request["purpose"], "event_id": entry.record_id,
            "journal_entry": entry.event_id, "native_outcome": gate["outcome"], "projected": 1,
            "refused": 0, "retry_frames": 0, "grade": grade, "ledger_sha256": sha(ledger_path)}


def validate_capture(out):
    require((out / "RESULT.json").is_file(), "missing terminal result")
    result = read_json(out / "RESULT.json")
    request = read_json(out / "request.json")
    expected_purpose = "official" if out == HERE / "native" else "publisher_smoke"
    require(request["purpose"] == expected_purpose == result["purpose"], "purpose mismatch")
    manifests, _ = input_check()
    native = read_json(out / "native.json")
    require(request["argv"] == ARGV and request["environment"] == ENV and request["seed"] == SEED
            and native["request_sha256"] == sha(out / "request.json"), "changed prospective request")
    require(native["raw_sha256"] == {name: sha(out / name) for name in ("stdout.log", "stderr.log")},
            "changed native logs or log inventory")
    gate = gate_from_output((out / "stdout.log").read_bytes(), (out / "stderr.log").read_bytes(),
                            native["exit"], reference(out / "native.json"))
    event = make_event(out, request, manifests, gate)
    entries = journal.Journal(str(out / "journal"), campaign_id=request["campaign"]).read_all()
    require(len(entries) == 1 and entries[0].payload == event, "journal event changed")
    assert_ingest(ingest(out, request["created_at"], "dry-run"), 0)
    reports = read_json(out / "ingest.json")
    assert_ingest(reports["first"], 3)
    assert_ingest(reports["retry"], 0)
    require(result == result_for(out, request, entries[0], gate), "terminal result changed")
    return 0


def interrupt(_signum, _frame):
    raise InterruptedError("row received stop signal")


def run():
    path, raw_grant, stop, deadline = grant()
    guard(stop, deadline)
    manifests, linkage = input_check()
    out = output_root()
    out.mkdir()
    purpose = "official" if out == HERE / "native" else "publisher_smoke"
    request = {"purpose": purpose, "campaign": f"ak-{ROW}-{purpose.replace('_', '-')}",
               "seed": SEED, "argv": ARGV, "environment": ENV,
               "source_commit": COMMIT, "source_dirty_state": "UNKNOWN",
               "research_commit": RESEARCH_COMMIT, "inputs_sha256": sha(HERE / "PINNED.sha256"),
               "structural_anchor_only": ANCHOR_COMMIT, "created_at": now()}
    write_json(out / "request.json", request)
    write_json(out / "host.json", {"hostname": socket.gethostname(), "kernel": os.uname().release,
                                  "cpu_affinity": sorted(os.sched_getaffinity(0)),
                                  "linkage_probe": linkage})
    with (out / "grant.txt").open("x") as stream:
        stream.write(raw_grant)
        stream.flush()
        os.fsync(stream.fileno())
    print("SC18 prospective custody written; starting one model-free CPU invocation", flush=True)
    guard(stop, deadline)
    pid, rc, started, ended = invoke_native(out, stop, deadline)
    hashes = {name: sha(out / name) for name in ("stdout.log", "stderr.log")}
    native = {"pid": pid, "exit": rc, "started_at": now(started), "ended_at": now(ended),
              "raw_sha256": hashes, "request_sha256": sha(out / "request.json")}
    write_json(out / "native.json", native)
    guard(stop, deadline)
    require(path.read_text() == raw_grant, "allocator grant changed across invocation")
    require(input_check()[0] == manifests, "pinned inputs changed across invocation")
    gate = gate_from_output((out / "stdout.log").read_bytes(), (out / "stderr.log").read_bytes(), rc,
                            reference(out / "native.json"))
    event = make_event(out, request, manifests, gate)
    entry = append_event(out, event)
    print("SC18 raw V2 residual journaled; checking isolated CLI ingestion", flush=True)
    guard(stop, deadline)
    accepted = ingest(out, request["created_at"], "write")
    assert_ingest(accepted, 3)
    ledger = out / "isolated-ledger.jsonl"
    ledger_digest = sha(ledger)
    retry = ingest(out, request["created_at"], "write")
    assert_ingest(retry, 0)
    require(sha(ledger) == ledger_digest, "retry mutated isolated ledger")
    write_json(out / "ingest.json", {"first": accepted, "retry": retry})
    guard(stop, deadline)
    write_json(out / "RESULT.json", result_for(out, request, entry, gate))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "run", "complete", "smoke"))
    args = parser.parse_args()
    if args.action == "verify":
        input_check()
        return 0
    if args.action in ("complete", "smoke"):
        return validate_capture(output_root())
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupt)
    return run()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        sys.exit(str(exc))
