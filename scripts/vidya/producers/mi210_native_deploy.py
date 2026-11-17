#!/usr/bin/env python3
"""Stage and run the Q38P-3a prospective native-capture successor."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROW = "vidya-mi210-q38-native-wire-20261117"
ENGINE_DIR = Path("/mnt/raid0/llm/tmp/compute-flags")
PACKET = "data/vidya/mi210-paired-wire-20261117"
C_RESTORED = "23d39c91a82fad0a83743829dd59a10df91bfe0c4a933f0cce693fc7a831beb4"
PINS = {
    "IDENTITY.json": "640d78fb576cd0fef0befe9d294e9dc1ee0481cb7b10772a4d21389a55ff537d",
    "gpuproof.py": "fb2615fbbc018926223506b5a8a1a3f422f02f66f046cc2b5f3f8387cd1ecc5b",
    "dependency.json": "e3e59b0eabb1f99ca2c8509b410d27265a93637d327cc59a34b5a8a23d7ca0d1",
}
HELPERS = (
    "scripts/vidya/producers/mi210_paired_capture.py",
    "scripts/vidya/producers/mi210_native_run.py",
    "scripts/vidya/adapters/_native_sidecar.py",
    "scripts/vidya/adapters/mi210_paired_raw.py",
    "scripts/vidya/claim_tuple.py",
    "scripts/vidya/lattice.py",
    "scripts/vidya/canonical.py",
)


def load(path):
    return json.loads(path.read_text())


def write(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_digest(path, expected):
    if digest(path) != expected:
        raise ValueError(f"SHA-256 mismatch: {path}")


def fingerprint(path):
    info = path.stat()
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def prepare_identity(path):
    path = Path(path)
    before = fingerprint(path)
    sha = digest(path)
    if fingerprint(path) != before:
        raise ValueError(f"input changed while hashing: {path}")
    return {"path": str(path), "sha256": sha, "error": None, "prepared_stat": before}


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"expected exactly one deployment amendment: {old}")
    return source.replace(old, new)


def deploy_job(job):
    source = job.read_text()
    source = replace_once(source, "OUT = os.path.join(D, 'smoke-out' if os.environ.get('FILLER_SMOKE') == '1' else 'out');",
                          "OUT = os.environ['MI210_NATIVE_OUTPUT'];")
    source = replace_once(source, "CPUS = os.environ.get('FILLER_CPUS', '184-191')",
                          "CPUS = os.environ['MI210_NATIVE_CPUS']; THREADS = str(len(os.sched_getaffinity(0)))")
    source = replace_once(source, "'-t', '8', '--load-threads', '8'",
                          "'-t', THREADS, '--load-threads', THREADS")
    source = replace_once(source, "time.time() + 1200", "time.time() + 300")
    source = replace_once(source, "if not gate_dependency()[0]:\n",
                          "if not gate_dependency()[0]:\n            capture.stop = 'dependency refused'\n")
    source = replace_once(source, "capture.update(release=rel)",
                          "capture.update(release=rel)\n            if x.get('error') in ('stop', 'deadline'):\n"
                          "                capture.stop = x['error']\n                return 75")
    source = replace_once(source, "if v['start'] <= ob['time'] <= v['end']",
                          "if ob['pid'] == proof['pid'] and v['start'] <= ob['time'] <= v['end']")
    source = replace_once(source, "'prompts':DECODE,",
                          "'prompts':DECODE[:1] if PLUMB else DECODE, 'n_predict':64 if PLUMB else 256,")
    job.write_text(source)


def deploy_gpu_proof(target):
    """Keep the sampler child inside rowflow's process group and attribute only the captured PID."""
    source = target.read_text()
    source = replace_once(source, "os.getsid(pid) == self.sid", "pid == self.sid")
    source = replace_once(source, f", start_new_session={True}", "")
    source = replace_once(source, "os.killpg(p.pid, sig)", "p.send_signal(sig)")
    start = source.index("        if on_spawn: on_spawn(p.pid)")
    end = source.index("\n    proof = s.record(v0)", start)
    body = source[start:end].splitlines()
    body.remove("        s = Sampler(sid=p.pid); s.start()")
    body[-1] = "        rc = p.wait()"
    cleanup = [
        "        finally:",
        "            if p.poll() is None:",
        "                p.terminate()",
        "                try:",
        "                    p.wait(timeout=10)",
        "                except subprocess.TimeoutExpired:",
        "                    p.kill()",
        "                    p.wait(timeout=10)",
        "            s.stop.set()",
        "            s.join(5)",
    ]
    source = (source[:start] + "        s = Sampler(sid=p.pid)\n"
              "        s.start()\n        try:\n" + "\n".join("    " + line for line in body)
              + "\n" + "\n".join(cleanup) + source[end:])
    target.write_text(source)


def prepare_builds(ident):
    builds = {}
    for arm, spec in ident["arms"].items():
        image = Path(spec["bin"])
        files = sorted({(image / "llama-server").resolve(), *(
            entry.resolve() for pattern in ("libggml*.so*", "libllama*.so*")
            for entry in image.glob(pattern))})
        file_ids = [prepare_identity(path) for path in files]
        hip = str((image / "libggml-hip.so").resolve())
        hip_id = next(entry for entry in file_ids if entry["path"] == hip)
        builds[arm] = {"source_commit": None, "files": file_ids, "hip_sha256": hip_id["sha256"]}
        if arm == "C":
            manifest = image.parent / "SHA256SUMS"
            recorded = {p[2:]: h for h, p in (line.split(maxsplit=1) for line in manifest.read_text().splitlines())}
            if any(recorded.get(Path(item["path"]).name) != item["sha256"] for item in file_ids):
                raise ValueError("restored C5 executable or library differs from its build manifest")
            builds[arm]["build_manifest"] = prepare_identity(manifest)
            builds[arm]["source_provenance"] = prepare_identity(image.parent / "PROVENANCE.md")
            builds[arm]["source_commit"] = "c72ec82f5417bb2937310326120f149b665e8400"
            if hip_id["sha256"] != C_RESTORED:
                raise ValueError("unexpected restored C5 HIP image")
        elif hip_id["sha256"] != spec["libggml_hip_sha256"]:
            raise ValueError("B HIP library differs from the original pinned image")
    return builds


def stage(destination, owner):
    repo = Path(__file__).resolve().parents[3]
    packet = repo / PACKET
    manifest = load(packet / "manifest.json")["sources"]
    for source in manifest.values():
        require_digest(Path(source["path"]), source["sha256"])
    source = manifest["q38p3a"]
    canonical = Path(source["path"]).parent
    ident_path = canonical / "IDENTITY.json"
    require_digest(ident_path, PINS["IDENTITY.json"])
    ident = load(ident_path)
    require_digest(Path(ident["depends_on"]["result"]), PINS["dependency.json"])
    require_digest(canonical / "gpuproof.py", PINS["gpuproof.py"])
    builds = prepare_builds(ident)
    model = prepare_identity(ident["model"])
    template = prepare_identity(ident["chat_template"])

    destination.mkdir(parents=True, exist_ok=False)
    job = destination / "job.py"
    shutil.copyfile(source["path"], job)
    subprocess.run(["patch", "--batch", "--forward", "-p1", "-i", str(packet / "q38p3a.patch")],
                   cwd=destination, check=True)
    require_digest(job, source["patched_sha256"])
    deploy_job(job)
    shutil.copyfile(canonical / "gpuproof.py", destination / "gpuproof.py")
    deploy_gpu_proof(destination / "gpuproof.py")
    shutil.copyfile(ident["depends_on"]["result"], destination / "dependency.json")
    ident["depends_on"]["result"] = str(destination / "dependency.json")
    original_hip = ident["arms"]["C"]["libggml_hip_sha256"]
    ident["arms"]["C"]["libggml_hip_sha256"] = C_RESTORED
    write(destination / "IDENTITY.json", ident)
    deployed = Path(__file__).name
    shutil.copyfile(__file__, destination / deployed)
    for name in HELPERS:
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / name, path)
    inputs = (deployed, "job.py", "gpuproof.py", "IDENTITY.json", "dependency.json", *HELPERS)
    for name in ("job.py", "gpuproof.py"):
        compile((destination / name).read_text(), name, "exec")
    write(destination / "prepared.json", {
        "row": ROW, "original_producer": source, "companion_npd1_source": manifest["npd1"],
        "original_pins": PINS, "original_c_hip_sha256": original_hip,
        "inputs": {name: digest(destination / name) for name in inputs},
        "model": model, "template": template, "builds": builds,
    })
    make_row(destination, owner)


def make_row(destination, owner):
    launch = (destination / "launch").with_suffix(".sh")
    run = f"/usr/bin/python3 -I {destination}/{Path(__file__).name}"
    launch.write_text(f"""#!/bin/bash
set -euo pipefail
exec /bin/bash {ENGINE_DIR}/bin/rowflow/filler_run15.sh --id {ROW} --class gpu \\
  --role bench --gpu-quiet exclusive --no-fold-siblings --claim-cpus 88-95,184-191 \\
  --gpu-threads 184-191 --port 18935 --min-window 1500 --stop-grace 35 \\
  --cmd "{run} run" --complete-cmd "{run} complete" \\
  --workdir "{destination}" --stop "{destination}/STOP"
""")
    launch.chmod(0o755)
    write(destination / "spec.json", {
        "id": ROW, "owner": owner, "launcher": str(launch),
        "lane": "gpu", "shape": "gpu-q3", "regions": "mi210_0,88-95,184-191", "ram_gib": 64,
        "result_path": str(destination / "RESULT.json"), "result_format": "json",
        "scratch_root": str(destination), "keep": ["captures/**", "RESULT.json", "SMOKE.json"],
        "estimate_s": 1800, "min_window_s": 1500, "max_window_s": 1800, "first_progress_s": 420,
        "handoff_task": "handoffs/active/vidya-belief-substrate-program.md:VB-MI210-PAIRED-DIAG-WIRE",
        "kind": "compute", "verdict_by": "agent", "smoke_predicate": f"{run} smoke",
        "decision_rule": (
            "Prospective Q38P-3a capture on restored C5 ROCm 6.2 and pinned ROCm 10.1 B with "
            "Qwen3.8-27B-Q8_0, speculation off, two ordered C/B/B/C pairs. "
            "Success requires a sealed measurement declaration, four valid ordered launches with five native "
            "timings each, actual placement, grant identity, in-request own MI210 residency and mapped HIP linkage, "
            "and clean release. Stop when all four are sealed or on STOP, deadline, invalid proof or launch failure. "
            "Native decode tokens/s is higher-better. No ratio verdict or serving decision."
        ),
    })


def prepared(root):
    manifest = load(root / "prepared.json")
    for name, sha in manifest["inputs"].items():
        require_digest(root / name, sha)
    for entry in (manifest["model"], manifest["template"], *(
            file for arm in manifest["builds"].values() for file in arm["files"])):
        if fingerprint(Path(entry["path"])) != entry["prepared_stat"]:
            raise ValueError(f"prepared input changed: {entry['path']}")
    ident = load(root / "IDENTITY.json")
    for arm, build in manifest["builds"].items():
        image = Path(ident["arms"][arm]["bin"])
        paths = {(image / "llama-server").resolve(), *(
            item.resolve() for pattern in ("libggml*.so*", "libllama*.so*") for item in image.glob(pattern))}
        if paths != {Path(entry["path"]) for entry in build["files"]}:
            raise ValueError(f"build file targets changed: {image}")
    return manifest, ident


def install_capture_bindings(root, manifest, ident, allocation):
    from scripts.vidya.producers import mi210_native_run as native

    def model_identities(path):
        if str(path) != manifest["model"]["path"]:
            raise ValueError(f"unprepared model: {path}")
        return [manifest["model"]]

    def build_identity(directory):
        for arm, spec in ident["arms"].items():
            if str(directory) == spec["bin"]:
                return manifest["builds"][arm]
        raise ValueError(f"unprepared build: {directory}")

    class BoundNativeRun(native.NativeRun):
        def __init__(self, out, declaration):
            super().__init__(out, {
                **declaration, "allocation": allocation, "deployment": native.identity(root / "prepared.json"),
                "original_native_producer": manifest["original_producer"],
            })

    native.model_identities = model_identities
    native.build_identity = build_identity
    native.NativeRun = BoundNativeRun


def runtime(root):
    import runpy
    import tempfile

    flags = Path(os.environ.get("FILLER_FLAGS_DIR", str(ENGINE_DIR)))
    rid = os.environ["FILLER_ID"]
    stop = os.environ["FILLER_STOPFILE"]
    deadline = int(os.environ["FILLER_DEADLINE"])
    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    if rid != ROW or not stop or deadline <= time.time() or os.environ.get("FILLER_NEEDGPU") != "1":
        raise ValueError("active rowflow GPU window required")
    grants = Path(os.environ["FILLER_DRYRUN_DIR"]) / "grants" if smoke else flags / "grants"
    grant = grants / (rid + ".grant")
    if not grant.is_file():
        raise ValueError("rowflow grant artifact missing")
    manifest, ident = prepared(root)
    cpu_pool = sorted(os.sched_getaffinity(0) & set(range(184, 192)))
    if len(cpu_pool) < (4 if smoke else 8):
        raise ValueError(f"rowflow supplied insufficient MI210 host threads: {cpu_pool}")
    cpus = cpu_pool[:4] if smoke else cpu_pool
    os.sched_setaffinity(0, cpus)
    output = root / "captures"
    output.mkdir(exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="smoke-" if smoke else "measurement-", dir=output))
    grant_snapshot = (attempt / "rowflow").with_suffix(".grant")
    grant_snapshot.write_bytes(grant.read_bytes())
    os.environ.update({
        "MI210_BELIEF_ROOT": str(root), "MI210_BELIEF_GRANT": str(grant_snapshot),
        "MI210_NATIVE_OUTPUT": str(attempt), "MI210_NATIVE_CPUS": ",".join(map(str, cpus)),
    })
    install_capture_bindings(root, manifest, ident, {
        "region": "mi210_0", "rowflow_id": rid, "grant_path": str(grant),
        "grant_sha256": digest(grant_snapshot),
        "grant_cpus": os.environ["FILLER_CPUS"], "actual_cpus": cpus, "threads": len(cpus),
        "stopfile": stop, "deadline_epoch": deadline,
    })

    def interrupt(sig, _frame):
        raise KeyboardInterrupt(f"signal {sig}")

    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    try:
        runpy.run_path(str(root / "job.py"), run_name="__main__")
    except SystemExit as exit_:
        rc = int(exit_.code or 0)
    except KeyboardInterrupt:
        rc = 75
    else:
        rc = 0
    finally:
        captures = list(attempt.glob("belief-*"))
        if len(captures) == 1:
            record_result(root, captures[0], smoke)
    return rc


def record_result(root, capture, smoke):
    from scripts.vidya.producers import mi210_paired_capture as raw

    run = raw.read(capture)
    write(root / ("SMOKE.json" if smoke else "RESULT.json"), {
        "capture": str(capture), "state": run["state"], "mode": "smoke" if smoke else "measurement",
        "count": len(run["attempts"]), "terminal_sha256": (run["terminal"] or {}).get("row_sha256"),
    })


def verified_result(root, smoke):
    from scripts.vidya.producers import mi210_paired_capture as raw

    try:
        path = root / ("SMOKE.json" if smoke else "RESULT.json")
        if smoke and path.stat().st_mtime < int(os.environ["FILLER_SMOKE_T0"]):
            return None
        result = load(path)
        capture = Path(result["capture"])
        if capture.resolve().parent.parent != root / "captures":
            return None
        run = raw.read(capture)
        declaration = run["intent"]["declaration"]
        allocation = declaration["allocation"]
        mode = "smoke" if smoke else "measurement"
        grant = declaration["grant"]
        grant_snapshot = Path(grant["path"])
        if (grant_snapshot != (capture.parent / "rowflow").with_suffix(".grant")
                or digest(grant_snapshot) != grant["sha256"]
                or allocation["grant_sha256"] != grant["sha256"]):
            return None
        n_launches, n_requests, width = (1, 1, 4) if smoke else (4, 5, 8)
        cpus = set(allocation["actual_cpus"])
        if (run["state"] != "complete" or declaration["mode"] != mode or declaration["source"] != "Q38P-3a"
                or run["terminal"]["row_sha256"] != result["terminal_sha256"]
                or len(run["attempts"]) != n_launches or allocation["threads"] != width
                or len(cpus) != width or not cpus <= set(range(184, 192))):
            return None
        for attempt in run["attempts"]:
            native = attempt["native"]
            if (set(native["checks"]) != {"in_request_own_residency_and_linkage", "requests",
                                         "no_draft", "no_error", "own_vram", "no_foreign_kfd",
                                         "linkage", "released"} or not all(native["checks"].values())
                    or native["grant"] != grant
                    or len(native["requests"]) != n_requests or not native["actual_placement"]
                    or any(set(sample["allowed"]) != cpus or sample["escapes"]
                           for sample in native["actual_placement"])):
                return None
        return capture
    except (KeyError, TypeError, ValueError, OSError):
        return None


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("command", choices=("stage", "run", "complete", "smoke", "project"))
    cli.add_argument("--destination", type=Path)
    cli.add_argument("--owner", default="handoff-vidya-belief-substrate")
    args = cli.parse_args()
    if args.command == "stage":
        if args.destination is None:
            cli.error("stage requires --destination")
        stage(args.destination.resolve(), args.owner)
        return 0
    root = Path(__file__).resolve().parent
    sys.path[:0] = [str(root), str(root / "scripts" / "vidya")]
    if args.command == "run":
        return runtime(root)
    capture = verified_result(root, args.command == "smoke")
    if capture is None:
        return 1
    if args.command == "project":
        from scripts.vidya.adapters.mi210_paired_raw import project
        from scripts.vidya.claim_tuple import grade

        print(json.dumps([{"claim": item.claim, "grade": grade(item)[:2], "value": item.value,
                           "direction": item.metric_direction} for item in project(capture)], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
