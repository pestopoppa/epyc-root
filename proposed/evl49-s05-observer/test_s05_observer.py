"""Synthetic raw files only; no process, cache drop, harness or inference."""
import copy
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import pytest
import s05_observer as observer


def fixture(tmp_path):
    archive = observer.Archive(tmp_path / "raw")
    manifest = {"cell_id": "synthetic", "instances": [{"port": 19080, "cpu_list": "0-95", "numactl_policy": "interleave=all"}]}
    argv = ["taskset", "-c", "0-95", "numactl", "--interleave=all", "llama-server", "--port", "19080"]
    fields = ["S"] + ["0"] * 18 + ["456"]
    proc_stat = ("123 (synthetic command) " + " ".join(fields) + "\n").encode()
    def sample(start, end):
        raw = {"stat_before": proc_stat, "stat_after": proc_stat,
               "cmdline": b"llama-server\0--port\0" b"19080\0",
               "status": b"Cpus_allowed_list:\t0-95\n",
               "numa_maps": b"1000 interleave:0-3 anon=16 N0=8 N1=8\n",
               "numastat_stdout": b"Node0 8 Node1 8\n", "numastat_stderr": b"",
               "numastat_argv": b'["numastat", "-p", "123"]\n'}
        return {"pid": 123, "start_ticks": 456, "start_ns": start * 10**9, "end_ns": end * 10**9,
                "pages_by_node": {"N0": 8, "N1": 8}, "numastat_exit": 0,
                "raw": {name: archive.put(name, value) for name, value in raw.items()}}
    seen = {"identity": {"pid": 123, "start_ticks": 456}, "launch_stat": archive.put("launch stat", proc_stat),
            "launch_argv": archive.json("launch argv", argv),
            "preflight": {"exit": 0, "artifact": archive.json("original synthetic preflight", {"live_affinity_verified": True,
                          "instances": [{"port": 19080, "pid": "123", "pid_on_port": "123", "match": True, "observed_thread_union": "0-95"}]}),
                          "output": archive.put("preflight output", b"fixture success")},
            "ready": sample(10, 11), "samples": [sample(30, 31), sample(40, 41)], "after": sample(60, 61)}
    record = {"inputs": {"manifest": archive.json("manifest", manifest), "admission": archive.put("synthetic admission", b"synthetic only")},
              "cache": {"exit": 0, "start_ns": 1, "end_ns": 2, "raw": {"argv": archive.json("cache argv", ["fixture-drop_caches"]),
                         "stdout": archive.put("stdout", b""), "stderr": archive.put("stderr", b""),
                         "meminfo_before": archive.put("meminfo before", b"Cached: 100 kB\n"), "meminfo_after": archive.put("meminfo after", b"Cached: 10 kB\n")}},
              "launch_ns": 10, "driver_window_ns": [20 * 10**9, 50 * 10**9], "instances": {"19080": seen},
              "driver_records": archive.json("original synthetic requests", [{"cell_id": "synthetic", "instance_port": 19080, "stream_id": 0, "request_index": 0, "start_s": 22.0, "end_s": 48.0}]),
              "harness_raw": {"stdout": archive.put("harness stdout", b"synthetic only"), "stderr": archive.put("harness stderr", b"")},
              "harness_exit": 0, "teardown": archive.json("teardown", {"all_pids_dead": True, "time_ns": 70 * 10**9})}
    return archive, manifest, record


def test_original_raw_bindings_pass(tmp_path):
    archive, manifest, record = fixture(tmp_path)
    observer.validate_capture(archive.root, record, manifest)


@pytest.mark.parametrize("defect", ["missing", "posthoc", "stale_pid", "tampered_raw", "contradictory_policy", "failed_cache", "survivor", "outside_request"])
def test_original_raw_binding_refusals(tmp_path, defect):
    archive, manifest, record = fixture(tmp_path)
    seen = record["instances"]["19080"]
    if defect == "missing":
        (archive.root / seen["ready"]["raw"]["numa_maps"]["name"]).unlink()
    elif defect == "posthoc":
        seen["samples"][0]["start_ns"] = 55 * 10**9
        seen["samples"][0]["end_ns"] = 56 * 10**9
    elif defect == "stale_pid":
        seen["identity"]["start_ticks"] = 999
    elif defect == "tampered_raw":
        (archive.root / seen["samples"][0]["raw"]["status"]["name"]).write_bytes(b"Cpus_allowed_list: 0-47\n")
    elif defect == "contradictory_policy":
        seen["ready"]["raw"]["numa_maps"] = archive.put("contradictory raw map", b"1000 bind:0 anon=16 N0=16\n")
        seen["ready"]["pages_by_node"] = {"N0": 16}
    elif defect == "failed_cache":
        record["cache"]["exit"] = 1
    elif defect == "survivor":
        record["teardown"] = archive.json("surviving fixture PID", {"all_pids_dead": False, "time_ns": 70 * 10**9})
    elif defect == "outside_request":
        record["driver_records"] = archive.json("request outside observed samples", [{"cell_id": "synthetic", "instance_port": 19080, "stream_id": 0, "request_index": 0, "start_s": 42.0, "end_s": 48.0}])
    with pytest.raises((ValueError, FileNotFoundError)):
        observer.validate_capture(archive.root, record, manifest)


def test_nonregular_raw_artifact_refused(tmp_path):
    archive, manifest, record = fixture(tmp_path)
    pin = record["instances"]["19080"]["ready"]["raw"]["status"]
    target = archive.root / pin["name"]
    target.unlink()
    target.symlink_to(archive.root / record["inputs"]["admission"]["name"])
    with pytest.raises(OSError):
        observer.validate_capture(archive.root, record, manifest)


def test_existing_lifecycle_seams_preserve_owned_identity(tmp_path, monkeypatch):
    """Fake Popen/driver only: verify the write-side hook sequencing itself."""
    archive, manifest, original = fixture(tmp_path)
    proc_root = tmp_path / "fake-proc"
    directory = proc_root / "123"
    directory.mkdir(parents=True)
    (directory / "stat").write_bytes(observer.reopen(archive.root, original["instances"]["19080"]["launch_stat"]))
    proc = SimpleNamespace(pid=123, dead=False)
    proc.poll = lambda: 0 if proc.dead else None
    sample_count = 0
    two_samples = threading.Event()
    capture = observer.Observer(archive, manifest, 0.001, "never-invoked-numastat", proc_root)
    def sample(port):
        nonlocal sample_count
        value = copy.deepcopy(original["instances"][str(port)]["samples"][0])
        value["start_ns"] = time.monotonic_ns()
        value["end_ns"] = time.monotonic_ns()
        sample_count += 1
        if sample_count >= 3:  # first sample is ready; next two overlap driver.
            two_samples.set()
        return value
    monkeypatch.setattr(capture, "sample", sample)
    def gate(**kwargs):
        kwargs["artifact_path"].write_bytes(observer.reopen(archive.root, original["instances"]["19080"]["preflight"]["artifact"]))
        return 0, {"live_affinity_verified": True}, "synthetic gate"
    def driver(**kwargs):
        start = time.perf_counter()
        assert two_samples.wait(2), "bounded sampler failed to advance"
        return [SimpleNamespace(cell_id="synthetic", instance_port=19080, stream_id=0, request_index=0,
                                start_s=start, end_s=time.perf_counter())]
    def teardown(procs):
        proc.dead = True
        (directory / "stat").unlink()
        directory.rmdir()
        return [{"pid": 123, "ps_verified_dead": True}]
    harness = SimpleNamespace(start_server=lambda *args: proc, run_affinity_preflight=gate,
                              run_cell_driver=driver, teardown_cell=teardown)
    capture.install(harness)
    argv = json.loads(observer.reopen(archive.root, original["instances"]["19080"]["launch_argv"]))
    assert harness.start_server(argv, {}, tmp_path / "unused.log") is proc
    harness.run_affinity_preflight(pid_map={"19080": 123}, artifact_path=tmp_path / "preflight.json")
    rows = harness.run_cell_driver(cell="synthetic")
    assert len(rows) == 1
    harness.teardown_cell([(None, proc)])
    seen = capture.record["instances"]["19080"]
    assert seen["identity"] == {"pid": 123, "start_ticks": 456}
    assert len(seen["samples"]) >= 2
    assert json.loads(observer.reopen(archive.root, capture.record["teardown"]))["all_pids_dead"] is True
    assert seen["ready"]["end_ns"] <= capture.record["driver_window_ns"][0]
    assert capture.record["driver_window_ns"][1] <= seen["after"]["start_ns"]
