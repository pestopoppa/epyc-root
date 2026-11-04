import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import job

class FailureTests(unittest.TestCase):
    def test_failed_full_capture_is_persisted_without_derived_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'result.json'
            env=dict(FILLER_DRYRUN='0',FILLER_NEEDGPU='1',FILLER_DEADLINE=str(int(time.time())+500),FILLER_PIDFILE=str(root/'pids'),FILLER_STOPFILE=str(root/'stop'),FILLER_CPUS='184-191')
            def failed_phase(args):
                self.assertEqual(args.park_mode,'prefill')
                (job.ROOT/'a1.json').write_text(json.dumps({'status':'failed','rows':[],'variant_runs':[{'status':'failed'}]}))
                return 1
            with patch.dict(os.environ,env),patch.object(job,'D',root),patch.object(job.os,'sched_getaffinity',return_value=set(range(184,192))),patch.object(job.os,'sched_setaffinity'),patch.object(job.p,'phase_a1',side_effect=failed_phase),patch.object(job.p,'phase_report') as report,patch.object(job.p,'server_argv'):
                self.assertEqual(job.main(),1)
            capture=json.loads(out.read_text())
            self.assertEqual(capture['status'],'failed')
            self.assertEqual(capture['full_rc'],1)
            self.assertEqual(capture['native_units'],1)
            self.assertNotIn('derived_report',capture)
            report.assert_not_called()

if __name__=='__main__':unittest.main()
