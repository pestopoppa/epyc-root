"""Model-free fixtures: no grant, provider lock or model is acquired."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import prepare
import publisher_smoke as smoke


class PublisherSmoke(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvfork',prefix='g3-smoke-fixture-')
        self.base=Path(self.temp.name)
        self.env={'FILLER_SMOKE':'1','FILLER_DRYRUN':'1','FILLER_CPUS':'184-187',
                  'FILLER_THREADS':'4','FILLER_NEEDGPU':'1','FILLER_STOPFILE':str(self.base/'STOP'),
                  'FILLER_END':'1000','FILLER_DEADLINE':'910'}
        self.stack=[]
        for manager in (patch.dict(os.environ,self.env,clear=True),patch.object(smoke.os,'sched_getaffinity',return_value={184,185,186,187}),patch.object(smoke.time,'time',return_value=800)):
            manager.start();self.stack.append(manager)
        self.addCleanup(self.temp.cleanup)
        for manager in self.stack:self.addCleanup(manager.stop)

    def test_exact_four_and_engine_identity(self):
        self.assertEqual(smoke.context(self.base),({184,185,186,187},910))
        for key,value in [('FILLER_CPUS','184-185'),('FILLER_CPUS','184-187,185'),('FILLER_CPUS','188-191'),('FILLER_CPUS','189-192'),('FILLER_THREADS','2'),('FILLER_NEEDGPU','0'),('FILLER_SMOKE','0'),('FILLER_DRYRUN','0'),('FILLER_STOPFILE',str(self.base/'elsewhere')),('FILLER_DEADLINE','911'),('FILLER_DEADLINE','799')]:
            with self.subTest(key=key,value=value),patch.dict(os.environ,{key:value}):
                with self.assertRaises(ValueError):smoke.context(self.base)

    def test_stop_and_dangling_stop(self):
        for name in ('STOP','STOP-smoke'):
            target=self.base/name
            target.symlink_to(self.base/'absent')
            with self.assertRaisesRegex(ValueError,'STOP'):smoke.context(self.base)
            target.unlink()

    def test_integrated_admission_retains_resources_and_provider(self):
        # Execute only generated admission module, with synthetic scheduler files.
        out=self.base/'prepared';prepare.prepare(out)
        runtime=out/'candidate'
        witness=types.ModuleType('lock_witness')
        witness.capture_gpu=lambda:(1,{'owner':1})
        witness.verify_gpu=lambda *args:True
        spec=importlib.util.spec_from_file_location('admission_fixture',runtime/'gpu_smoke_admission.py')
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'lock_witness':witness,'publisher_smoke':smoke}):spec.loader.exec_module(module)
        flags=self.base/'flags';(flags/'grants').mkdir(parents=True)
        (flags/'FILLERS.md').write_text('')
        module.FLAGS=flags
        with patch.dict(os.environ,{'FILLER_STOPFILE':str(runtime/'STOP')}),patch.object(module.shutil,'disk_usage',return_value=types.SimpleNamespace(free=214*1024**3)),patch.object(module.Path,'read_text',autospec=True) as read:
            def text(path,*args,**kwargs):
                if str(path)=='/proc/meminfo':return 'MemAvailable: 400000000 kB\n'
                if path==flags/'FILLERS.md':return ''
                return self.records[str(path)]
            self.records={};read.side_effect=text
            self.assertTrue(module.check(admit_ram=True))
            for cpu in (186,187):
                grant=flags/'grants'/'other.grant';grant.touch()
                self.records[str(grant)]=f'regions={cpu} start=1970-01-01T00:00:00Z end=1970-01-01T00:16:40Z'
                with self.assertRaisesRegex(RuntimeError,'overlaps actual smoke CPUs'):module.check()
                grant.unlink()
            with patch.object(module.shutil,'disk_usage',return_value=types.SimpleNamespace(free=214*1024**3-1)):
                with self.assertRaisesRegex(RuntimeError,'disk floor'):module.check()
            with patch.object(module.Path,'read_text',return_value='MemAvailable: 1 kB\n'):
                with self.assertRaisesRegex(RuntimeError,'memory'):module.check(admit_ram=True)
            # A later grant inside the inherited deadline must also conflict.
            with patch.object(smoke.time,'time',return_value=100):
                grant=flags/'grants'/'future.grant';grant.touch()
                self.records[str(grant)]='regions=187 start=1970-01-01T00:10:00Z end=1970-01-01T00:16:40Z'
                with self.assertRaisesRegex(RuntimeError,'overlaps actual smoke CPUs'):module.check()
                grant.unlink()
            (flags/'HOLD_test').touch()
            with self.assertRaisesRegex(RuntimeError,'HOLD'):module.check()
            (flags/'HOLD_test').unlink()
            witness.verify_gpu=lambda *args:(_ for _ in ()).throw(ValueError('writer lost'))
            with self.assertRaisesRegex(ValueError,'writer lost'):module.check()
        supervisor=(runtime/'supervisor.py').read_text()
        self.assertIn('publisher_smoke.context(D)',supervisor)
        self.assertNotIn("FILLER_ID='kpf18-g3-diagnostic-smoke'",supervisor)
        self.assertNotIn("else '184-185'",supervisor)
        self.assertEqual(__import__('subprocess').run(['bash',str(out/'launch.sh')],capture_output=True).returncode,78)


if __name__=='__main__':unittest.main()
