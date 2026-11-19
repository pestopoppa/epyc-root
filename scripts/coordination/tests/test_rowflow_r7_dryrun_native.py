import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'rowflow'))
sys.path.insert(0,str(HERE))
import rowflow as rf
import publish_row
from test_rowflow import Fixture

class DryrunNativeResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.fx=Fixture()
    @classmethod
    def tearDownClass(cls): cls.fx.cleanup()

    def test_each_dryrun_counts_only_unique_native_file_and_preserves_production(self):
        fx=self.fx; rid='w5s-dryrun-native-isolation'
        d=fx.job(rid)
        production=Path(d)/'LAST-RESULT.json'
        production.write_text('{"production":"keep"}\n')
        spec=fx.spec(rid,d,result_path=str(production),result_format='json',regions='0-95',shape_override='operator: fixture 2026-11-05: whole-host dry-run fixture',
                     min_window_s=300,dryrun_timeout_s=60,dryrun_native_result=True,
                     dryrun_whole_host=True,admission_class='diagnostic')
        row=rf.publish(spec,fx.flags)
        self.assertTrue(row['dryrun_native_result'])

        class Done:
            pid=424242
            def poll(self): return 0
            def wait(self,timeout=None): return 0

        def launch(_argv, cwd, env, stdout, stderr, start_new_session):
            result=Path(env['FILLER_DRYRUN_RESULT_PATH'])
            launched.append(result)
            result.write_text('{"schema":"native-test","value":1}\n')
            Path(env['FILLER_DRYRUN_DIR'],'ended').write_text('rc=0 complete\n')
            return Done()

        attempts=[]; launched=[]
        for _ in range(2):
            with patch.object(rf,'status',return_value={'state':'needs-dryrun'}), \
                 patch.object(rf,'rl_status',return_value={r:('free','') for r in rf.REGIONS}), \
                 patch.object(rf,'open_grants',return_value=[]), \
                 patch.object(rf,'row_orphans',return_value=[]), \
                 patch.object(rf,'cpu_sample',return_value={}), \
                 patch.object(rf.subprocess,'Popen',side_effect=launch), \
                 patch.object(rf.time,'sleep',return_value=None):
                verdict, message=rf.dryrun_run(fx.flags,rid,'0-95')
            self.assertEqual(verdict,'PASS',message)
            result_paths=list((Path(fx.flags)/'dryrun'/rid/'native-attempts').glob('attempt-*/native-result.json'))
            self.assertEqual(len(result_paths),len(attempts)+1)
            attempt_result=launched[-1]
            attempts.append(attempt_result)
            self.assertTrue(attempt_result.exists())
            self.assertEqual(rf.count_units(str(attempt_result),'json'),1)
        self.assertNotEqual(attempts[0].parent,attempts[1].parent)
        self.assertEqual(production.read_text(),'{"production":"keep"}\n')
        self.assertEqual(list(Path(fx.flags,'grants').glob(rid+'.grant')),[])

    def test_repair_round_trip_preserves_optional_native_result_flag(self):
        fx=self.fx;rid='w5s-repair-native-result';d=fx.job(rid)
        spec=fx.spec(rid,d,result_path=str(Path(d)/'LAST-RESULT.json'),result_format='json',
                     dryrun_native_result=True,dryrun_whole_host=True)
        row=rf.publish(spec,fx.flags)
        row.pop('lane')
        Path(rf.ready_path(fx.flags,rid)).write_text(json.dumps(row)+'\n')
        failure=Path(rf.dry_dir(fx.flags,rid));failure.mkdir(parents=True,exist_ok=True)
        (failure/'FAIL-1.json').write_text(json.dumps({'reason':'spec.lane missing'})+'\n')
        rc,message=publish_row.repair(rid,fx.flags)
        self.assertEqual(rc,0,message)
        repaired=rf.load_json(rf.ready_path(fx.flags,rid))
        self.assertTrue(repaired['dryrun_native_result'])

    def test_native_output_root_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);dry=root/'dryrun';dry.mkdir();outside=root/'outside';outside.mkdir()
            (dry/'native-attempts').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(rf.Refused):rf.new_dryrun_native_result_path(str(dry))

    def test_false_flag_preserves_legacy_result_contract(self):
        fx=self.fx;rid='w5s-dryrun-native-optional';d=fx.job(rid)
        row=rf.publish(fx.spec(rid,d),fx.flags)
        self.assertNotIn('dryrun_native_result',row)

if __name__=='__main__': unittest.main()
