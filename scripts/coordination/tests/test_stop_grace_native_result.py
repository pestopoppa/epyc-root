"""Isolated proof that stop-grace PASS reports the selected native dry-run result."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

COORD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(COORD / 'rowflow'))
sys.path.insert(0, str(COORD / 'tests'))
import rowflow as rf
from test_rowflow import Fixture


def test_stop_grace_pass_counts_isolated_native_result_not_production_result():
    fx = Fixture()
    try:
        rid = 'stop-grace-native-result-isolation'
        job_dir = fx.job(rid)
        production = Path(job_dir) / 'LAST-RESULT.json'
        production.write_text(json.dumps([{'old': i} for i in range(23)]) + '\n')
        spec = fx.spec(rid, job_dir, result_path=str(production), result_format='json',
                       regions='0-95', shape_override='operator: fixture 2026-11-05: whole-host dry-run fixture', min_window_s=300, dryrun_timeout_s=60,
                       dryrun_native_result=True, dryrun_whole_host=True,
                       admission_class='diagnostic')
        rf.publish(spec, fx.flags)

        class NeverExits:
            pid = 424242
            def poll(self): return None
            def wait(self, timeout=None): return 0

        class Clock:
            now = 1000.0
            def sleep(self, seconds): self.now += seconds
            def time(self): return self.now

        clock = Clock()
        launched = {}

        def launch(_argv, cwd, env, stdout, stderr, start_new_session):
            selected = Path(env['FILLER_DRYRUN_RESULT_PATH'])
            selected.write_text('{"native":"one unit","value":1}\n')
            launched['path'] = selected
            return NeverExits()

        with patch.object(rf, 'status', return_value={'state': 'needs-dryrun'}), \
             patch.object(rf, 'rl_status', return_value={r: ('free', '') for r in rf.REGIONS}), \
             patch.object(rf, 'open_grants', return_value=[]), \
             patch.object(rf, 'lock_waits', return_value=[]), \
             patch.object(rf, 'cpu_sample', return_value={}), \
             patch.object(rf, 'row_orphans', return_value=[]), \
             patch.object(rf, 'kill_group') as kill_group, \
             patch.object(rf.subprocess, 'Popen', side_effect=launch), \
             patch.object(rf.time, 'time', side_effect=clock.time), \
             patch.object(rf.time, 'sleep', side_effect=clock.sleep), \
             patch.object(rf, 'STOP_GRACE_S', 10):
            verdict, reason = rf.dryrun_run(fx.flags, rid, '0-95')

        assert verdict == 'PASS', reason
        assert 'job did not stop within 10s' in reason
        assert reason.startswith('first progress: new record in ' + str(launched['path'])), reason
        assert launched['path'] != production
        assert rf.count_units(str(launched['path']), 'json') == 1
        assert rf.count_units(str(production), 'json') == 23
        assert json.loads(Path(rf.pass_path(fx.flags, rid)).read_text())['units'] == 1
        assert production.exists() and rf.count_units(str(production), 'json') == 23
        kill_group.assert_called_once_with(424242)
        assert list(Path(fx.flags, 'grants').glob(rid + '.grant')) == []
    finally:
        fx.cleanup()
