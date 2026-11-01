import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import entry_binding

spec=importlib.util.spec_from_file_location('candidate_run', Path(__file__).with_name('run.py'))
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Integrated(unittest.TestCase):
    def test_disabled_before_any_binding_or_execution(self):
        with patch.object(m,'CANDIDATE_EXECUTION_ENABLED',False), patch.object(entry_binding,'validate') as check:
            with self.assertRaisesRegex(SystemExit,'candidate disabled'): m.main()
            check.assert_not_called()

    def drive(self, dryrun, stop=False):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); cfg=root/'cfg.json'; cfg.write_text(json.dumps({'state':'REVIEWED_BINDING','request_sha256':'a'*64,'approved_builds':{}}))
            stopfile=root/'stop'
            if stop: stopfile.touch()
            env={'FILLER_ID':m.ROW_ID,'FILLER_CPUS':'0','FILLER_DEADLINE':'99999999999','FILLER_STOPFILE':str(stopfile),'FILLER_DRYRUN':str(int(dryrun))}
            calls=[]
            def fake_cell(image,arm,level,mode,deadline):
                calls.append((image,arm,level)); p=root/f'{image}-{arm}-{level}'/'complete.json'; p.parent.mkdir(); p.write_text(json.dumps({'status':'COMPLETE','image':image,'arm':arm,'level':level})); return 0
            with patch.dict(os.environ,env,clear=True), patch.object(m,'OUT_ROOT',root), patch.object(m,'CANDIDATE_EXECUTION_ENABLED',True), patch.object(m,'run_step',side_effect=fake_cell), patch.object(entry_binding,'validate',return_value={'status':'PASS_OFFLINE_BINDINGS_ONLY','recipe_sha256':'r'}), patch.object(sys,'argv',['run.py','--config',str(cfg)]):
                rc=m.main()
            return rc,calls,((root/'completed-cells.jsonl').read_text().splitlines() if (root/'completed-cells.jsonl').exists() else [])

    def test_dryrun_actual_main_writes_exactly_one_cell(self):
        rc,calls,rows=self.drive(True)
        self.assertEqual(rc,75); self.assertEqual(calls,[('E1','A0','low')]); self.assertEqual(len(rows),1)

    def test_run_step_stop_during_load_drains_captured_children(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); bindir=root/'bin'; bindir.mkdir(); (bindir/'llama-server').touch(); shim=root/'shim'; shim.touch(); kfd=root/'kfd'; kfd.mkdir(); stop=root/'stop'; stop.touch()
            class Proc:
                def __init__(self,pid): self.pid=pid; self.dead=False
                def poll(self): return 0 if self.dead else None
                def terminate(self): self.dead=True
                def wait(self,timeout=None): return 0
            procs=[Proc(321),Proc(322)]
            def check_output(args,**kwargs):
                return b'KVU16H_SHIM_LOG' if args[0]=='strings' else b''
            env={'FILLER_CPUS':'0','FILLER_STOPFILE':str(stop)}
            with patch.dict(os.environ,env,clear=True), patch.object(m,'OUT_ROOT',root/'out'), patch.object(m,'IMAGES',{'E1':bindir}), patch.object(m,'SHIM',shim), patch.object(m,'KFD',kfd), patch.object(m,'pin',return_value={}), patch.object(m,'health',return_value=False), patch.object(m.subprocess,'check_output',side_effect=check_output), patch.object(m.subprocess,'run'), patch.object(m.subprocess,'Popen',side_effect=procs):
                m.CHILDREN.clear()
                rc=m.run_step('E1','A0','low','full',99999999999)
                self.assertEqual(rc,75)
                self.assertTrue(all(p.dead for p in procs))
                self.assertEqual(json.loads((root/'out/E1-A0-low/partial.json').read_text())['reason'],'stop-during-load')
                m.CHILDREN.clear()

    def test_existing_stop_refuses_before_cell(self):
        rc,calls,rows=self.drive(True,True)
        self.assertEqual(rc,75); self.assertEqual(calls,[]); self.assertEqual(rows,[])

if __name__=='__main__': unittest.main()
