"""Offline custody and failure-path tests; no inference or GPU claimed."""
import importlib.util
import json
import os
import ctypes
from pathlib import Path
import select
import signal
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "scripts/benchmark/gpqa_current_arm.py"
spec = importlib.util.spec_from_file_location("gpqa_current_arm", SOURCE)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


@pytest.fixture
def cohort(tmp_path, monkeypatch):
    questions = [{"id": f"q{i}", "prompt": f"Question {i}", "expected": "A"} for i in range(198)]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"suites": {driver.SUITE: questions}}))
    monkeypatch.setattr(driver, "MANIFEST_SHA", driver.digest(manifest))
    weight = tmp_path / "fake-weight"
    weight.write_bytes(b"fixture")
    s = weight.stat()
    config = {"arm": "current", "context": 32768, "max_tokens": 8192,
              "manifest": str(manifest), "sources": [{"path": str(manifest), "sha256": driver.digest(manifest)}],
              "weights": [{"path": str(weight), "stat": [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns]}]}
    # Native runner validation is tested in its own repo; this stub isolates the wrapper's checks.
    runner = SimpleNamespace(valid_resume_row=lambda row, suite, q: row.get("native_valid", True),
                             extract_letter_answer=lambda text: text, score_response=lambda text, gold, q: text == gold)
    return questions, config, runner, tmp_path / "out"


def capture(question, config):
    return {"protocol": driver.fingerprint(config), "request_start": 1, "request_end": 4,
            "device_samples": [{"pid": 123, "at": n, "vram_bytes": 100, "hip_library": "/approved/hip.so", "kfd": "/kfd/123", "slot_processing": True} for n in (2, 3)],
            "record": {"id": question["id"], "arm": config["arm"], "seed": 42, "rep": 0,
                       "prompt_tokens": 20, "correct": True, "truncated": False, "extracted": "A", "response": "A",
                       "effective_request": {"endpoint": "chat", "request_path": "/v1/chat/completions",
                                             "temperature": 0.6, "top_p": 0.95, "top_k": 20, "enable_thinking": False}}}


def test_prepared_inputs_fail_on_source_or_weight_change(cohort):
    questions, config, _, _ = cohort
    assert driver.prepare(config) == questions
    Path(config["weights"][0]["path"]).write_bytes(b"changed fixture")
    with pytest.raises(ValueError, match="weight identity"):
        driver.prepare(config)
    config["weights"] = []
    Path(config["manifest"]).write_text("changed")
    with pytest.raises(ValueError, match="source pin"):
        driver.prepare(config)


def test_context_bound_and_runtime_slot_are_required(cohort, tmp_path):
    _, config, _, _ = cohort
    config["context"] = 8192
    with pytest.raises(ValueError, match="insufficient context"):
        driver.prepare(config)
    log = tmp_path / "server.log"
    log.write_text("n_ctx_per_seq = 4096\n")
    with pytest.raises(ValueError, match="per-slot"):
        driver.context_capacity(log, 32768)
    log.write_text("n_ctx_per_seq = 32768\n")
    assert driver.context_capacity(log, 32768) == 32768


@pytest.mark.parametrize("change", [
    {"id": "wrong"}, {"arm": "retired"}, {"seed": 43}, {"rep": 1}, {"native_valid": False},
    {"effective_request": {}}, {"prompt_tokens": 30000}, {"prompt_tokens": 0},
    {"correct": False}, {"extracted": "B"}, {"truncated": True},
])
def test_invalid_or_stale_record_is_never_resumed(cohort, change):
    questions, config, runner, out = cohort
    value = capture(questions[0], config)
    value["record"].update(change)
    path = out / "accepted.json"
    driver.atomic_json(path, value)
    with pytest.raises(ValueError):
        driver.checkpoint(path, questions[0], config, runner)


@pytest.mark.parametrize("mode", ["one", "zero-vram", "late", "wrong-pid", "same-time", "idle", "protocol"])
def test_missing_or_nonoverlapping_device_evidence_is_rejected(cohort, mode):
    questions, config, runner, out = cohort
    value = capture(questions[0], config)
    if mode == "one":
        value["device_samples"].pop()
    elif mode == "zero-vram":
        value["device_samples"][0]["vram_bytes"] = 0
    elif mode == "late":
        value["device_samples"][1]["at"] = 5
    elif mode == "wrong-pid":
        value["device_samples"][1]["pid"] = 999
    elif mode == "same-time":
        value["device_samples"][1]["at"] = 2
    elif mode == "idle":
        value["device_samples"][0]["slot_processing"] = False
    else:
        value["protocol"] = "stale"
    path = out / "accepted.json"
    driver.atomic_json(path, value)
    with pytest.raises(ValueError):
        driver.checkpoint(path, questions[0], config, runner)


def test_full_consolidation_and_missing_item(cohort):
    questions, config, runner, out = cohort
    for i, q in enumerate(questions):
        driver.atomic_json(out / f"{i:03d}" / "accepted.json", capture(q, config))
    result = driver.consolidate(questions, config, runner, out)
    assert (result["n"], result["correct"], result["accuracy"], result["noparse"]) == (198, 198, 1.0, 0)
    (out / "197" / "accepted.json").unlink()
    with pytest.raises(FileNotFoundError):
        driver.consolidate(questions, config, runner, out)


def test_duplicate_and_malformed_raw_rows_rejected(tmp_path):
    path = tmp_path / "per_question.jsonl"
    for payload in ('{}\n{}\n', '{bad}\n', ''):
        path.write_text(payload)
        with pytest.raises(ValueError):
            driver.raw_record(path)


def test_hybrid_target_placement_excludes_external_draft(tmp_path):
    log = tmp_path / "server.log"
    target = ("load_tensors: offloaded 24/49 layers to GPU\n"
              "load_tensors:   CPU_Mapped model buffer size = 54000.00 MiB\n"
              "load_tensors:        ROCm0 model buffer size = 35000.00 MiB\n")
    draft = ("load_tensors: offloaded 2/2 layers to GPU\n"
             "load_tensors:        ROCm0 model buffer size = 2700.00 MiB\n")
    log.write_text(target + draft)
    assert driver.model_placement(log, 24) == {
        "offloaded_layers": 24, "total_layers": 49, "cpu_model_mib": 54000.0, "gpu_model_mib": 35000.0}
    for bad in (draft, target.replace("24/49", "49/49"), target.replace("54000.00", "0.00"),
                target.replace("35000.00", "0.00"), ""):
        log.write_text(bad)
        with pytest.raises(ValueError, match="hybrid weight placement"):
            driver.model_placement(log, 24)


def test_hybrid_checkpoint_requires_target_placement(cohort):
    questions, config, runner, out = cohort
    config.update(residency_mode="hybrid", gpu_layers=24)
    value = capture(questions[0], config)
    path = out / "accepted.json"
    driver.atomic_json(path, value)
    with pytest.raises(ValueError, match="hybrid weight placement"):
        driver.checkpoint(path, questions[0], config, runner)
    value["model_placement"] = {"offloaded_layers": 24, "total_layers": 49,
                                "cpu_model_mib": 54000, "gpu_model_mib": 35000}
    driver.atomic_json(path, value)
    assert driver.checkpoint(path, questions[0], config, runner) == value


@pytest.mark.parametrize("cutoff", ["stop", "deadline", "signal", "timeout", "observer"])
def test_inflight_child_is_reaped_on_all_cutoffs(tmp_path, cutoff):
    stop = tmp_path / "STOP"
    clock = [0]
    budget = driver.Budget(10, stop, clock=lambda: clock[0])
    seen = []
    original_popen = driver.subprocess.Popen

    def popen(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        seen.append(child)
        return child

    def observe():
        if cutoff == "stop":
            stop.touch()
        elif cutoff == "deadline":
            clock[0] = 10
        elif cutoff == "signal":
            budget.interrupted = True
        elif cutoff == "observer":
            raise ValueError("GPU evidence unavailable")

    exception = TimeoutError if cutoff == "timeout" else ValueError if cutoff == "observer" else driver.Cutoff
    with patch.object(driver.subprocess, "Popen", popen), pytest.raises(exception):
        driver.run_child([sys.executable, "-c", "import signal; signal.pause()"], tmp_path / "log", budget,
                         0.15 if cutoff == "timeout" else 5, observe)
    assert len(seen) == 1 and seen[0].poll() is not None
    with pytest.raises(ProcessLookupError):
        os.kill(seen[0].pid, 0)


def test_successful_child_and_server_failure(tmp_path):
    budget = driver.Budget(10, tmp_path / "STOP", clock=lambda: 0)
    assert driver.run_child([sys.executable, "-c", "raise SystemExit(0)"], tmp_path / "ok", budget, 5) == 0
    assert driver.run_child([sys.executable, "-c", "raise SystemExit(9)"], tmp_path / "bad", budget, 5) == 9


@pytest.mark.parametrize("mode", ["success", "nonzero", "stop", "observer"])
def test_owned_runner_group_reaps_term_resistant_worker(tmp_path, mode):
    # Adopt the fixture's grandchild so waitpid proves it died, rather than
    # mistaking a zombie or a missing leader for complete process cleanup.
    libc = ctypes.CDLL(None, use_errno=True)
    previous = ctypes.c_int()
    assert libc.prctl(37, ctypes.byref(previous), 0, 0, 0) == 0  # GET_CHILD_SUBREAPER
    assert libc.prctl(36, 1, 0, 0, 0) == 0  # SET_CHILD_SUBREAPER
    pidfile = tmp_path / "worker.pid"
    command = """
import os, signal, sys
from pathlib import Path
r, w = os.pipe()
pid = os.fork()
if pid == 0:
    os.close(r)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    os.write(w, b'ready')
    os.close(w)
    while True:
        signal.pause()
os.close(w)
os.read(r, 5)
os.close(r)
Path(sys.argv[1]).write_text(str(pid))
if sys.argv[2] in ('stop', 'observer'):
    signal.pause()
raise SystemExit(9 if sys.argv[2] == 'nonzero' else 0)
"""
    budget = driver.Budget(10, tmp_path / "STOP", clock=lambda: 0)

    def observe():
        if pidfile.exists():
            if mode == "stop":
                budget.stopfile.touch()
            elif mode == "observer":
                raise ValueError("observer failed with worker alive")

    try:
        args = ([sys.executable, "-c", command, str(pidfile), mode],
                tmp_path / "native.log", budget, 5, observe)
        if mode in ("stop", "observer"):
            with pytest.raises(driver.Cutoff if mode == "stop" else ValueError):
                driver.run_child(*args)
        else:
            assert driver.run_child(*args) == (9 if mode == "nonzero" else 0)
        worker = int(pidfile.read_text())
        # Wait on an exit event with a bound; a surviving worker fails promptly.
        pidfd = os.pidfd_open(worker)
        try:
            assert select.select([pidfd], [], [], 2)[0], "owned worker survived cleanup"
        finally:
            os.close(pidfd)
        reaped, status = os.waitpid(worker, 0)
        assert reaped == worker
        assert os.WIFSIGNALED(status) and os.WTERMSIG(status) == signal.SIGKILL
    finally:
        if pidfile.exists():
            worker = int(pidfile.read_text())
            try:
                os.kill(worker, signal.SIGKILL)
            except ProcessLookupError:
                pass
            try:
                os.waitpid(worker, 0)
            except ChildProcessError:
                pass
        assert libc.prctl(36, previous.value, 0, 0, 0) == 0


def test_failed_atomic_replace_preserves_checkpoint(tmp_path):
    path = tmp_path / "accepted.json"
    driver.atomic_json(path, {"existing": True})
    with patch.object(driver.os, "replace", side_effect=OSError("disk error")), pytest.raises(OSError):
        driver.atomic_json(path, {"incomplete": True})
    assert json.loads(path.read_text()) == {"existing": True}
    assert not list(tmp_path.glob(".pending-*"))


@pytest.mark.parametrize("hybrid", [False, True])
def test_execute_complete_then_resume_without_server_and_interrupted_retry(cohort, monkeypatch, hybrid):
    questions, config, runner, out = cohort
    config.update({"runner": "fake-runner", "binary": "fake-server", "model": "fake-weight",
                   "python": sys.executable, "kernel": "fixture", "spec_flags": [],
                   "library_dir": "/approved", "items_dir": str(out.parent / "items"),
                   "research_repo": str(out.parent)})
    placement = {"offloaded_layers": 24, "total_layers": 49, "cpu_model_mib": 54000, "gpu_model_mib": 35000}
    if hybrid:
        config.update(residency_mode="hybrid", gpu_layers=24)
    monkeypatch.setattr(driver, "model_placement", lambda log, layers: placement if layers == 24 else {})
    for i, q in enumerate(questions):
        driver.atomic_json(Path(config["items_dir"]) / f"{i:03d}.json", {"suites": {driver.SUITE: [q]}})
    monkeypatch.setattr(driver, "load_runner", lambda path: runner)
    monkeypatch.setattr(driver, "context_capacity", lambda *args: 32768)
    monkeypatch.setenv("FILLER_CPUS", "1-4")
    monkeypatch.setenv("FILLER_THREADS", "4")
    monkeypatch.setenv("FILLER_PORTS", "18072")
    class Response:
        status = 200
        def read(self, *args):
            return b'[{"is_processing": true}]'
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

    monkeypatch.setattr(driver.urllib.request, "urlopen", lambda *args, **kwargs: Response())
    children = []

    class Server:
        pid = 123
        def __init__(self, *args, **kwargs):
            command = args[0]
            assert command[command.index("-ngl") + 1] == ("24" if hybrid else "99")
            self.rc = None
            children.append(self)
        def poll(self):
            return self.rc
        def terminate(self):
            self.rc = -15
        def wait(self, **kwargs):
            return self.rc

    monkeypatch.setattr(driver.subprocess, "Popen", Server)
    monkeypatch.setattr(driver, "residency", lambda *args: {
        "pid": 123, "at": driver.time.time(), "vram_bytes": 100, "hip_library": "/approved/hip.so", "kfd": "/kfd/123"})
    calls = []
    interrupt_at = [1]

    def request(args, log, budget, timeout, observer, env, cwd):
        source = Path(args[args.index("--questions-in") + 1])
        q = json.loads(source.read_text())["suites"][driver.SUITE][0]
        calls.append(q["id"])
        if len(calls) == interrupt_at[0]:
            raise driver.Cutoff("interrupted fixture")
        observer()
        observer()
        path = Path(args[args.index("--per-question-out") + 1])
        path.write_text(json.dumps(capture(q, config)["record"]) + "\n")
        return 0

    monkeypatch.setattr(driver, "run_child", request)
    budget = driver.Budget(10, out.parent / "STOP", clock=lambda: 0)
    with pytest.raises(driver.Cutoff):
        driver.execute(config, budget, out)
    assert children[-1].poll() == -15 and not (out / "RESULT.json").exists()
    interrupt_at[0] = -1
    driver.execute(config, budget, out)
    assert json.loads((out / "RESULT.json").read_text())["n"] == 198
    assert len(calls) == 199 and len(children) == 2 and all(s.poll() == -15 for s in children)
    driver.execute(config, budget, out)
    assert len(children) == 2 and len(calls) == 199
