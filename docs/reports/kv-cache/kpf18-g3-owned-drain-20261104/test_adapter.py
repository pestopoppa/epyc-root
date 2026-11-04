#!/usr/bin/env python3
"""Injected-fake tests; no subprocesses, OS signals, or process scans are used."""
import importlib.util
import hashlib
import json
import types
from functools import partial
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
CANDIDATE = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/g3-qualification/candidate')
for relative, expected in {
    'owned_drain.py': '6cf1d4159ee768b762ba76f911cab16b675a4b115b1fff34cf6c3e35aa461ec4',
    'controller.py': '8ec6701726c61aa0e279bdd4e8f7f7f37633e4751d0359a95334036d36e7ea27',
    'research/scripts/benchmark/kpf18/kpf18_gate.py': 'a3a357fee44a712982247e3d4c0544b4d140c08f75530519c2d3910c97ef8c0a',
}.items():
    assert hashlib.sha256((CANDIDATE / relative).read_bytes()).hexdigest() == expected
sys.path.insert(0, str(HERE))
from adapter import may_start_unit, rowflow_entry
from driver_boundary import EntryRefused, run_with_rowflow_boundary
from model_identity_receipt import verify_precomputed

spec = importlib.util.spec_from_file_location('candidate_owned_drain', CANDIDATE / 'owned_drain.py')
owned_drain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owned_drain)


class StopDeadlineTests(unittest.TestCase):
    def test_stop_file_blocks_next_unit(self):
        with tempfile.TemporaryDirectory() as td:
            stop = Path(td) / 'STOP'
            self.assertTrue(may_start_unit(stop, 50, now=49))
            stop.touch()
            self.assertFalse(may_start_unit(stop, 50, now=49))

    def test_deadline_is_strict(self):
        with tempfile.TemporaryDirectory() as td:
            stop = Path(td) / 'STOP'
            self.assertTrue(may_start_unit(stop, 50, now=49.999))
            self.assertFalse(may_start_unit(stop, 50, now=50))
            self.assertFalse(may_start_unit(stop, 50, now=51))

    def test_rowflow_exported_contract_allows_only_before_deadline(self):
        with tempfile.TemporaryDirectory() as td:
            env = {"FILLER_END": "100", "FILLER_DEADLINE": "90",
                   "FILLER_STOPFILE": str(Path(td) / "STOP")}
            self.assertEqual(rowflow_entry(env, now=89), (True, "allowed"))
            self.assertEqual(rowflow_entry(env, now=90), (False, "deadline"))

    def test_rowflow_contract_missing_or_malformed_fails_closed(self):
        self.assertEqual(rowflow_entry({}, now=1), (False, "missing-or-invalid-rowflow-contract"))
        with tempfile.TemporaryDirectory() as td:
            env = {"FILLER_END": "100", "FILLER_DEADLINE": "100",
                   "FILLER_STOPFILE": str(Path(td) / "STOP")}
            self.assertEqual(rowflow_entry(env, now=1), (False, "invalid-rowflow-window"))

    def test_rowflow_relative_stop_path_fails_closed(self):
        env = {"FILLER_END":"100", "FILLER_DEADLINE":"90", "FILLER_STOPFILE":"STOP"}
        self.assertEqual(rowflow_entry(env, now=1), (False, "invalid-stop-path"))

    def test_broken_stop_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            stop = Path(td) / "STOP"
            stop.symlink_to(Path(td) / "missing")
            env = {"FILLER_END": "100", "FILLER_DEADLINE": "90", "FILLER_STOPFILE": str(stop)}
            self.assertEqual(rowflow_entry(env, now=1), (False, "invalid-stop-path"))

    def test_rowflow_stop_blocks_next_unit(self):
        with tempfile.TemporaryDirectory() as td:
            stop = Path(td) / "STOP"
            env = {"FILLER_END": "100", "FILLER_DEADLINE": "90", "FILLER_STOPFILE": str(stop)}
            stop.touch()
            self.assertEqual(rowflow_entry(env, now=1), (False, "stop-file"))


class FakeDrain:
    """Replace every process-facing primitive used by owned_drain.drain."""
    def __init__(self, finish_after_term=True, uid=1000):
        self.pid = 424242
        self.uid = uid
        self.finish_after_term = finish_after_term
        self.children_live = True
        self.signals = []
        self.waits = 0
        self.clock = 1.0

    def children(self):
        return [self.pid] if self.children_live else []

    def pidfd_open(self, pid):
        assert pid == self.pid
        return 73

    def pidfd_send_signal(self, fd, sig):
        assert fd == 73
        self.signals.append((fd, sig))
        if sig == owned_drain.signal.SIGKILL:
            self.children_live = False

    def waitpid(self, pid, flags):
        assert (pid, flags) == (self.pid, owned_drain.os.WNOHANG)
        self.waits += 1
        if self.finish_after_term and self.signals and self.waits == 1:
            self.children_live = False
            return (pid, 0)
        if not self.children_live:
            return (pid, 0)
        return (0, 0)

    def close(self, fd):
        assert fd == 73

    def monotonic(self):
        self.clock += 0.1
        return self.clock

    def sleep(self, _duration):
        pass


def fake_path_class(uid):
    class FakePath:
        def __init__(self, value): self.value = str(value)
        def __truediv__(self, other): return FakePath(self.value.rstrip('/') + '/' + str(other))
        def stat(self):
            class Stat: st_uid = uid
            return Stat()
    return FakePath


def run_with_fakes(fake):
    with patch.object(owned_drain, 'children', fake.children), \
         patch.object(owned_drain.os, 'pidfd_open', fake.pidfd_open), \
         patch.object(owned_drain.os, 'getuid', return_value=1000), \
         patch.object(owned_drain.signal, 'pidfd_send_signal', fake.pidfd_send_signal), \
         patch.object(owned_drain.os, 'waitpid', fake.waitpid), \
         patch.object(owned_drain.os, 'close', fake.close), \
         patch.object(owned_drain.time, 'monotonic', fake.monotonic), \
         patch.object(owned_drain.time, 'sleep', fake.sleep), \
         patch.object(owned_drain, 'Path', fake_path_class(fake.uid)):
        owned_drain.drain()


class OwnedDrainIntegrationTests(unittest.TestCase):
    def test_term_reaps_only_the_adopted_owned_pid(self):
        fake = FakeDrain(finish_after_term=True)
        run_with_fakes(fake)
        self.assertEqual(fake.signals, [(73, owned_drain.signal.SIGTERM)])
        self.assertFalse(fake.children_live)

    def test_kill_escalation_targets_same_adopted_pidfd(self):
        fake = FakeDrain(finish_after_term=False)
        run_with_fakes(fake)
        self.assertEqual(fake.signals, [
            (73, owned_drain.signal.SIGTERM),
            (73, owned_drain.signal.SIGKILL),
        ])
        self.assertFalse(fake.children_live)

    def test_foreign_adopted_child_is_never_signalled(self):
        fake = FakeDrain(finish_after_term=True, uid=2000)
        with self.assertRaisesRegex(RuntimeError, 'foreign adopted child'):
            run_with_fakes(fake)
        self.assertEqual(fake.signals, [])


class DriverBoundaryTests(unittest.TestCase):
    def make_context(self):
        class Context:
            def __init__(self): self.checks = 0
            def check_boundary(self): self.checks += 1
        return Context()

    @staticmethod
    def fake_trial_driver(ctx, units):
        completed = []
        for work in units:
            ctx.check_boundary()  # same boundary used by candidate controller.run
            work()
            completed.append(work.__name__)
        return completed

    def test_real_driver_boundary_checks_each_trial_and_runs_fake_work(self):
        ctx = self.make_context()
        now = iter([10, 11])
        work = [lambda: None, lambda: None]
        result = run_with_rowflow_boundary(self.fake_trial_driver, ctx, work,
            env={"FILLER_END":"30", "FILLER_DEADLINE":"20", "FILLER_STOPFILE":"/missing/STOP"},
            now_fn=lambda: next(now))
        self.assertEqual(result, ["<lambda>", "<lambda>"])
        self.assertEqual(ctx.checks, 2)

    def test_stop_between_trials_refuses_and_defers_drain_to_finalizer(self):
        with tempfile.TemporaryDirectory() as td:
            stop = Path(td) / "STOP"
            calls, drains = [], []
            def first_work():
                calls.append("first")
                stop.touch()
            def second_work(): calls.append("second")
            ctx = self.make_context()
            env = {"FILLER_END":"30", "FILLER_DEADLINE":"20", "FILLER_STOPFILE":str(stop)}
            with self.assertRaisesRegex(EntryRefused, "stop-file"):
                run_with_rowflow_boundary(self.fake_trial_driver, ctx, [first_work, second_work],
                    env=env, now_fn=lambda: 10)
            self.assertEqual(calls, ["first"])
            self.assertEqual(drains, [])
            self.assertEqual(ctx.checks, 1)
            # Candidate lifecycle order: record refusal, stop server, publish
            # partial evidence, then supervisor-owned finalizer drains.
            drains.extend(["stop", "publish", "owned-drain"])
            self.assertEqual(drains, ["stop", "publish", "owned-drain"])

    def test_deadline_between_trials_refuses_without_early_drain(self):
        calls, drains = [], []
        times = iter([19, 20])
        units = [lambda: calls.append("first"), lambda: calls.append("second")]
        ctx = self.make_context()
        env = {"FILLER_END":"30", "FILLER_DEADLINE":"20", "FILLER_STOPFILE":"/missing/STOP"}
        with self.assertRaisesRegex(EntryRefused, "deadline"):
            run_with_rowflow_boundary(self.fake_trial_driver, ctx, units, env=env,
                now_fn=lambda: next(times))
        self.assertEqual(calls, ["first"])
        self.assertEqual(drains, [])
        self.assertEqual(ctx.checks, 1)

    def test_terminal_wrapper_failure_bypasses_inner_generic_retry_and_keeps_finally(self):
        events = []
        class GuardContext:
            def check_boundary(self): raise ValueError("guard STOP")
        def attempt_driver(ctx):
            try:
                try: ctx.check_boundary()
                except Exception: events.append("ordinary-attempt-retry")
            finally:
                events.append("attempt-finally-ledger")
        with self.assertRaisesRegex(EntryRefused, "underlying guard refusal: ValueError: guard STOP"):
            run_with_rowflow_boundary(attempt_driver, GuardContext(),
                env={"FILLER_END":"30", "FILLER_DEADLINE":"20", "FILLER_STOPFILE":"/missing/STOP"},
                now_fn=lambda:10)
        self.assertEqual(events, ["attempt-finally-ledger"])

    def test_actual_candidate_controller_run_refuses_before_unit_then_stop_publish_drain(self):
        """Run actual controller.run through actual gate.main with fake server/work."""
        candidate_dir = CANDIDATE
        modules = {}
        def stub_module(name, **attrs):
            mod = types.ModuleType(name)
            for key, value in attrs.items(): setattr(mod, key, value)
            modules[name] = mod
            return mod
        stub_module("ledger", Ledger=object, file_sha=lambda *_: "")
        stub_module("normalize_bridge", Observation=object)
        stub_module("native_response", response=lambda *_: {}, verify_raw_frames=lambda *_: None)
        stub_module("cancel_seed_transport", SeedControl=object, prefix_hash=lambda *_: "")
        stub_module("cancel_seed_admission", emitted_generated_tokens=lambda *_: [], nofork_continuation=lambda **_: None)
        stub_module("native_group3", ORDER=["X1"], N=256, T=32000)
        stub_module("pipeline", raw_rows=lambda *_: b"")
        old_modules = {name: sys.modules.get(name) for name in modules}
        sys.modules.update(modules)
        spec = importlib.util.spec_from_file_location("candidate_controller_boundary", candidate_dir / "controller.py")
        controller = importlib.util.module_from_spec(spec)
        events = []
        try:
            spec.loader.exec_module(controller)
            class Gate:
                @staticmethod
                def G(_ctx, _index):
                    return {"T":32000, "trunk":[0]*32000, "src_tail":[0]*512,
                            "suffixes":[[], [], [1]*4000], "filler":[0]*32000}
            class Context:
                def check_boundary(self): events.append("underlying-check")
            ctx = Context()
            env = {"FILLER_END":"30", "FILLER_DEADLINE":"20", "FILLER_STOPFILE":"/tmp/nonexistent-g3-stop"}
            gate_path = candidate_dir / "research/scripts/benchmark/kpf18/kpf18_gate.py"
            gate_spec = importlib.util.spec_from_file_location("candidate_gate_boundary", gate_path)
            gate_module = importlib.util.module_from_spec(gate_spec)
            prior_gate_module = sys.modules.get(gate_spec.name)
            sys.modules[gate_spec.name] = gate_module
            try: gate_spec.loader.exec_module(gate_module)
            except BaseException:
                sys.modules.pop(gate_spec.name, None)
                raise
            record = {"diagnostic_error": None}
            ledger = types.SimpleNamespace(json=lambda name, value: events.append("refusal-artifact:" + name))
            class FakeRun:
                run_id = "fake-run"
                extra = {}
                srv = None
                def finish(self): events.append("run-finish")
            fake_run = FakeRun()
            class FakeServer:
                label = "fake-server"
                def stop(self):
                    events.append("server-stop")
                    if self in ctx.own_children: ctx.own_children.remove(self)
            fake_server = FakeServer()
            fake_server.ctx = ctx
            fake_run.srv = fake_server
            ctx = types.SimpleNamespace(open_runs=[fake_run], own_children=[], preempted=False)
            def start():
                events.append("server-start")
                ctx.own_children.append(fake_server)
            def cell():
                try:
                    run_with_rowflow_boundary(partial(controller.run, Gate()), ctx, None, None, record, {}, object(),
                        env=env, now_fn=lambda:20)
                except EntryRefused as error:
                    # Candidate integration must put this typed branch before
                    # its existing `except Exception` and abort the gate.
                    record["diagnostic_error"] = type(error).__name__ + ": " + str(error)
                    ledger.json("DIAGNOSTIC-REFUSAL.json", record["diagnostic_error"])
                    raise gate_module.Abort(str(error))
                except Exception as error:
                    record["diagnostic_error"] = type(error).__name__ + ": " + str(error)
                    ledger.json("DIAGNOSTIC-REFUSAL.json", record["diagnostic_error"])
            def publish(): events.append("publish")
            original = {name:getattr(gate_module,name) for name in ("build_ctx","ITEMS","print_plan","write_json")}
            original_signal = gate_module.signal.signal
            original_argv = sys.argv
            try:
                gate_module.build_ctx = lambda _args, _items: (ctx, [], [])
                gate_module.ITEMS = {3:lambda _ctx:[gate_module.Step("fake server launch",0,start),
                    gate_module.Step("candidate controller cell",0,cell), gate_module.stop_step(fake_server),
                    gate_module.Step("candidate publish",0,publish)]}
                gate_module.print_plan = lambda *_: None
                gate_module.write_json = lambda *_: None
                gate_module.signal.signal = lambda *_: None
                with tempfile.TemporaryDirectory() as td:
                    sys.argv = ["kpf18_gate.py","item3","--argv-file","injected","--out",str(Path(td)/"out"),
                                "--no-device-claim","fake-only"]
                    rc = gate_module.main()
            finally:
                sys.argv = original_argv
                gate_module.signal.signal = original_signal
                for name, value in original.items(): setattr(gate_module,name,value)
                if prior_gate_module is None: sys.modules.pop(gate_spec.name, None)
                else: sys.modules[gate_spec.name] = prior_gate_module
            events.append("supervisor-owned-drain")
            self.assertEqual(rc, 3)
            self.assertEqual(record["diagnostic_error"], "EntryRefused: deadline")
            self.assertEqual(events, ["server-start", "refusal-artifact:DIAGNOSTIC-REFUSAL.json", "server-stop",
                "run-finish", "supervisor-owned-drain"])
            self.assertTrue(fake_run.extra["partial"])
            self.assertNotIn("publish", events)
        finally:
            for name, previous in old_modules.items():
                if previous is None: sys.modules.pop(name, None)
                else: sys.modules[name] = previous


class PrecomputedIdentityReceiptTests(unittest.TestCase):
    def fixture(self, td):
        root = Path(td)
        target = root / "target.fixture"
        drafter = root / "drafter.fixture"
        target.write_bytes(b"test fixture marker")
        drafter.write_bytes(b"test fixture marker")
        def identity(path):
            st = path.stat()
            return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]
        pinned = {"target":{"path":str(target),"sha256":"t"},
                  "drafter":{"path":str(drafter),"sha256":"d"}}
        receipt = {"target":{**pinned["target"],"stat_identity":identity(target),"metadata":{}},
                   "drafter":{**pinned["drafter"],"stat_identity":identity(drafter),"metadata":{
                       "general.architecture":"dflash","dflash.block_count":5,
                       "dflash.attention.sliding_window":2048,
                       "dflash.attention.sliding_window_pattern":[True]*5}}}
        pinned_path, receipt_path = root/"ORIGINAL-MODELS.json", root/"PRELOAD-MODEL-IDENTITY.json"
        pinned_path.write_text(json.dumps(pinned, sort_keys=True))
        receipt_path.write_text(json.dumps(receipt, sort_keys=True))
        digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        return pinned_path, receipt_path, digest(pinned_path), digest(receipt_path)

    def test_receipt_uses_fake_stat_and_returns_precomputed_draft_shape(self):
        with tempfile.TemporaryDirectory() as td:
            pp, rp, pd, rd = self.fixture(td)
            value = verify_precomputed(rp, pp, receipt_sha256=rd, pinned_models_sha256=pd)
            self.assertEqual(value["draft_cache_shape"]["draft_swa_layers"], 5)

    def test_receipt_refuses_stat_drift_without_reading_model_content(self):
        with tempfile.TemporaryDirectory() as td:
            pp, rp, pd, rd = self.fixture(td)
            def wrong_stat(_path):
                class FakeStat:
                    st_dev, st_ino, st_size, st_mtime_ns, st_ctime_ns = (1, 2, 3, 4, 5)
                return FakeStat()
            with self.assertRaisesRegex(ValueError, "stat identity drift"):
                verify_precomputed(rp, pp, receipt_sha256=rd, pinned_models_sha256=pd, stat_fn=wrong_stat)

    def test_receipt_refuses_unpinned_small_receipt_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            pp, rp, pd, _rd = self.fixture(td)
            with self.assertRaisesRegex(ValueError, "receipt digest mismatch"):
                verify_precomputed(rp, pp, receipt_sha256="0"*64, pinned_models_sha256=pd)


if __name__ == '__main__':
    unittest.main()
