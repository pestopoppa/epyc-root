"""Keeper-bound paired C13 MI210 timing and isolated publisher qualification."""

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
import device_pin
import verdict

ROW = "v11-122-llg-gpu-c13-gate-20261118"
BUILD_ROW = "v11-122-llg-gpu-c13-nollg-build-20261118"
COMMIT = "bda43aa17c11b671e0e203e7eb7bf4f1303bc273"
TREE = "e6dc8715fa3374406b38de48571e8700bded094f"
BASELINE_SHA = "91b4466a1cd4546697cb2dd9ca90b25c1dc764caecbb8324f2e22764a11a9892"
MODEL = "/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf"
IMAGES = {"llg": Path("/mnt/raid0/llm/kernels/builds/gpu-20261117-bda43aa17-c13"),
          "nollg": HERE.parent / "c13-nollg-image"}
ENGINE = Path("/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh")
SNAPSHOT = ENGINE.parents[2] / "dryrun" / ROW / "engine" / ENGINE.name
KFD = Path("/sys/class/kfd/kfd/proc")
GPU_LOCK = Path("/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock")
RESULT = HERE / "RESULT.json"
NATIVE_CPUS = set(range(184, 192))
MIN_VRAM = 64 << 20
ARTIFACTS = {"llama-bench", "libllama-bench-impl.so", "libllama-common.so", "libllama.so",
             "libggml.so", "libggml-base.so", "libggml-cpu.so", "libggml-hip.so"}


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


def stat_model(model):
    info = Path(model["path"]).stat()
    require(model["stat"] == [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns],
            f"model stat tuple changed: {model['path']}")
    return model


def model_pins():
    identity = read_json(HERE / "model-identity.json")
    native = {"path": MODEL, "stat": identity["model_stat"], "sha256": identity["model_sha256"]}
    return {"native": stat_model(native), "smoke": stat_model(read_json(HERE / "smoke-model.json"))}


def admission():
    enabled_pin = HERE / "llg-build-identity.json"
    disabled_pin = HERE / "nollg-build-identity.json"
    receipt_pin = HERE / "nollg-build-receipt.json"
    enabled, disabled, receipt = map(read_json, (enabled_pin, disabled_pin, receipt_pin))
    require_digest(enabled_pin, BASELINE_SHA)
    for arm, pin, identity in (("llg", enabled_pin, enabled), ("nollg", disabled_pin, disabled)):
        require((identity["source_sha"], identity["source_tree"], identity["kind"]) == (COMMIT, TREE, "gpu"),
                f"{arm}: unexpected C13 source commit, tree or backend")
        require(identity["output"] == str(IMAGES[arm]), f"{arm}: unexpected build image")
        require_digest(IMAGES[arm] / "BUILD-IDENTITY.json", digest(pin))
    require(receipt["ok"] is True and receipt["verdict"] == "BUILD_PASS"
            and receipt["row_id"] == BUILD_ROW and receipt["arm"] == "nollg"
            and receipt["image"] == disabled["output"] and receipt["kind"] == "gpu"
            and receipt["llg_matcher_strings"] == 0
            and receipt["baseline_identity_sha256"] == disabled["baseline_identity_sha256"] == BASELINE_SHA,
            "invalid disabled build receipt lineage")
    for field in ("source", "source_sha", "source_tree", "configure_argv", "files"):
        require(receipt[field] == disabled[field], f"build receipt differs on {field}")
    require(enabled["ck"] == disabled["ck"], "CK source pins differ")

    on, off = "-DLLAMA_LLGUIDANCE:BOOL=ON", "-DLLAMA_LLGUIDANCE:BOOL=OFF"
    original = enabled["configure_argv"]
    required = {"-DGGML_HIP:BOOL=ON", "-DGGML_BACKEND_DL:BOOL=OFF", "-DGGML_CUDA:BOOL=OFF",
                "-DAMDGPU_TARGETS:UNINITIALIZED=gfx90a"}
    require(original.count(on) == 1 and off not in original and required.issubset(original),
            "invalid enabled gfx90a configure recipe")
    expected = [off if option == on else option.replace(enabled["source"], disabled["source"]).replace(
        enabled["output"], disabled["output"]) for option in original]
    require(disabled["configure_argv"] == expected, "effective configure differs beyond paths and llguidance toggle")

    enabled_artifacts = HERE / "llg-artifacts.sha256"
    require_digest(enabled_artifacts, disabled["baseline_image_pins_sha256"])
    files = {arm: {} for arm in verdict.ARMS}
    for line in enabled_artifacts.read_text().splitlines():
        sha, name = line.split(maxsplit=1)
        path = Path(name)
        if path == IMAGES["llg"] / "CMakeCache.txt":
            require_digest(path, sha)
            continue
        require(path.parent == IMAGES["llg"] / "bin", f"invalid enabled artifact path: {path}")
        files["llg"][path.name] = sha
    files["nollg"] = receipt["files"]
    for arm, entries in files.items():
        require(set(entries) == ARTIFACTS, f"{arm}: incorrect pinned artifact set")
        for name, sha in entries.items():
            require_digest(IMAGES[arm] / "bin" / name, sha)
    require(files["llg"]["libllama-bench-impl.so"] == files["nollg"]["libllama-bench-impl.so"],
            "benchmark implementation differs between arms")
    return {"source_sha": COMMIT, "source_tree": TREE, "build_row_id": BUILD_ROW,
            "enabled_build_identity_sha256": BASELINE_SHA, "disabled_build_identity_sha256": digest(disabled_pin),
            "disabled_build_receipt_sha256": digest(receipt_pin), "configure_argv": {"llg": original, "nollg": expected},
            "linkage_verifier_sha256": digest(HERE / "verify_ggml_linkage.sh"), "build_files": files,
            "models": model_pins(), "device": device_pin.verify()}


def process_birth(pid):
    return (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()[19]


def keeper_inner():
    """Bind the live parent chain to the canonical engine holding this GPU flock."""
    child = os.getpid()
    while child > 1:
        parent = int((Path("/proc") / str(child) / "stat").read_text().rsplit(")", 1)[1].split()[1])
        proc = Path("/proc") / str(parent)
        argv = (proc / "cmdline").read_bytes().split(b"\0")
        if (len(argv) >= 7 and argv[1] in (os.fsencode(ENGINE), os.fsencode(SNAPSHOT))
                and argv[0] == b"/bin/bash"
                and argv[2:7] == [b"--inner", b"--id", ROW.encode(), b"--class", b"gpu"]):
            lock = (proc / "fd/9").stat()
            actual = GPU_LOCK.stat()
            fdinfo = (proc / "fdinfo/9").read_text()
            require((lock.st_dev, lock.st_ino) == (actual.st_dev, actual.st_ino)
                    and any("FLOCK" in line and "WRITE" in line for line in fdinfo.splitlines()
                            if line.startswith("lock:")), "keeper inner has no exclusive MI210 flock")
            return parent, process_birth(parent), Path(os.fsdecode(argv[1]))
        child = parent
    raise ValueError("canonical keeper inner GPU engine missing")


def cpu_list(value):
    result = set()
    for item in value.split(","):
        low, _, high = item.partition("-")
        result.update(range(int(low), int(high or low) + 1))
    return result


def grant(smoke):
    env = os.environ
    require(env.get("FILLER_ID") == ROW and env.get("FILLER_NEEDGPU") == "1"
            and env.get("FILLER_GPU_FENCE") == "0" and env.get("FILLER_DIRECT") != "1",
            "requires keeper custody of the MI210")
    require((env.get("FILLER_DRYRUN") == "1") == smoke, "requires either publisher smoke or native grant")
    path = Path(env["FILLER_GRANTS_DIR"]) / f"{ROW}.grant"
    content = path.read_text()
    fields = dict(field.split("=", 1) for field in content.split() if "=" in field)
    grants = fields["regions"].split(",")
    require("mi210_0" in grants and "gpu-quiet" in fields["holds"].split(","), "grant lacks MI210 custody")
    if smoke:
        require(fields.get("id") == ROW and fields.get("schema") == "epyc.rowflow.dryrun-grant.v1"
                and fields.get("kind") == "rowflow-dryrun", "requires native GPU publisher dry-run grant")
    actual = os.sched_getaffinity(0)
    declared = cpu_list(env["FILLER_CPUS"])
    require(actual == declared and NATIVE_CPUS.issubset(actual), "unexpected keeper GPU CPU affinity")
    require(actual <= NATIVE_CPUS | set(range(88, 96)), "GPU grant contains unexpected logical CPUs")
    selected = set(range(184, 188)) if smoke else NATIVE_CPUS
    os.sched_setaffinity(0, selected)
    require(os.sched_getaffinity(0) == selected, "could not restrict benchmark CPU affinity")
    pid, birth, engine = keeper_inner()
    engine_sha = digest(engine)
    if engine == SNAPSHOT:
        pin = read_json(engine.parent / "ENGINE.json")
        require(pin["id"] == ROW and pin["source_dir"] == str(ENGINE.parent)
                and pin["engine"] == ENGINE.name and pin["files"][ENGINE.name] == engine_sha,
                "keeper snapshot differs from recorded engine pin")
    return {"path": str(path), "contents": content, "keeper_pid": pid, "keeper_birth": birth, "engine": str(engine), "engine_sha256": engine_sha,
            "granted_affinity": sorted(actual), "affinity": sorted(selected), "threads": len(selected)}


def check_window(custody):
    require(not Path(os.environ["FILLER_STOPFILE"]).exists(), "keeper STOP requested")
    require(time.time() < int(os.environ["FILLER_DEADLINE"]), "keeper deadline reached")
    require((custody["keeper_pid"], custody["keeper_birth"]) == keeper_inner()[:2]
            and Path(custody["path"]).read_text() == custody["contents"], "keeper grant custody changed")


def arm_environment(arm, threads):
    return {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "ROCR_VISIBLE_DEVICES": "0",
            "FILLER_ID": ROW, "FILLER_STOPFILE": os.environ.get("FILLER_STOPFILE", ""),
            "LD_LIBRARY_PATH": f"{IMAGES[arm]}/bin:/opt/rocm/lib",
            "GGML_N_THREADS": str(threads), "OMP_NUM_THREADS": str(threads), "OMP_DYNAMIC": "FALSE"}


def prove_arm(arm, env):
    image = IMAGES[arm]
    root = image / "bin"
    bench = root / "llama-bench"
    linkage = subprocess.check_output(["/bin/bash", str(HERE / "verify_ggml_linkage.sh"), str(bench),
                                       str(image)], env=env, text=True)
    resolved = {Path(path).resolve() for path in re.findall(r"^  OK\s+\S+\s+-> (\S+)", linkage, re.M)}
    expected = {(root / name).resolve() for name in ARTIFACTS - {bench.name}}
    require(resolved == expected and all(path.parent == root for path in resolved),
            f"{arm}: loaded project library set differs from local digest pins")
    loader = subprocess.check_output(["/usr/bin/ldd", str(bench)], env=env, text=True)
    require("not found" not in loader, f"{arm}: unresolved library")
    all_loaded = {Path(path).resolve() for path in re.findall(r"(?:=>\s+|^\s*)(/\S+)\s+\(", loader, re.M)}
    symbols = subprocess.check_output(["/usr/bin/strings", str(root / "libllama-common.so")], env=env)
    count = sum(b"llg_matcher_compute_mask" in line for line in symbols.splitlines())
    require(count == (9 if arm == "llg" else 0), f"{arm}: unexpected matcher string count {count}")
    return {"linkage": linkage, "ldd": loader, "llg_matcher_strings": count,
            "system_loader_paths": sorted(map(str, all_loaded - resolved))}


def clients():
    return sorted(int(path.name) for path in KFD.iterdir() if path.name.isdigit())


def sample_hip(pid, birth, hip, gpu):
    entry = KFD / str(pid)
    start = time.time_ns()
    live = clients()
    require(set(live) <= {pid}, f"foreign KFD clients during owned arm: {live}")
    sample = {"start_ns": start, "kfd_pids": live, "kfd_process_count": len(live)}
    if pid in live:
        try:
            require(process_birth(pid) == birth, "benchmark child PID birth changed")
            pasid = int((entry / "pasid").read_text())
            used = int((entry / f"vram_{gpu}").read_text())
            maps = (Path("/proc") / str(pid) / "maps").read_text().splitlines()
            hip_paths = sorted({item[-1] for line in maps if len(item := line.split(maxsplit=5)) == 6
                                and "/libggml-hip.so" in item[-1]})
            sample.update(pasid=pasid, own_vram_bytes=used, hip_maps=hip_paths,
                          resident=pasid > 0 and used >= MIN_VRAM and hip_paths == [str(hip)])
        except FileNotFoundError:
            # The child can exit between sysfs enumeration and maps collection.
            sample["exited_during_sample"] = True
    sample["end_ns"] = time.time_ns()
    return sample


def run_arm(run, label, arm, env, workload, model, custody, device):
    check_window(custody)
    stat_model(model)
    require(not clients(), "KFD clients present before benchmark arm")
    pp, tg, repeats = workload
    root = IMAGES[arm] / "bin"
    hip = (root / "libggml-hip.so").resolve()
    threads = custody["threads"]
    argv = [str(root / "llama-bench"), "-m", model["path"], "--device", "ROCm0", "-ngl", "99", "-fa", "1",
            "-t", str(threads), "-p", str(pp), "-n", str(tg), "-r", str(repeats), "-o", "json"]
    stem = f"{label}-{arm}"
    output, error, samples = (run / f"{stem}.{ext}" for ext in ("json", "err", "hip.jsonl"))
    record = {"arm": arm, "argv": argv, "environment": env, "affinity": custody["affinity"], "stdout": str(output),
              "stderr": str(error), "hip_samples": str(samples), "started_at": utc()}
    record_path = run / f"{stem}.meta.json"
    save(record_path, record)
    child = None
    resident = []
    try:
        with output.open("wb") as stdout, error.open("wb") as stderr, samples.open("w", buffering=1) as witness:
            child = subprocess.Popen(argv, env=env, stdout=stdout, stderr=stderr)
            birth = process_birth(child.pid)
            record.update(pid=child.pid, process_birth=birth)
            while child.poll() is None:
                check_window(custody)
                sample = sample_hip(child.pid, birth, hip, device["gpu_id"])
                if child.poll() is None and sample.get("resident") is True:
                    resident.append(sample["own_vram_bytes"])
                witness.write(json.dumps(sample) + "\n")
                time.sleep(0.2)
        record["exit_code"] = child.returncode
        require(child.returncode == 0, f"{stem} benchmark exited {child.returncode} ({error})")
        require(len(resident) >= 2, f"{stem}: insufficient live own-PID MI210 VRAM and HIP map samples")
        stat_model(model)
        validated = verdict.validate(read_json(output), pp, tg, repeats, threads, model["path"])
        print(f"{utc()} {stem} validated ({output})", flush=True)
        return validated, max(resident)
    except BaseException as exc:
        record["error"] = str(exc)
        raise
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)
        record.update(ended_at=utc(), resident_samples=len(resident), vram_peak_bytes=max(resident, default=0))
        if child is not None:
            record["cleanup_proved"] = child.poll() is not None and not (KFD / str(child.pid)).exists()
        save(record_path, record)
        if child is not None:
            require(record["cleanup_proved"] is True, f"{stem}: child or KFD context survives")


def run_job():
    smoke = os.environ.get("FILLER_SMOKE") == "1"
    custody = grant(smoke)
    out = HERE / ("smoke" if smoke else "out")
    out.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="run-", dir=out))
    record = {"row_id": ROW, "grant": custody, "started_at": utc(), "mode": "smoke" if smoke else "native"}
    state = run / "run.json"
    save(state, record)
    result = None
    try:
        check_window(custody)
        proof = admission()
        environments = {arm: arm_environment(arm, custody["threads"]) for arm in verdict.ARMS}
        proof["arms"] = {arm: prove_arm(arm, environments[arm]) for arm in verdict.ARMS}
        require(proof["arms"]["llg"]["system_loader_paths"] == proof["arms"]["nollg"]["system_loader_paths"],
                "system runtime loader paths differ between arms")
        proof_path = run / "proof.json"
        save(proof_path, proof)
        record["proof"] = str(proof_path)

        if smoke:
            verdict.smoke_fixtures()
            peaks = {arm: run_arm(run, "smoke", arm, environments[arm], (32, 16, 2),
                                  proof["models"]["smoke"], custody, proof["device"])[1] for arm in verdict.ARMS}
            record.update(fixtures="PASS", vram_peak_bytes=peaks)
        else:
            pairs = []
            for number, order in enumerate(verdict.ORDER, start=1):
                paired = {arm: run_arm(run, f"p{number}", arm, environments[arm], (512, 128, 5),
                                       proof["models"]["native"], custody, proof["device"])[0] for arm in order}
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
        result_path = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"])
        dry_dir = Path(os.environ["FILLER_DRYRUN_DIR"]).resolve()
        require(result_path.is_absolute() and result_path.parent.resolve() == result_path.parent
                and result_path.parent.is_relative_to(dry_dir) and not result_path.exists(),
                "unexpected smoke result path")
        result = {"unit_id": ROW, "status": "plumbing_only", "ok": True, "run": str(run),
                  "smoke_t0": int(os.environ["FILLER_SMOKE_T0"]), "fixtures": "PASS",
                  "affinity": custody["affinity"], "vram_peak_bytes": peaks, "ended_at": record["ended_at"]}
        save(run / "smoke.json", result)
        save(result_path, result)
    else:
        save(RESULT, {**result, "ended_at": record["ended_at"]})


def predicate(mode):
    try:
        if mode == "--complete":
            data = read_json(RESULT)
            return data["row_id"] == ROW and data["final"] is True and data["verdict"] in (
                "PASS", "FAIL", "INCONCLUSIVE")
        t0 = int(os.environ["FILLER_SMOKE_T0"])
        path = Path(os.environ["FILLER_DRYRUN_RESULT_PATH"])
        data = read_json(path)
        run = Path(data["run"])
        return (path.stat().st_mtime >= t0 == data["smoke_t0"] and data["unit_id"] == ROW
                and data["ok"] is True and data["status"] == "plumbing_only" and data["fixtures"] == "PASS"
                and data["affinity"] == list(range(184, 188)) and set(data["vram_peak_bytes"]) == set(verdict.ARMS)
                and all(type(size) is int and size >= MIN_VRAM for size in data["vram_peak_bytes"].values())
                and run.parent == HERE / "smoke" and (run / "smoke.json").read_bytes() == path.read_bytes())
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
        signal.signal(signal.SIGINT, terminated)
        run_job()
    else:
        sys.exit("unexpected arguments")
