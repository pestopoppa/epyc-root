"""Keeper-bound C13 CPU llguidance benchmark and publisher-smoke entry point."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verdict

ROW = "v11-122-llg-cpu-c13-gate-20261118"
BUILD_ROW = "v11-122-llg-cpu-c13-nollg-build-20261118-r2"
COMMIT = "bda43aa17c11b671e0e203e7eb7bf4f1303bc273"
TREE = "e6dc8715fa3374406b38de48571e8700bded094f"
MODEL = Path("/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf")
IMAGES = {"llg": Path("/mnt/raid0/llm/kernels/builds/cpu-20261117-bda43aa17-c13"),
          "nollg": HERE.parent / "c13-nollg-image"}
VERIFIER = HERE.parent / "build-r2/verify_ggml_linkage.sh"
BASELINE = IMAGES["llg"] / "BUILD-IDENTITY.json"
BASELINE_SHA = "16145e6b5b21d05b8f38ea140900932ca3dd5171efd0855685f6b8743d9937ca"
RECEIPT = HERE / "nollg-build-identity.json"
RECEIPT_SHA = "12c39c0ad927602578be7bcdfde7c42b6ca1fcff477213b6253c61ba7b0c18dc"
RESULT = HERE / "RESULT.json"
SMOKE = HERE / "smoke/SMOKE.json"


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def save(path, document):
    draft = path.with_suffix(".tmp")
    draft.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")
    draft.replace(path)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def require_digest(path, expected):
    require(digest(path) == expected, f"SHA-256 mismatch: {path}")


def hash_manifest(path):
    return {name: checksum for checksum, name in
            (line.split(maxsplit=1) for line in path.read_text().splitlines())}


def model_stat():
    actual = MODEL.stat()
    identity = read_json(HERE / "model-identity.json")
    require(identity["model_stat"] == [actual.st_dev, actual.st_ino, actual.st_size, actual.st_mtime_ns,
                                       actual.st_ctime_ns], f"model stat tuple changed: {MODEL}")
    return {"path": str(MODEL), **identity}


def admission():
    require_digest(BASELINE, BASELINE_SHA)
    require_digest(RECEIPT, RECEIPT_SHA)
    require_digest(VERIFIER, "57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33")
    enabled, disabled = read_json(BASELINE), read_json(RECEIPT)
    for arm in (enabled, disabled):
        require((arm["source_sha"], arm["source_tree"], arm["kind"]) == (COMMIT, TREE, "cpu"),
                "arm has unexpected source commit, tree or backend")
    require(disabled["ok"] is True and disabled["verdict"] == "BUILD_PASS"
            and disabled["row_id"] == BUILD_ROW and disabled["arm"] == "nollg"
            and disabled["baseline_identity_sha256"] == BASELINE_SHA
            and disabled["image"] == str(IMAGES["nollg"])
            and enabled["output"] == str(IMAGES["llg"]), "invalid build receipt lineage")

    on, off = "-DLLAMA_LLGUIDANCE:BOOL=ON", "-DLLAMA_LLGUIDANCE:BOOL=OFF"
    original = enabled["configure_argv"]
    require(original.count(on) == 1 and original.count(off) == 0, "invalid original llguidance config")
    expected = [off if option == on else option.replace(enabled["source"], disabled["source"]).replace(
        enabled["output"], disabled["image"]) for option in original]
    require(disabled["configure_argv"] == expected and "-DGGML_BACKEND_DL:BOOL=OFF" in original
            and "-DGGML_HIP:BOOL=OFF" in original and "-DGGML_CUDA:BOOL=OFF" in original,
            "effective configure argv differs beyond paths and llguidance toggle")

    files = {}
    impl = read_json(HERE / "bench-impl-identities.json")
    for arm in verdict.ARMS:
        root = IMAGES[arm] / "bin"
        local = {Path(name).name: sha for name, sha in hash_manifest(HERE / f"{arm}-artifacts.sha256").items()}
        if arm == "nollg":
            require(local == disabled["files"], "disabled artifact manifest differs from build receipt")
        else:
            archived = hash_manifest(IMAGES[arm] / "SHA256SUMS.c13")
            require(all(archived.get(f"bin/{name}") == sha for name, sha in local.items())
                    and archived.get("bin/libllama-bench-impl.so") == impl[arm]["sha256"],
                    "enabled digest pins differ from C13 archive")
        impl_file = root / "libllama-bench-impl.so"
        require(impl[arm]["path"] == str(impl_file), f"{arm}: bench implementation path mismatch")
        files[arm] = {str(root / name): sha for name, sha in local.items()}
        files[arm][str(impl_file)] = impl[arm]["sha256"]
        for name, sha in files[arm].items():
            require_digest(Path(name), sha)
    require(impl["llg"]["sha256"] == impl["nollg"]["sha256"], "bench implementation differs between arms")

    system = hash_manifest(HERE / "system-runtime.sha256")
    for name, sha in system.items():
        require_digest(Path(name), sha)
    return {"source_sha": COMMIT, "source_tree": TREE, "build_row_id": BUILD_ROW,
            "enabled_build_identity_sha256": BASELINE_SHA, "disabled_build_identity_sha256": RECEIPT_SHA,
            "configure_argv": {"llg": original, "nollg": expected},
            "linkage_verifier_sha256": digest(VERIFIER),
            "build_files": files, "system_runtime": system, "model": model_stat()}


def cpus(value):
    ids = set()
    for item in value.split(","):
        lower, _, upper = item.partition("-")
        ids.update(range(int(lower), int(upper or lower) + 1))
    return ids


def granted_affinity(smoke):
    threads = int(os.environ["FILLER_THREADS"])
    granted = cpus(os.environ["FILLER_CPUS"])
    actual = os.sched_getaffinity(0)
    require(actual == granted and actual, f"affinity is not the grant: {actual} vs {granted}")
    cores = {}
    for cpu in sorted(actual):
        siblings = Path(f"/sys/devices/system/cpu/cpu{cpu}/topology/thread_siblings_list")
        physical_cpu = min(cpus(siblings.read_text().strip()))
        cores.setdefault(physical_cpu, cpu)
    require(len(cores) == threads, "FILLER_THREADS differs from granted physical core count")
    if smoke:
        require(threads == len(actual) == 4, "publisher smoke requires exactly four allocated CPUs")
    else:
        require(threads == 24 and len({cpu // 24 for cpu in cores}) == 1,
                "native job requires one 24-core quarter")
    selected = sorted(cores.values())
    os.sched_setaffinity(0, selected)
    require(os.sched_getaffinity(0) == set(selected), "physical affinity binding failed")
    return threads, sorted(granted), selected


def bench_environment(threads):
    hidden = {"ROCR_VISIBLE_DEVICES": "", "HIP_VISIBLE_DEVICES": "-1", "GPU_DEVICE_ORDINAL": "-1",
              "CUDA_VISIBLE_DEVICES": "-1", "GGML_VK_VISIBLE_DEVICES": "-1", "HSA_ENABLE_SDMA": "0"}
    require(os.environ["FILLER_GPU_FENCE"] == "1"
            and all(os.environ.get(key) == value for key, value in hidden.items())
            and os.environ["FILLER_NEEDGPU"] == "0", "missing keeper CPU GPU fence")
    preloads = re.split(r"[:\s]+", os.environ.get("LD_PRELOAD", "").strip())
    fence = [preload for preload in preloads
             if re.fullmatch(r"gpu_fence-[0-9a-f]{12}\.so", Path(preload).name)]
    require(len(fence) == 1 and Path(fence[0]).is_absolute(), "missing keeper GPU device fence shim")
    return {**hidden, "FILLER_GPU_FENCE": "1", "FILLER_ID": ROW, "LD_PRELOAD": fence[0],
            "PATH": "/usr/bin:/bin", "LC_ALL": "C", "GGML_N_THREADS": str(threads),
            "OMP_NUM_THREADS": str(threads), "OMP_DYNAMIC": "FALSE"}


def prove_arm(arm, env, proof):
    root = IMAGES[arm] / "bin"
    bench = root / "llama-bench"
    linkage = subprocess.check_output(["/bin/bash", str(VERIFIER), str(bench), str(root)], env=env, text=True)
    resolved = {str(Path(path).resolve()) for path in re.findall(r"^  OK\s+\S+\s+-> (\S+)", linkage, re.M)}
    expected = {str(Path(path).resolve()) for path in proof["build_files"][arm] if path != str(bench)}
    require(resolved == expected, f"{arm}: loaded project-library set differs from pinned files")
    loader_paths = subprocess.check_output(["/usr/bin/ldd", str(bench)], env=env, text=True)
    require("not found" not in loader_paths, f"{arm}: unresolved library")
    all_loaded = {str(Path(path).resolve()) for path in re.findall(r"(?:=>\s+|^\s*)(/\S+)\s+\(", loader_paths, re.M)}
    all_pinned = resolved | {str(Path(path).resolve()) for path in proof["system_runtime"]}
    all_pinned.add(str(Path(env["LD_PRELOAD"]).resolve()))
    require(all_loaded == all_pinned, f"{arm}: loaded library set mismatch: {all_loaded ^ all_pinned}")
    symbols = subprocess.check_output(["/usr/bin/strings", str(root / "libllama-common.so")], env=env)
    count = sum(b"llg_matcher_compute_mask" in line for line in symbols.splitlines())
    require(count == (9 if arm == "llg" else 0), f"{arm}: unexpected matcher string count {count}")
    return {"linkage": linkage, "ldd": loader_paths, "llg_matcher_strings": count}


def check_window():
    require(not Path(os.environ["FILLER_STOPFILE"]).exists(), "keeper STOP requested")
    require(time.time() < int(os.environ["FILLER_DEADLINE"]), "keeper deadline reached")


def run_arm(run, label, arm, env, workload, threads):
    check_window()
    model_stat()
    pp, tg, repeats = workload
    bench = IMAGES[arm] / "bin/llama-bench"
    argv = [str(bench), "-m", str(MODEL), "--device", "none", "-ngl", "0", "-fa", "1", "-t",
            str(threads), "-p", str(pp), "-n", str(tg), "-r", str(repeats), "-o", "json"]
    stem = f"{label}-{arm}"
    output, error = run / f"{stem}.json", run / f"{stem}.err"
    record = {"arm": arm, "argv": argv, "environment": env, "affinity": sorted(os.sched_getaffinity(0)),
              "stdout": str(output), "stderr": str(error), "started_at": utc()}
    record_path = run / f"{stem}.meta.json"
    save(record_path, record)
    try:
        with output.open("wb") as stdout, error.open("wb") as stderr:
            record["exit_code"] = subprocess.run(argv, env=env, stdout=stdout, stderr=stderr).returncode
        require(record["exit_code"] == 0, f"{stem} benchmark exited {record['exit_code']} ({error})")
        validated = verdict.validate(read_json(output), pp, tg, repeats, threads, str(MODEL))
        print(f"{utc()} {stem} validated ({output})", flush=True)
        return validated
    except BaseException as exc:
        record["error"] = str(exc)
        raise
    finally:
        record["ended_at"] = utc()
        save(record_path, record)


def run_job():
    smoke = os.environ.get("FILLER_SMOKE") == "1"
    require(os.environ.get("FILLER_ID") == ROW and (smoke or os.environ.get("FILLER_DRYRUN") != "1"),
            "requires a native keeper grant or publisher smoke")
    out = HERE / ("smoke" if smoke else "out")
    out.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="run-", dir=out))
    record = {"row_id": ROW, "grant_id": ROW, "started_at": utc(), "mode": "smoke" if smoke else "native"}
    state = run / "run.json"
    save(state, record)
    result = None
    try:
        record["grant"] = (Path(os.environ["FILLER_GRANTS_DIR"]) / f"{ROW}.grant").read_text().strip()
        threads, granted, affinity = granted_affinity(smoke)
        environment = bench_environment(threads)
        record.update(threads=threads, granted_affinity=granted, affinity=affinity)
        save(state, record)

        proof = admission()
        proof["fence_sha256"] = digest(Path(environment["LD_PRELOAD"]))
        proof["arms"] = {}
        environments = {}
        for arm in verdict.ARMS:
            environments[arm] = {**environment, "LD_LIBRARY_PATH": str(IMAGES[arm] / "bin")}
            proof["arms"][arm] = prove_arm(arm, environments[arm], proof)
        proof_path = run / "proof.json"
        save(proof_path, proof)
        record["proof"] = str(proof_path)

        if smoke:
            verdict.smoke_fixtures()
            for arm in verdict.ARMS:
                run_arm(run, "smoke", arm, environments[arm], (8, 2, 1), threads)
            record["verdict_fixtures"] = "PASS"
        else:
            pairs = []
            for number, order in enumerate(verdict.ORDER, start=1):
                label = f"p{number}"
                paired = {arm: run_arm(run, label, arm, environments[arm], (512, 128, 5), threads)
                          for arm in order}
                pairs.append(paired)
                result = {**verdict.checkpoint(pairs), "row_id": ROW, "run": str(run),
                          "run_metadata": str(state), "proof": str(proof_path),
                          "started_at": record["started_at"], "checkpoint_at": utc()}
                if result["final"]:
                    break
                save(RESULT, result)
        record["status"] = "COMPLETE"
    except BaseException as exc:
        record.update(status="ERROR", error=str(exc))
        raise
    finally:
        record["ended_at"] = utc()
        save(state, record)
    if smoke:
        save(SMOKE, {"ok": True, "row_id": ROW, "run": str(run), "arms": verdict.ARMS,
                     "fixtures": "PASS", "ended_at": record["ended_at"]})
    else:
        save(RESULT, {**result, "ended_at": record["ended_at"]})


def predicate(mode):
    try:
        if mode == "--complete":
            data = read_json(RESULT)
            return data["row_id"] == ROW and data["final"] is True and data["verdict"] in (
                "PASS", "FAIL", "INCONCLUSIVE")
        t0 = int(os.environ["FILLER_SMOKE_T0"])
        data = read_json(SMOKE)
        return SMOKE.stat().st_mtime >= t0 and data["row_id"] == ROW and data["ok"] is True and (
            data["arms"] == list(verdict.ARMS) and data["fixtures"] == "PASS")
    except (OSError, ValueError, KeyError, TypeError):
        return False


def terminated(signum, _frame):
    raise SystemExit(f"keeper sent signal {signum}")


if __name__ == "__main__":
    mode = sys.argv[1:]
    if mode == ["--precondition"]:
        admission()
    elif mode in (["--complete"], ["--smoke-predicate"]):
        sys.exit(0 if predicate(mode[0]) else 1)
    elif not mode:
        signal.signal(signal.SIGTERM, terminated)
        run_job()
    else:
        sys.exit("unexpected arguments")
