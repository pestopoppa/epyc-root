import importlib.util
import sys
from unittest import mock
import unittest
from pathlib import Path

P = Path(__file__).with_name('producer.py')
sys.path.insert(0, str(P.parent))
SPEC = importlib.util.spec_from_file_location('kvu19a2_gpu_producer', P)
producer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(producer)


class ProducerControls(unittest.TestCase):
    def test_expected_bytes(self):
        self.assertEqual(producer.EXPECTED_BYTES, {78: 131072, 79: 8388608, 80: 65536})

    def test_stdout_requires_one_supported_record(self):
        text = 'case 78 hs=576/512 nh=1 nr2=16 kv=8192 nb=4 nseq=4 run=1024 free=1024 type=f16 bias=0 cap=0 hash=0123456789abcdef nan=0\n'
        self.assertIn('case 78', producer.validate_stdout(text, 78))
        for bad in ('case 78 unsupported\n', '', text + text, text.replace('hs=576/512', 'hs=576/576'), text + 'case 79 unsupported\n'):
            with self.assertRaises(producer.Refusal):
                producer.validate_stdout(bad, 78)

    def test_repeated_raw_hash_rule(self):
        self.assertEqual(producer.summarize_hashes(['a', 'b']), 'observed_mismatch')
        self.assertEqual(producer.summarize_hashes(['a'] * 5), 'no_mismatch_observed_in_five')
        self.assertEqual(producer.summarize_hashes(['a'] * 4), 'incomplete')

    def test_capture_assets_preserve_filed_inconclusive(self):
        import json
        assets = json.loads((P.parent / 'assets.json').read_text())
        self.assertEqual(assets['capture_build']['verdict'], 'inconclusive')
        self.assertTrue(assets['same_uid_mutation_caveat'])

    def test_child_cleanup_is_scoped_to_captured_group(self):
        class FakeProcess:
            pid = 99999999
            def poll(self): return None
            def wait(self, timeout=None): return 0
        proc = FakeProcess()
        with mock.patch.object(producer, 'birth_ticks', return_value=123), \
             mock.patch.object(producer, 'proc_group_members', return_value=[]), \
             mock.patch.object(producer.os, 'killpg') as killpg:
            record = producer.terminate_owned(proc, 123)
        killpg.assert_called_once_with(proc.pid, producer.signal.SIGTERM)
        self.assertEqual(record, {'pid': proc.pid, 'birth_ticks': 123, 'verified_dead': True})

    def test_actual_grant_selects_exact_four_from_intersection(self):
        actual=set(range(184,192))
        def get(pid): return actual.copy()
        def set_affinity(pid, value): actual.clear(); actual.update(value)
        with mock.patch.object(producer.os, 'sched_getaffinity', side_effect=get), mock.patch.object(producer.os,'sched_setaffinity',side_effect=set_affinity) as setter:
            result=producer.validate_cpu_grant('184-191', True)
            self.assertEqual(result['affinity'],[184,185,186,187])
            self.assertEqual(result['count'],4)
            setter.assert_called_once_with(0,{184,185,186,187})
            for value in ('', '184-186','0-3'):
                with self.assertRaises(producer.Refusal): producer.validate_cpu_grant(value, True)
        with mock.patch.object(producer.os,'sched_getaffinity',return_value={188,189,190,191}), mock.patch.object(producer.os,'sched_setaffinity'):
            self.assertEqual(producer.validate_cpu_grant('184-191',True)['affinity'],[188,189,190,191])
        with mock.patch.object(producer.os,'sched_getaffinity',return_value=set(range(184,192))):
            self.assertEqual(producer.validate_cpu_grant('184-191',False)['count'],8)
            with self.assertRaises(producer.Refusal): producer.validate_cpu_grant('184-187',False)

    def test_stop_deadline_refuse_before_launch(self):
        with self.assertRaises(producer.Refusal):
            producer.deadline_guard(Path(__file__), producer.time.time()+100)
        with self.assertRaises(producer.Refusal):
            producer.deadline_guard(Path('/does-not-exist-kvu-stop'), producer.time.time())

    def test_real_owned_process_cleanup_and_birth_refusal(self):
        import subprocess
        proc = subprocess.Popen(['/usr/bin/sleep','30'], start_new_session=True)
        birth = producer.birth_ticks(proc.pid)
        try:
            with self.assertRaises(producer.Refusal): producer.terminate_owned(proc, birth+1, timeout=.1)
            self.assertIsNone(proc.poll())
            self.assertTrue(producer.terminate_owned(proc, birth)['verified_dead'])
            self.assertIsNotNone(proc.poll())
        finally:
            if proc.poll() is None: producer.terminate_owned(proc, birth)

    def test_private_lock_rejects_mutated_catalog_source(self):
        import tempfile, shutil, json
        spec = importlib.util.spec_from_file_location('private_lock', P.parent/'lock_bootstrap.py')
        loader = importlib.util.module_from_spec(spec); spec.loader.exec_module(loader)
        self.assertEqual(len(loader.verified_sources(P.parent)), 6)
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            shutil.copy2(P.parent/'lock-catalog.json', temp/'lock-catalog.json')
            shutil.copytree(P.parent/'lock-source', temp/'lock-source')
            module = temp/'lock-source/region_lock_cli.py'
            module.write_text(module.read_text()+'\n# mutation\n')
            with self.assertRaises(ValueError): loader.verified_sources(temp)

    def test_offline_control_cannot_emit_qualifying_result(self):
        import tempfile, json
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'control.json'
            env = {'FILLER_ID':'handoff-kvu-kvu19a2-repeatability-20261104','FILLER_DRYRUN':'1', 'KVU_OFFLINE_CONTROL':'1','FILLER_DRYRUN_RESULT_PATH':str(out)}
            with mock.patch.dict(producer.os.environ, env, clear=True), mock.patch.object(producer,'OUT',Path(temp)), mock.patch.object(producer, 'one_run', side_effect=AssertionError('GPU forbidden')):
                self.assertEqual(producer.main(),1)
            self.assertFalse(out.exists())
            result=json.loads((Path(temp)/'OFFLINE-CONTROL.json').read_text())
            self.assertEqual(result['status'],'inconclusive')
            self.assertEqual(result['mode'],'offline_control')
            self.assertEqual(result['runs'],[])
            self.assertIn('not a qualifying',result['detail'])

    def test_custody_failure_is_inconclusive_without_gpu(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'refusal.json'
            env={'FILLER_ID':'handoff-kvu-kvu19a2-repeatability-20261104','FILLER_DRYRUN':'1','FILLER_DRYRUN_RESULT_PATH':str(out)}
            with mock.patch.dict(producer.os.environ,env,clear=True), mock.patch.object(producer,'OUT',Path(temp)), mock.patch.object(producer,'load_assets',side_effect=producer.Refusal('mutation detected')), mock.patch.object(producer,'one_run',side_effect=AssertionError('GPU forbidden')):
                self.assertEqual(producer.main(),1)
            self.assertFalse(out.exists())
            result=json.loads(next((Path(temp)/'smoke-runs').glob('attempt-*/RESULT.json')).read_text())
            self.assertEqual(result['status'],'inconclusive')
            self.assertEqual(result['runs'],[])
            self.assertIn('mutation detected',result['stop_reason'])

    def test_cpu_fixture_with_valid_stdout_and_raw_is_not_gpu_success(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            harness=root/'cpu-fixture'
            harness.write_text("#!/usr/bin/python3\nimport os\nfrom pathlib import Path\nprint('case 78 hs=576/512 nh=1 nr2=16 kv=8192 nb=4 nseq=4 run=1024 free=1024 type=f16 bias=0 cap=0 hash=0123456789abcdef nan=0')\nPath(os.environ['FA_DUMP_DIR'],'out_78.bin').write_bytes(bytes(131072))\n")
            harness.chmod(0o700)
            assets={'harness':str(harness),'harness_sha256':producer.sha256(harness),'arms':{'base':{'directory':str(root),'libraries':{}}}}
            case=json.loads(producer.CASES.read_text())['cases'][0]
            with mock.patch.dict(producer.os.environ,{'FILLER_PIDFILE':str(root/'engine.pids')}), mock.patch.object(producer,'read_kfd',return_value={'own_vram_b':0,'mapped_libraries':{}}):
                with self.assertRaisesRegex(producer.Refusal,'no contemporaneous'):
                    producer.one_run(assets,case,'base',1,{},root/'STOP',producer.time.time()+60,root)
            self.assertEqual((root/'run-base-case78-r01/raw/out_78.bin').stat().st_size,131072)
            pid,birth=(root/'engine.pids').read_text().split()
            self.assertGreater(int(pid),0);self.assertGreater(int(birth),0)
            self.assertFalse(Path('/proc',pid).exists())

    def test_failed_smoke_retries_preserve_attempts_and_no_native_target(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'requested.json'
            env={'FILLER_ID':'handoff-kvu-kvu19a2-repeatability-20261104','FILLER_DRYRUN':'1','FILLER_DRYRUN_RESULT_PATH':str(out),'FILLER_CPUS':'184-191','FILLER_NEEDGPU':'1','FILLER_PIDFILE':str(root/'engine.pids'),'FILLER_STOPFILE':str(root/'STOP'),'FILLER_DEADLINE':str(producer.time.time()+60)}
            with mock.patch.dict(producer.os.environ,env,clear=True), mock.patch.object(producer,'OUT',root), mock.patch.object(producer,'load_assets',return_value={}), mock.patch.object(producer,'validate_cpu_grant',return_value={'count':4}), mock.patch.object(producer.device_identity,'discover',return_value={}), mock.patch.object(producer,'check_linkage',return_value={}), mock.patch.object(producer,'one_run',side_effect=producer.Refusal('no live GPU evidence')) as child:
                self.assertEqual(producer.main(),1)
                self.assertEqual(producer.main(),1)
            self.assertFalse(out.exists())
            attempts=list((root/'smoke-runs').glob('attempt-*/RESULT.json'))
            self.assertEqual(len(attempts),2)
            self.assertEqual(child.call_count,2)
            self.assertTrue(all(json.loads(p.read_text())['status']=='inconclusive' for p in attempts))

    def test_completion_rejects_failed_or_control_modes(self):
        import tempfile,json
        spec=importlib.util.spec_from_file_location('completion',P.parent/'complete.py')
        completion=importlib.util.module_from_spec(spec);spec.loader.exec_module(completion)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'result.json'
            for mode,status,expected in [('qualification','inconclusive',False),('offline_control','qualified_gpu_smoke',False),('qualification','completed_sample',False),('full','inconclusive',False),('qualification','qualified_gpu_smoke',True),('full','completed_sample',True),('full','observed_mismatch',True)]:
                path.write_text(json.dumps({'row_id':completion.ROW_ID,'mode':mode,'status':status}))
                self.assertEqual(completion.complete(path,'qualification' if mode!='full' else 'full'),expected)

    def test_full_inconclusive_returns75_and_does_not_complete(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            env={'FILLER_ID':'handoff-kvu-kvu19a2-repeatability-20261104','FILLER_DRYRUN':'0'}
            with mock.patch.dict(producer.os.environ,env,clear=True), mock.patch.object(producer,'OUT',root), mock.patch.object(producer,'load_assets',side_effect=producer.Refusal('bad custody')):
                self.assertEqual(producer.main(),75)
            self.assertEqual(json.loads((root/'RESULT.json').read_text())['status'],'inconclusive')

    def test_gpu_grant_and_registry_are_mandatory(self):
        import tempfile,json
        for extra in ({},{'FILLER_NEEDGPU':'1'}):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                env={'FILLER_ID':'handoff-kvu-kvu19a2-repeatability-20261104','FILLER_DRYRUN':'1','FILLER_DRYRUN_RESULT_PATH':str(root/'requested.json'),**extra}
                with mock.patch.dict(producer.os.environ,env,clear=True), mock.patch.object(producer,'OUT',root), mock.patch.object(producer,'load_assets',return_value={}), mock.patch.object(producer.device_identity,'discover',side_effect=AssertionError('GPU forbidden')):
                    self.assertEqual(producer.main(),1)
                self.assertFalse((root/'requested.json').exists())
                result=json.loads(next((root/'smoke-runs').glob('attempt-*/RESULT.json')).read_text())
                self.assertIn('required',result['stop_reason'])

    def test_atomic_result_publication_interruption_and_no_replace(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);target=root/'result.json'
            with mock.patch.object(producer.os,'link',side_effect=KeyboardInterrupt('before publication')):
                with self.assertRaises(KeyboardInterrupt): producer.write_result(target,{'status':'partial'})
            self.assertFalse(target.exists())
            self.assertEqual(list(root.iterdir()),[])
            producer.write_result(target,{'status':'original'})
            original=target.read_bytes()
            with self.assertRaises(FileExistsError): producer.write_result(target,{'status':'replacement'})
            self.assertEqual(target.read_bytes(),original)
            self.assertEqual(list(root.iterdir()),[target])

    def test_parent_death_signal_is_declared(self):
        source = P.read_text()
        self.assertIn('libc.prctl(1, signal.SIGKILL', source)


if __name__ == '__main__':
    unittest.main()
