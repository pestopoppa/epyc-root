import json
import tempfile
import unittest
from pathlib import Path
from keeper_job import coordinate, coordinate_admitted

class TestCoordinator(unittest.TestCase):
    def test_partial_persists_and_does_not_claim_campaign_completion(self):
        with tempfile.TemporaryDirectory() as d:
            c=dict(command=['unused'],env={},base_url='http://127.0.0.1:1',plan_path='plan',
              fixture_root='fixtures',output_dir='ledger',arm='J',budget_s=2,minimum_cell_s=1,
              request_timeout_s=1,log_path='log',stop_file=None,granted_cpus='0',result_path=str(Path(d)/'RESULT.json'))
            seen=[]
            rc=coordinate(c,lambda **kw: seen.append(kw) or 75,
                          lambda plan,ledger: {'state':'incomplete','task_complete':False})
            r=json.loads(Path(c['result_path']).read_text())
            self.assertEqual((rc,r['segment_rc'],r['campaign']['task_complete']),(75,75,False))
            self.assertEqual(seen[0]['arm'],'J')
    def test_aggregate_failure_writes_no_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            c=dict(command=['unused'],env={},base_url='http://127.0.0.1:1',plan_path='p',
              fixture_root='f',output_dir='o',arm='Y',budget_s=2,minimum_cell_s=1,
              request_timeout_s=1,log_path='l',stop_file=None,granted_cpus='0',result_path=str(Path(d)/'RESULT.json'))
            def fail(*args): raise ValueError('broken ledger')
            with self.assertRaises(ValueError): coordinate(c,lambda **kw: 0,fail)
            self.assertFalse(Path(c['result_path']).exists())

class TestAdmittedCoordinator(unittest.TestCase):
    def test_refuses_short_grant_before_lifecycle_and_binds_dry_result(self):
        with tempfile.TemporaryDirectory() as d:
            result = str(Path(d) / 'normal.json')
            c=dict(command=['unused'],env={},base_url='http://127.0.0.1:1',plan_path='p',
              fixture_root='f',output_dir='o',arm='Y',budget_s=2,minimum_cell_s=100,
              request_timeout_s=1,log_path='l',stop_file=None,granted_cpus='1',result_path=result)
            env={'FILLER_END':'2000','FILLER_DEADLINE':'1900','FILLER_CPUS':'0-95',
                 'FILLER_STOPFILE':str(Path(d)/'stop'), 'FILLER_DRYRUN':'1',
                 'FILLER_DRYRUN_DIR':d,'FILLER_DRYRUN_RESULT_PATH':str(Path(d)/'dry.json')}
            seen=[]
            with self.assertRaises(ValueError):
                coordinate_admitted(c, env, 1890, lambda **kw: seen.append(kw),
                    lambda *args: {}, startup_s=10, cleanup_s=10)
            self.assertEqual(seen, [])
            rc=coordinate_admitted(c, env, 1000, lambda **kw: seen.append(kw) or 75,
                lambda *args: {'state':'incomplete','task_complete':False}, startup_s=10, cleanup_s=10)
            self.assertEqual(rc, 75)
            self.assertEqual(seen[0]['budget_s'], 900)
            self.assertEqual(seen[0]['granted_cpus'], '0-95')
            self.assertTrue(Path(d,'dry.json').exists())
            self.assertFalse(Path(result).exists())

if __name__ == '__main__': unittest.main()
