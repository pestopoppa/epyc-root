#!/usr/bin/env python3
"""Stage and qualify the private, CPU-only NPD1-STEP3 native-capture successor."""
from __future__ import annotations

import argparse
import ast
from datetime import datetime
import math
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mi210_native_deploy import (ENGINE_DIR, HELPERS, PACKET, digest, fingerprint, load,
                                 prepare_identity, replace_once, require_digest, write)

ROW = "vidya-mi210-npd1-native-wire-20261117"
SOURCE = "NPD1-STEP3"
ORDER = [["p1", "cpu"], ["p1", "gpu_cpu"], ["p2", "gpu_cpu"], ["p2", "cpu"]]
CPU_POOL = set(range(96))
PORT = 18933
SOURCE_COMMIT = "181483cfc8154be00c6369eb4ee0d7d931c9faf8"


def deploy_npd1(job):
    source = job.read_text()
    amendments = (
        ("OUT = D / ('smoke-out' if os.environ.get('FILLER_SMOKE') == '1' else 'out')",
         "OUT = Path(os.environ['MI210_NATIVE_OUTPUT'])"),
        ("PORT = 18933", "PORT = int(os.environ['FILLER_PORTS'])"),
        ("if SMOKE:\n    cpus = cpus[:4]\n    os.sched_setaffinity(0, cpus)",
         "if SMOKE:\n    ORDER = ORDER[:1]"),
        ("with urllib.request.urlopen(req, timeout=timeout)",
         "with urllib.request.urlopen(req, timeout=min(timeout, max(0.1, int(os.environ['FILLER_DEADLINE']) - time.time())))"),
        ("p.wait(timeout=60)", "p.wait(timeout=10)"),
        ("p.kill(); p.wait(timeout=30)", "p.kill(); p.wait(timeout=10)"),
        ("return Path(os.environ.get('FILLER_STOPFILE', str(D / 'STOP'))).exists()",
         "return Path(os.environ['FILLER_STOPFILE']).exists() or time.time() >= int(os.environ['FILLER_DEADLINE'])"),
        ("raise SystemExit(0 if SMOKE else 'STOP')", "raise SystemExit(75)"),
        ("        with socket.socket() as probe:", "        capture.start(pair, arm)\n        with socket.socket() as probe:"),
        ("        capture.start(pair, arm)\n        store", "        store"),
        ("if stopped(): raise SystemExit(0 if SMOKE else 'STOP while loading')",
         "if stopped():\n                        capture.stop = 'STOP or deadline while loading'\n                        raise SystemExit(75)"),
        ("                run_completion()  # warmup",
         "                if stopped():\n                    capture.stop = 'STOP or deadline before warmup'\n"
         "                    raise SystemExit(75)\n                capture.update(warmup=run_completion())\n"
         "                if stopped():\n                    capture.stop = 'STOP or deadline before measurement'\n"
         "                    raise SystemExit(75)"),
        ("                request_start = time.time()\n                measure = run_completion()\n"
         "                request_end = time.time()",
         "                with native_samples(p.pid) as sampled:\n"
         "                    capture.update(residency_linkage={'scope':'sampled-process-maps', 'samples':sampled})\n"
         "                    request_start = time.time()\n"
         "                    try:\n"
         "                        measure = run_completion()\n"
         "                    except OSError:\n"
         "                        if stopped():\n"
         "                            capture.stop = 'STOP or deadline during measurement'\n"
         "                        raise\n"
         "                    request_end = time.time()"),
        ("                cleanup(p)\n                capture.update",
         "                try:\n                    cleanup(p)\n                finally:\n                    capture.update"),
        ("        capture.record('complete')",
         "        if stopped():\n            capture.stop = 'STOP or deadline after launch'\n"
         "            raise SystemExit(75)\n        check_native_attempt(capture.active, arm, cpus, SMOKE)\n"
         "        capture.record('complete')"),
    )
    for before, after in amendments:
        source = replace_once(source, before, after)
    compile(source, str(job), "exec")
    job.write_text(source)


def source_inputs(source):
    """Read the four literal recipe paths without importing the launch-at-import job."""
    wanted = {"CPU", "GPU", "MODEL", "MTP"}
    values = {}
    for stmt in ast.parse(source).body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            name = getattr(stmt.targets[0], "id", None)
            if name in wanted:
                values[name] = Path(ast.literal_eval(stmt.value))
    if values.keys() != wanted or not all(path.is_absolute() for path in values.values()):
        raise ValueError("pinned producer recipe paths missing")
    return values


def library_targets(image):
    names = {"llama-server", *(entry.name for glob in ("libggml*.so*", "libllama*.so*", "libmtmd*.so*")
                               for entry in image.glob(glob))}
    return {name: str((image / name).resolve(strict=True)) for name in sorted(names)}


def prepare_build(store, kind):
    ident = prepare_identity(store / "BUILD-IDENTITY.json")
    metadata = load(Path(ident["path"]))
    if (metadata["source_sha"] != SOURCE_COMMIT or metadata["kind"] != kind
            or metadata["output"] != str(store)):
        raise ValueError(f"build identity mismatch: {store}")
    checksum = prepare_identity(store / "SHA256SUMS")
    recorded = {name: sha for sha, name in (line.split() for line in Path(checksum["path"]).read_text().splitlines())}
    image = store / "bin"
    targets = library_targets(image)
    files = [prepare_identity(Path(path)) for path in sorted(set(targets.values()))]
    if any(recorded.get(str(Path(entry["path"]).relative_to(store))) != entry["sha256"] for entry in files):
        raise ValueError(f"build bytes differ from store manifest: {store}")
    return {"directory": str(image), "source_commit": SOURCE_COMMIT, "build_identity": ident,
            "build_manifest": checksum, "files": files, "targets": targets}


def stage_npd1(destination, owner, model_prehash):
    repo = Path(__file__).resolve().parents[3]
    packet = repo / PACKET
    inventory = load(packet / "SHA256.json")
    for name in ("manifest.json", "npd1.patch"):
        require_digest(packet / name, inventory[name])
    source = load(packet / "manifest.json")["sources"]["npd1"]
    original = Path(source["path"])
    require_digest(original, source["sha256"])
    paths = source_inputs(original.read_text())
    builds = {"cpu": prepare_build(paths["CPU"], "cpu"), "gpu_cpu": prepare_build(paths["GPU"], "gpu")}
    model_groups = {str(paths["MODEL"]): [
        str(paths["MODEL"]).replace("-00001-of-00003.gguf", f"-{i:05d}-of-00003.gguf")
        for i in range(1, 4)], str(paths["MTP"]): [str(paths["MTP"])]}
    model_paths = [p for group in model_groups.values() for p in group]
    models_by_path = {entry["path"]: entry for entry in load(model_prehash)} if model_prehash else {}
    if models_by_path and set(models_by_path) != set(model_paths):
        raise ValueError("prepared model identities differ from pinned recipe paths")
    models = [models_by_path[path] if models_by_path else prepare_identity(path) for path in model_paths]
    for entry in models:
        p = Path(entry["path"])
        if fingerprint(p) != entry["prepared_stat"] or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError(f"prepared model identity changed: {p}")
        expected = p.with_name(p.name + ".sha256")
        if expected.exists() and expected.read_text().split()[0] != entry["sha256"]:
            raise ValueError(f"model differs from checksum: {p}")
    destination.mkdir(parents=True, exist_ok=False)
    job = destination / "job.py"
    shutil.copyfile(original, job)
    subprocess.run(["patch", "--batch", "--forward", "-p1", "-i", str(packet / "npd1.patch")],
                   cwd=destination, check=True)
    require_digest(job, source["patched_sha256"])
    deploy_npd1(job)
    module = Path(__file__).resolve()
    common = module.with_name("mi210_native_deploy.py")
    for path in (module, common):
        shutil.copyfile(path, destination / path.name)
    for name in HELPERS:
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo / name, path)
    inputs = ("job.py", module.name, common.name, *HELPERS)
    write(destination / "prepared.json", {
        "schema": "epyc.mi210.npd1-prepared.v1", "row": ROW, "original_producer": source,
        "packet_digests": {name: inventory[name] for name in ("manifest.json", "npd1.patch")},
        "inputs": {name: digest(destination / name) for name in inputs},
        "models": models, "model_groups": model_groups, "builds": builds,
    })
    make_row(destination, owner)


def make_row(root, owner):
    launch = root / "launch.sh"
    runner = f"/usr/bin/python3 -BI {shlex.quote(str(root / Path(__file__).name))}"
    seal = digest(root / "prepared.json")
    command = lambda action: f"{runner} {action} --prepared-sha256 {seal}"
    launch.write_text(f"""#!/bin/bash
set -euo pipefail
exec /bin/bash {ENGINE_DIR}/bin/rowflow/filler_run15.sh --id {ROW} --class cpu \\
  --role bench --gpu-quiet exclusive --claim-cpus 0-95 --port {PORT} --min-window 1800 --stop-grace 45 \\
  --cmd "{command('run')}" --complete-cmd "{command('complete')}" \\
  --precond-cmd "{command('verify')}" --workdir "{root}" --stop "{root}/STOP"
""")
    launch.chmod(0o755)
    write(root / "spec.json", {
        "id": ROW, "owner": owner, "launcher": str(launch),
        "lane": "cpu", "shape": "quiet-host", "regions": "0-95", "ram_gib": 160,
        "declared_threads": 48, "timing": "bench",
        "baseline_ref": str(Path(load(root / "prepared.json")["original_producer"]["path"]).parent / "out/results.jsonl"),
        "width_justification": "Preserve the original CPU-only NUMA-interleaved 0-95 placement, including 96 loader threads and matched 48 decode threads for both stores. GPU quiet is a guard for the paired CPU timing.",
        "result_path": str(root / "RESULT.json"), "result_format": "json",
        "scratch_root": str(root), "keep": ["captures/**", "RESULT.json", "SMOKE.json", "prepared.json"],
        "estimate_s": 1800, "min_window_s": 1800, "max_window_s": 2100, "first_progress_s": 420,
        "handoff_task": "handoffs/active/vidya-belief-substrate-program.md:VB-MI210-PAIRED-DIAG-WIRE",
        "kind": "compute", "verdict_by": "agent", "smoke_predicate": command("smoke"),
        "decision_rule": (
            "Capture NPD1-STEP3 CPU-only Qwen3.8-Flash-Next UD-IQ4_XS plus MTP, 48 decode and 96 loader threads. "
            "Run two ordered launch pairs CPU/GPU-store/GPU-store/CPU on CPUs 0-95; both stores use -dev none -ngl 0. "
            "Success requires four sealed 512-token timings, mapped store linkage during each request, matched affinity, "
            "the quiet-host grant and verified process release. Stop after four valid launches or on STOP, deadline, "
            "invalid proof, load or request failure. Native TPOT is lower-better. Diagnostic observations only."
        ),
    })


def prepared(root, seal):
    require_digest(root / "prepared.json", seal)
    manifest = load(root / "prepared.json")
    if manifest["row"] != ROW:
        raise ValueError("prepared row mismatch")
    for name, sha in manifest["inputs"].items():
        require_digest(root / name, sha)
    for build in manifest["builds"].values():
        if library_targets(Path(build["directory"])) != build["targets"]:
            raise ValueError(f"build file targets changed: {build['directory']}")
    return manifest


def validate_external(manifest):
    entries = list(manifest["models"])
    for build in manifest["builds"].values():
        entries.extend([build["build_identity"], build["build_manifest"], *build["files"]])
    for entry in entries:
        if fingerprint(Path(entry["path"])) != entry["prepared_stat"]:
            raise ValueError(f"prepared input changed: {entry['path']}")


def cpu_set(value):
    cpus = set()
    for part in value.split(","):
        match = re.fullmatch(r"(\d{1,3})(?:-(\d{1,3}))?", part)
        if not match:
            raise ValueError(f"invalid CPU list: {value}")
        lo, hi = int(match[1]), int(match[2] or match[1])
        if not 0 <= lo <= hi < 192:
            raise ValueError(f"CPU out of range: {value}")
        cpus.update(range(lo, hi + 1))
    return cpus


def validate_grant(data, smoke, cpus):
    fields = dict(field.split("=", 1) for field in data.split())
    start, end = (datetime.fromisoformat(fields[k]) for k in ("start", "end"))
    if end <= start or fields.get("id", ROW) != ROW:
        raise ValueError("rowflow grant identity or time range mismatch")
    allocation_cpus = cpu_set(fields.get("lock", fields["regions"]))
    if smoke:
        if (fields.get("id") != ROW or fields.get("kind") != "rowflow-dryrun"
                or len(cpus) != 4 or allocation_cpus != cpus):
            raise ValueError("smoke requires its four-CPU rowflow dry-run grant")
    elif (fields.get("kind") == "rowflow-dryrun" or cpus != CPU_POOL
          or cpu_set(fields["regions"]) != CPU_POOL
          or not cpus <= allocation_cpus
          or not {"q0", "q1", "q2", "q3", "gpu-quiet"} <= set(fields["holds"].split(","))):
        raise ValueError("measurement requires a full quiet-host grant")
    return start.timestamp(), end.timestamp(), allocation_cpus


def check_native_attempt(native, arm, cpus, smoke, files=None):
    request, = native["requests"]
    timing = request["timings"]
    predicted = 8 if smoke else 512
    ms = timing["predicted_ms"]
    placement = native["actual_placement"]
    samples = native["residency_linkage"]["samples"]
    if (type(timing["predicted_n"]) is not int or timing["predicted_n"] != predicted
            or type(ms) not in (int, float) or not math.isfinite(ms) or ms <= 0
            or request["start"] >= request["end"]
            or placement["before_request"] != sorted(cpus)
            or placement["after_request"] != sorted(cpus)
            or native["release"]["pid"] != placement["pid"]
            or native["release"]["alive"] is not False):
        raise ValueError(f"invalid {arm} timing, placement or release")
    expected = {entry["path"] for entry in files} if files else None
    in_request = [x for x in samples if request["start"] < x["time"] < request["end"]]
    if not in_request or any(
            x["pid"] != placement["pid"] or x["affinity"] != sorted(cpus)
            or not any(Path(path).name.startswith("libggml-cpu.so") for path in x["paths"])
            or (expected is not None and not set(x["paths"]) <= expected)
            for x in in_request):
        raise ValueError(f"invalid {arm} in-request CPU linkage or affinity")


def install_bindings(root, manifest, allocation):
    from contextlib import contextmanager
    from scripts.vidya.producers import mi210_native_run as native

    builds = {entry["directory"]: entry for entry in manifest["builds"].values()}
    models = {entry["path"]: entry for entry in manifest["models"]}

    class BoundRun(native.NativeRun):
        def __init__(self, out, declaration):
            super().__init__(out, {**declaration, "allocation": allocation,
                                   "deployment": native.identity(root / "prepared.json"),
                                   "original_native_producer": manifest["original_producer"]})

    @contextmanager
    def native_samples(pid):
        samples, done = [], threading.Event()

        def observe():
            # Observe only the child created by this launch.
            while not done.is_set():
                try:
                    paths = set()
                    for line in Path(f"/proc/{pid}/maps").read_text().splitlines():
                        fields = line.split(maxsplit=5)
                        if len(fields) == 6 and Path(fields[-1]).name.startswith(("libggml", "libllama", "libmtmd")):
                            paths.add(fields[-1])
                    samples.append({"time": time.time(), "pid": pid, "paths": sorted(paths),
                                    "affinity": sorted(os.sched_getaffinity(pid))})
                except OSError:
                    return
                done.wait(0.25)

        observer = threading.Thread(target=observe, daemon=True)
        observer.start()
        try:
            yield samples
        finally:
            done.set()
            observer.join()

    native.NativeRun = BoundRun
    native.build_identity = lambda directory: builds[str(directory)]
    native.model_identities = lambda path: [models[p] for p in manifest["model_groups"][str(path)]]
    return {
        "native_samples": native_samples,
        "check_native_attempt": lambda attempt, arm, cpus, smoke: check_native_attempt(
            attempt, arm, cpus, smoke, manifest["builds"][arm]["files"]),
    }


def runtime(root, seal):
    from scripts.vidya.producers import mi210_paired_capture as raw

    smoke = os.environ.get("FILLER_DRYRUN") == "1"
    result_path = root / ("SMOKE.json" if smoke else "RESULT.json")
    result_path.unlink(missing_ok=True)
    output = root / "captures"
    output.mkdir(exist_ok=True)
    attempt = Path(tempfile.mkdtemp(prefix="smoke-" if smoke else "measurement-", dir=output))
    result = {"attempt": str(attempt), "mode": "smoke" if smoke else "measurement", "state": "interrupted"}
    write(attempt / "custody.json", result)
    try:
        rid, stop = os.environ["FILLER_ID"], os.environ["FILLER_STOPFILE"]
        deadline = int(os.environ["FILLER_DEADLINE"])
        if (rid != ROW or not stop or deadline <= time.time() or os.environ.get("FILLER_NEEDGPU") != "0"
                or int(os.environ["FILLER_PORTS"]) != PORT
                or smoke != (os.environ.get("FILLER_SMOKE") == "1")):
            raise ValueError("active CPU-only rowflow window required")
        flags = Path(os.environ.get("FILLER_FLAGS_DIR", str(ENGINE_DIR)))
        grants = Path(os.environ["FILLER_DRYRUN_DIR"]) / "grants" if smoke else flags / "grants"
        grant = grants / (rid + ".grant")
        snapshot = attempt / "rowflow.grant"
        snapshot.write_bytes(grant.read_bytes())
        inherited = os.sched_getaffinity(0)
        cpus = inherited if smoke else CPU_POOL
        start, end, grant_cpus = validate_grant(snapshot.read_text(), smoke, cpus)
        if (inherited != cpu_set(os.environ["FILLER_CPUS"]) or inherited != grant_cpus
                or not cpus <= inherited or not start <= time.time() < deadline == int(end) - 90):
            raise ValueError("rowflow grant and effective placement/window mismatch")
        os.sched_setaffinity(0, cpus)
        manifest = prepared(root, seal)
        validate_external(manifest)
        os.environ.update({
            "MI210_BELIEF_ROOT": str(root), "MI210_BELIEF_GRANT": str(snapshot),
            "MI210_NATIVE_OUTPUT": str(attempt),
        })
        bindings = install_bindings(root, manifest, {
            "rowflow_id": rid, "grant_path": str(grant), "grant_sha256": digest(snapshot),
            "grant_cpus": os.environ["FILLER_CPUS"], "actual_cpus": sorted(cpus),
            "decode_threads": 4 if smoke else 48, "load_threads": 4 if smoke else 96,
            "stopfile": stop, "deadline_epoch": deadline,
        })
        runpy.run_path(str(root / "job.py"), run_name="__main__", init_globals=bindings)
        rc = 0
    except (KeyboardInterrupt, SystemExit) as error:
        result["error"] = repr(error)
        rc = 75
    except Exception as error:
        result["error"] = repr(error)
        print(result["error"], file=sys.stderr)
        rc = 1
    finally:
        captures = list(attempt.glob("belief-*"))
        if len(captures) == 1:
            result["capture"] = str(captures[0])
            try:
                run = raw.read(captures[0])
                result.update(state=run["state"], count=len(run["attempts"]),
                              terminal_sha256=(run["terminal"] or {}).get("row_sha256"))
            except (KeyError, TypeError, ValueError, OSError) as error:
                result.update(state="invalid", capture_error=repr(error))
                rc = 1
        elif "error" in result:
            result["state"] = "refused"
        else:
            rc = 1
        write(attempt / "custody.json", result)
        write(result_path, result)
    return rc


def verified_result(root, seal, smoke):
    from scripts.vidya.producers import mi210_paired_capture as raw

    try:
        manifest = prepared(root, seal)
        result = load(root / ("SMOKE.json" if smoke else "RESULT.json"))
        mode = "smoke" if smoke else "measurement"
        capture = Path(result["capture"])
        if (capture.resolve() != capture or capture.parent.parent != root / "captures"
                or not capture.parent.name.startswith(mode + "-")
                or result != load(capture.parent / "custody.json") or result["state"] != "complete"):
            return None
        run = raw.read(capture)
        intent = run["intent"]
        declaration = intent["declaration"]
        if smoke and datetime.fromisoformat(intent["date"]).timestamp() <= int(os.environ["FILLER_SMOKE_T0"]):
            return None
        grant = declaration["grant"]
        snapshot = capture.parent / "rowflow.grant"
        allocation = declaration["allocation"]
        cpus = set(allocation["actual_cpus"])
        start, end, grant_cpus = validate_grant(snapshot.read_text(), smoke, cpus)
        order = ORDER[:1] if smoke else ORDER
        if (run["state"] != "complete" or declaration["source"] != SOURCE or declaration["order"] != order
                or declaration["mode"] != mode or result["mode"] != mode
                or run["terminal"]["row_sha256"] != result["terminal_sha256"]
                or allocation["rowflow_id"] != ROW or cpu_set(allocation["grant_cpus"]) != grant_cpus
                or not start <= datetime.fromisoformat(intent["date"]).timestamp() < allocation["deadline_epoch"]
                or allocation["deadline_epoch"] != int(end) - 90
                or (allocation["decode_threads"], allocation["load_threads"]) != ((4, 4) if smoke else (48, 96))
                or Path(grant["path"]) != snapshot or grant["sha256"] != digest(snapshot)
                or grant["sha256"] != allocation["grant_sha256"]
                or declaration["deployment"]["sha256"] != seal
                or declaration["native_producer"]["sha256"] != manifest["inputs"]["job.py"]
                or declaration["original_native_producer"] != manifest["original_producer"]
                or declaration["builds"] != manifest["builds"] or declaration["model"] != manifest["models"]):
            return None
        for attempt in run["attempts"]:
            native = attempt["native"]
            if native["grant"] != grant:
                return None
            arm = native["arm"]
            check_native_attempt(native, arm, cpus, smoke, manifest["builds"][arm]["files"])
        return capture
    except (KeyError, TypeError, ValueError, OSError):
        return None


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("command", choices=("stage", "verify", "run", "complete", "smoke", "project"))
    cli.add_argument("--destination", type=Path)
    cli.add_argument("--owner", default="handoff-vidya-belief-substrate")
    cli.add_argument("--model-prehash", type=Path)
    cli.add_argument("--prepared-sha256")
    args = cli.parse_args()
    if args.command == "stage":
        if args.destination is None:
            cli.error("stage requires --destination")
        stage_npd1(args.destination.resolve(), args.owner, args.model_prehash)
        return 0
    if not args.prepared_sha256:
        cli.error("staged execution requires --prepared-sha256")
    root = Path(__file__).resolve().parent
    sys.path[:0] = [str(root), str(root / "scripts" / "vidya")]
    if args.command == "verify":
        validate_external(prepared(root, args.prepared_sha256))
        return 0
    if args.command == "run":
        return runtime(root, args.prepared_sha256)
    capture = verified_result(root, args.prepared_sha256, args.command == "smoke")
    if capture is None:
        return 1
    if args.command == "project":
        import json
        from scripts.vidya.adapters.mi210_paired_raw import project
        from scripts.vidya.claim_tuple import grade

        print(json.dumps([{"claim": item.claim, "grade": grade(item)[:2], "value": item.value,
                           "direction": item.metric_direction} for item in project(capture)], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
