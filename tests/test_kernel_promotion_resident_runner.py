"""Lifecycle failures and the observation-only fallback contract."""

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
from dataclasses import dataclass
from types import SimpleNamespace

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/benchmark/kernel_promotion_resident_runner.py"
SPEC = importlib.util.spec_from_file_location("kernel_promotion_resident_runner", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def write_json(path, value):
    path.write_text(json.dumps(value))


def plan():
    return runner.resident_plan.build_plan([
        {
            "scenario": "frontdoor",
            "nominal_context": context,
            "request_body": {"prompt": "benchmark", "seed": 42, "cache_prompt": False,
                             "temperature": 0, "n_predict": 128},
        }
        for context in (2048, 4096)
    ])


class FakeRuntime:
    def __init__(self, failure=None):
        self.failure = failure
        self.events = []
        self.live = set()
        self.k35 = SimpleNamespace(
            write_json=write_json,
            scenario_by_name=lambda name: name,
            summarize_response=lambda scenario, context, limit, response, elapsed, floor: response,
        )

    def preflight(self, output):
        self.events.append(("preflight",))
        if self.failure == "claim":
            raise ValueError("invalid live claim")

    def start(self, cohort, arm, directory):
        self.events.append(("start", arm))
        if self.failure == "spawn" and arm == "candidate":
            raise OSError("candidate spawn failed")
        handle = SimpleNamespace(arm=arm, proc=SimpleNamespace(pid=len(self.events)))
        self.live.add(arm)
        return handle

    def ready(self, server, arm, directory):
        self.events.append(("ready", arm))
        assert server.arm == arm
        if self.failure == "health" and arm == "candidate":
            raise TimeoutError("candidate failed health")
        if self.failure == "register_and_terminate" and arm == "candidate":
            raise OSError("candidate PID registration failed")
        return {"pid": server.proc.pid}

    def sample(self, server):
        assert server.arm in self.live
        busy = self.failure == "idle_peer" and len(self.events) >= 8
        return {"cpu_s": float(len(self.events)) if busy else 0.0, "rss_bytes": 10}

    def affinity(self, server):
        assert server.arm in self.live
        return {server.proc.pid: [0]}

    def request(self, server, arm, body):
        assert self.live == {"production", "candidate"}
        assert server.arm == arm
        self.events.append(("request", arm, body))
        if self.failure == "request" and body["n_predict"] != 64:
            raise TimeoutError("measured request timed out")
        if self.failure == "short" and body["n_predict"] != 64:
            return {"completion_tokens": 1}
        return response_fixture(body["n_predict"])

    def stop(self, server):
        self.events.append(("stop", server.arm))
        if self.failure in {"terminate", "register_and_terminate"} and server.arm == "candidate":
            raise RuntimeError("cleanup witness failed")
        self.live.remove(server.arm)
        return {"pid": server.proc.pid, "dead": True,
                "port_closed": self.failure != "port_leak"}


def response_fixture(limit):
    return {
        "completion_tokens": limit,
        "content": "full output " * 25,
        "tokens": list(range(limit)),
        "timings": {"predicted_per_second": 100.0},
    }


class ValidityRuntime(FakeRuntime):
    def __init__(self, change, *, cleanup_failure=None):
        super().__init__(cleanup_failure)
        self.change = change
        self.fresh = False
        self.measured = 0

    def verify_fresh_ready(self):
        assert not self.live
        self.events.append(("fresh_guard",))
        self.fresh = True

    def request(self, server, arm, body):
        assert server.arm == arm
        assert self.live == ({arm} if self.fresh else set(runner.resident_plan.ARMS))
        self.events.append(("request", arm, body))
        limit = body["n_predict"]
        response = response_fixture(limit)
        if not self.fresh and limit != runner.resident_plan.WARMUP_TOKENS:
            self.change(response, arm, self.measured)
            self.measured += 1
        return response


def arm_pins():
    pin = {"binary_sha256": "a" * 64, "commit": "b" * 40, "libraries": {"libggml.so": "c" * 64}}
    return {"arms": {arm: pin.copy() for arm in runner.resident_plan.ARMS}}


def test_validated_plan_runs_sequential_loads_warmups_and_abba(tmp_path):
    schedule = plan()
    runtime = FakeRuntime()
    output = tmp_path / "capture"
    assert runner.execute_plan(schedule, output, runtime) == 0
    assert runtime.events[1:5] == [
        ("start", "production"), ("ready", "production"),
        ("start", "candidate"), ("ready", "candidate"),
    ]
    requests = [event for event in runtime.events if event[0] == "request"]
    for index, cohort in enumerate(schedule["cohorts"]):
        warmup_a, warmup_b, *requested = requests[index * 22:(index + 1) * 22]
        assert [warmup_a[1], warmup_b[1]] == ["production", "candidate"]
        assert warmup_a[2] == warmup_b[2] == cohort["request_body"] | {"n_predict": 64}
        assert [event[1] for event in requested] == [row["arm"] for row in cohort["requests"]]
        assert all(event[2] == cohort["request_body"] for event in requested)
        assert runner.read_json(output / f"cohort-{index:03}/warmup-production/row.json")["excluded"]
    report = runner.read_json(output / "capture.json")
    assert report["status"] == "observation_only"
    assert report["complete"] is True
    assert report["resident_validity"]["status"] == "pass"
    assert report["cohorts"][0]["validity"]["calibration_ratio_pass"] is None
    assert report["cohorts"][0]["validity"]["arm_order_bias"]["production"]["quartet_positions"] == [0, 3]
    assert report["cohorts"][1]["validity"]["arm_order_bias"]["production"]["quartet_positions"] == [1, 2]
    assert not runtime.live
    assert not (output / "fresh-fallback.json").exists()


@pytest.mark.parametrize(
    ("failure", "stopped", "cleanup_proved"),
    [
        ("claim", [], True), ("spawn", ["production"], True),
        ("health", ["candidate", "production"], True),
        ("request", ["candidate", "production"], True),
        ("short", ["candidate", "production"], True),
        ("idle_peer", ["candidate", "production"], True),
        ("terminate", ["candidate", "production"], False),
        ("register_and_terminate", ["candidate", "production"], False),
        ("port_leak", ["candidate", "production"], False),
    ],
)
def test_failure_cleans_captured_servers_and_reemits_plan(tmp_path, failure, stopped, cleanup_proved):
    schedule = plan()
    runtime = FakeRuntime(failure=failure)
    output = tmp_path / "capture"
    assert runner.execute_plan(schedule, output, runtime) == runner.FRESH_REQUIRED
    assert [event[1] for event in runtime.events if event[0] == "stop"] == stopped
    if cleanup_proved:
        assert not runtime.live
    fallback = runner.read_json(output / "fresh-fallback.json")
    assert fallback["lifecycle_mode"] == "fresh_server"
    assert fallback["status"] == "observation_only"
    assert fallback["plan"] == schedule
    assert fallback["cleanup_proved"] is cleanup_proved
    assert fallback["requires_fresh_execution"] is True
    assert fallback["resident_rows_valid"] is False
    report = runner.read_json(output / "capture.json")
    assert report["complete"] is False
    assert report["cleanup_proved"] is cleanup_proved
    assert len(report["cohorts"]) <= 1


def change_candidate_tps(response, arm, _, tps):
    if arm == "candidate":
        response["timings"]["predicted_per_second"] = tps


@pytest.mark.parametrize(
    ("defect", "failure", "field"),
    [
        ("content", "exact parity mismatch", "content"),
        ("token", "exact parity mismatch", "token_ids"),
        ("drift", "incumbent throughput drift", "calibration_ratio_pass"),
        ("order", "ABBA schedule-position bias", "order_effect_pass"),
        ("missing_timing", "invalid decode timing or ratio", "invalid_timing_positions"),
        ("infinite_timing", "invalid decode timing or ratio", "invalid_timing_positions"),
        ("zero_timing", "invalid decode timing or ratio", "invalid_timing_positions"),
    ],
)
def test_validity_failure_replays_unchanged_plan_after_cleanup(tmp_path, defect, failure, field):
    def change(response, arm, position):
        if defect == "content" and position == 1:
            response["content"] += "changed after K35 preview"
        elif defect == "token" and position == 1:
            response["tokens"][-1] += 1
        elif defect == "drift":
            change_candidate_tps(response, arm, position, 102.0)
        elif defect == "order" and position % 4 in (0, 1):
            response["timings"]["predicted_per_second"] = 103.0
        elif defect == "missing_timing" and position == 1:
            del response["timings"]
        elif defect == "infinite_timing" and position == 1:
            response["timings"]["predicted_per_second"] = float("inf")
        elif defect == "zero_timing" and position == 1:
            response["timings"]["predicted_per_second"] = 0

    schedule = plan()
    output = tmp_path / "capture"
    runtime = ValidityRuntime(change)
    assert runner.execute_plan(schedule, output, runtime, provenance=arm_pins()) == runner.FRESH_REQUIRED
    fresh_guard = runtime.events.index(("fresh_guard",))
    assert runtime.events[fresh_guard - 3:fresh_guard] == [
        ("stop", "candidate"), ("stop", "production"), ("preflight",),
    ]
    report = runner.read_json(output / "capture.json")
    assert report["resident_validity"]["status"] == "failed"
    assert report["cleanup_proved"] and not report["complete"]
    validity = report["cohorts"][0]["validity"]
    assert validity["violations"] == [failure]
    if defect in {"content", "token"}:
        assert validity["comparisons"][0][field] == "different"
        assert validity["parity"] == "different"
    elif defect in {"drift", "order"}:
        assert validity[field] is False
        if defect == "order":
            assert validity["calibration_ratio_pass"] is True
            assert validity["arm_order_bias"]["production"]["relative_effect"] == pytest.approx(0.03)
    else:
        assert validity["invalid_timing_positions"] == [1]
        assert validity["median_paired_ratio"] is None
        assert validity["comparisons"][0]["candidate_over_production"] is None
    fallback = runner.read_json(output / "fresh-fallback.json")
    assert fallback["plan"] == schedule == runner.read_json(output / "fresh-replay/plan.json")
    assert fallback["fresh_complete"] and not fallback["resident_rows_valid"]
    assert failure in fallback["reason"]


def test_validity_violation_with_unproved_cleanup_cannot_replay(tmp_path):
    runtime = ValidityRuntime(lambda response, arm, pos: change_candidate_tps(response, arm, pos, 102.0),
                              cleanup_failure="port_leak")
    output = tmp_path / "capture"
    assert runner.execute_plan(plan(), output, runtime, provenance=arm_pins()) == runner.FRESH_REQUIRED
    report = runner.read_json(output / "capture.json")
    assert report["cohorts"][0]["validity"]["violations"] == ["incumbent throughput drift"]
    assert not report["cleanup_proved"]
    assert ("fresh_guard",) not in runtime.events
    assert not (output / "fresh-replay").exists()


@pytest.mark.parametrize(("tps", "is_calibration"), [(99.0, True), (101.0, True), (140.0, False)])
def test_calibration_ratio_is_inclusive_and_requires_identical_runtime_images(tmp_path, tps, is_calibration):
    runtime = ValidityRuntime(lambda response, arm, pos: change_candidate_tps(response, arm, pos, tps))
    pins = arm_pins()
    if not is_calibration:
        pins["arms"]["candidate"]["libraries"] = {"libggml.so": "d" * 64}
    output = tmp_path / "capture"
    assert runner.execute_plan(plan(), output, runtime, provenance=pins) == 0
    report = runner.read_json(output / "capture.json")
    assert report["resident_validity"]["same_runtime_calibration"] is is_calibration
    for cohort in report["cohorts"]:
        validity = cohort["validity"]
        assert validity["calibration_ratio_pass"] is (True if is_calibration else None)
        assert validity["median_paired_ratio"] == pytest.approx(tps / 100)
        assert validity["median_by_arm"] == {"production": 100.0, "candidate": tps}
        assert validity["mad_by_arm"] == {"production": 0.0, "candidate": 0.0}
        assert validity["mad_paired_ratio"] == 0


def test_unsealed_calibration_requires_same_resolved_path_and_sha():
    production = {"path": "/pinned/llama-server", "sha256": "a" * 64}
    candidate = production.copy()
    pins = {"arms": {"production": production, "candidate": candidate}}
    assert runner.same_runtime_image(pins)
    candidate["path"] = "/other/llama-server"
    assert not runner.same_runtime_image(pins)


def test_missing_token_ids_preserve_diagnostic_capture(tmp_path):
    runtime = ValidityRuntime(lambda response, *_: response.pop("tokens"))
    output = tmp_path / "capture"
    assert runner.execute_plan(plan(), output, runtime, provenance=arm_pins()) == 0
    report = runner.read_json(output / "capture.json")
    assert report["complete"] and report["resident_validity"]["status"] == "incomplete"
    for cohort in report["cohorts"]:
        assert cohort["validity"]["parity"] == "incomplete"
        assert cohort["validity"]["comparisons"][0]["token_ids"] == "incomplete"
        assert cohort["validity"]["comparisons"][0]["content"] == "exact"
    assert not (output / "fresh-fallback.json").exists()


def test_mutated_plan_does_not_enter_preflight_or_create_capture(tmp_path):
    mutated = plan()
    mutated["cohorts"][0]["requests"][0]["arm"] = "candidate"
    runtime = FakeRuntime()
    output = tmp_path / "capture"
    with pytest.raises(ValueError, match="canonical resident schedule"):
        runner.execute_plan(mutated, output, runtime)
    assert not runtime.events
    assert not output.exists()


@pytest.mark.parametrize(
    ("exclusive", "check_rc", "topology_matches", "age", "expected"),
    [
        (True, 2, True, 46, None),
        (True, 2, False, 46, ValueError),
        (True, 2, True, 1, ValueError),
        (True, 3, True, 46, subprocess.CalledProcessError),
        (False, 2, True, 46, subprocess.CalledProcessError),
        (True, 0, True, 1, None),
    ],
)
def test_contention_admission_keeps_checker_and_requires_proven_age_only(
    tmp_path, monkeypatch, exclusive, check_rc, topology_matches, age, expected
):
    orchestrator = tmp_path / "orchestrator"
    matrix = orchestrator / "orchestration/contention_matrix.yaml"
    matrix.parent.mkdir(parents=True)
    recorded = "560d489bb6df16b9"
    matrix.write_text(f'topology_hash: "{recorded}"\n')
    os.utime(matrix, ns=(1_760_000_000_000_000_000,) * 2)
    monkeypatch.setattr(runner, "ORCHESTRATOR", orchestrator)
    runtime = runner.Runtime(SimpleNamespace(write_json=write_json),
                             SimpleNamespace(exclusive_self_calibration=exclusive))
    proof = {
        "recorded_topology_hash": recorded,
        # Same displayed 8-digit prefix, but the full fingerprint differs.
        "live_topology_hash": recorded if topology_matches else "560d489b12345678",
        "matrix_status": "stale", "max_age_days": 30, "age_days": age,
    }
    calls = []

    def run(argv, **kwargs):
        calls.append(argv)
        if len(calls) == 1:
            assert "--max-age-days" not in argv
            assert ("--matrix-path" in argv) is exclusive
            return subprocess.CompletedProcess(argv, check_rc, "", "official checker output\n")
        assert argv[1:4] == ["-I", "-c", runner.CONTENTION_TOPOLOGY_PROBE]
        assert Path(argv[-1]) == tmp_path / "contention-matrix.yaml"
        return subprocess.CompletedProcess(argv, 0, json.dumps(proof), "")

    monkeypatch.setattr(runner.subprocess, "run", run)
    if expected is None:
        runtime.check_contention_matrix(tmp_path)
    else:
        with pytest.raises(expected):
            runtime.check_contention_matrix(tmp_path)
    assert (tmp_path / "contention-matrix.txt").read_text() == "official checker output\n"
    if exclusive:
        captured = tmp_path / "contention-matrix.yaml"
        assert captured.read_bytes() == matrix.read_bytes()
        assert captured.stat().st_mtime_ns == matrix.stat().st_mtime_ns
    assert len(calls) == (2 if exclusive and check_rc == 2 else 1)
    witness = tmp_path / "contention-matrix-age-only.json"
    if exclusive and check_rc == 2 and expected is None:
        assert runner.read_json(witness) == proof
    else:
        assert not witness.exists()


def test_exclusive_self_calibration_requires_a_present_matrix(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "ORCHESTRATOR", tmp_path)
    runtime = runner.Runtime(None, SimpleNamespace(exclusive_self_calibration=True))
    with pytest.raises(FileNotFoundError, match="contention_matrix.yaml"):
        runtime.check_contention_matrix(tmp_path)
    assert not (tmp_path / "contention-matrix-age-only.json").exists()


def test_exclusive_self_calibration_checks_live_claim_before_matrix(tmp_path, monkeypatch):
    runtime = runner.Runtime(None, SimpleNamespace(exclusive_self_calibration=True, claim_open=tmp_path / "claim"))
    write_json(runtime.args.claim_open, {"schema": "region-lock-claim.v1", "phase": "open", "regions": ["q0"]})
    monkeypatch.setattr(runtime, "check_contention_matrix", lambda *_: pytest.fail("invalid claim reached matrix"))
    with pytest.raises(ValueError, match="live parent region-lock receipt"):
        runtime.preflight(tmp_path)


OCR_BLOCKER = {
    "pid": 3223248,
    "comm": "llama-server",
    "args": f"{runner.V10_CPU_BINARY} --alias lightonocr-2-1b -m "
            "/mnt/raid0/llm/models/LightOnOCR-2-1B-bbox-F16.gguf --port 9003 -t 24 --device none -ngl 0",
    "reason": "llama workload",
}


@pytest.mark.parametrize("blocker", [OCR_BLOCKER, {"error": "ps failed"}])
def test_exclusive_self_calibration_retains_competing_workload_refusal(tmp_path, monkeypatch, blocker):
    k35 = SimpleNamespace(write_json=write_json, collect_process_blockers=lambda: [blocker])
    args = SimpleNamespace(exclusive_self_calibration=True, claim_open=tmp_path / "claim", base_port=19360)
    runtime = runner.Runtime(k35, args)
    runtime.calibration_image = object()
    monkeypatch.delenv("FILLER_PORTS", raising=False)
    monkeypatch.setattr(runner.urllib.request, "getproxies", lambda: {})
    monkeypatch.setattr(runner, "verify_claim", lambda _: {"claim_id": "test"})
    monkeypatch.setattr(runtime, "timeout", lambda *_: 1)
    monkeypatch.setattr(runner, "verify_calibration_host", lambda: {"cpu_online": "0-191"})
    monkeypatch.setattr(runtime, "check_contention_matrix", lambda _: None)
    monkeypatch.setattr(runner.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("linkage ran with blockers"))
    with pytest.raises(RuntimeError, match="competing workloads"):
        runtime.preflight(tmp_path)
    assert runner.read_json(tmp_path / "process-blockers.json") == [blocker]


@pytest.mark.parametrize("blockers, code", [([OCR_BLOCKER], 75), ([], 0)])
def test_workload_quiet_check_runs_without_claim_or_model_launch(tmp_path, monkeypatch, blockers, code):
    k35 = SimpleNamespace(write_json=write_json, collect_process_blockers=lambda: blockers)
    monkeypatch.setattr(runner, "load_k35", lambda _: k35)
    monkeypatch.setattr(runner, "validate_inputs", lambda *_: None)
    monkeypatch.setattr(runner, "verify_claim", lambda *_: pytest.fail("workload check acquired a claim"))
    monkeypatch.setattr(runner, "execute_plan", lambda *_: pytest.fail("workload check entered inference"))
    input_path = tmp_path / "plan.json"
    write_json(input_path, {})
    output = tmp_path / "check"
    assert runner.main([
        "--plan", str(input_path), "--output", str(output), "--k35-sha256", "test",
        "--production-binary", "production", "--production-sha256", "test",
        "--candidate-binary", "candidate", "--candidate-sha256", "test",
        "--kv-mode", "split", "--check-workload-quiet",
    ]) == code
    report = output / "process-blockers.json"
    if blockers:
        assert runner.read_json(report) == blockers
    else:
        assert not report.exists()


@pytest.mark.parametrize("defect", ["mixed", "non-v10", "narrow-cpu", "gpu", "drafter"])
def test_exclusive_self_calibration_rejects_other_images_and_recipes(tmp_path, monkeypatch, defect):
    v10 = tmp_path / "v10/llama-server"
    alternate = tmp_path / "alternate/llama-server"
    for path in (v10, alternate):
        path.parent.mkdir()
        path.write_text("same executable bytes\n")
        path.chmod(0o755)
    digest = runner.sha256_file(v10)
    monkeypatch.setattr(runner, "V10_CPU_BINARY", v10)
    monkeypatch.setattr(runner, "V10_CPU_SHA256", digest)
    production = alternate if defect == "non-v10" else v10
    candidate = alternate if defect == "mixed" else production
    recipe = SimpleNamespace(
        name="frontdoor_cpu_no_spec", device="hip" if defect == "gpu" else "none", n_gpu_layers=0,
        spec_draft_device=None, spec_draft_ngl=None, spec_type="none", threads=96,
        draft_model=Path("/draft") if defect == "drafter" else None,
        cpu_affinity="0-23" if defect == "narrow-cpu" else "0-95",
    )
    args = SimpleNamespace(
        exclusive_self_calibration=True, production_binary=production, candidate_binary=candidate,
        production_sha256=digest, candidate_sha256=digest,
    )
    runtime = runner.Runtime(SimpleNamespace(scenario_by_name=lambda _: recipe), args)
    with pytest.raises(ValueError, match="pinned v10 CPU store image|full-host K35 frontdoor CPU no-spec|CPU-only"):
        runner.validate_inputs(plan(), args, runtime)


def test_pidfd_cleanup_leaves_unrelated_process_running(monkeypatch):
    unrelated = subprocess.Popen(["/usr/bin/sleep", "60"])
    proc, fd, birth = runner.owned.spawn(["/usr/bin/sleep", "60"], env=os.environ.copy())
    monkeypatch.setattr(runner, "port_listeners", lambda port: set())
    runtime = runner.Runtime(None, None)
    try:
        cleanup = runtime.stop(runner.Server(proc, fd, birth, 19100, {0}))
        assert cleanup["pid"] == proc.pid
        assert cleanup["dead"] and cleanup["port_closed"]
        assert unrelated.poll() is None
    finally:
        unrelated.terminate()
        unrelated.wait(timeout=5)


def test_port_ownership_matches_listener_inode():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        assert runner.owns_listener(os.getpid(), port)
    assert not runner.port_listeners(port)


@dataclass
class NarrowRecipe:
    cpu_affinity: str = "24-47"
    slot_save_path: str = "/production-slot-cache"


def test_command_preserves_explicit_narrow_k35_placement():
    scenario = NarrowRecipe()

    def argv(recipe, *, binary, **kwargs):
        assert recipe.slot_save_path is None
        return ["numactl", "--interleave=all", "--", "taskset", "-c", recipe.cpu_affinity, str(binary)]

    k35 = SimpleNamespace(scenario_by_name=lambda name: scenario, build_server_argv=argv)
    runtime = runner.Runtime(k35, SimpleNamespace(production_binary=Path("/sealed/llama-server"), kv_mode="split"))
    assert runtime.command(plan()["cohorts"][0], "production", 19100)[3:6] == ["taskset", "-c", "24-47"]
    scenario.cpu_affinity = "96-119"
    with pytest.raises(ValueError, match="exceeds"):
        runtime.command(plan()["cohorts"][0], "production", 19100)


@pytest.mark.parametrize("prospective", [False, True])
def test_post_request_image_failure_preserves_response(tmp_path, monkeypatch, prospective):
    args = SimpleNamespace(request_timeout=1, claim_open=tmp_path / "claim")
    response = {"content": "raw response", "tokens": [1]}
    k35 = SimpleNamespace(write_json=write_json, query_chat=lambda *args, **kwargs: response)
    runtime = runner.Runtime(k35, args)
    runtime.evidence = object()
    if prospective:
        runtime.observation_source = {}

    def verify_server(*_):
        if checks:
            raise ValueError("changed mapped inode")
        checks.append(True)

    checks = []
    claim = {"claim_id": "fixture", "provider_pid_starttime": 1}
    monkeypatch.setattr(runner, "verify_claim", lambda path: claim)
    monkeypatch.setattr(runner, "AFFINITY_SAMPLE_INTERVAL", 0.001)
    monkeypatch.setattr(runtime, "timeout", lambda *args: 1)
    monkeypatch.setattr(runtime, "verify_server", verify_server)
    sampled = runner.threading.Event()

    def affinity(_):
        sampled.set()
        return {"10": [0]}

    def query(*args, **kwargs):
        assert sampled.wait(1)
        runner.time.sleep(0.01)
        return response

    monkeypatch.setattr(runtime, "affinity", affinity)
    k35.query_chat = query
    raw = b'{ "content": "raw response", "tokens": [1] }\n'
    if prospective:
        class Reply:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def read(self):
                query()
                return raw

            def geturl(self):
                return "http://127.0.0.1:19100/completion"

        def urlopen(request, *, timeout):
            assert timeout == 1 and request.full_url == Reply().geturl()
            assert json.loads(request.data) == {"n_predict": 1}
            return Reply()

        monkeypatch.setattr(runner.urllib.request, "urlopen", urlopen)
    with pytest.raises(runner.CapturedResponseError, match="post-request image witness failed"):
        runner.request_with_capture(runtime, SimpleNamespace(port=19100), "production", {"n_predict": 1}, tmp_path)
    assert runner.read_json(tmp_path / "response.json") == response
    assert not (tmp_path / "row.json").exists()
    if prospective:
        assert (tmp_path / "response.http.json").read_bytes() == raw
        assert (tmp_path / "request.http.json").read_bytes() == b'{"n_predict": 1}'
        witness = runner.read_json(tmp_path / "request-affinity.json")
        assert witness["claim_id"] == claim["claim_id"]
        assert witness["http_status"] == 200
        assert witness["http_body_sha256"]["response"] == runner.hashlib.sha256(raw).hexdigest()
        assert witness["sample_offsets_s"]
