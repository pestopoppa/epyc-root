"""Opt-in raw write-side observer of pinned E5 seams. No grade or defaults."""
from __future__ import annotations
import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

# Reuse accepted opt-in leaf parsers; source7 remains unchanged.
from s05_sourceprep import (_normalize_cpu_list, _pages_by_node_from_maps,
                           _numa_policy_from_maps, CONTROL_NOTE, SWEEP_HARNESS_BLOB,
                           SWEEP_HARNESS_PATH, SOURCE_COMMIT)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stable_bytes(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("nonregular raw artifact")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read()
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError("raw source changed during read")
        return raw
    finally:
        os.close(fd)


def ticks(raw):
    # comm may contain spaces/parentheses; fields after its final ')' start at field3.
    value = int(raw.decode().rsplit(")", 1)[1].split()[19])
    if value <= 0:
        raise ValueError("invalid PID start ticks")
    return value


class Archive:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.lock = threading.Lock()
        self.sequence = 0

    def put(self, label, raw):
        with self.lock:
            name = f"raw-{self.sequence:06d}.bin"
            self.sequence += 1
            with (self.root / name).open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            pin = {"name": name, "label": label, "bytes": len(raw), "sha256": sha(raw)}
            with (self.root / "raw-index.jsonl").open("a") as journal:
                journal.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), "monotonic_ns": time.monotonic_ns(), "pin": pin}) + "\n")
                journal.flush()
                os.fsync(journal.fileno())
        return pin

    def file(self, path):
        return self.put(str(path), stable_bytes(path))

    def json(self, label, value):
        return self.put(label, (json.dumps(value, sort_keys=True) + "\n").encode())


def reopen(root, pin):
    if Path(pin["name"]).name != pin["name"] or pin["name"] in (".", ".."):
        raise ValueError("nonlocal raw artifact")
    raw = stable_bytes(Path(root) / pin["name"])
    if len(raw) != pin["bytes"] or sha(raw) != pin["sha256"]:
        raise ValueError("raw artifact digest mismatch")
    return raw


def validate_sample(root, sample, expected, identity, launch_argv):
    raw = {name: reopen(root, pin) for name, pin in sample["raw"].items()}
    if sample["pid"] != identity["pid"] or sample["start_ticks"] != identity["start_ticks"]:
        raise ValueError("PID identity changed")
    if ticks(raw["stat_before"]) != identity["start_ticks"] or ticks(raw["stat_after"]) != identity["start_ticks"]:
        raise ValueError("stale/reused PID")
    if sample["start_ns"] > sample["end_ns"]:
        raise ValueError("sample timestamp ordering")
    status = raw["status"].decode()
    allowed = next((line.split(":", 1)[1].strip() for line in status.splitlines() if line.startswith("Cpus_allowed_list:")), None)
    if allowed is None or _normalize_cpu_list(allowed) != _normalize_cpu_list(expected["cpu_list"]):
        raise ValueError("raw affinity disagrees with manifest")
    maps = raw["numa_maps"].decode()
    if sample["pages_by_node"] != _pages_by_node_from_maps(maps):
        raise ValueError("page projection disagrees with raw maps")
    if not sample["pages_by_node"] or not raw["numastat_stdout"].strip() or sample["numastat_exit"] != 0:
        raise ValueError("missing/failed pages or numastat")
    policy = expected["numactl_policy"]
    actual = _numa_policy_from_maps(maps)
    argv = launch_argv
    if not any(argv[i:i + 2] == ["-c", expected["cpu_list"]] for i in range(len(argv) - 1)) or "taskset" not in argv:
        raise ValueError("launch argv lacks exact taskset")
    prefix = 5 if "numactl" in argv else 3
    effective = [part.decode() for part in raw["cmdline"].split(b"\0") if part]
    if argv[:1] != ["taskset"] or effective != argv[prefix:]:
        raise ValueError("raw cmdline differs from captured server argv")
    if policy == "interleave=all":
        if _normalize_cpu_list(expected["cpu_list"]) != set(range(96)) or "numactl" not in argv or "--interleave=all" not in argv or actual not in ("interleave", "mixed"):
            raise ValueError("contradictory full interleave policy")
    elif policy == "none":
        if "numactl" in argv or actual != "default" or _normalize_cpu_list(expected["cpu_list"]) == set(range(96)):
            raise ValueError("contradictory taskset-only policy")
    else:
        raise ValueError("unsupported manifest policy")


def validate_capture(root, record, manifest):
    for pin in record["inputs"].values():
        reopen(root, pin)
    if json.loads(reopen(root, record["inputs"]["manifest"])) != manifest:
        raise ValueError("manifest raw binding mismatch")
    if len(manifest["instances"]) != len(record["instances"]):
        raise ValueError("instance capture count mismatch")
    cache = record["cache"]
    for pin in cache["raw"].values():
        reopen(root, pin)
    argv = json.loads(reopen(root, cache["raw"]["argv"]))
    if cache["exit"] != 0 or not any("drop_caches" in token for token in argv) or cache["end_ns"] > record["launch_ns"]:
        raise ValueError("cache drop missing/failed/late")
    start, end = record["driver_window_ns"]
    request_windows = json.loads(reopen(root, record["driver_records"]))
    if start >= end:
        raise ValueError("invalid driver observation window")
    for expected in manifest["instances"]:
        seen = record["instances"][str(expected["port"])]
        launch = json.loads(reopen(root, seen["launch_argv"]))
        reopen(root, seen["launch_stat"])
        if ticks(reopen(root, seen["launch_stat"])) != seen["identity"]["start_ticks"]:
            raise ValueError("launch PID identity mismatch")
        gate = seen["preflight"]
        artifact = json.loads(reopen(root, gate["artifact"]))
        if gate["exit"] != 0 or artifact.get("live_affinity_verified") is not True:
            raise ValueError("existing live affinity preflight failed")
        matches = [row for row in artifact["instances"] if row["port"] == expected["port"]]
        if len(matches) != 1 or matches[0]["match"] is not True or str(matches[0]["pid"]) != str(seen["identity"]["pid"]) or str(matches[0]["pid_on_port"]) != str(seen["identity"]["pid"]) or _normalize_cpu_list(matches[0]["observed_thread_union"]) != _normalize_cpu_list(expected["cpu_list"]):
            raise ValueError("raw preflight PID/port/thread-affinity binding mismatch")
        reopen(root, gate["output"])
        ready, after = seen["ready"], seen["after"]
        if not ready["end_ns"] <= start < end <= after["start_ns"]:
            raise ValueError("before/after timestamps do not bracket driver")
        during = [sample for sample in seen["samples"] if start <= sample["start_ns"] <= sample["end_ns"] <= end]
        during = [sample for sample in during if any(
            row["cell_id"] == manifest["cell_id"] and row["instance_port"] == expected["port"]
            and row["stream_id"] >= 0 and int(row["start_s"] * 1e9) <= sample["start_ns"] <= sample["end_ns"] <= int(row["end_s"] * 1e9)
            for row in request_windows)]
        if len(during) < 2:
            raise ValueError("missing two observations DURING driver window")
        for sample in [ready, *during, after]:
            validate_sample(root, sample, expected, seen["identity"], launch)
        # Preserve and rebind transition observations too, even though they
        # cannot establish a fact about the measured driver interval.
        for sample in seen["samples"]:
            for pin in sample["raw"].values():
                reopen(root, pin)
        if expected["cpu_list"] in ("0-47,96-143", "48-95,144-191") and CONTROL_NOTE not in manifest.get("notes", ""):
            raise ValueError("unmarked half control")
    for pin in record["harness_raw"].values():
        reopen(root, pin)
    teardown = json.loads(reopen(root, record["teardown"]))
    if teardown["all_pids_dead"] is not True or record["harness_exit"] != 0:
        raise ValueError("failed harness or surviving PID")
    if teardown["time_ns"] < end:
        raise ValueError("teardown predates driver")
    return record


class Observer:
    def __init__(self, archive, manifest, interval, numastat, proc_root=Path("/proc")):
        self.archive, self.manifest, self.interval, self.numastat, self.proc_root = archive, manifest, interval, numastat, proc_root
        self.record = {"schema": "s05.raw-observer/1", "scope": "original raw source observations only; no grade or admission authority", "instances": {}}
        self.processes = []
        self.error = None

    def sample(self, port):
        seen = self.record["instances"][str(port)]
        pid = seen["identity"]["pid"]
        directory = self.proc_root / str(pid)
        sample = {"pid": pid, "start_ticks": seen["identity"]["start_ticks"], "start_ns": time.monotonic_ns(),
                  "utc": datetime.now(timezone.utc).isoformat(), "raw": {}}
        for name, file in (("stat_before", "stat"), ("cmdline", "cmdline"), ("status", "status"), ("numa_maps", "numa_maps")):
            sample["raw"][name] = self.archive.file(directory / file)
        completed = subprocess.run([self.numastat, "-p", str(pid)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        sample["numastat_exit"] = completed.returncode
        sample["raw"]["numastat_argv"] = self.archive.json("numastat argv", [self.numastat, "-p", str(pid)])
        sample["raw"]["numastat_stdout"] = self.archive.put("numastat stdout", completed.stdout)
        sample["raw"]["numastat_stderr"] = self.archive.put("numastat stderr", completed.stderr)
        sample["raw"]["stat_after"] = self.archive.file(directory / "stat")
        sample["end_ns"] = time.monotonic_ns()
        maps = reopen(self.archive.root, sample["raw"]["numa_maps"]).decode()
        sample["pages_by_node"] = _pages_by_node_from_maps(maps)
        if ticks(reopen(self.archive.root, sample["raw"]["stat_before"])) != sample["start_ticks"] or ticks(reopen(self.archive.root, sample["raw"]["stat_after"])) != sample["start_ticks"]:
            raise ValueError("PID identity changed during capture")
        return sample

    def install(self, harness):
        original_start, original_gate = harness.start_server, harness.run_affinity_preflight
        original_driver, original_teardown = harness.run_cell_driver, harness.teardown_cell
        def start(argv, env, log_path):
            self.record.setdefault("launch_ns", time.monotonic_ns())
            proc = original_start(argv, env, log_path)
            self.processes.append(proc)
            port = int(argv[argv.index("--port") + 1])
            try:
                stat_pin = self.archive.file(self.proc_root / str(proc.pid) / "stat")
                self.record["instances"][str(port)] = {"identity": {"pid": proc.pid, "start_ticks": ticks(reopen(self.archive.root, stat_pin))},
                    "launch_stat": stat_pin, "launch_argv": self.archive.json("actual start_server argv", argv),
                    "launch_env_allowlist": self.archive.json("actual launch environment allowlist", {key: value for key, value in env.items()
                        if key.startswith(("OMP_", "GGML_", "KMP_")) or key == "LD_LIBRARY_PATH"}), "samples": []}
            except Exception:
                # The original harness has not yet received this Popen handle.
                # Reuse its exact owned-PID verified stop, never a name scan.
                self.archive.json("launch-capture failure owned-PID cleanup", harness.stop_instance(proc))
                raise
            return proc
        def gate(**kwargs):
            rc, artifact, output = original_gate(**kwargs)
            pin = self.archive.file(kwargs["artifact_path"])
            for port, pid in kwargs["pid_map"].items():
                seen = self.record["instances"][str(port)]
                if seen["identity"]["pid"] != pid:
                    raise ValueError("preflight PID differs from captured launch")
                seen["preflight"] = {"exit": rc, "artifact": pin, "output": self.archive.put("original preflight output", output.encode())}
                seen["ready"] = self.sample(port)
            return rc, artifact, output
        def driver(**kwargs):
            stopped = threading.Event()
            def collect():
                try:
                    while not stopped.is_set():
                        for port, seen in self.record["instances"].items():
                            seen["samples"].append(self.sample(port))
                        stopped.wait(self.interval)
                except Exception as exc:
                    self.error = repr(exc)
                    stopped.set()
            start_ns = time.monotonic_ns()
            thread = threading.Thread(target=collect, daemon=False)
            thread.start()
            end_ns = None
            try:
                records = original_driver(**kwargs)
                end_ns = time.monotonic_ns()
                self.record["driver_records"] = self.archive.json("original driver request identities/windows", [
                    {"cell_id": row.cell_id, "instance_port": row.instance_port, "stream_id": row.stream_id,
                     "request_index": row.request_index, "start_s": row.start_s, "end_s": row.end_s}
                    for row in records])
                return records
            finally:
                if end_ns is None:
                    end_ns = time.monotonic_ns()
                stopped.set()
                thread.join()
                self.record["driver_window_ns"] = [start_ns, end_ns]
                for port, seen in self.record["instances"].items():
                    seen["after"] = self.sample(port)
                if self.error:
                    raise ValueError("observer capture failed: " + self.error)
        def teardown(procs):
            result = original_teardown(procs)
            status = {"time_ns": time.monotonic_ns(), "all_pids_dead": all(proc.poll() is not None and not (self.proc_root / str(proc.pid)).exists() for proc in self.processes), "original_results": result}
            self.record["teardown"] = self.archive.json("original teardown plus process-death verification", status)
            return result
        harness.start_server, harness.run_affinity_preflight = start, gate
        harness.run_cell_driver, harness.teardown_cell = driver, teardown


def owner_main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--admission", required=True, type=Path)
    parser.add_argument("--cache-command-json", required=True, type=Path)
    parser.add_argument("--source-plan", required=True, type=Path)
    parser.add_argument("--numastat", required=True)
    parser.add_argument("--sample-interval", required=True, type=float)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--owner-execute", action="store_true")
    parser.add_argument("harness_argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not Path(args.numastat).is_absolute() or not Path(args.numastat).is_file():
        raise ValueError("explicit absolute numastat executable required")
    if time.get_clock_info("monotonic").implementation != time.get_clock_info("perf_counter").implementation:
        raise ValueError("request/sample clocks cannot be compared")
    argv = args.harness_argv[1:] if args.harness_argv[:1] == ["--"] else args.harness_argv
    if not args.owner_execute or args.sample_interval <= 0 or "--execute" not in argv or "--i-have-operator-grant" not in argv:
        raise ValueError("explicit admitted owner execution and sample interval required")
    positions = [i for i, token in enumerate(argv) if token == "--cell-manifest"]
    if len(positions) != 1 or Path(argv[positions[0] + 1]).resolve() != args.manifest.resolve():
        raise ValueError("one exact manifest per invocation required")
    root = args.research_root.resolve()
    source_plan = json.loads(stable_bytes(args.source_plan))
    if source_plan.get("research_commit") != SOURCE_COMMIT:
        raise ValueError("reviewed Research source plan required")
    source_rows = [row for row in source_plan["source_pins"] if row["repository"] == "research" and row["path"].endswith(".py")]
    if len(source_rows) != 5:
        raise ValueError("complete five-module Research import closure required")
    for row in source_rows:
        raw = stable_bytes(root / row["path"])
        if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
            raise ValueError("Research import closure drift")
    harness_path = root / SWEEP_HARNESS_PATH
    for cmd, expected in ((["rev-parse", f"{SOURCE_COMMIT}:{SWEEP_HARNESS_PATH}"], SWEEP_HARNESS_BLOB), (["hash-object", str(harness_path)], SWEEP_HARNESS_BLOB)):
        if subprocess.check_output(["git", "-C", str(root), *cmd], text=True).strip() != expected:
            raise ValueError("unchanged harness source pin mismatch")
    archive = Archive(args.output)
    manifest = json.loads(stable_bytes(args.manifest))
    observer = Observer(archive, manifest, args.sample_interval, args.numastat)
    record = observer.record
    record["inputs"] = {name: archive.file(path) for name, path in (("manifest", args.manifest), ("admission", args.admission), ("harness", harness_path), ("cache_command", args.cache_command_json),
        ("source_plan", args.source_plan), ("observer_source", Path(__file__)), ("parser_source", Path(_normalize_cpu_list.__code__.co_filename)), ("numastat_executable", Path(args.numastat)))}
    for row in source_rows:
        record["inputs"]["research:" + row["path"]] = archive.file(root / row["path"])
    record["harness_argv"] = argv
    cache_argv = json.loads(reopen(archive.root, record["inputs"]["cache_command"]))
    if not isinstance(cache_argv, list) or not cache_argv or not all(isinstance(x, str) for x in cache_argv) or not any("drop_caches" in x for x in cache_argv):
        raise ValueError("explicit cache-drop command required")
    cache = {"start_ns": time.monotonic_ns(), "raw": {"argv": archive.json("cache argv", cache_argv), "meminfo_before": archive.file(Path("/proc/meminfo"))}}
    record["cache"] = cache
    result = subprocess.run(cache_argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    cache.update(exit=result.returncode, end_ns=time.monotonic_ns())
    cache["raw"].update(stdout=archive.put("cache stdout", result.stdout), stderr=archive.put("cache stderr", result.stderr), meminfo_after=archive.file(Path("/proc/meminfo")))
    if result.returncode:
        raise ValueError("cache drop failed; harness not started")
    spec = importlib.util.spec_from_file_location("s05_pinned_observed_harness", harness_path)
    harness = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = harness
    spec.loader.exec_module(harness)
    for row in source_rows:
        if sha(stable_bytes(root / row["path"])) != row["sha256"]:
            raise ValueError("Research import source changed before execution")
    observer.install(harness)
    stdout_path, stderr_path = archive.root / "harness.stdout.raw", archive.root / "harness.stderr.raw"
    try:
        with stdout_path.open("x") as stdout, stderr_path.open("x") as stderr:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                record["harness_exit"] = harness.main(argv)
        record["harness_raw"] = {"stdout": archive.file(stdout_path), "stderr": archive.file(stderr_path)}
        validate_capture(archive.root, record, manifest)
        record["structural_validation"] = "passed; original raw bindings only, no grade/admission authority"
    except Exception as exc:
        record["observer_failure"] = repr(exc)
        raise
    finally:
        record["ended_utc"] = datetime.now(timezone.utc).isoformat()
        with (archive.root / "capture.json").open("x") as stream:
            json.dump(record, stream, indent=2)
            stream.write("\n")
    return record["harness_exit"]


def main():
    try:
        return owner_main()
    except Exception as exc:
        # Early failures (including cache/import) retain their original raw
        # index and an explicit failure file; never seal a successful capture.
        if "--output" in sys.argv:
            output = Path(sys.argv[sys.argv.index("--output") + 1])
            if (output / "raw-index.jsonl").is_file():
                with (output / "failure.json").open("x") as stream:
                    json.dump({"error": repr(exc), "utc": datetime.now(timezone.utc).isoformat()}, stream)
                    stream.write("\n")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
