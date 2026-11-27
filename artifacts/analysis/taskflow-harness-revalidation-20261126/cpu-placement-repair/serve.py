"""Load only the approved CPU C22 replacement within this pilot's held grant."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import signal
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
LEGACY = HERE.parent / "legacy-runner"
sys.path.insert(0, str(LEGACY))
import run as legacy

SEAL = "9498641010d8c6e910862f38e1f838e28432a7934b205a2a874b3079837c3fd2"
OLD_CPU = 1016704
GPU, CONTROLLER, OWNER = 1016973, 1016657, 1016652
START = {GPU: 160923084, CONTROLLER: 160922944, OWNER: 160922939}
PREVIOUS = legacy.FROZEN / "quality-runs/cache-safe-01"
GPU_SHA = "0e2bdb4c70f64fbf78791dd805aed37702324c02ef8d45d1f686c68ddf61cf4e"
CPU_SHA = "811475d0707823c9cdeba68fd06275cf05ac66556bde7060654af6296ed831c3"


def identity(pid):
    fields = (Path(f"/proc/{pid}") / "stat").read_text().rsplit(")", 1)[1].split()
    return {"state": fields[0], "parent": int(fields[1]), "start_ticks": int(fields[19])}


def grant_live(*, check_gpu=False):
    for pid, expected_parent in ((OWNER, None), (CONTROLLER, OWNER)):
        state = identity(pid)
        if state["start_ticks"] != START[pid] or state["state"] == "Z":
            raise RuntimeError(f"recorded owner exited or changed: {pid}")
        if expected_parent is not None and state["parent"] != expected_parent:
            raise RuntimeError("quality controller is outside the held region lock")
    fd_root = Path(f"/proc/{OWNER}/fd")
    for fd, quarter in zip(range(3, 7), range(4), strict=True):
        if (fd_root / str(fd)).readlink().name != f"cpu_region.GLOBAL.q{quarter}.lock":
            raise RuntimeError(f"recorded whole-host fd changed: {fd}")
        info = (fd_root.parent / "fdinfo" / str(fd)).read_text()
        if re.search(rf"^lock:\s+\d+: FLOCK\s+ADVISORY\s+WRITE {OWNER}\s", info, re.MULTILINE) is None:
            raise RuntimeError(f"whole-host region lock inactive: q{quarter}")
    if Path(f"/proc/{OLD_CPU}").exists():
        raise RuntimeError("previous CPU process must be confirmed dead before replacement")
    if check_gpu:
        state = identity(GPU)
        if state["start_ticks"] != START[GPU] or state["parent"] != CONTROLLER or state["state"] == "Z":
            raise RuntimeError("GPU sibling no longer belongs to the active pilot")
        legacy.same_file(Path(f"/proc/{GPU}/exe"), GPU_SHA)
        if not Path(f"/sys/class/kfd/kfd/proc/{GPU}").exists():
            raise RuntimeError("GPU sibling native residency was lost")
    return {"region_owner": OWNER, "controller": CONTROLLER, "gpu": GPU, "old_cpu": OLD_CPU,
            "start_ticks": START, "global_regions": ["q0", "q1", "q2", "q3"]}


def memory_residency(lines, model):
    large = []
    weights_file_bytes = 0
    for line in lines:
        parts = line.split()
        page = next((int(word.split("=")[1]) * 1024 for word in parts if word.startswith("kernelpagesize_kB=")), 4096)
        pages = {int(n): int(q) for n, q in re.findall(r"\bN(\d+)=(\d+)", line)}
        counts = {node: count * page for node, count in pages.items()}
        total = sum(counts.values())
        if f"file={model}" in line:
            weights_file_bytes += total
        if (len(parts) >= 2 and parts[1] == "interleave:0-3" and " anon=" in line
                and " file=" not in line and total >= 2**30):
            large.append({"line": line.strip(), "bytes": total, "nodes": counts})
    nodes = Counter()
    for item in large:
        nodes.update(item["nodes"])
    total = sum(nodes.values())
    portions = {node: count / total for node, count in sorted(nodes.items())} if total else {}
    return {"model_file_mapped_bytes": weights_file_bytes, "anonymous_large_interleaved_bytes": total,
            "nodes_bytes": dict(nodes), "node_fractions": portions, "mappings": large}


def verify_residency(record, model_bytes):
    # Requiring a single large allocated region with even placement distinguishes
    # the weight buffer from the collection of smaller KV and scratch mappings.
    def balanced(mapping):
        return set(mapping["nodes"]) == {0, 1, 2, 3} and all(
            0.15 <= size / mapping["bytes"] <= 0.35 for size in mapping["nodes"].values())
    if record["model_file_mapped_bytes"] > 1024**2:
        raise RuntimeError("CPU model is still resident through a GGUF file mapping")
    if not any(item["bytes"] >= 0.75 * model_bytes and balanced(item) for item in record["mappings"]):
        raise RuntimeError("could not establish interleaving for the large anonymous weight allocation")


def check_native(epoch, pilot, server, port, cfg, process):
    if pilot.stop.is_set() or not server.wait_health(port, process, 180):
        raise RuntimeError("CPU replacement failed readiness or its grant was withdrawn")
    grant_live()
    path = Path(f"/proc/{process.pid}")
    argv = (path / "cmdline").read_bytes().split(b"\0")[:-1]
    old = legacy.read(PREVIOUS / "out-cpu/server.json")["argv"]
    old = old[old.index(cfg["build_bin"] + "/llama-server"):]
    new = [os.fsdecode(value) for value in argv]
    normalized = list(new)
    normalized[normalized.index("--port") + 1] = "33505"
    normalized[normalized.index("--slot-save-path") + 1] = old[old.index("--slot-save-path") + 1]
    normalized.remove("--no-mmap")
    if normalized != old or new.count("--no-mmap") != 1:
        raise RuntimeError("native argv differs beyond placement, port and private slot cache")
    slots = pilot.fetch(port, "/slots")
    log = (epoch / "out-cpu/server.log").read_text(errors="replace")
    ctx = cfg["ctx_by_np"]["4"]
    if [slot["id"] for slot in slots] != [0, 1, 2, 3] or f"n_ctx_slot = {ctx}, kv_unified = 'false'" not in log:
        raise RuntimeError("native context or slot shape changed")
    maps = sorted({line.split()[-1] for line in (path / "maps").read_text().splitlines()
                   if "/libggml" in line or "/libllama" in line})
    expected = legacy.read(epoch / "out-cpu/proofs.json")["manifest_verified"]
    if not maps or not all(legacy.digest(Path(lib)) == expected.get("bin/" + Path(lib).name)
                           and Path(lib).parent == Path(cfg["build_bin"]) for lib in maps):
        raise RuntimeError("native library bytes differ from the bound C22 store")
    legacy.same_file(path / "exe", CPU_SHA)
    if process.pid in pilot.kfd_pids():
        raise RuntimeError("CPU replacement registered a GPU context")
    with (path / "numa_maps").open() as source:
        record = memory_residency(source, cfg["model"])
    legacy.write(epoch / "NUMA-AFTER.json", record)
    verify_residency(record, Path(cfg["model"]).stat().st_size)
    receipt = {"pid": process.pid, "port": port, "n_parallel": 4, "n_ctx_slot": ctx,
               "kv_unified": False, "maps": maps, "model": cfg["model"], "argv": new,
               "cpu_only": True, "residency_sha256": legacy.digest(epoch / "NUMA-AFTER.json"),
               "owned_grant": grant_live(), "verified_at": time.time()}
    legacy.write(epoch / "out-cpu/live.json", receipt)
    return receipt


def launch(epoch):
    legacy.verify(SEAL)
    proof = grant_live(check_gpu=True)
    if not epoch.is_relative_to(HERE / "runs"):
        raise ValueError("use a private new runtime directory inside cpu-numa-repair/runs")
    epoch.mkdir(parents=True, mode=0o700)
    legacy.write(epoch / "GRANT.json", proof)
    pilot, server, _ = legacy.runtime_modules()
    pilot.ROOT = epoch
    config = legacy.read(LEGACY / "CONFIG-cpu.json")
    flags = config["server_flags"]
    if "--no-mmap" in flags:
        raise RuntimeError("base placement differs")
    flags.append("--no-mmap")
    legacy.write(epoch / "CONFIG-cpu.json", config)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda *_: pilot.stop.set())
    cfg, out = pilot.setup("cpu")
    slots = out / "slot-cache"
    slots.mkdir()
    if pilot.stop.is_set():
        return
    server.ARM["thinking"] = False
    grant_live()
    port = server.free_port()
    if port == 33505:
        raise RuntimeError("replacement must use a fresh port")
    process = server.start_server(port, np_=4, slot_save_path=slots)
    print(f"CPU C22 replacement pid={process.pid} port={port}", flush=True)
    def watch():
        while not pilot.stop.wait(.5):
            if (epoch / "STOP").exists():
                pilot.stop.set()
                break
            try:
                grant_live()
            except (OSError, ValueError, RuntimeError) as error:
                legacy.write(epoch / "GRANT-LOST.json", {"issued_at": time.time(), "error": repr(error)})
                pilot.stop.set()
                break
    watcher = threading.Thread(target=watch, daemon=True)
    sampler = threading.Thread(target=pilot.sample, args=({"cpu": (port, cfg, process)},), daemon=True)
    started = []
    try:
        for thread in (watcher, sampler):
            thread.start()
            started.append(thread)
        receipt = check_native(epoch, pilot, server, port, cfg, process)
        if pilot.stop.is_set():
            raise InterruptedError("replacement was stopped before readiness")
        legacy.write(epoch / "READY.json", {**receipt, "live_receipt": str(out / "live.json"),
                                             "live_receipt_sha256": legacy.digest(out / "live.json"),
                                             "server_executable_sha256": CPU_SHA})
        print(f"READY {epoch / 'READY.json'}", flush=True)
        while not pilot.stop.wait(.5) and process.poll() is None:
            pass
    finally:
        pilot.stop.set()
        for thread in started:
            thread.join(timeout=2)
        cleanup = server.stop_server(process)
        legacy.write(epoch / "CLEANUP.json", {"cpu_only": cleanup, "gpu": GPU, "controller": CONTROLLER})
        if not cleanup["dead_verified"]:
            raise RuntimeError("replacement CPU process failed cleanup")


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path)
    cli.add_argument("--verify-only", action="store_true")
    args = cli.parse_args()
    if args.verify_only:
        legacy.verify(SEAL)
        print(json.dumps(grant_live(check_gpu=True)))
        return
    if args.out is None:
        cli.error("--out is required")
    launch(args.out.resolve())


if __name__ == "__main__":
    main()
