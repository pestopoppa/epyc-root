import copy
import importlib.util
import hashlib
import json
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "evalperf_endpoint", Path(__file__).resolve().parents[2]
    / "scripts/experiments/evalperf_endpoint.py"
)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
IDS = [f"HumanEval/{i}" for i in range(118)]


def native(profiled=30):
    tasks = {}
    for i, task_id in enumerate(IDS):
        has_score = i < profiled
        tasks[task_id] = {
            "pass@1": 100 if has_score else 0,
            "results": [{"pass": has_score, "profiled": has_score,
                         "dps": 50 if has_score else None,
                         "dps_norm": 40 if has_score else None,
                         "_num_cpu_instructions": 1234 if has_score else None}],
            "dps": 50 if has_score else None,
            "dps_norm": 40 if has_score else None,
            "n_profiled": 1 if has_score else None,
        }
    return {"n_samples": 1, "min_correct": 1, "max_profile": 1,
            "temperature": 1, "eval": tasks}


def summary(value):
    return runner.summarize(value, IDS, 1, 1, 1)


def test_failures_do_not_become_efficiency_sentinels():
    result = summary(native())
    assert result["correctness_rate"] == 30 / 118
    assert result["unknown_efficiency_tasks"] == 88
    assert result["conditional_harmonic_dps_norm"] == 40


def test_conditional_requires_30_profiled_tasks():
    assert summary(native(29))["conditional_harmonic_dps_norm"] is None


def test_zero_is_a_valid_native_score_for_correct_code():
    data = native()
    data["eval"][IDS[0]]["dps_norm"] = 0
    data["eval"][IDS[0]]["results"][0]["dps_norm"] = 0
    assert summary(data)["conditional_harmonic_dps_norm"] == 0


@pytest.mark.parametrize("mutation", [
    lambda d: d["eval"].pop(IDS[0]),
    lambda d: d["eval"][IDS[0]]["results"].clear(),
    lambda d: d["eval"][IDS[0]].update({"pass@1": 0}),
    lambda d: d["eval"][IDS[0]].update({"dps_norm": float("nan")}),
    lambda d: d["eval"][IDS[0]]["results"][0].update({"_num_cpu_instructions": 0}),
    lambda d: d["eval"][IDS[0]]["results"][0].pop("_num_cpu_instructions"),
    lambda d: d["eval"][IDS[0]].update({"dps_norm": None, "dps": None}),
    lambda d: d["eval"][IDS[0]].update({"n_profiled": 2}),
    lambda d: d["eval"][IDS[0]]["results"][0].update({"pass": 1}),
    lambda d: d.update({"n_samples": 100}),
    lambda d: d.update({"max_profile": 10}),
    lambda d: d["eval"][IDS[117]].update({"dps_norm": 0, "dps": 0}),
])
def test_incomplete_or_inconsistent_native_output_fails_closed(mutation):
    data = copy.deepcopy(native())
    mutation(data)
    with pytest.raises(ValueError):
        summary(data)


def test_task_manifest_is_an_exact_cohort():
    with pytest.raises(ValueError, match="118 unique"):
        runner.summarize(native(), IDS[:-1] + [IDS[0]], 1, 1, 1)


@pytest.mark.parametrize("mutation", [
    lambda t: t["results"][0].update({"profiled": 1}),
    lambda t: t["results"][0].pop("profiled"),
    lambda t: t.update({"n_profiled": True}),
    lambda t: t.update({"dps": 51}),
    lambda t: t.update({"dps_norm": 41}),
    lambda t: t["results"][0].update({"dps_norm": None}),
    lambda t: t["results"][0].update({"dps": float("nan")}),
])
def test_profile_flags_counts_and_aggregates_must_match_native_samples(mutation):
    data = native()
    mutation(data["eval"][IDS[0]])
    with pytest.raises(ValueError):
        summary(data)


@pytest.mark.parametrize("fields", [
    {"profiled": True}, {"dps": 0}, {"dps_norm": 0},
    {"_num_cpu_instructions": 1234},
])
def test_unscored_task_cannot_hide_profile_evidence(fields):
    data = native()
    data["eval"][IDS[-1]]["results"][0].update(fields)
    with pytest.raises(ValueError):
        summary(data)


def test_full_native_profile_bound_and_sample_means():
    data = native()
    data.update(n_samples=3, min_correct=1, max_profile=2)
    for task in data["eval"].values():
        sample = task["results"][0]
        task["results"] = [copy.deepcopy(sample) for _ in range(3)]
        if sample["pass"]:
            task["results"][1].update(dps=70, dps_norm=60)
            task["results"][2].update(profiled=False, dps=None, dps_norm=None,
                                      _num_cpu_instructions=None)
            task.update(n_profiled=2, dps=60, dps_norm=50)
    result = runner.summarize(data, IDS, 3, 1, 1)
    assert result["conditional_harmonic_dps_norm"] == 50
    task = data["eval"][IDS[0]]
    task["results"][1].update(profiled=False, dps=None, dps_norm=None,
                              _num_cpu_instructions=None)
    task.update(n_profiled=1, dps=50, dps_norm=40)
    with pytest.raises(ValueError, match="missing native profile evidence"):
        runner.summarize(data, IDS, 3, 1, 1)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    manifest = tmp_path / "tasks.json"
    manifest.write_text(json.dumps(IDS))
    config = {
        "source": str(tmp_path), "source_commit": "abc",
        "task_manifest": str(manifest),
        "task_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "python": "/prepared/venv/bin/python", "n_samples": 1, "min_correct": 1,
        "temperature": 1, "parallel": 1, "max_new_tokens": 2048, "arm_timeout_s": 600,
        "arms": [{"role": role, "model": role, "base_url": f"http://localhost/{role}/v1"}
                 for role in ("coder", "architect")],
    }
    monkeypatch.setattr(runner.subprocess, "check_output",
                        lambda argv, **kw: "abc\n" if "rev-parse" in argv else "")
    class Response:
        def __init__(self, role):
            self.role = role
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return json.dumps({"data": [{"id": self.role}]}).encode()
    monkeypatch.setattr(runner.urllib.request, "urlopen",
                        lambda req, **kw: Response(req.full_url.split("/")[3]))
    return config, tmp_path / "output"


def test_two_arm_runner_preserves_native_outputs_and_bounded_configuration(prepared, monkeypatch):
    config, output = prepared
    commands = []
    def invoke(argv, **kwargs):
        commands.append(argv)
        assert argv[:3] == ["timeout", "--kill-after=5s", "600"]
        assert argv[argv.index("--n-samples") + 1] == "1"
        assert argv[argv.index("--max-new-tokens") + 1] == "2048"
        assert argv[argv.index("--parallel") + 1] == "1"
        assert kwargs["env"]["PYTHONPATH"] == config["source"]
        root = Path(argv[argv.index("--root") + 1])
        (root / "model_evalperf_results.json").write_text(json.dumps(native()))
    monkeypatch.setattr(runner, "run_native", invoke)
    result = runner.run(config, output)
    assert len(commands) == 2
    assert result["status"] == "COMPLETE"
    assert set(result["arms"]) == {"coder", "architect"}
    assert len(result["arms"]["coder"]["native_sha256"]) == 64
    assert (output / "checkpoint.json").exists()


def test_wrong_endpoint_identity_stops_before_generation(prepared, monkeypatch):
    config, output = prepared
    config["arms"][0]["model"] = "wrong-model"
    def forbidden(*args, **kwargs):
        pytest.fail("generation must not start")
    monkeypatch.setattr(runner, "run_native", forbidden)
    with pytest.raises(ValueError, match="identity mismatch"):
        runner.run(config, output)
    assert not output.exists()


def test_native_nonzero_exit_is_reaped_and_fails_closed():
    import subprocess
    import sys

    with pytest.raises(subprocess.CalledProcessError) as exc:
        runner.run_native([sys.executable, "-c", "raise SystemExit(7)"])
    assert exc.value.returncode == 7


@pytest.mark.parametrize("sig_name", ["SIGTERM", "SIGINT"])
def test_native_cancellation_reaps_owned_child_and_restores_handlers(monkeypatch, sig_name):
    import os
    import signal
    import sys

    original = runner.subprocess.Popen
    children = []
    def capture(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(runner.subprocess, "Popen", capture)
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    # The native child signals its parent once running, then waits for cleanup.
    code = ("import os,signal; "
            f"os.kill(os.getppid(), signal.{sig_name}); signal.pause()")
    with pytest.raises(InterruptedError, match="cancelled by signal"):
        runner.run_native([sys.executable, "-c", code])
    assert children[0].returncode is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(children[0].pid, 0)
    assert all(signal.getsignal(sig) == handler for sig, handler in previous.items())


def test_signal_during_spawn_is_deferred_until_pid_is_captured(monkeypatch):
    import os
    import signal
    import sys

    original = runner.subprocess.Popen
    children = []
    def interrupted_spawn(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        os.kill(os.getpid(), signal.SIGTERM)
        return child
    monkeypatch.setattr(runner.subprocess, "Popen", interrupted_spawn)
    with pytest.raises(InterruptedError, match="cancelled by signal"):
        runner.run_native([sys.executable, "-c", "import signal; signal.pause()"])
    assert children[0].returncode is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(children[0].pid, 0)


def test_spawn_failure_restores_signal_state(monkeypatch):
    import signal

    handlers = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, set())
    def fail(*args, **kwargs):
        raise FileNotFoundError("missing native executable")
    monkeypatch.setattr(runner.subprocess, "Popen", fail)
    with pytest.raises(FileNotFoundError):
        runner.run_native(["missing"])
    assert signal.pthread_sigmask(signal.SIG_BLOCK, set()) == mask
    assert all(signal.getsignal(sig) == handler for sig, handler in handlers.items())


def test_cleanup_escalates_even_when_group_leader_has_exited(monkeypatch):
    import signal
    import subprocess

    class Child:
        pid = 123456789
        calls = 0
        def wait(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                return 0  # leader exited, but its worker can still exist
            if timeout is not None:
                raise subprocess.TimeoutExpired("native", timeout)
            return 0
    child = Child()
    signals = []
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *a, **kw: child)
    monkeypatch.setattr(runner.os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    runner.run_native(["native"])
    assert signals == [(child.pid, signal.SIGTERM), (child.pid, signal.SIGKILL)]
    assert child.calls == 3


def test_native_deadline_failure_propagates():
    import subprocess
    import sys

    with pytest.raises(subprocess.CalledProcessError) as exc:
        runner.run_native(["timeout", "--kill-after=0.1s", "0.05s", sys.executable,
                           "-c", "import signal; signal.pause()"])
    assert exc.value.returncode == 124


@pytest.mark.parametrize("failure", [InterruptedError("cancelled"), RuntimeError("native failed")])
def test_second_arm_failure_keeps_first_checkpoint_without_complete(prepared, monkeypatch, failure):
    config, output = prepared
    calls = []
    def invoke(argv, **kwargs):
        calls.append(argv)
        if len(calls) == 2:
            raise failure
        root = Path(argv[argv.index("--root") + 1])
        (root / "model_evalperf_results.json").write_text(json.dumps(native()))
    monkeypatch.setattr(runner, "run_native", invoke)
    with pytest.raises(type(failure)):
        runner.run(config, output)
    assert set(json.loads((output / "checkpoint.json").read_text())) == {"coder"}
    assert not (output / "RESULT.json").exists()
