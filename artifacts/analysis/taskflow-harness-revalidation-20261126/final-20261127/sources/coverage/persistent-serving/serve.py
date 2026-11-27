"""Keep qualified C22 serving owned until main closes the follow-up campaign."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "legacy-boundary-v3"
SOURCE_SEAL = "185ba0467a41eefd63a9ada0d3856abb565ce7d5a7a6f0af68ef4d0362a288cb"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-sha256", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if sha(Path(__file__)) != args.approved_sha256:
        raise RuntimeError("main-approved serving wrapper changed")
    manifest = SOURCE / "RUNNER-SEAL.json"
    if sha(manifest) != SOURCE_SEAL:
        raise RuntimeError("qualified serving source manifest changed")
    for name, expected in json.loads(manifest.read_text())["sha256"].items():
        if sha(SOURCE / name) != expected:
            raise RuntimeError("qualified serving source changed: " + name)
    sys.path.insert(0, str(SOURCE))
    spec = importlib.util.spec_from_file_location("qualified_persistent_serving", SOURCE / "run.py")
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    cpu, gpu, _, _ = engine.inputs()
    engine.verify(SOURCE_SEAL, cpu.legacy)
    epoch = args.out.resolve()
    if not epoch.is_relative_to(HERE / "runs") or epoch == HERE / "runs":
        raise ValueError("use a new private persistent-serving epoch")
    epoch.mkdir(parents=True, mode=0o700)
    grant = engine.region(True)
    cpu.legacy.write(epoch / "GRANT.json", grant)
    cpu.legacy.write(epoch / "APPROVAL.json", {
        "approved_by": "main", "wrapper_sha256": args.approved_sha256,
        "qualified_server_source_seal_sha256": SOURCE_SEAL,
        "max_lifetime_after_ready_s": 7200, "stop_condition": "main STOP or owned signal",
        "model_jobs": "separately hash-approved; this wrapper submits no inference",
    })

    def stop(*_):
        gpu.STOP.set()
        cpu.legacy.STOP.set()
        (epoch / "STOP").touch()

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, stop)
    with engine.owned_servers(epoch, cpu, gpu, True) as (serving, pilot):
        native = {
            side: engine.mechanical.proc_identity(json.loads(Path(item["serving_receipt"]).read_text())["pid"])
            for side, item in serving.items()
        }
        cpu.legacy.write(epoch / "READY.json", {
            "holder": engine.mechanical.proc_identity(os.getppid()),
            "controller": engine.mechanical.proc_identity(os.getpid()),
            "grant": grant, "serving": serving, "native": native, "ready_at": time.time(),
            "model_calls_from_owner": 0,
        })
        end = time.monotonic() + 7200
        while not pilot.stop.wait(1):
            if (epoch / "STOP").exists() or gpu.STOP.is_set() or time.monotonic() >= end:
                break
            for side, identity in native.items():
                if engine.mechanical.proc_identity(identity["pid"]) != identity:
                    raise RuntimeError("owned native process changed: " + side)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
