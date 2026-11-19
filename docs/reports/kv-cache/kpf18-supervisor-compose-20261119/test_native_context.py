"""Real retained Ctx boundaries under private admission; never launch native work."""
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import install
import test_execution_admission as fixtures
from test_execution_admission import load


class NativeContext(unittest.TestCase):
    def test_actual_inputs_native_context_and_readonly_preflight(self):
        result = subprocess.run(
            [sys.executable, '-I', '-B', __file__, '--worker', 'publisher-smoke', 'preflight'],
            capture_output=True, text=True, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_installed_startup_interruptions(self):
        for mode in ('official', 'publisher-smoke'):
            for event in ('valid', 'linkage', 'prelaunch', 'health', 'healthy',
                          'readback', 'residency', 'provider'):
                with self.subTest(mode=mode, event=event):
                    result = subprocess.run(
                        [sys.executable, '-I', '-B', __file__, '--worker', mode, 'startup-' + event],
                        capture_output=True, text=True, timeout=45)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_installed_native_context_current_and_retained_refusals(self):
        for admission_mode in ('official', 'publisher-smoke'):
            for mutation in ('valid', 'stop', 'provider', 'grant', 'deadline',
                             'output', 'reserve', 'sticky', 'dead-child',
                             'sampler', 'budget', 'preempt'):
                with self.subTest(admission_mode=admission_mode, mutation=mutation):
                    result = subprocess.run(
                        [sys.executable, '-I', '-B', __file__, '--worker', admission_mode, mutation],
                        capture_output=True, text=True, timeout=45)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


def worker(admission_mode, mutation):
    actual_path = os.environ.get('PATH', os.defpath)
    fixture = (fixtures.PublisherSmokeAdmission() if admission_mode == 'publisher-smoke'
               else fixtures.ExecutionAdmission())
    fixture.setUp()
    try:
        output = fixture.result.parent if admission_mode == 'publisher-smoke' else fixture.root / 'output'
        output.mkdir(exist_ok=True)
        fixture.config['output_root'] = str(output)
        prepared = []
        if mutation == 'preflight':
            os.environ['PATH'] = actual_path
            from test_retained_r7 import PATHS
            from execution_binding import PROJECTION
            from test_execution_admission import sha
            retained = Path('/mnt/raid0/llm/tmp/codex-ni-20261027-kpf18-native-control-r15')
            canonical = retained / 'canonical-export-root'
            receipt = retained / 'out/PRELOAD-MODEL-IDENTITY.json'
            fixture.native = Path('/mnt/raid0/llm/kernels/builds/gpu-20261020-a1f0c8cf9/bin/llama-server')
            fixture.config['artifacts']['server'] = str(fixture.native)
            fixture.config.update(preload_receipt=str(receipt), enrollment=dict(
                framing_mode='retained-r7-v1', canonical_export=str(canonical),
                **{k: str(p) for k, p in PATHS.items()}))
            inputs = [fixture.native, receipt, install.RETAINED / 'ORIGINAL-MODELS.json',
                      *PATHS.values(), *(canonical / name for name in PROJECTION)]
            for option, name in (
                    ('--argv-file', '/mnt/raid0/llm/tmp/overnight-20261020/argv.8083-gate.txt'),
                    ('--prompt-set', '/mnt/raid0/llm/tmp/overnight-20261020/kpf18-run/prompt_set.jsonl')):
                inputs.append(Path(name))
                prepared.extend([option, name])
            fixture.seal['sources'].update({str(p): sha(p) for p in inputs})
        destination = fixture.root / 'installed'
        install.install(destination, binding_revision=install.REVISION,
                        guard_revision='current-guard-v3',
                        execution=dict(fixture.config, sources=fixture.seal['sources']))
        outer = load(destination / 'supervisor.py', 'native_context_outer')
        captured = {}
        class PrivateAdmission(ModuleType):
            def __getattribute__(self, name):
                if name == 'capture':
                    self.__dict__['FLAGS'] = fixture.flags
                    original = super().__getattribute__(name)
                    def capture(seal):
                        result = original(seal)
                        captured['provider'] = result[0]
                        return result
                    return capture
                return super().__getattribute__(name)
        class DriverControl(ModuleType):
            def __getattribute__(self, name):
                original = super().__getattribute__(name)
                if name != 'main': return original
                def main():
                    gate = self.gate
                    if mutation == 'preflight':
                        # Real retained metadata and live model stat checks;
                        # never hash/load the weights or invoke a model server.
                        self.guard.tests_and_enrollment()
                        self.load_preload_models(self.RETAINED_PRELOAD_RECEIPT,
                                                 self.BASE / 'ORIGINAL-MODELS.json')
                        original_build = gate.build_ctx
                        visited = []
                        def build(args, items):
                            ctx, probs, notes = original_build(args, items)
                            assert not probs, probs
                            assert type(ctx) is gate.Ctx
                            ctx.check_boundary()
                            visited.append(ctx)
                            return ctx, probs, notes
                        with patch.object(gate, 'build_ctx', side_effect=build), \
                             patch.object(gate.subprocess, 'Popen', side_effect=AssertionError('native launch forbidden')):
                            assert original() == 0
                        assert len(visited) == 1
                        assert not list(output.iterdir())
                        return 0
                    if mutation.startswith('startup-'):
                        event = mutation.removeprefix('startup-')
                        args = NS(out=str(output), card='/private/unread-card', budget_min=30,
                                  port=18486, vram_free_max_gib=1, vram_ceiling_gib=30,
                                  load_timeout_s=20)
                        ctx = gate.Ctx(args, None, [], [], {})
                        srv = object.__new__(gate.Server)
                        srv.ctx, srv.label = ctx, 'owned'
                        srv.binary, srv.log = Path('/inert/server'), output / 'logs/server.log'
                        srv.proc, srv.sampler, srv.env = None, None, {}
                        seen = []
                        def stop():
                            Path(fixture.config['stop_file']).touch()
                        def linkage():
                            seen.append('linkage')
                            if event == 'linkage': stop()
                            return {'pass': True}
                        def health():
                            seen.append('health')
                            if event in ('health', 'healthy'): stop()
                            if event == 'provider':
                                captured['provider'].recheck = lambda _: (_ for _ in ()).throw(ValueError('provider lost'))
                            return event != 'health'
                        def sleep(seconds):
                            seen.append(('sleep', seconds))
                            if event == 'prelaunch' and seconds == 2.0: stop()
                        def readback():
                            seen.append('readback')
                            if event == 'readback': stop()
                            return {'checked': True}
                        def residency():
                            seen.append('residency')
                            if event == 'residency': stop()
                        sampler = NS(abort=NS(is_set=lambda: False), stop=lambda: seen.append('sampler-stop'))
                        sampler.start = lambda: sampler
                        proc = NS(pid=123456, poll=lambda: None)
                        from contextlib import ExitStack
                        with ExitStack() as stack:
                            for obj, name, kwargs in (
                                (gate, 'CPU_MODE', {'new': False}),
                                (gate, 'port_listening', {'return_value': False}),
                                (gate, 'kfd_pids', {'return_value': {}}),
                                (gate, 'card_vram', {'return_value': (0, 1)}),
                                (gate, 'window_status', {'return_value': {}}),
                                (gate, 'Sampler', {'return_value': sampler}),
                                (gate, 'Client', {'return_value': NS(health=health)}),
                                (gate.threading, 'Thread', {'return_value': NS(start=lambda: None)}),
                                (gate.time, 'sleep', {'side_effect': sleep}),
                                (srv, 'run_linkage', {'side_effect': linkage}),
                                (srv, 'full_cmd', {'return_value': ['/inert/server']}),
                                (srv, 'read_back', {'side_effect': readback}),
                                (srv, 'check_residency', {'side_effect': residency}),
                            ):
                                stack.enter_context(patch.object(obj, name, **kwargs))
                            launch = stack.enter_context(patch.object(gate.subprocess, 'Popen', return_value=proc))
                            if event == 'valid':
                                srv.start()
                                assert srv.readback == {'checked': True}
                                assert ctx.client is not None
                            else:
                                with self_test.assertRaisesRegex(gate.Abort, 'provider lost' if event == 'provider' else 'STOP'):
                                    srv.start()
                            if event in ('linkage', 'prelaunch'):
                                launch.assert_not_called()
                                assert not ctx.own_children
                                assert 'health' not in seen
                                assert ('sampler-stop' in seen) == (event == 'prelaunch')
                            else:
                                launch.assert_called_once()
                                assert ctx.own_children == [srv], 'cleanup lost the captured server'
                                assert srv.sampler.own_pid == proc.pid
                            if event in ('health', 'healthy', 'provider'):
                                assert seen.count('health') == 1
                                assert 'readback' not in seen
                            if event != 'valid' and event != 'residency':
                                assert 'residency' not in seen
                            if event != 'valid':
                                Path(fixture.config['stop_file']).unlink(missing_ok=True)
                                with self_test.assertRaises(gate.Abort): ctx.check_boundary()
                        return 0
                    # Ctx is the actual constructor used by unmodified build_ctx.
                    args = NS(out=str(output), card='/private/unread-card', budget_min=30)
                    ctx = gate.Ctx(args, None, [], [], {})
                    ctx.check_boundary()
                    reason = {'stop': 'STOP', 'provider': 'provider lost',
                              'grant': 'grant changed', 'deadline': 'deadline',
                              'output': 'context output', 'reserve': 'reserve exhausted',
                              'sticky': 'STOP', 'dead-child': 'server owned died',
                              'sampler': 'VRAM: private sampler refusal',
                              'budget': 'time budget', 'preempt': 'preempt requested'}
                    if mutation == 'stop' or mutation == 'sticky':
                        Path(fixture.config['stop_file']).touch()
                    if mutation == 'provider':
                        captured['provider'].recheck = lambda _: (_ for _ in ()).throw(ValueError('provider lost'))
                    if mutation == 'grant': fixture.grant.write_text(fixture.grant.read_text() + ' cpus=184-187')
                    if mutation == 'deadline': fixture.gate.time.time.return_value = fixture.end - 90
                    if mutation == 'output': ctx.out = fixture.root / 'elsewhere'
                    if mutation in ('dead-child', 'sampler'):
                        ctx.own_children.append(NS(
                            label='owned', proc=NS(poll=lambda: 7, returncode=7),
                            sampler=(NS(abort=NS(is_set=lambda: True),
                                        abort_reason='private sampler refusal') if mutation == 'sampler' else None)))
                    if mutation == 'budget': ctx.t0 -= 31 * 60
                    with patch.object(self.guard.output_reserve, 'check',
                                      side_effect=RuntimeError('reserve exhausted') if mutation == 'reserve' else None), \
                         patch.object(gate, 'window_status', return_value=(
                             {'preempt_requested_at': 'private-preemption'} if mutation == 'preempt' else {})):
                        if mutation == 'valid': ctx.check_boundary()
                        else:
                            with self_test.assertRaisesRegex(gate.Abort, reason[mutation]): ctx.check_boundary()
                            if mutation == 'preempt': assert ctx.preempted
                            if mutation == 'sticky':
                                Path(fixture.config['stop_file']).unlink()
                                with self_test.assertRaisesRegex(gate.Abort, 'STOP'): ctx.check_boundary()
                    assert not list(output.iterdir()), 'boundary test wrote a native result'
                    return 0
                return main
        self_test = unittest.TestCase()
        original_module = outer.importlib.util.module_from_spec
        def module(spec):
            loaded = original_module(spec)
            if spec.name == '_execution_admission': loaded.__class__ = PrivateAdmission
            if spec.name == '_supervised_driver': loaded.__class__ = DriverControl
            return loaded
        sys.modules.pop('install', None)
        argv = ['driver.py', 'item3', '--out', str(output)]
        if mutation == 'preflight':
            argv.extend(['--dry-run', '--fork-bin', str(fixture.native), *prepared,
                         '--port', '18486', '--gpu-window-id', 'synthetic-row'])
        # The actual-input helper imports are preparation, never preloaded into
        # the isolated supervisor's sealed dependency namespace.
        sys.modules.pop('execution_binding', None)
        with patch.object(sys, 'argv', argv), \
             patch.object(outer.importlib.util, 'module_from_spec', side_effect=module):
            assert outer.run_driver() == 0
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--worker': worker(*sys.argv[2:])
    else: unittest.main()
