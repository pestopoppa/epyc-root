"""Exercise the sealed driver's real main body with model-free collaborators."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE = Path('/mnt/raid0/llm/tmp/kvu/g3-gpu-integrated-20261105/candidate/driver.py')
PIN = '36f6c4af601d97e8606a8f93ae269adc159e19fedba7d22b8b4a09e1057af77b'

class DriverIntegration(unittest.TestCase):
    def setUp(self):
        raw=SOURCE.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=PIN:
            raise ValueError('integrated driver source drift')
        main=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='main')
        self.tmp=tempfile.TemporaryDirectory(dir='/mnt/raid0/llm/tmp/kvu')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.events=[]
        self.gate=types.SimpleNamespace(PROD_ENV={},ITEMS={},
            parse_argv_file=lambda _: (['-m','target','-md','draft'],None),
            flag_val=lambda argv,names:argv[argv.index(names[0])+1],
            main=lambda:self.events.append(('gate',list(sys.argv))) or 19)
        self.guard=types.SimpleNamespace(sources=lambda:self.events.append('sources'),
            boundary=lambda:self.events.append('boundary'),
            tests_and_enrollment=lambda:self.events.append('enrollment'))
        self.witness=types.ModuleType('gpu_witness')
        self.witness.install=lambda gate:self.events.append(('install',gate,list(sys.argv)))
        self.model={'path':'target','sha256':'a'}
        self.draft={'path':'draft','sha256':'b'}
        (self.root/'ORIGINAL-MODELS.json').write_text(json.dumps({'target':self.model,'drafter':self.draft}))
        self.env={'sys':sys,'os':__import__('os'),'json':json,'Path':Path,'BASE':self.root,
                  'OUT':self.root,'gate':self.gate,'guard':self.guard,
                  'item3':object(),'item3_smoke':object(),
                  'metadata':lambda p:self.model.copy() if str(p)=='target' else self.draft.copy(),
                  'draft_shape':lambda _: 'fake-shape',
                  'unchanged_models':lambda:self.events.append('model_identity')}
        exec(compile(ast.Module(body=[main],type_ignores=[]),str(SOURCE),'exec'),self.env)

    def invoke(self,args):
        with patch.object(sys,'argv',['driver.py',*args]), patch.dict(sys.modules,{'gpu_witness':self.witness}):
            return self.env['main']()

    def test_normal_entry_installs_after_guards_and_preserves_arguments(self):
        self.assertEqual(self.invoke(['--window-id','w']),19)
        self.assertEqual(self.events[:4],['sources','boundary','enrollment','model_identity'])
        install=self.events[-2]; gate=self.events[-1]
        self.assertEqual(install[0],'install')
        self.assertIs(install[1],self.gate)
        self.assertEqual(install[2][1:],['--window-id','w'])
        self.assertEqual(gate,('gate',install[2]))
        self.assertEqual(self.gate.PROD_ENV['LLAMA_KV_CACHE_DEBUG'],'3')
        self.assertIs(self.gate.ITEMS[3],self.env['item3'])

    def test_failed_install_never_calls_gate(self):
        def refuse(_): raise ValueError('GPU witness refused')
        self.witness.install=refuse
        with self.assertRaisesRegex(ValueError,'GPU witness refused'):
            self.invoke(['--dry-run'])
        self.assertFalse(any(isinstance(x,tuple) and x[0]=='gate' for x in self.events))

    def test_guard_refusal_precedes_install(self):
        def refuse(): raise ValueError('bad source')
        self.guard.sources=refuse
        with self.assertRaisesRegex(ValueError,'bad source'):
            self.invoke(['--dry-run'])
        self.assertEqual(self.events,[])

if __name__=='__main__': unittest.main()
